# Meshtastic-Fun

A collection of Python scripts for working with Meshtastic devices, including MQTT monitoring, Discord integration, and testing utilities.

## Overview

This project provides tools to bridge Meshtastic mesh networks with Discord, monitor MQTT topics, and test MQTT message sending capabilities. Perfect for mesh network enthusiasts who want to integrate their Meshtastic devices with modern communication platforms.

## Scripts

### 1. `meshtastic_to_discord.py`

A bidirectional bridge between Meshtastic devices and Discord servers. This script listens to both a local Meshtastic device (via serial) and an MQTT broker, then forwards messages to specified Discord channels. It also supports sending messages from Discord back to Meshtastic.

**Features:**
- Listens to Meshtastic device via serial port
- Monitors MQTT topics for Meshtastic messages
- Decrypts encrypted Meshtastic packets using channel PSKs
- Forwards messages to Discord channels with custom embeds
- Supports multiple channel mapping (Meshtastic channels → Discord channels)
- Bidirectional: sends Discord messages back to Meshtastic network
- Node name resolution and caching
- Generates consistent user avatars based on node names

**Usage:**
```bash
python meshtastic_to_discord.py
```

**Configuration:**
Requires a `.env` file with the following variables:
```env
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token
DISCORD_SERVER_ID=your_server_id
DISCORD_CHANNEL_LONGFAST=channel_id_for_longfast
DISCORD_CHANNEL_MICHIGAN=channel_id_for_michigan

# Meshtastic Serial
SERIAL_PORT=/dev/ttyUSB0

# MQTT Configuration
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_USER=your_mqtt_user
MQTT_PASSWORD=your_mqtt_password
MQTT_TOPIC=msh/US/MI/2/e/#
MQTT_ENCRYPTION_KEY=base64_encoded_key

# Channel PSKs (Base64 encoded)
PSK_LONGFAST=AQ==
PSK_MICHIGAN=MA==
```

### 2. `monitor_topics.py`

A monitoring utility that subscribes to MQTT topics and provides a real-time summary of incoming message traffic. Useful for debugging and understanding Meshtastic MQTT traffic patterns.

**Features:**
- Subscribes to MQTT topics with wildcard support
- Real-time console display with topic statistics
- Normalizes topics by removing user IDs
- Sorts topics by message count
- Auto-refreshing terminal display

**Usage:**
```bash
# Monitor with defaults
python monitor_topics.py

# Specify custom topic and broker
python monitor_topics.py --topic "msh/US/#" --host mqtt.example.com --port 1883

# With authentication
python monitor_topics.py --username myuser --password mypass
```

**Command-line Options:**
- `--topic`: MQTT topic filter (default: `msh/US/MI/2/e/#`)
- `--host`: MQTT broker hostname (default: `localhost`)
- `--port`: MQTT broker port (default: `1883`)
- `--username`: MQTT username (optional)
- `--password`: MQTT password (optional)

### 3. `send_mqtt_test.py`

A testing utility to send encrypted test messages to a Meshtastic MQTT broker in the proper protocol buffer format.

**Features:**
- Creates properly formatted Meshtastic MQTT messages
- Encrypts messages using AES-CTR with channel PSK
- Wraps messages in ServiceEnvelope format
- Useful for testing MQTT→Meshtastic message flow

**Usage:**
```bash
python send_mqtt_test.py
```

**Configuration:**
Edit the script to customize:
- `MQTT_BROKER`: MQTT broker hostname
- `MQTT_PORT`: MQTT broker port
- `MQTT_USER`: MQTT username
- `MQTT_PASSWORD`: MQTT password
- `MQTT_TOPIC`: Target topic (includes channel and node ID)
- `KEY`: Base64-encoded encryption key for the channel

## Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd meshtastic-fun
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables:**
Create a `.env` file in the project directory with your configuration (see example above).

## Dependencies

- `meshtastic`: Meshtastic Python library
- `paho-mqtt`: MQTT client library
- `cryptography`: Encryption/decryption support
- `discord.py`: Discord API wrapper
- `python-dotenv`: Environment variable management
- `pubsub`: Publish-subscribe messaging

All dependencies are listed in `requirements.txt`.

## Requirements

- Python 3.7+
- Meshtastic device (for serial interface features)
- MQTT broker (local or remote)
- Discord bot token (for Discord bridge)

## Common Use Cases

### Monitor Your Mesh Network
Use `monitor_topics.py` to see what messages are flowing through your MQTT broker and identify active channels.

### Bridge to Discord
Run `meshtastic_to_discord.py` to create a persistent bridge between your mesh network and Discord, enabling mesh users to communicate with Discord users and vice versa.

### Test MQTT Integration
Use `send_mqtt_test.py` to verify your MQTT setup is working correctly before deploying the full bridge.

## Troubleshooting

### Serial Port Access
If you get permission errors accessing `/dev/ttyUSB0`, add your user to the dialout group:
```bash
sudo usermod -a -G dialout $USER
```
Then log out and back in.

### Discord Bot Setup
1. Create a Discord application at https://discord.com/developers/applications
2. Create a bot and copy the token
3. Enable "Message Content Intent" in bot settings
4. Invite the bot to your server with appropriate permissions (Send Messages, Read Messages, Embed Links)

### MQTT Connection Issues
- Verify your broker is running: `mosquitto_sub -h localhost -t '#' -v`
- Check firewall rules if connecting to a remote broker
- Ensure credentials are correct if authentication is enabled

## License

This project is provided as-is for educational and personal use.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## Acknowledgments

- Meshtastic project for the excellent mesh networking platform
- Discord.py for the robust Discord API library
