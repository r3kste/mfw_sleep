import os

import torch
import torch.nn as nn
import torch.optim as optim
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

import config


class EyeDataset(Dataset):
    def __init__(self, root_dir, subfolders, transform=None):
        self.data = []
        self.labels = []
        self.transform = transform

        for subfolder, label in subfolders.items():
            folder_path = os.path.join(root_dir, subfolder)
            for filename in os.listdir(folder_path):
                if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    self.data.append(os.path.join(folder_path, filename))
                    self.labels.append(label)

        print(f"Loaded {len(self.data)} images from {len(subfolders)} subfolders.")

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        image_path = self.data[idx]
        label = self.labels[idx]
        image = Image.open(image_path).convert("RGB")

        if self.transform:
            image = self.transform(image)

        return image, torch.tensor(label, dtype=torch.float32)


class EyeOpennessModel(nn.Module):
    def __init__(self):
        super(EyeOpennessModel, self).__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(16, 32, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
        )
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(32 * 64 * 64, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        x = self.conv(x)
        x = self.fc(x)
        return x


def main(user: str):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    root_dir = config.RECORDED_FRAMES_DIR
    batch_size = config.batch_size
    num_epochs = config.num_epochs
    learning_rate = config.learning_rate

    transform = transforms.Compose(
        [
            transforms.Resize((256, 256)),
            transforms.ToTensor(),
        ]
    )

    dataset = EyeDataset(root_dir, config.subfolders, transform=transform)

    train_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model = EyeOpennessModel().to(device)
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    print("Starting training...")
    for epoch in range(num_epochs):
        model.train()
        train_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs.squeeze(), labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        print(
            f"Epoch {epoch + 1}/{num_epochs}, Train Loss: {train_loss / len(train_loader):.4f}"
        )

    print("Training complete.")

    torch.save(
        model.state_dict(), os.path.join(config.TRAINED_MODELS_DIR, f"{user}.pth")
    )
    print(f"Model saved as {user}.pth")


if __name__ == "__main__":
    main()
