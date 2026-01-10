#!/usr/bin/env python3
"""
Temperature Alert - Cloud Mode

Uses Ecowitt Cloud APIs to fetch temperature data and 24-hour history.
Unlike the LAN mode, this fetches true historical highs/lows from the cloud.

Designed for scheduled execution (cron/Task Scheduler) rather than continuous polling.
"""

import urllib.request
import urllib.parse
import json
import datetime
import sys
import socket
import logging
import os
import collections

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Project root is 3 levels up from legacy/ (legacy -> temperature_agent -> src -> root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))
LOG_FILE = os.path.join(PROJECT_ROOT, "temperature_alert_cloud.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

# Load Configuration - config.json is in project root
CONFIG_FILE = os.path.join(PROJECT_ROOT, "config.json")

try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f, object_pairs_hook=collections.OrderedDict)
except FileNotFoundError:
    logging.error(f"Config file not found: {CONFIG_FILE}")
    sys.exit(1)
except json.JSONDecodeError as e:
    logging.error(f"Error parsing config file: {e}")
    sys.exit(1)

# Common config
LAT = config.get("latitude")
LONG = config.get("longitude")
FREEZE_THRESHOLD_F = config.get("freeze_threshold_f", 60.0)
HEAT_THRESHOLD_F = config.get("heat_threshold_f", 70.0)
TOPIC = config.get("ntfy_topic")
SENSOR_NAMES = config.get("sensors", collections.OrderedDict())

# Cloud API config
ECOWITT_APP_KEY = config.get("ecowitt_application_key")
ECOWITT_API_KEY = config.get("ecowitt_api_key")
ECOWITT_MAC = config.get("ecowitt_mac")

# Validate cloud config
if not all([ECOWITT_APP_KEY, ECOWITT_API_KEY, ECOWITT_MAC]):
    logging.error("Missing Ecowitt cloud API configuration. Please set:")
    logging.error("  - ecowitt_application_key")
    logging.error("  - ecowitt_api_key")
    logging.error("  - ecowitt_mac")
    logging.error("See README.md for instructions on obtaining these credentials.")
    sys.exit(1)

# API endpoints
ECOWITT_API_BASE = "https://api.ecowitt.net/api/v3"
FORECAST_URL = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LONG}&hourly=temperature_2m&temperature_unit=fahrenheit&timezone=auto"

# Trigger port (same as LAN version for compatibility)
TRIGGER_PORT = 65433  # Different port to allow both to run


def ecowitt_api_request(endpoint, extra_params=None):
    """Make a request to the Ecowitt Cloud API."""
    params = {
        "application_key": ECOWITT_APP_KEY,
        "api_key": ECOWITT_API_KEY,
        "mac": ECOWITT_MAC,
    }
    if extra_params:
        params.update(extra_params)
    
    url = f"{ECOWITT_API_BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
            
            # Check for API errors
            if data.get("code") != 0:
                logging.error(f"Ecowitt API error: {data.get('msg', 'Unknown error')}")
                return None
            
            return data.get("data", {})
    except urllib.error.URLError as e:
        logging.error(f"Network error calling Ecowitt API: {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing Ecowitt API response: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error calling Ecowitt API: {e}")
        return None


def get_cloud_realtime_temps():
    """Fetch current temperatures from Ecowitt Cloud API."""
    temps = {}
    
    data = ecowitt_api_request("device/real_time", {"call_back": "all"})
    if not data:
        return temps
    
    # Parse indoor temperature (from indoor sensor)
    indoor = data.get("indoor", {})
    if "temperature" in indoor:
        temp_data = indoor["temperature"]
        temp_f = float(temp_data.get("value", 0))
        # Convert if in Celsius
        if temp_data.get("unit") == "℃":
            temp_f = temp_f * 9/5 + 32
        name = SENSOR_NAMES.get("Indoor", "Indoor")
        temps[name] = round(temp_f, 1)
    
    # Parse outdoor temperature
    outdoor = data.get("outdoor", {})
    if "temperature" in outdoor:
        temp_data = outdoor["temperature"]
        temp_f = float(temp_data.get("value", 0))
        if temp_data.get("unit") == "℃":
            temp_f = temp_f * 9/5 + 32
        name = SENSOR_NAMES.get("Outdoor", "Outdoor")
        temps[name] = round(temp_f, 1)
    
    # Parse channel sensors (temp_ch1, temp_ch2, etc.)
    for i in range(1, 9):  # Channels 1-8
        ch_key = f"temp_ch{i}"
        if ch_key in data:
            ch_data = data[ch_key]
            if "temperature" in ch_data:
                temp_data = ch_data["temperature"]
                temp_f = float(temp_data.get("value", 0))
                if temp_data.get("unit") == "℃":
                    temp_f = temp_f * 9/5 + 32
                raw_name = f"Channel {i}"
                name = SENSOR_NAMES.get(raw_name, raw_name)
                temps[name] = round(temp_f, 1)
    
    return temps


