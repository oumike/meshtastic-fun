#!/usr/bin/env python3
"""Subscribe to MQTT topic and print incoming message topics."""

import argparse
import sys
from collections import defaultdict
import time

try:
    import paho.mqtt.client as mqtt
except ModuleNotFoundError:
    print("paho-mqtt is required. Install with: pip install paho-mqtt", file=sys.stderr)
    sys.exit(1)


def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker."""
    print(f"Connected with result code: {rc}", file=sys.stderr)
    if rc == 0:
        topic = userdata["topic"]
        print(f"Subscribing to: {topic}", file=sys.stderr)
        client.subscribe(topic, qos=0)
    else:
        print(f"Connection failed with code: {rc}", file=sys.stderr)


def on_subscribe(client, userdata, mid, granted_qos):
    """Callback when subscription is confirmed."""
    print(f"Subscribed! mid={mid}, qos={granted_qos}", file=sys.stderr)


def on_message(client, userdata, msg):
    """Callback when a message is received."""
    topic_counts = userdata["topic_counts"]
    
    # Strip the last part (user ID) from the topic
    topic_parts = msg.topic.split('/')
    if topic_parts and topic_parts[-1].startswith('!'):
        # Remove the user ID (last part starting with !)
        normalized_topic = '/'.join(topic_parts[:-1])
    else:
        normalized_topic = msg.topic
    
    topic_counts[normalized_topic] += 1
    
    # Print running summary
    print("\033[2J\033[H", end="")  # Clear screen and move cursor to top
    print(f"MQTT Topic Summary (Updated: {time.strftime('%H:%M:%S')})")
    print("=" * 60)
    total = sum(topic_counts.values())
    print(f"Total messages: {total}\n")
    
    # Sort by count (descending) then by topic name
    for topic, count in sorted(topic_counts.items(), key=lambda x: (-x[1], x[0])):
        print(f"{count:6d}  {topic}")
    
    print(flush=True)


def main():
    parser = argparse.ArgumentParser(description="Subscribe to MQTT and print topics")
    parser.add_argument("--topic", default="msh/US/MI/2/e/#", help="Topic filter")
    parser.add_argument("--host", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--username", help="MQTT username")
    parser.add_argument("--password", help="MQTT password")
    args = parser.parse_args()

    print(f"Connecting to {args.host}:{args.port}...", file=sys.stderr)
    print(f"Will subscribe to: {args.topic}", file=sys.stderr)

    # Create client with userdata
    topic_counts = defaultdict(int)
    client = mqtt.Client(userdata={"topic": args.topic, "topic_counts": topic_counts})

    if args.username:
        client.username_pw_set(args.username, args.password)

    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message

    try:
        client.connect(args.host, args.port, keepalive=60)
        print("Starting loop...", file=sys.stderr)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nShutting down...", file=sys.stderr)
        client.disconnect()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
