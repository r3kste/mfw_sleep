import socket
import struct
from datetime import datetime
import cv2
import numpy as np
import requests


class ESP32Cam_UDP:
    ESP_IP = "192.168.0.118"
    UDP_IP = "0.0.0.0"
    PORT = 6969
    HEADER_SIZE = 4  # 2B total packets, 2B packet number
    BUFFER_SIZE = 1024

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.UDP_IP, self.PORT))
        self.current_image = bytearray()
        self.expected_packets = 0
        self.received_packets = 0
        print(f"Listening for ESP32-CAM images on UDP port {self.PORT}...")

    def send(self, message):
        message = message.encode("utf-8")
        self.sock.sendto(message, (ESP32Cam_UDP.ESP_IP, ESP32Cam_UDP.PORT))
        print(f"Sent: {message}")

    def stream(self):
        while True:
            data, addr = self.sock.recvfrom(ESP32Cam_UDP.BUFFER_SIZE)
            header = data[: self.HEADER_SIZE]
            payload = data[self.HEADER_SIZE :]

            total_packets = struct.unpack(">H", header[:2])[0]
            packet_num = struct.unpack(">H", header[2:4])[0]

            if packet_num == 0:
                self.current_image = bytearray()
                self.expected_packets = total_packets
                self.received_packets = 0

            self.current_image.extend(payload)
            self.received_packets += 1

            if self.received_packets == self.expected_packets:
                np_image = np.frombuffer(self.current_image, dtype=np.uint8)
                frame = cv2.imdecode(np_image, cv2.IMREAD_COLOR)

                if frame is not None:
                    cv2.imshow("ESP32-CAM", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                else:
                    print("Failed to decode image")

                self.current_image = bytearray()
                self.expected_packets = 0
                self.received_packets = 0

    def recv_text(self):
        data, addr = self.sock.recvfrom(ESP32Cam_UDP.BUFFER_SIZE)
        print(f"Received {data} from {addr}")


class ESP32Cam_HTTP:
    ESP_IP = "192.168.0.118"

    def __init__(self):
        self.url = f"http://{ESP32Cam_HTTP.ESP_IP}/capture"
        print(f"Listening for ESP32-CAM images on HTTP {self.url}...")

    def stream(self):
        while True:
            response = requests.get(self.url, stream=True)
            if response.status_code == 200:
                image = np.array(bytearray(response.content), dtype=np.uint8)
                frame = cv2.imdecode(image, cv2.IMREAD_COLOR)

                if frame is not None:
                    cv2.imshow("ESP32-CAM", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                else:
                    print("Failed to decode image")
            else:
                print(f"Failed to get image: {response.status_code}")


esp = ESP32Cam_UDP()
esp.stream()
