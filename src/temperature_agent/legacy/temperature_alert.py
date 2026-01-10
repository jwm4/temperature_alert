import urllib.request
import json
import datetime
import sys
import socket
import threading
import ipaddress
import time
import collections
import logging
import os

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Project root is 3 levels up from legacy/ (legacy -> temperature_agent -> src -> root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))
LOG_FILE = os.path.join(PROJECT_ROOT, "temperature_alert.log")

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

LAT = config.get("latitude")
LONG = config.get("longitude")
FREEZE_THRESHOLD_F = config.get("freeze_threshold_f", 60.0)
HEAT_THRESHOLD_F = config.get("heat_threshold_f", 70.0)
TOPIC = config.get("ntfy_topic")
SENSOR_NAMES = config.get("sensors", collections.OrderedDict())
URL = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LONG}&hourly=temperature_2m&temperature_unit=fahrenheit&timezone=auto"
GW1200_IP = None # Will be discovered
TRIGGER_PORT = 65432


# History Storage: {sensor_name: [(timestamp, temp_float), ...]}
HISTORY = collections.defaultdict(list)
HISTORY_LOCK = threading.Lock()

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def check_ip(ip):
    url = f"http://{ip}/get_livedata_info"
    try:
        with urllib.request.urlopen(url, timeout=1) as response:
            if response.status == 200:
                data = response.read().decode()
                if "common_list" in data:
                    return ip
    except:
        pass
    return None

def find_ecowitt_device():
    global GW1200_IP
    if GW1200_IP: return GW1200_IP
    
    logging.info("Scanning network for Ecowitt device...")
    local_ip = get_local_ip()
    network = ipaddress.IPv4Interface(f"{local_ip}/24").network
    
    threads = []
    found_ip = None
    
    def check_and_set(ip):
        nonlocal found_ip
        if found_ip: return
        if check_ip(str(ip)):
            found_ip = str(ip)

    for ip in network.hosts():
        if found_ip: break
        t = threading.Thread(target=check_and_set, args=(ip,))
        t.start()
        threads.append(t)
        if len(threads) > 50:
            for t in threads: t.join()
            threads = []
            
    for t in threads: t.join()
    
    if found_ip:
        GW1200_IP = found_ip
        logging.info(f"Found Ecowitt at {GW1200_IP}")
    else:
        logging.warning("No Ecowitt device found.")
        
    return found_ip

def get_ecowitt_temps(ip):
    temps = {}
    if not ip: return temps
        
    try:
        url = f"http://{ip}/get_livedata_info"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            
            # Indoor Sensor (wh25)
            for sensor in data.get("wh25", []):
                if "intemp" in sensor:
                    name = SENSOR_NAMES.get("Indoor", "Indoor")
                    temps[name] = float(sensor['intemp'])
            
            # External Sensors (ch_aisle)
            for sensor in data.get("ch_aisle", []):
                raw_name = sensor.get("name") or f"Channel {sensor.get('channel')}"
                name = SENSOR_NAMES.get(raw_name, raw_name)
                if "temp" in sensor:
                    temps[name] = float(sensor['temp'])
                    
    except Exception as e:
        logging.error(f"Error reading Ecowitt: {e}")
        
    return temps

def update_history(current_temps):
    now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(hours=24)
    
    with HISTORY_LOCK:
        for name, temp in current_temps.items():
            # Add new reading
            HISTORY[name].append((now, temp))
            
            # Prune old readings
            HISTORY[name] = [x for x in HISTORY[name] if x[0] > cutoff]

def get_24h_stats():
    lows = {}
    highs = {}
    with HISTORY_LOCK:
        for name, readings in HISTORY.items():
            if readings:
                # Find reading with min temp
                min_reading = min(readings, key=lambda x: x[1])
                lows[name] = min_reading # (timestamp, temp)
                
                # Find reading with max temp
                max_reading = max(readings, key=lambda x: x[1])
                highs[name] = max_reading # (timestamp, temp)
    return lows, highs

def check_weather_and_alert():
    logging.info("Running check...")
    ip = find_ecowitt_device()
    current_temps = get_ecowitt_temps(ip)
    
    # Update history first so current reading is included
    update_history(current_temps)
    lows, highs = get_24h_stats()
    
    # Format temps for display/alert
    display_temps_freeze = {}
    display_temps_heat = {}
    
    # Sort keys based on the order of values in SENSOR_NAMES
    # Sensors not in SENSOR_NAMES values will be appended at the end
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

    try:
        logging.info(f"Checking forecast for Lat: {LAT}, Long: {LONG}...")
        with urllib.request.urlopen(URL) as response:
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
                # Run check in a separate thread to not block listener
                threading.Thread(target=check_weather_and_alert).start()
            except Exception as e:
                logging.error(f"Accept error: {e}")
    except Exception as e:
        logging.error(f"Failed to start listener: {e}")

def main():
    logging.info("Starting TemperatureAlert Service...")
    
    # Start trigger listener
    threading.Thread(target=trigger_listener, daemon=True).start()
    
    # Initial scan
    find_ecowitt_device()
    
    last_poll = 0
    poll_interval = 300 # 5 minutes
    
    # Track if we've alerted for the current slot to avoid duplicates
    last_alert_slot = None 
    
    while True:
        now = time.time()
        
        # Polling Logic
        if now - last_poll > poll_interval:
            ip = find_ecowitt_device()
            if ip:
                temps = get_ecowitt_temps(ip)
                update_history(temps)
                logging.info(f"Polled temperatures: {temps}")
            last_poll = now
            
        # Scheduling Logic
        dt = datetime.datetime.now()
        current_slot = None
        
        # Check 8:15 PM
        if dt.hour == 20 and dt.minute == 15:
            current_slot = "evening"
        # Check 9:40 AM
        elif dt.hour == 9 and dt.minute == 40:
            current_slot = "morning"
            
        if current_slot and current_slot != last_alert_slot:
            logging.info(f"Triggering scheduled check for {current_slot} slot...")
            check_weather_and_alert()
            last_alert_slot = current_slot
        elif not current_slot:
            last_alert_slot = None # Reset when out of the minute window
            
        time.sleep(10)

if __name__ == "__main__":
    main()
