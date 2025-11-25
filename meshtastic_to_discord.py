#!/usr/bin/env python3
"""Listen to Meshtastic device and send messages to Discord."""

import sys
import base64
import asyncio
import hashlib
import os
from pubsub import pub

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    print("python-dotenv is required. Install with: pip install python-dotenv", file=sys.stderr)
    sys.exit(1)

try:
    import meshtastic
    import meshtastic.serial_interface
    from meshtastic.protobuf import mesh_pb2, portnums_pb2
except ModuleNotFoundError:
    print("meshtastic is required. Install with: pip install meshtastic", file=sys.stderr)
    sys.exit(1)

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
except ModuleNotFoundError:
    print("cryptography is required. Install with: pip install cryptography", file=sys.stderr)
    sys.exit(1)

try:
    import discord
except ModuleNotFoundError:
    print("discord.py is required. Install with: pip install discord.py", file=sys.stderr)
    sys.exit(1)

# Load environment variables
load_dotenv()

# Discord configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_SERVER_ID = int(os.getenv("DISCORD_SERVER_ID"))

# Channel mapping: Meshtastic channel index -> Discord channel ID
DISCORD_CHANNEL_MAP = {
    0: int(os.getenv("DISCORD_CHANNEL_LONGFAST")),  # PRIMARY (LongFast)
    1: int(os.getenv("DISCORD_CHANNEL_MICHIGAN")),  # Michigan
    2: int(os.getenv("DISCORD_CHANNEL_SUMAT")),  # Sumat
    3: int(os.getenv("DISCORD_CHANNEL_FARMINGTON")),  # Farmington
    4: int(os.getenv("DISCORD_CHANNEL_WMI")),  # WMI
    5: int(os.getenv("DISCORD_CHANNEL_EMI")),  # EMI
    6: int(os.getenv("DISCORD_CHANNEL_MUSKEGON")),  # Muskegon
    7: int(os.getenv("DISCORD_CHANNEL_UMICHMESH")),  # umichmesh
}

# Device configuration
SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")

# Channel configuration with PSKs
CHANNELS = {
    0: {"name": "PRIMARY", "psk": "AQ=="},
    1: {"name": "Michigan", "psk": "MA=="},
    2: {"name": "Sumat", "psk": "Sg=="},
    3: {"name": "Farmington", "psk": "MA=="},
    4: {"name": "WMI", "psk": "MA=="},
    5: {"name": "EMI", "psk": "MA=="},
    6: {"name": "Muskegon", "psk": "MA=="},
    7: {"name": "umichmesh", "psk": "TFwwsCxHbkqPH5gZJ5pvM/V7QFgLwrI6Ry5YubCQQAE="},
}

# Node ID to name mapping (will be populated as we see nodes)
node_names = {}

# Discord client and channels
discord_client = None
discord_channels = {}  # Maps channel index to Discord channel object
message_queue = asyncio.Queue()