def get_cloud_24h_history():
    """
    Fetch 24-hour temperature history and calculate highs/lows.
    
    Returns:
        tuple: (lows, highs) where each is a dict of {sensor_name: (timestamp, temp)}
    """
    lows = {}
    highs = {}
    
    # Calculate time range for last 24 hours
    now = datetime.datetime.now()
    start = now - datetime.timedelta(hours=24)
    
    # Format dates for API (YYYY-MM-DD HH:MM:SS)
    start_str = start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    def process_temp_history(sensor_data, sensor_name):
        """Process temperature history for a single sensor."""
        if "temperature" not in sensor_data:
            return None, None
        
        temp_history = sensor_data["temperature"]
        if not isinstance(temp_history, dict) or "list" not in temp_history:
            return None, None
        
        readings = temp_history.get("list", {})
        unit = temp_history.get("unit", "℉")
        
        if not readings:
            return None, None
        
        min_temp = float('inf')
        min_time = None
        max_temp = float('-inf')
        max_time = None
        
        for timestamp_str, temp_val in readings.items():
            try:
                temp_f = float(temp_val)
                if unit == "℃":
                    temp_f = temp_f * 9/5 + 32
                
                timestamp = datetime.datetime.fromtimestamp(int(timestamp_str))
                
                if temp_f < min_temp:
                    min_temp = temp_f
                    min_time = timestamp
                if temp_f > max_temp:
                    max_temp = temp_f
                    max_time = timestamp
            except (ValueError, TypeError):
                continue
        
        if min_time and max_time:
            return (min_time, round(min_temp, 1)), (max_time, round(max_temp, 1))
        return None, None
    
    # The history endpoint doesn't accept "all" - we need to request specific sensor types
    # Try each sensor type separately and combine results
    sensor_types = ["indoor", "outdoor"]
    # Add channel sensors (temp_and_humidity_chN or temp_chN)
    for i in range(1, 9):
        sensor_types.append(f"temp_and_humidity_ch{i}")
    
    for sensor_type in sensor_types:
        data = ecowitt_api_request("device/history", {
            "start_date": start_str,
            "end_date": end_str,
            "call_back": sensor_type,
        })
        
        if not data:
            continue
        
        # The response structure varies - the data might be directly under the sensor type key
        # or it might be at the root level
        sensor_data = data.get(sensor_type, data)
        
        # Determine the display name based on sensor type
        if sensor_type == "indoor":
            name = SENSOR_NAMES.get("Indoor", "Indoor")
        elif sensor_type == "outdoor":
            name = SENSOR_NAMES.get("Outdoor", "Outdoor")
        elif sensor_type.startswith("temp_and_humidity_ch"):
            ch_num = sensor_type.replace("temp_and_humidity_ch", "")
            raw_name = f"Channel {ch_num}"
            name = SENSOR_NAMES.get(raw_name, raw_name)
        else:
            name = sensor_type
        
        low, high = process_temp_history(sensor_data, name)
        if low:
            lows[name] = low
        if high:
            highs[name] = high
    
    return lows, highs


def check_weather_and_alert():
    """Main check function - fetches data from cloud and sends alerts if needed."""
    logging.info("Running cloud check...")
    
    # Get current temps from cloud
    current_temps = get_cloud_realtime_temps()
    if not current_temps:
        logging.warning("Could not fetch current temperatures from cloud")
    else:
        logging.info(f"Current temperatures: {current_temps}")
    
    # Get 24-hour history from cloud (TRUE highs/lows)
    lows, highs = get_cloud_24h_history()
    logging.info(f"24h Lows: {lows}")
    logging.info(f"24h Highs: {highs}")
    
    # Format temps for display/alert
    display_temps_freeze = {}
    display_temps_heat = {}
    
    # Sort keys based on the order of values in SENSOR_NAMES
    preferred_order = list(SENSOR_NAMES.values())
    sorted_sensors = sorted(current_temps.keys(), key=lambda x: preferred_order.index(x) if x in preferred_order else 999)
    
    for name in sorted_sensors:
        t = current_temps[name]
        
        # Prepare freeze display (show lows)
        low_info = ""
        if name in lows:
            low_time, low_temp = lows[name]
            time_str = low_time.strftime("%I:%M%p").lstrip("0").lower().replace(":00", "")
            low_info = f"(Low: {low_temp}F @ {time_str})"
        display_temps_freeze[name] = f"{t}F {low_info}"
        
        # Prepare heat display (show highs)
        high_info = ""
        if name in highs:
            high_time, high_temp = highs[name]
            time_str = high_time.strftime("%I:%M%p").lstrip("0").lower().replace(":00", "")
            high_info = f"(High: {high_temp}F @ {time_str})"
        display_temps_heat[name] = f"{t}F {high_info}"
    
    logging.info("Current Home Temperatures:")
    for name, t in display_temps_freeze.items():
        logging.info(f"  {name}: {t}")
    
    # Check forecast (same as LAN version)
    try:
        logging.info(f"Checking forecast for Lat: {LAT}, Long: {LONG}...")
        with urllib.request.urlopen(FORECAST_URL, timeout=30) as response:
            data = json.loads(response.read().decode())
        
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        
        now = datetime.datetime.now()
        min_temp = 1000
        min_time = ""
        max_temp = -1000
        max_time = ""
        
        count = 0
        for t_str, temp in zip(times, temps):
            t = datetime.datetime.fromisoformat(t_str)
            if t > now and count < 24:
                if temp < min_temp:
                    min_temp = temp
                    min_time = t_str
                if temp > max_temp:
                    max_temp = temp
                    max_time = t_str
                count += 1
        
        logging.info(f"Forecasted low: {min_temp}F at {min_time}")
        logging.info(f"Forecasted high: {max_temp}F at {max_time}")
        
        if min_temp < FREEZE_THRESHOLD_F:
            send_alert("Freeze Warning", min_temp, min_time, display_temps_freeze)
        elif max_temp > HEAT_THRESHOLD_F:
            send_alert("Heat Warning", max_temp, max_time, display_temps_heat)
        else:
            logging.info("Temperature is within normal range. No alert needed.")
            
    except Exception as e:
        logging.error(f"Error checking weather: {e}")


