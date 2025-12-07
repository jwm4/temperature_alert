import urllib.request

import json
import os
import sys

# Load Configuration
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        TOPIC = config.get("ntfy_topic")
        if not TOPIC:
            raise ValueError("ntfy_topic not found in config")
except Exception as e:
    print(f"Error loading config: {e}")
    sys.exit(1)

def send_test_alert():
    msg = "This is a TEST alert from your Freeze Alert System. If you see this, it works!"
    print(f"Sending test alert to topic: {TOPIC}")
    
    try:
        req = urllib.request.Request(
            f"https://ntfy.sh/{TOPIC}",
            data=msg.encode('utf-8'),
            method='POST'
        )
        req.add_header("Title", "Test Alert")
        req.add_header("Priority", "default")
        
        with urllib.request.urlopen(req) as resp:
            print("Test alert sent successfully!")
    except Exception as e:
        print(f"Failed to send test alert: {e}")

if __name__ == "__main__":
    send_test_alert()
