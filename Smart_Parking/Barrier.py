import socket
import time
import RPi.GPIO as GPIO
import json
import datetime

IR1_PIN = 16
IR2_PIN = 20
SERVO_PIN = 21

duong_dan_json = "/home/anhem/Smart_Parking/data.json"

bien_so_duoc_phep = ["51F97022", "30E92291", "43S43210"]
tap_hop_bien_so = set(p.upper() for p in bien_so_duoc_phep)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(IR1_PIN, GPIO.IN)
GPIO.setup(IR2_PIN, GPIO.IN)
GPIO.setup(SERVO_PIN, GPIO.OUT)

pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

def dieu_khien_servo(goc):
    duty = goc / 18 + 2
    GPIO.output(SERVO_PIN, True)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.02)
    GPIO.output(SERVO_PIN, False)

def mo_cong():
    for goc in range(0, 91, 5):
        dieu_khien_servo(goc)
        time.sleep(0.05)

def dong_cong():
    for goc in range(90, -1, -5):
        dieu_khien_servo(goc)
        time.sleep(0.05)

time.sleep(0.5)
dieu_khien_servo(0)
print("San sang, doi ket noi...")

HOST = '0.0.0.0'
PORT = 9999
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(1)

print("Dang doi PC ket noi...")
conn, addr = server_socket.accept()
print("Da ket noi voi:", addr)

HOST_IR = '127.0.0.1'
PORT_IR = 8888
ir_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ir_server.bind((HOST_IR, PORT_IR))
ir_server.listen(1)
print("Dang doi ket noi voi ir_parking.py...")
ir_conn, ir_addr = ir_server.accept()
print("Da ket noi voi ir_parking.py", ir_addr)

try:
    while True:
        ir1 = GPIO.input(IR1_PIN)
        ir2 = GPIO.input(IR2_PIN)

        if ir1 == 0 and ir2 == 1:
            huong = 'vao'
        elif ir2 == 0 and ir1 == 1:
            huong = 'ra'
        else:
            time.sleep(0.1)
            continue

        print("Phat hien xe", huong)

        if huong == 'vao':
            conn.sendall(b"PROCESS_CAM1")
        elif huong == 'ra':
            conn.sendall(b"PROCESS_CAM0")

        plate = conn.recv(1024).decode().strip().upper()
        print("Bien so doc duoc:", plate)

        if plate in tap_hop_bien_so:
            print("Bien so hop le, mo cong")
            conn.sendall(b"OPEN")

            mo_cong()
            while GPIO.input(IR1_PIN) == 0 or GPIO.input(IR2_PIN) == 0:
                time.sleep(0.1)
            print("Xe da qua cong")
            time.sleep(1)
            dong_cong()

            try:
                ir_conn.sendall(plate.encode())
                print("Da gui bien so", plate, "cho ir_parking.py")

                msg = ir_conn.recv(1024).decode().strip()
                if msg.startswith("OCCUPIED:"):
                    spot_id = int(msg.split(":")[1])
                    print("Vi tri bi chiem:", spot_id)

                    with open(duong_dan_json, "r") as f:
                        data = json.load(f)

                    cap_nhat = False
                    for v in data["vehicles"]:
                        if v["spot"] == spot_id and v["plate"].strip() == "":
                            v["plate"] = plate
                            v["time_in"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            cap_nhat = True
                            break

                    if cap_nhat:
                        with open(duong_dan_json, "w") as f:
                            json.dump(data, f, indent=4)
                        print(f"? Da cap nhat bien so {plate} vao spot {spot_id}")
                    else:
                        print(f"?? Vi tri {spot_id} da co bien so hoac khong tim thay.")

                else:
                    print("?? Khong nhan duoc thong tin OCCUPIED hop le")

            except Exception as e:
                print("? Loi khi cap nhat JSON:", e)

        else:
            print("? Bien so khong hop le:", plate)

except KeyboardInterrupt:
    print("Ket thuc chuong trinh.")

finally:
    pwm.stop()
    GPIO.cleanup()
    server_socket.close()
    ir_server.close()
