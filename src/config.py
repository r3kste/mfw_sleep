import os

IP = "192.168.0.103"
PORT = 6969
HEADER_SIZE = 4
BUFFER_SIZE = 1024

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# /mfw_sleep/trained
TRAINED_MODELS_DIR = os.path.join(PROJECT_DIR, "trained")  

# /mfw_sleep/output
RECORDED_FRAMES_DIR = os.path.join(PROJECT_DIR, "output")

subfolders = {
    "open": 1,
    "close": 0,
}

batch_size = 16
num_epochs = 10
learning_rate = 0.001
