import RPi.GPIO as GPIO
import time
import json
import logging
import socket
from typing import List, Dict

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='/home/anhem/Smart_Parking/parking.log'
)

# Sensor to pin mapping
SENSOR_PINS = {
    1: 17,
    2: 27,
    3: 22,
    4: 23,
    5: 24
}

DATA_FILE = "/home/anhem/Smart_Parking/data.json"

# Socket setup
HOST = '127.0.0.1'
PORT = 8888
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Attempt to connect socket
while True:
    try:
        client_socket.connect((HOST, PORT))
        logging.info("Socket connected to main_gate.py on port 8888")
        break
    except Exception as e:
        logging.warning(f"Waiting for socket connection to main_gate.py: {e}")
        time.sleep(2)

def setup_gpio() -> None:
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in SENSOR_PINS.values():
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        logging.info("GPIO setup completed")
    except Exception as e:
        logging.error(f"GPIO setup failed: {e}")
        raise

def read_sensors() -> List[Dict[str, any]]:
    try:
        status = []
        for spot_id, pin in SENSOR_PINS.items():
            sensor_state = GPIO.input(pin)
            status.append({
                "id": spot_id,
                "status": "occupied" if sensor_state == 0 else "free"
            })
        logging.debug(f"Sensor readings: {status}")
        return status
    except Exception as e:
        logging.error(f"Error reading sensors: {e}")
        return []

def update_data_file(parking_status: List[Dict[str, any]]) -> None:
    try:
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {"parking_spots": [], "vehicles": []}

        data["parking_spots"] = parking_status

        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

        logging.info("Parking status updated")
    except Exception as e:
        logging.error(f"Error updating data file: {e}")

def remove_vehicle_data(spot_id: int) -> None:
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)

        vehicles = data.get("vehicles", [])
        updated = False

        for vehicle in vehicles:
            if vehicle.get("spot_id") == spot_id:
                if vehicle.get("plate") or vehicle.get("time_in"):
                    logging.info(f"Clearing vehicle data at spot {spot_id}: plate={vehicle.get('plate')}, time_in={vehicle.get('time_in')}")
                vehicle["plate"] = ""
                vehicle["time_in"] = ""
                updated = True
                break
        if updated:
            with open(DATA_FILE, "w") as f:
                json.dump(data, f, indent=4)
            logging.info(f"Vehicle data cleared at spot {spot_id}")
    except Exception as e:
        logging.error(f"Error clearing vehicle data: {e}")

def main() -> None:
    try:
        setup_gpio()
        logging.info("Starting parking sensor monitoring")

        prev_status = {spot_id: None for spot_id in SENSOR_PINS.keys()}
        free_start_time = {}

        while True:
            parking_status = read_sensors()
            if parking_status:
                update_data_file(parking_status)

                for spot in parking_status:
                    spot_id = spot["id"]
                    current = spot["status"]
                    previous = prev_status[spot_id]

                    if current != previous:
                        if current == "occupied":
                            msg = f"OCCUPIED:{spot_id}"
                            try:
                                client_socket.sendall(msg.encode())
                                logging.info(f"Sent socket message: {msg}")
                            except Exception as e:
                                logging.error(f"Socket send failed: {e}")
                            if spot_id in free_start_time:
                                del free_start_time[spot_id]
                        elif current == "free":
                            free_start_time[spot_id] = time.time()
                        prev_status[spot_id] = current
                    else:
                         
                        if current == "free" and spot_id in free_start_time:
                            elapsed = time.time() - free_start_time[spot_id]
                            if elapsed >= 5:
                                remove_vehicle_data(spot_id)
                                del free_start_time[spot_id]

            time.sleep(1)

    except KeyboardInterrupt:
        logging.info("Stopped by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        client_socket.close()
        GPIO.cleanup()
        logging.info("GPIO cleaned up and socket closed")

if __name__ == "__main__":
    main()