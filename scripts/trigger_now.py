import socket
import sys

TRIGGER_PORT = 65432

def trigger():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', TRIGGER_PORT))
        print("Trigger sent to TemperatureAlert service.")
        s.close()
    except ConnectionRefusedError:
        print("Error: TemperatureAlert service is not running.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    trigger()
