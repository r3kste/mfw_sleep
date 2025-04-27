import socket

# Sending a warning manually for testing purposes.
HOST = '255.255.255.255'  # Example: localhost
PORT =    5005     # Example: port number

def send_message():
    message = "GUY_DEAD"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enable broadcasting
            s.sendto(message.encode('utf-8'), (HOST, PORT))
            print(f"Message '{message}' sent to {HOST}:{PORT} via UDP")
        except Exception as e:
            print(f"Failed to send message: {e}")

if __name__ == "__main__":
    send_message()
