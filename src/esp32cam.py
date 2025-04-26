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
        self.frames = {
            key: [] for key in config.subfolders.keys()
        }  # Initialize frames for each subfolder
        self.current_state = None
        self.ir_status = None
        print(f"Listening for ESP32-CAM images on UDP port {self.port}")

    def send(self, message: str):
        message = message.encode("utf-8")
        self.sock.sendto(message, (self.ip, self.port))

    def handshake(self):
        """Perform the initial handshake with the sender."""
        print("Waiting for ESP32-CAM broadcast...")
        self.sock.settimeout(10)
        try:
            while True:
                data, addr = self.sock.recvfrom(self.buffer_size)
                if data.decode("utf-8") == "I_AM_THE_CAMERA":
                    self.ip = addr[0]
                    print(f"ESP32-CAM found at {self.ip}. Starting handshake.")
                    break
        except socket.timeout:
            print("Failed to detect ESP32-CAM broadcast. Aborting handshake.")
            self.connected = False
            return

        # Proceed with the handshake
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

            self.send("ACK")

            # Parse the header
            total_packets = struct.unpack(">H", header[:2])[0]
            packet_num = struct.unpack(">H", header[2:4])[0]
            ir_status = header[4]  # Extract the IR sensor status (5th byte)

            # Store the IR status in a variable
            self.ir_status = ir_status
            print(f"Received IR status: {self.ir_status}")

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

    @staticmethod
    def calculate_brightness(frame):
        """Calculate the average brightness of the frame."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return gray.mean()

    def display_frames(self, record: bool = False):
        while True:
            frame_data = self.frame_queue.get()
            frame = self.process_frame(frame_data)

            if frame is not None:
                cv2.imshow("ESP32-CAM", frame)

                # Calculate brightness and determine LED state
                brightness = self.calculate_brightness(frame)
                self.send(f"LED_{255 - int(brightness)}")
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                elif key in [ord(str(i)) for i in range(1, len(config.subfolders) + 1)]:
                    # Change state based on key press
                    state_index = int(chr(key)) - 1
                    self.current_state = list(config.subfolders.keys())[state_index]
                    print(f"State changed to: {self.current_state}")

                # Save frames based on the current state
                if self.current_state is not None:
                    self.frames[self.current_state].append(frame)
            else:
                print("Failed to decode image")

        cv2.destroyAllWindows()
        if record and self.current_state is not None:
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

        for state, frames in self.frames.items():
            state_dir = os.path.join(output_dir, state)
            os.makedirs(state_dir, exist_ok=True)
            for i, frame in enumerate(frames):
                cv2.imwrite(os.path.join(state_dir, f"{state}_{i}.jpg"), frame)

        print(f"Saved frames for states: {', '.join(self.frames.keys())}")

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
    esp.stream(record=True)


if __name__ == "__main__":
    main()
