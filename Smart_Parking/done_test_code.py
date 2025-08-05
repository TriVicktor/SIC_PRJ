#!/usr/bin/env python
# coding: utf-8

# In[2]:


import time
import cv2
import numpy as np
import socket
from code_detect import detect_and_recognize_plate

PI_HOST = '172.172.29.112'
PI_PORT = 9999


# In[ ]:


def connect_to_pi():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((PI_HOST, PI_PORT))
        print("[PC] ✅ Đã kết nối tới Pi.")
        return client
    except Exception as e:
        print("[PC] ❌ Lỗi kết nối tới Pi:", e)
        return None

def main():
    cap_laptop = cv2.VideoCapture(0)
    cap_usb = cv2.VideoCapture(1)

    for cap in [cap_laptop, cap_usb]:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

    if not cap_laptop.isOpened() and not cap_usb.isOpened():
        print("[PC] ❌ Không mở được bất kỳ camera nào.")
        return

    client = connect_to_pi()
    if client is None:
        return

    client.settimeout(0.5)  # Thử nhận lệnh mỗi 0.5 giây
    print("[PC] 🟢 Đang chờ lệnh từ Raspberry Pi.")

    while True:
        try:
            # Cho phép nhấn phím 'q' để thoát vòng lặp
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("[PC] 👋 Đã nhấn phím 'q'. Thoát chương trình.")
                break

            try:
                data = client.recv(1024).decode().strip()
            except socket.timeout:
                continue  # Không có lệnh → tiếp tục vòng lặp

            if not data:
                continue

            print(f"[PC] 📩 Nhận lệnh từ Pi: {data}")

            if data == "IR1_ON":
                print("[PC] 🔔 IR1 bật – sử dụng camera USB (cam 1)")
                time.sleep(2)
                ret, frame = cap_usb.read()
                if ret:
                    cv2.imwrite("frame_cam1.jpg", frame)
                    plate = detect_and_recognize_plate("frame_cam1.jpg")
                    print("[PC] ✅ Biển số:", plate)
                    client.sendall(f"PLATE:{plate}".encode())
                else:
                    print("[PC] ❌ Không đọc được ảnh từ cam 1")
                continue

            elif data == "IR2_ON":
                print("[PC] 🔔 IR2 bật – sử dụng camera laptop (cam 0)")
                time.sleep(2)
                ret, frame = cap_laptop.read()
                if ret:
                    cv2.imwrite("frame_cam0.jpg", frame)
                    plate = detect_and_recognize_plate("frame_cam0.jpg")
                    print("[PC] ✅ Biển số:", plate)
                    client.sendall(f"PLATE:{plate}".encode())
                else:
                    print("[PC] ❌ Không đọc được ảnh từ cam 0")
                continue

            elif data == "PROCESS_CAM1":
                print("[PC] 📷 Live Cam 1 - Nhấn 'c' để chụp, 'q' để thoát")
                while True:
                    ret, frame = cap_usb.read()
                    if ret:
                        cv2.imshow("Cam 1", frame)
                        key = cv2.waitKey(1) & 0xFF
                        if key == ord('c'):
                            cv2.imwrite("frame_cam1.jpg", frame)
                            print("[PC] 📸 Đã chụp ảnh từ cam 1")
                            break
                        elif key == ord('q'):
                            print("[PC]  ❌ Hủy chụp cam 1")
                            client.sendall(b"UNKNOWN")
                            break
                try:
                    cv2.destroyWindow("Cam 1")
                except:
                    pass

                plate = detect_and_recognize_plate("frame_cam1.jpg")
                if plate and plate.strip():
                    client.sendall(plate.strip().upper().encode())
                    print("[PC] ✅ Gửi biển số:", plate)
                else:
                    print("[PC] ❌ Không nhận diện được biển số.")
                    client.sendall(b"UNKNOWN")
                continue

            elif data == "PROCESS_CAM0":
                print("[PC] 📷 Live Cam 0 - Nhấn 'c' để chụp, 'q' để thoát")
                while True:
                    ret, frame = cap_laptop.read()
                    if ret:
                        cv2.imshow("Cam 0", frame)
                        key = cv2.waitKey(1) & 0xFF
                        if key == ord('c'):
                            cv2.imwrite("frame_cam0.jpg", frame)
                            print("[PC] 📸 Đã chụp ảnh từ cam 0")
                            break
                        elif key == ord('q'):
                            print("[PC] ❌ Hủy chụp cam 0")
                            client.sendall(b"UNKNOWN")
                            break
                try:
                    cv2.destroyWindow("Cam 0")
                except:
                    pass

                plate = detect_and_recognize_plate("frame_cam0.jpg")
                if plate and plate.strip():
                    client.sendall(plate.strip().upper().encode())
                    print("[PC] ✅ Gửi biển số:", plate)
                else:
                    print("[PC] ❌ Không nhận diện được biển số.")
                    client.sendall(b"UNKNOWN")
                continue

            else:
                print("[PC] Xác nhận lệnh:", data)
                continue  # QUAN TRỌNG: quay lại vòng lặp để tiếp tục nhận lệnh

        except Exception as e:
            print("[PC] ❌ Lỗi khi xử lý lệnh:", e)
            break

    # Dọn tài nguyên
    cap_laptop.release()
    cap_usb.release()
    client.close()
    try:
        cv2.destroyAllWindows()
    except:
        pass

if __name__ == "__main__":
    main()

    


# In[ ]:




