#!/usr/bin/env python3
"""Send a test MQTT message in Meshtastic format."""

import paho.mqtt.client as mqtt
from meshtastic.protobuf import mqtt_pb2, mesh_pb2, portnums_pb2
import base64
import time
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# MQTT config
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_USER = "meshdev"
MQTT_PASSWORD = "large4cats"
MQTT_TOPIC = "msh/US/MI/2/e/Farmington/!12345678"  # Test node ID

# Encryption key for Farmington channel
KEY = "MA=="  # Farmington key

def encrypt_message(text, from_id, packet_id, key):
    """Encrypt a text message."""
    key_bytes = base64.b64decode(key.encode('ascii'))
    
    # Expand key to 128-bit by padding with zeros if needed
    if len(key_bytes) < 16:
        key_bytes = key_bytes + b'\x00' * (16 - len(key_bytes))
    
    # Build the nonce
    nonce_packet_id = packet_id.to_bytes(8, "little")
    nonce_from_node = from_id.to_bytes(8, "little")
    nonce = nonce_packet_id + nonce_from_node
    
    # Create the data payload
    data = mesh_pb2.Data()
    data.portnum = portnums_pb2.TEXT_MESSAGE_APP
    data.payload = text.encode('utf-8')
    
    # Encrypt
    cipher = Cipher(algorithms.AES(key_bytes), modes.CTR(nonce), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_bytes = encryptor.update(data.SerializeToString()) + encryptor.finalize()
    
    return encrypted_bytes

def send_test_message():
    """Send a test message via MQTT."""
    # Create mesh packet
    packet = mesh_pb2.MeshPacket()
    packet.id = int(time.time() * 1000000) & 0xFFFFFFFF  # Random packet ID
    from_id = 0x12345678  # Test sender ID
    setattr(packet, "from", from_id)
    packet.to = 0xFFFFFFFF  # Broadcast
    packet.channel = 2  # Farmington channel (corrected to index 2)
    
    # Encrypt the message
    message_text = "Test message from MQTT! 🚀"
    packet.encrypted = encrypt_message(message_text, from_id, packet.id, KEY)
    
    # Wrap in service envelope
    envelope = mqtt_pb2.ServiceEnvelope()
    envelope.packet.CopyFrom(packet)
    envelope.channel_id = "Farmington"
    envelope.gateway_id = "!12345678"
    
    # Publish to MQTT
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    
    result = client.publish(MQTT_TOPIC, envelope.SerializeToString())
    print(f"Published test message to {MQTT_TOPIC}")
    print(f"Message: {message_text}")
    print(f"Result: {result}")
    
    client.disconnect()

if __name__ == "__main__":
    send_test_message()
