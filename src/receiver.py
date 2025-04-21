import socket
import struct
import cv2
import numpy as np


class ESP32Cam_UDP:
    ESP_IP = "192.168.0.118"
    UDP_IP = "0.0.0.0"
    PORT = 6969
    HEADER_SIZE = 4  # 2B total packets, 2B packet number
    BUFFER_SIZE = 1024

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.UDP_IP, self.PORT))
        self.current_packets = {}
        self.expected_packets = 0
        self.connected = False
        print(f"Listening for ESP32-CAM images on UDP port {self.PORT}...")

    def send(self, message):
        message = message.encode("utf-8")
        self.sock.sendto(message, (ESP32Cam_UDP.ESP_IP, ESP32Cam_UDP.PORT)) 

    def handshake(self):
        """Perform the initial handshake with the sender."""
        print("Starting handshake...")
        self.send("HELLO")
        self.sock.settimeout(5)  # Wait for up to 5 seconds for a response
        try:
            data, addr = self.sock.recvfrom(ESP32Cam_UDP.BUFFER_SIZE)
            if data.decode("utf-8") == "ACK":
                self.connected = True
                print("Handshake successful. Connected to sender.")
            else:
                print("Unexpected response during handshake.")
        except socket.timeout:
            print("Handshake failed: No response from sender.")
            self.connected = False

    def stream(self):
        """Receive and process image packets."""
        if not self.connected:
            print("Not connected to sender. Aborting stream.")
            return

        while True:
            data, addr = self.sock.recvfrom(ESP32Cam_UDP.BUFFER_SIZE)
            header = data[: ESP32Cam_UDP.HEADER_SIZE]
            payload = data[ESP32Cam_UDP.HEADER_SIZE :]

            total_packets = struct.unpack(">H", header[:2])[0]
            packet_num = struct.unpack(">H", header[2:4])[0]

            # Send acknowledgment for the received packet
            self.send("ACK")

            if packet_num == 0:
                self.current_packets = {}
                self.expected_packets = total_packets

            self.current_packets[packet_num] = payload

            if len(self.current_packets) == self.expected_packets:
                # Check if all packets are received
                if len(self.current_packets) == self.expected_packets:
                    # Merge packets in order
                    self.current_image = bytearray()
                    for i in range(self.expected_packets):
                        if i in self.current_packets:
                            self.current_image.extend(self.current_packets[i])
                        else:
                            print("Missing packet, dropping frame")
                            self.current_packets = {}
                            self.expected_packets = 0
                            break
                    else:
                        # Decode and display the image
                        np_image = np.frombuffer(self.current_image, dtype=np.uint8)
                        frame = cv2.imdecode(np_image, cv2.IMREAD_COLOR)

                        if frame is not None:
                            cv2.imshow("ESP32-CAM", frame)
                            if cv2.waitKey(1) & 0xFF == ord("q"):
                                break
                        else:
                            print("Failed to decode image")
                else:
                    print("Incomplete frame, dropping")
                self.current_packets = {}
                self.expected_packets = 0

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
esp.handshake()  # Perform the handshake before starting the stream
if esp.connected:
    esp.stream()