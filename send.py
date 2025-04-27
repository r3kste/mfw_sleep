import socket
import time

UDP_IP = "255.255.255.255"  # Broadcast address
UDP_PORT = 5005
MESSAGE = "GUY_DEAD"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enable broadcasting
while True:
    sock.sendto(MESSAGE.encode("utf-8"), (UDP_IP, UDP_PORT))
    print(f"Sent message: {MESSAGE} to {UDP_IP}:{UDP_PORT}")
    time.sleep(1)
