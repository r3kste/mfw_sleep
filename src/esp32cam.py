import queue
import socket
import struct
import threading
import time

import cv2
import numpy as np

import config


class ESP32Cam:
    def __init__(
        self,
        ip: str,
        port: int,
        header_size: int = config.HEADER_SIZE,
        buffer_size: int = config.BUFFER_SIZE,
    ):
        self.ip = ip
        self.udp_ip = "0.0.0.0"
        self.port = port
        self.header_size = header_size
        self.buffer_size = buffer_size

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.udp_ip, self.port))
        self.current_packets = {}
        self.expected_packets = 0
        self.connected = False
        self.frame_queue = queue.Queue(maxsize=10)
        self.open_frames = []
        self.close_frames = []
        self.is_eye_open = True
        print(f"Listening for ESP32-CAM images on UDP port {self.port}")

    def send(self, message: str):
        message = message.encode("utf-8")
        self.sock.sendto(message, (self.ip, self.port))

    def handshake(self):
        """Perform the initial handshake with the sender."""
        print("Starting handshake")
        self.send("HELLO")
        self.sock.settimeout(5)
        try:
            data, addr = self.sock.recvfrom(self.buffer_size)
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
            time.sleep(0.5)

    def receive_packets(self):
        """Receive and assemble image packets."""
        while self.connected:
            data, addr = self.sock.recvfrom(self.buffer_size)
            header = data[: self.header_size]
            payload = data[self.header_size :]

            total_packets = struct.unpack(">H", header[:2])[0]
            packet_num = struct.unpack(">H", header[2:4])[0]

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
                    self.frame_queue.put(current_image)
                    self.current_packets = {}
                    self.expected_packets = 0

    def process_frame(self, frame_data):
        np_image = np.frombuffer(frame_data, dtype=np.uint8)
        frame = cv2.imdecode(np_image, cv2.IMREAD_COLOR)
        frame = cv2.flip(frame, 0)
        return frame

    def display_frames(self, record: bool = False):
        while True:
            frame_data = self.frame_queue.get()
            frame = self.process_frame(frame_data)

            if frame is not None:
                cv2.imshow("ESP32-CAM", frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                elif key == ord("c"):
                    # Toggle eye state
                    self.is_eye_open = not self.is_eye_open
                    print(
                        "Eye state toggled:", "Open" if self.is_eye_open else "Closed"
                    )

                if self.is_eye_open:
                    self.open_frames.append(frame)
                else:
                    self.close_frames.append(frame)
            else:
                print("Failed to decode image")

        cv2.destroyAllWindows()
        if record:
            print("Recording frames")
            self.save_frames()

    def save_frames(self):
        """Save collected frames to the output folder."""
        import os
        import shutil

        output_dir = config.RECORDED_FRAMES_DIR
        if not os.path.exists(output_dir):
            print(f"Creating output directory: {output_dir}")
            os.makedirs(output_dir)
        else:
            print(f"Clearing existing frames in {output_dir}")
            shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        open_dir = os.path.join(output_dir, "open")
        close_dir = os.path.join(output_dir, "close")

        os.makedirs(open_dir, exist_ok=True)
        os.makedirs(close_dir, exist_ok=True)

        for i, frame in enumerate(self.open_frames):
            cv2.imwrite(os.path.join(open_dir, f"open_{i}.jpg"), frame)

        for i, frame in enumerate(self.close_frames):
            cv2.imwrite(os.path.join(close_dir, f"close_{i}.jpg"), frame)

        print(
            f"Saved {len(self.open_frames)} open eye frames and {len(self.close_frames)} closed eye frames."
        )

    def stream(self, record=False):
        """Start the streaming process."""
        if not self.connected:
            print("Not connected to sender. Aborting stream.")
            return

        print("Starting stream")
        # Start threads for receiving packets and displaying frames
        threading.Thread(target=self.receive_packets, daemon=True).start()
        self.display_frames(record)


def main(esp: ESP32Cam):
    esp.handshake()
    if esp.connected:
        esp.stream(record=True)
    else:
        print("Failed to connect to ESP32-CAM.")


if __name__ == "__main__":
    main()
