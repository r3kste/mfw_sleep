import os
from collections import deque
from threading import Thread

import cv2
import matplotlib.pyplot as plt
import torch

import config
import esp32cam
from model.train import EyeOpennessModel


def preprocess_frame(frame):
    """Preprocess the frame for the model."""
    frame = cv2.resize(frame, (256, 256))
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = torch.tensor(frame, dtype=torch.float32).permute(2, 0, 1) / 255.0
    return frame.unsqueeze(0).to(device)


def update_graph():
    """Update the live graph."""
    plt.ion()
    fig, ax = plt.subplots()
    while True:
        ax.clear()
        ax.plot(prediction_history, label="Eye Openness")
        ax.set_ylim(-1, 2)
        ax.set_title("Live Prediction Graph")
        ax.set_xlabel("Time (frames)")
        ax.set_ylabel("Prediction")
        ax.legend()
        plt.pause(0.1)


def main(esp: esp32cam.ESP32Cam, user: str):
    global device, prediction_history
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = EyeOpennessModel().to(device)
    model.load_state_dict(
        torch.load(
            os.path.join(config.TRAINED_MODELS_DIR, f"{user}.pth"),
            map_location=device,
        )
    )
    model.eval()

    prediction_history = deque(maxlen=100)

    graph_thread = Thread(target=update_graph, daemon=True)
    graph_thread.start()

    frame_thread = Thread(target=esp.receive_packets, daemon=True)
    frame_thread.start()

    while True:
        if not esp.frame_queue.empty():
            frame_data = esp.frame_queue.get()
            frame = esp.process_frame(frame_data)

            if frame is not None:
                input_tensor = preprocess_frame(frame)
                with torch.no_grad():
                    prediction = model(input_tensor).item()

                prediction_history.append(prediction)

                # Overlay prediction on the frame
                cv2.putText(
                    frame,
                    f"Prediction: {prediction:.2f}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2,
                )

                cv2.imshow("ESP32-CAM Live Stream", frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
