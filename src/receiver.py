import socket
import struct
import threading
import time
import queue

import cv2
import numpy as np


class ESP32Cam_UDP:
    ESP_IP = "192.168.0.103"
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
        self.frame_queue = queue.Queue(maxsize=10)  # Queue for frames
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

                # Start a thread to send periodic ACKs
                threading.Thread(target=self._send_periodic_ack, daemon=True).start()
            else:
                print("Unexpected response during handshake.")
        except socket.timeout:
            print("Handshake failed: No response from sender.")
            self.connected = False

    def _send_periodic_ack(self):
        """Send periodic ACK packets to keep the sender from timing out."""
        while self.connected:
            self.send("ACK")
            time.sleep(0.5)  # Send ACK every 0.5 seconds

    def receive_packets(self):
        """Receive and assemble image packets."""
        while self.connected:
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
                current_image = bytearray()
                for i in range(self.expected_packets):
                    if i in self.current_packets:
                        current_image.extend(self.current_packets[i])
                    else:
                        print("Missing packet, dropping frame")
                        self.current_packets = {}
                        self.expected_packets = 0
                        break
                else:
                    # Add the frame to the queue
                    self.frame_queue.put(current_image)
                    self.current_packets = {}
                    self.expected_packets = 0

    def display_frames(self):
        """Display frames using OpenCV."""
        while True:
            frame_data = self.frame_queue.get()
            np_image = np.frombuffer(frame_data, dtype=np.uint8)
            frame = cv2.imdecode(np_image, cv2.IMREAD_COLOR)
            frame = cv2.flip(frame, 0)

            if frame is not None:
                cv2.imshow("ESP32-CAM", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            else:
                print("Failed to decode image")

        cv2.destroyAllWindows()

    def stream(self):
        """Start the streaming process."""
        if not self.connected:
            print("Not connected to sender. Aborting stream.")
            return

        # Start threads for receiving packets and displaying frames
        threading.Thread(target=self.receive_packets, daemon=True).start()
        self.display_frames()


esp = ESP32Cam_UDP()
esp.handshake()
if esp.connected:
    esp.stream()
