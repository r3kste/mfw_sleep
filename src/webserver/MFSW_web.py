from flask import Flask, jsonify, send_file
from flask_cors import CORS  # Import Flask-CORS
import socket
import threading
import os
import pygame

from flask_socketio import SocketIO

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

socketio = SocketIO(app, cors_allowed_origins="*")  # Allow all origins for WebSocket connections


# UDP server configuration
UDP_IP = "0.0.0.0"
UDP_PORT = 5005
BUFFER_SIZE = 1024
alarm_triggered = False
is_alarm_playing = False


def udp_listener():
    global alarm_triggered
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow address reuse
    sock.bind((UDP_IP, UDP_PORT))
    print(f"Listening for UDP packets on {UDP_IP}:{UDP_PORT}...")
    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)
        message = data.decode("utf-8")
        print(f"Received message: {message}")
        if message == "GUY_DEAD":
            alarm_triggered = True
            print("Buzzer state updated: ON")
            # Notify the frontend via WebSocket
            socketio.emit("buzzer_update", {"buzzer_on": True})


def broadcast_message(message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(message.encode("utf-8"), ("255.255.255.255", UDP_PORT))
    print(f"Broadcasted message: {message}")


@app.route("/camera/start", methods=["GET"])
def start_camera():
    print("Sending camera start command")
    broadcast_message("CAM_ON")
    return "Camera started", 200


@app.route("/camera/stop", methods=["GET"])
def stop_camera():
    print("Sending camera stop command")
    broadcast_message("CAM_OFF")
    return "Camera stopped", 200


@app.route("/buzzer/state", methods=["GET"])
def get_buzzer_state():
    global alarm_triggered
    return jsonify({"buzzer_on": alarm_triggered})


@app.route("/buzzer/stop", methods=["GET"])
def stop_buzzer():
    global alarm_triggered
    alarm_triggered = False
    print("Buzzer state updated: OFF")
    socketio.emit("buzzer_update", {"buzzer_on": False})
    return "Buzzer stopped", 200


# @app.route("/alarm/start", methods=["GET"])
# def start_alarm():
#     global is_alarm_playing
#     print("Alarm started")
#     if not is_alarm_playing:
#         is_alarm_playing = True
#         threading.Thread(target=play_alarm, daemon=True).start()
#     return "Alarm started", 200


# @app.route("/alarm/stop", methods=["GET"])
# def stop_alarm():
#     global is_alarm_playing
#     is_alarm_playing = False
#     return "Alarm stopped", 200


# def play_alarm():
#     global is_alarm_playing
#     alarm_file = os.path.join(app.root_path, "static", "alarm.mp3")
#     pygame.mixer.init()
#     while is_alarm_playing:
#         if os.path.exists(alarm_file):
#             pygame.mixer.music.load(alarm_file)
#             pygame.mixer.music.play()
#             while pygame.mixer.music.get_busy() and is_alarm_playing:
#                 pygame.time.Clock().tick(10)
#         else:
#             print("Alarm file not found")
#             break
#     pygame.mixer.music.stop()


if __name__ == "__main__":
    threading.Thread(target=udp_listener, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=8080, debug=True)
