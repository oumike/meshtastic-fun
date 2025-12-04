#!/usr/bin/env python3
"""
Fun/Trivia bot for MeshMonitor auto-responder.
Provides trivia, facts, jokes, and quotes - all content stored locally.

Requirements:
- Python 3.6+
- No external dependencies or API keys required

Setup:
1. Ensure volume mapping in docker-compose.yaml:
   - ./scripts:/data/scripts
2. Copy fun.py to scripts/ directory
3. Make executable: chmod +x scripts/fun.py
4. Copy to container: docker cp scripts/fun.py meshmonitor:/data/scripts/
5. Configure triggers in MeshMonitor web UI:
   - Trigger: trivia (Response: /data/scripts/fun.py)
     IMPORTANT: Set PARAM_command=trivia in trigger configuration
   - Trigger: fact (Response: /data/scripts/fun.py)
     IMPORTANT: Set PARAM_command=fact in trigger configuration
   - Trigger: joke (Response: /data/scripts/fun.py)
     IMPORTANT: Set PARAM_command=joke in trigger configuration
   - Trigger: quote (Response: /data/scripts/fun.py)
     IMPORTANT: Set PARAM_command=quote in trigger configuration
   
   Note: If PARAM_command is not set, script will try to detect from message,
   but it's recommended to set it explicitly in trigger configuration.

Usage:
- MeshMonitor auto-responder: trivia, fact, joke, or quote
- Local testing: TEST_MODE=true PARAM_command="trivia" python3 fun.py

Examples:
- trivia
- fact
- joke
- quote

Made with ❤️ for the MeshMonitor community.
"""

import os
import sys
import json
import random
from datetime import datetime
from typing import Dict, Any, List, Union

# Test mode flag - set to True for local testing
TEST_MODE = os.environ.get('TEST_MODE', 'false').lower() == 'true'

class FunBot:
    """Fun bot that provides trivia, facts, jokes, and quotes."""

    def __init__(self):
        # Initialize random seed based on date for daily variety
        today = datetime.now()
        random.seed(today.year * 1000 + today.timetuple().tm_yday)

    def get_trivia(self) -> str:
        """Return a random mesh/radio/tech trivia question."""
        trivia_list = [
            "Q: What does LoRa stand for? A: Long Range radio technology.",
            "Q: What frequency band do most Meshtastic nodes use? A: 915 MHz (US) or 868 MHz (EU).",
            "Q: What is mesh networking? A: A network where nodes relay messages for each other.",
            "Q: What is the max range of LoRa? A: Up to 10+ miles line-of-sight.",
            "Q: What does MQTT stand for? A: Message Queuing Telemetry Transport.",
            "Q: What is a hop in mesh networking? A: One relay between source and destination.",
            "Q: What is the ISM band? A: Industrial, Scientific, Medical radio band (unlicensed).",
            "Q: What does APRS stand for? A: Automatic Packet Reporting System.",
            "Q: What is packet radio? A: Digital data transmission over radio waves.",
            "Q: What does RSSI measure? A: Received Signal Strength Indicator.",
        ]
        return random.choice(trivia_list)

    def get_fact(self) -> str:
        """Return an interesting tech/mesh fact."""
        facts = [
            "Meshtastic can work completely offline - no internet required!",
            "LoRa can transmit through obstacles better than WiFi or Bluetooth.",
            "Mesh networks are self-healing - if one node fails, others route around it.",
            "The first packet radio network was created in the 1970s by amateur radio operators.",
            "LoRa uses spread spectrum modulation for long-range, low-power communication.",
            "Mesh networks can span hundreds of miles with enough relay nodes.",
            "Meshtastic uses encryption to secure all messages on the mesh.",
            "LoRa devices can run for months on battery power.",
            "The 915 MHz band is shared with WiFi, Bluetooth, and other devices.",
            "Mesh networks are used in disaster relief when infrastructure fails.",
        ]
        return random.choice(facts)

    def get_joke(self) -> str:
        """Return a radio/mesh/tech-themed joke."""
        jokes = [
            "Why did the mesh node break up? It couldn't find a good connection!",
            "What do you call a mesh network that tells jokes? A pun-net!",
            "Why do mesh nodes make good friends? They're always relaying messages!",
            "What's a mesh node's favorite song? 'I Will Always Route You'!",
            "Why did the packet cross the mesh? To get to the other node!",
            "What do you call a sleeping mesh network? A nap-net!",
            "Why are mesh nodes so reliable? They always hop to it!",
            "What's a mesh node's favorite game? Hopscotch!",
            "Why don't mesh nodes get lost? They always know the route!",
            "What do mesh nodes say when they meet? 'Nice to relay you!'",
        ]
        return random.choice(jokes)

    def get_quote(self) -> str:
        """Return an inspirational tech/communication quote."""
        quotes = [
            "The network is the computer. - John Gage",
            "Communication is the key to understanding. - Unknown",
            "In a mesh network, every node is important. - Mesh Philosophy",
            "The best network is one that works when you need it most. - Unknown",
            "Radio waves connect us across distances. - Ham Radio Operator",
            "A mesh network is only as strong as its weakest link. - Network Theory",
            "Technology should serve humanity, not the other way around. - Unknown",
            "The internet of things starts with the mesh of things. - Unknown",
            "In disaster, mesh networks become lifelines. - Emergency Responder",
            "Connectivity is a human right. - Digital Rights Advocate",
        ]
        return random.choice(quotes)

    def split_message(self, text: str, max_chars: int = 199) -> List[str]:
        """
        Split a long message into multiple messages, each under max_chars.

        Args:
            text: Text to split
            max_chars: Maximum characters per message (default: 199)

        Returns:
            List of message strings
        """
        if len(text) <= max_chars:
            return [text]

        messages = []
        lines = text.split('\n')
        current_message = []

        for line in lines:
            test_message = '\n'.join(current_message + [line]) if current_message else line
            if len(test_message) <= max_chars:
                current_message.append(line)
            else:
                if current_message:
                    messages.append('\n'.join(current_message))
                if len(line) > max_chars:
                    # Split long line by words
                    words = line.split(' ')
                    current_line = []
                    for word in words:
                        test_line = ' '.join(current_line + [word]) if current_line else word
                        if len(test_line) <= max_chars:
                            current_line.append(word)
                        else:
                            if current_line:
                                messages.append(' '.join(current_line))
                            current_line = [word]
                    if current_line:
                        current_message = [' '.join(current_line)]
                else:
                    current_message = [line]

        if current_message:
            messages.append('\n'.join(current_message))

        return messages

    def get_help(self) -> Union[str, List[str]]:
        """Return help text for the fun bot."""
        help_text = (
            'Fun Bot:\n'
            '• trivia - Random trivia\n'
            '• fact - Tech fact\n'
            '• joke - Get joke\n'
            '• quote - Inspiration\n'
            'Examples:\n'
            '• trivia\n'
            '• fact\n'
            'See script for more details.'
        )
        # Split if needed (though it's currently under 199)
        messages = self.split_message(help_text, max_chars=199)
        return messages[0] if len(messages) == 1 else messages