def send_alert(title, temp, time_str, current_temps):
    """Send alert via ntfy.sh."""
    dt = datetime.datetime.fromisoformat(time_str)
    day = dt.strftime("%a")
    hour = dt.strftime("%I").lstrip("0")
    ampm = dt.strftime("%p").lower()
    formatted_time = f"{day} {hour}{ampm}"
    
    type_str = "Low" if "Freeze" in title else "High"
    msg = f"Forecast {type_str}: {temp}F @ {formatted_time}"
    
    if current_temps:
        for name, t in current_temps.items():
            msg += f"\n{name}: {t}"
    
    logging.info(f"Sending alert ({title}): {msg}")
    
    try:
        req = urllib.request.Request(
            f"https://ntfy.sh/{TOPIC}",
            data=msg.encode('utf-8'),
            method='POST'
        )
        req.add_header("Title", title)
        req.add_header("Priority", "high")
        with urllib.request.urlopen(req) as resp:
            logging.info("Alert sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send alert: {e}")


def trigger_listener():
    """Listen for manual trigger requests (optional, for compatibility)."""
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('127.0.0.1', TRIGGER_PORT))
        server.listen(1)
        logging.info(f"Listening for manual triggers on port {TRIGGER_PORT}...")
        
        while True:
            try:
                client, addr = server.accept()
                logging.info("Manual trigger received!")
                client.close()
                check_weather_and_alert()
            except Exception as e:
                logging.error(f"Accept error: {e}")
    except Exception as e:
        logging.error(f"Failed to start listener: {e}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Temperature Alert - Cloud Mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python temperature_alert_cloud.py              # Run once and exit
  python temperature_alert_cloud.py --daemon     # Run with trigger listener
  python temperature_alert_cloud.py --test       # Test API connection only
        """
    )
    parser.add_argument("--daemon", action="store_true",
                        help="Run in daemon mode with trigger listener")
    parser.add_argument("--test", action="store_true",
                        help="Test API connection and exit")
    
    args = parser.parse_args()
    
    if args.test:
        logging.info("Testing Ecowitt Cloud API connection...")
        temps = get_cloud_realtime_temps()
        if temps:
            logging.info("✓ Successfully connected to Ecowitt Cloud API")
            logging.info(f"  Current temperatures: {temps}")
            
            lows, highs = get_cloud_24h_history()
            if lows or highs:
                logging.info("✓ Successfully fetched 24-hour history")
                logging.info(f"  24h Lows: {lows}")
                logging.info(f"  24h Highs: {highs}")
            else:
                logging.warning("⚠ Could not fetch 24-hour history")
        else:
            logging.error("✗ Failed to connect to Ecowitt Cloud API")
            logging.error("  Check your credentials in config.json")
            sys.exit(1)
        return
    
    logging.info("Starting Temperature Alert (Cloud Mode)...")
    
    if args.daemon:
        # Daemon mode - run with trigger listener
        import threading
        threading.Thread(target=trigger_listener, daemon=True).start()
        
        # Initial check
        check_weather_and_alert()
        
        # Keep running for trigger listener
        import time
        while True:
            time.sleep(60)
    else:
        # Single run mode - check once and exit
        check_weather_and_alert()


if __name__ == "__main__":
    main()
