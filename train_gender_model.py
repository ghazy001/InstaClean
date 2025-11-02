# train_gender_model.py
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import json
import os

# ------------------- CONFIG -------------------
DATA_PATH = "dataname_clean.csv"  
MODEL_SAVE = "gender_model.pth"
VOCAB_SAVE = "vocab.json"
MAX_NAME_LEN = 20  
BATCH_SIZE = 64
EPOCHS = 10
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ------------------- DATASET -------------------
class NameDataset(Dataset):
    def __init__(self, names, labels, char_to_idx, max_len):
        self.names = names
        self.labels = labels
        self.char_to_idx = char_to_idx
        self.max_len = max_len

    def __len__(self):
        return len(self.names)

    def __getitem__(self, idx):
        name = self.names[idx].lower()
        label = 1 if self.labels[idx].lower() == "female" else 0  # 1=female, 0=male

        # One-hot encode chars
        seq = [self.char_to_idx.get(c, 0) for c in name[:self.max_len]]
        seq += [0] * (self.max_len - len(seq))  # pad with 0
        return torch.tensor(seq, dtype=torch.long), torch.tensor(label, dtype=torch.float)

# ------------------- MODEL -------------------
class GenderCNN(nn.Module):
    def __init__(self, vocab_size, embed_dim=32, num_filters=64):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.conv1 = nn.Conv1d(embed_dim, num_filters, kernel_size=3, padding=1)
        self.conv2 = nn.Conv1d(num_filters, num_filters, kernel_size=3, padding=1)
        self.pool = nn.AdaptiveMaxPool1d(1)
        self.fc = nn.Linear(num_filters, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.embedding(x)                # (B, L, E)
        x = x.transpose(1, 2)                # (B, E, L)
        x = torch.relu(self.conv1(x))
        x = torch.relu(self.conv2(x))
        x = self.pool(x).squeeze(-1)         # (B, F)
        x = self.fc(x).squeeze(-1)           # (B)
        return self.sigmoid(x)

# ------------------- TRAIN -------------------
def train():
    print("Loading data...")
    df = pd.read_csv(DATA_PATH)
    df = df.dropna()
    df = df[df['name'].str.len() >= 2]

    # Build vocab (all unique chars in names)
    chars = set(''.join(df['name'].str.lower()))
    char_to_idx = {c: i+1 for i, c in enumerate(sorted(chars))}
    char_to_idx[''] = 0  # padding
    vocab_size = len(char_to_idx)
    with open(VOCAB_SAVE, 'w', encoding='utf-8') as f:
        json.dump(char_to_idx, f, ensure_ascii=False)

    # Split data
    train_names, val_names, train_labels, val_labels = train_test_split(
        df['name'].tolist(), df['gender'].tolist(), test_size=0.2, random_state=42
    )

    train_ds = NameDataset(train_names, train_labels, char_to_idx, MAX_NAME_LEN)
    val_ds = NameDataset(val_names, val_labels, char_to_idx, MAX_NAME_LEN)
    train_dl = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_dl = DataLoader(val_ds, batch_size=BATCH_SIZE)

    model = GenderCNN(vocab_size).to(DEVICE)
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    print(f"Training on {DEVICE} | {len(train_ds)} samples")
    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0
        for x, y in train_dl:
            x, y = x.to(DEVICE), y.to(DEVICE)
            pred = model(x)
            loss = criterion(pred, y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"Epoch {epoch+1}/{EPOCHS} | Loss: {total_loss/len(train_dl):.4f}")

        # Validation (optional)
        model.eval()
        correct = 0
        with torch.no_grad():
            for x, y in val_dl:
                x, y = x.to(DEVICE), y.to(DEVICE)
                pred = model(x).round()
                correct += (pred == y).sum().item()
        print(f"Validation Accuracy: {correct / len(val_ds):.2f}")

    # Save model
    torch.save(model.state_dict(), MODEL_SAVE)
    print(f"Model saved: {MODEL_SAVE}, {VOCAB_SAVE}")

if __name__ == "__main__":
    train()