def main():
    """Main function to handle fun bot requests."""
    try:
        # Get command parameter from environment (set by MeshMonitor)
        # For different triggers, MeshMonitor will pass different PARAM_command values
        command = os.environ.get('PARAM_command', '').strip().lower()
        
        # If PARAM_command is empty, try to infer from original message
        # This handles cases where trigger is configured without explicitly setting PARAM_command
        if not command:
            # Try to get from MESSAGE environment variable (original message text)
            original_message = os.environ.get('MESSAGE', '').strip().lower()
            # Extract first word which should be the command
            if original_message:
                first_word = original_message.split()[0] if original_message.split() else ''
                if first_word in ['trivia', 'fact', 'joke', 'quote']:
                    command = first_word

        bot = FunBot()

        if command in ['help', 'h', '?']:
            # Explicit help request
            response = bot.get_help()
        elif command == 'trivia':
            response = bot.get_trivia()
        elif command == 'fact':
            response = bot.get_fact()
        elif command == 'joke':
            response = bot.get_joke()
        elif command == 'quote':
            response = bot.get_quote()
        elif not command:
            # No command detected - this means trigger wasn't configured with PARAM_command
            # Return helpful error message instead of help
            response = (
                'Error: Command not specified.\n'
                'Configure trigger with PARAM_command:\n'
                '• trivia → PARAM_command=trivia\n'
                '• fact → PARAM_command=fact\n'
                '• joke → PARAM_command=joke\n'
                '• quote → PARAM_command=quote'
            )
        else:
            # Unknown command, show help
            response = bot.get_help()

        # Split response if it exceeds 199 characters
        if isinstance(response, str) and len(response) > 199:
            response = bot.split_message(response, max_chars=199)
            if len(response) == 1:
                response = response[0]

        # Ensure we always have a response
        if not response:
            response = 'Error: No response generated'

        # Output JSON response for MeshMonitor
        # If response is a list, use 'responses' field; otherwise use 'response'
        try:
            if isinstance(response, list):
                output = {'responses': response}
            else:
                output = {'response': response}
            print(json.dumps(output))
            sys.stdout.flush()

            if TEST_MODE:
                print(f'\n--- TEST MODE OUTPUT ---\n{response}\n--- END TEST ---\n', file=sys.stderr)
        except Exception as output_error:
            try:
                error_output = {'response': f'Error: Failed to format response: {str(output_error)}'}
                print(json.dumps(error_output))
                sys.stdout.flush()
            except:
                print('{"response": "Error: Script execution failed"}')
                sys.stdout.flush()

    except Exception as e:
        # Handle any unexpected errors - ensure we always output something
        try:
            error_msg = f'Error: {str(e)}'
            if len(error_msg) > 195:
                error_msg = error_msg[:192] + '...'
            output = {'response': error_msg}
            print(json.dumps(output))
            sys.stdout.flush()

            if TEST_MODE:
                print(f'\n--- TEST MODE ERROR ---\n{error_msg}\n--- END TEST ---\n', file=sys.stderr)

            print(f'Error in fun script: {str(e)}', file=sys.stderr)
        except:
            print('{"response": "Error: Script execution failed"}')
            sys.stdout.flush()
        finally:
            sys.exit(0)

if __name__ == '__main__':
    main()

