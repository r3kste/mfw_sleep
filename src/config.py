import os

IP = "192.168.29.131"
PORT = 6969
HEADER_SIZE = 4
BUFFER_SIZE = 1024

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# /mfw_sleep/trained
TRAINED_MODELS_DIR = os.path.join(PROJECT_DIR, "trained")
if not os.path.exists(TRAINED_MODELS_DIR):
    os.makedirs(TRAINED_MODELS_DIR)

# /mfw_sleep/output
RECORDED_FRAMES_DIR = os.path.join(PROJECT_DIR, "output")
if not os.path.exists(RECORDED_FRAMES_DIR):
    os.makedirs(RECORDED_FRAMES_DIR)

subfolders = {
    "open": 1,
    "close": 0,
}

# subfolders = {
#     "full_open": 1,
#     "part_open": 0.75,
#     "half_open": 0.5,
#     "full_close": 0,
# }

batch_size = 16
num_epochs = 10
learning_rate = 0.001
weight_decay = 0

# If lower than this, the image is considered dark
BRIGHTNESS_THRESHOLD_MIN = 50
# If higher than this, the image is considered bright
BRIGHTNESS_THRESHOLD_MAX = 75
# between these values [128, 192] the image will retain its previous state (dark or bright)