def decrypt_message(packet, psk):
    """Decrypt an encrypted meshtastic packet with the given PSK."""
    try:
        # Decode the PSK
        key_bytes = base64.b64decode(psk.encode('ascii'))
        
        # Expand AQ== (default key) to full 128-bit key
        if psk == "AQ==":
            key_bytes = b'\x01' + b'\x00' * 15
        # Expand simple PSKs to 128-bit by padding with zeros
        elif len(key_bytes) < 16:
            key_bytes = key_bytes + b'\x00' * (16 - len(key_bytes))

        # Build the nonce from packet ID and sender
        nonce_packet_id = getattr(packet, "id").to_bytes(8, "little")
        nonce_from_node = getattr(packet, "from").to_bytes(8, "little")
        nonce = nonce_packet_id + nonce_from_node

        # Decrypt the encrypted payload
        cipher = Cipher(algorithms.AES(key_bytes), modes.CTR(nonce), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_bytes = decryptor.update(getattr(packet, "encrypted")) + decryptor.finalize()

        # Parse the decrypted bytes into a Data object
        data = mesh_pb2.Data()
        data.ParseFromString(decrypted_bytes)
        return data
    
    except Exception as e:
        return None


def get_node_name(node_id, interface=None):
    """Get the name of a node by its ID."""
    if node_id in node_names:
        return node_names[node_id]
    
    # Try to get from node database
    if interface:
        try:
            # Access the nodesByNum dictionary directly
            if hasattr(interface, 'nodesByNum') and node_id in interface.nodesByNum:
                node_info = interface.nodesByNum[node_id]
                if 'user' in node_info and 'longName' in node_info['user']:
                    name = node_info['user']['longName']
                    if name and name.strip():
                        node_names[node_id] = name
                        return name
                elif 'user' in node_info and 'shortName' in node_info['user']:
                    name = node_info['user']['shortName']
                    if name and name.strip():
                        node_names[node_id] = name
                        return name
        except Exception as e:
            print(f"DEBUG: Error getting node name for {node_id:08x}: {e}", file=sys.stderr)
    
    # Return hex ID as fallback
    return f"!{node_id:08x}"


def on_receive(packet, interface):
    """Callback when a packet is received."""
    
    try:
        # Packet comes as a dict from pub/sub
        if isinstance(packet, dict):
            # Get channel index
            channel_index = packet.get("channel", 0)
            
            # Get sender information
            from_id = packet.get("from")
            to_id = packet.get("to")
            if not from_id:
                return
            
            from_name = get_node_name(from_id, interface)
            
            channel_info = CHANNELS.get(channel_index, {"name": f"Unknown-{channel_index}", "psk": None})
            channel_name = channel_info["name"]
            
            # Try to decrypt if encrypted
            if "encrypted" in packet and packet["encrypted"]:
                # Try to decrypt with the channel's PSK
                psk = channel_info.get("psk")
                if psk:
                    # Convert dict to object-like structure for decrypt function
                    class PacketObj:
                        def __init__(self, data):
                            for key, value in data.items():
                                setattr(self, key.replace("from", "from_"), value)
                    
                    packet_obj = PacketObj(packet)
                    setattr(packet_obj, "from", from_id)  # Set the from field
                    
                    decrypted = decrypt_message(packet_obj, psk)
                    if decrypted and hasattr(decrypted, "payload"):
                        # Check if it's a text message
                        if decrypted.portnum == portnums_pb2.TEXT_MESSAGE_APP:
                            message_text = decrypted.payload.decode('utf-8', errors='ignore')
                            print(f"[{channel_name}] {from_name} -> {to_id:08x}: {message_text}")
                            # Queue message for Discord if channel is mapped
                            if channel_index in DISCORD_CHANNEL_MAP:
                                asyncio.run_coroutine_threadsafe(
                                    message_queue.put((channel_index, from_name, message_text)),
                                    discord_client.loop
                                )
                            return
            
            # Handle already decoded messages
            elif "decoded" in packet and packet["decoded"]:
                decoded = packet["decoded"]
                
                # Check portnum - can be string or int
                portnum = decoded.get("portnum")
                if portnum == "TEXT_MESSAGE_APP" or portnum == portnums_pb2.TEXT_MESSAGE_APP:
                    # Try to get text directly first
                    message_text = decoded.get("text")
                    
                    # If no text field, try payload
                    if not message_text and "payload" in decoded:
                        payload_bytes = decoded["payload"]
                        # Handle if payload is bytes or base64
                        if isinstance(payload_bytes, str):
                            import base64
                            payload_bytes = base64.b64decode(payload_bytes)
                        message_text = payload_bytes.decode('utf-8', errors='ignore')
                    
                    if message_text:
                        print(f"[{channel_name}] {from_name} -> {to_id:08x}: {message_text}")
                        # Queue message for Discord if channel is mapped
                        if channel_index in DISCORD_CHANNEL_MAP:
                            asyncio.run_coroutine_threadsafe(
                                message_queue.put((channel_index, from_name, message_text)),
                                discord_client.loop
                            )
            else:
                pass  # Silently ignore non-text messages
    
    except Exception as e:
        print(f"Error processing packet: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


class MeshtasticDiscordBot(discord.Client):
    """Discord bot to relay Meshtastic messages."""
    
    def __init__(self, *args, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, *args, **kwargs)
        self.meshtastic_interface = None
    
    async def on_ready(self):
        """Called when the bot is ready."""
        global discord_client, discord_channels
        discord_client = self
        
        print(f'Discord bot logged in as {self.user}')
        
        # Get all the Discord channels
        for mesh_channel_idx, discord_channel_id in DISCORD_CHANNEL_MAP.items():
            channel = self.get_channel(discord_channel_id)
            if channel:
                discord_channels[mesh_channel_idx] = channel
                channel_name = CHANNELS.get(mesh_channel_idx, {}).get("name", f"Channel {mesh_channel_idx}")
                print(f'Found Discord channel for {channel_name}: #{channel.name}')
                await channel.send(f"🟢 Meshtastic bridge connected")
            else:
                print(f'ERROR: Could not find Discord channel with ID {discord_channel_id}')
        
        # Start processing message queue
        self.loop.create_task(self.process_message_queue())
        
        # Start Meshtastic in a thread
        import threading
        threading.Thread(target=self.start_meshtastic, daemon=True).start()
    
    async def process_message_queue(self):
        """Process messages from the queue and send to Discord."""
        while True:
            try:
                channel_index, from_name, message_text = await message_queue.get()
                discord_channel = discord_channels.get(channel_index)
                if discord_channel:
                    # Generate a consistent avatar URL based on username
                    # Using ui-avatars.com for persistent text-based avatars
                    import urllib.parse
                    encoded_name = urllib.parse.quote(from_name)
                    # Generate color based on username hash
                    name_hash = hashlib.md5(from_name.encode()).hexdigest()
                    color = name_hash[:6]  # Use first 6 chars as hex color
                    avatar_url = f"https://ui-avatars.com/api/?name={encoded_name}&background={color}&color=fff&size=128&bold=true"
                    
                    # Create an embed for better formatting
                    embed = discord.Embed(
                        description=message_text,
                        color=0x5865F2  # Discord blurple color
                    )
                    embed.set_author(
                        name=from_name,
                        icon_url=avatar_url
                    )
                    await discord_channel.send(embed=embed)
            except Exception as e:
                print(f"Error sending to Discord: {e}", file=sys.stderr)
    
    def start_meshtastic(self):
        """Start listening to Meshtastic device."""
        try:
            print(f"Connecting to Meshtastic device on {SERIAL_PORT}...")
            self.meshtastic_interface = meshtastic.serial_interface.SerialInterface(SERIAL_PORT)
            
            print("Connected to Meshtastic! Listening for messages...\n")
            
            # Subscribe to messages
            def on_meshtastic_message(packet, interface):
                on_receive(packet, interface)
            
            pub.subscribe(on_meshtastic_message, "meshtastic.receive")
            
            # Keep thread alive
            while True:
                import time
                time.sleep(1)
        
        except Exception as e:
            print(f"Meshtastic error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    async def on_message(self, message):
        """Handle messages from Discord."""
        # Ignore bot's own messages
        if message.author == self.user:
            return
        
        # Check if message is from one of our monitored Discord channels
        # Find which Meshtastic channel this Discord channel maps to
        mesh_channel_idx = None
        for idx, discord_channel_id in DISCORD_CHANNEL_MAP.items():
            if message.channel.id == discord_channel_id:
                mesh_channel_idx = idx
                break
        
        if mesh_channel_idx is not None:
            # Send to the corresponding Meshtastic channel
            try:
                if self.meshtastic_interface:
                    text = f"{message.author.display_name}: {message.content}"
                    self.meshtastic_interface.sendText(text, channelIndex=mesh_channel_idx)
                    print(f"Sent to Meshtastic channel {mesh_channel_idx}: {text}")
            except Exception as e:
                print(f"Error sending to Meshtastic: {e}", file=sys.stderr)


def main():
    global discord_client
    
    print("Starting Meshtastic to Discord bridge...")
    print(f"Discord server: {DISCORD_SERVER_ID}")
    print(f"Monitored channels:")
    for mesh_idx, discord_id in DISCORD_CHANNEL_MAP.items():
        channel_name = CHANNELS.get(mesh_idx, {}).get("name", f"Channel {mesh_idx}")
        print(f"  {channel_name} (mesh:{mesh_idx}) -> Discord:{discord_id}")
    print(f"Meshtastic port: {SERIAL_PORT}\n")
    
    try:
        # Start Discord bot
        bot = MeshtasticDiscordBot()
        bot.run(DISCORD_TOKEN)
    
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        if interface:
            interface.close()
        sys.exit(1)
        sys.exit(1)


if __name__ == "__main__":
    main()
