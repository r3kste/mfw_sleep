import argparse

import esp32cam
import predictor
from model import train
import config


def main():
    parser = argparse.ArgumentParser(description="ESP32-CAM Eye Openness Detection")
    parser.add_argument(
        "-u", "--user", type=str, default="anton", help="User name for the model"
    )
    parser.add_argument(
        "--ip", type=str, default=config.IP, help="IP address of the ESP32-CAM"
    )
    parser.add_argument(
        "-p", "--port", type=int, default=config.PORT, help="Port number for UDP"
    )

    esp = esp32cam.ESP32Cam(
        ip=parser.parse_args().ip,
        port=parser.parse_args().port,
    )
    esp.handshake()
    if not esp.connected:
        print("Failed to connect to ESP32-CAM. Exiting.")
        return

    esp32cam.main(esp)
    train.main(user=parser.parse_args().user)
    predictor.main(esp, user=parser.parse_args().user)
    esp.send("LED_0")


if __name__ == "__main__":
    main()
