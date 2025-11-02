# test_model.py
import torch
import json
import re

MODEL_PATH = "gender_model.pth"
VOCAB_PATH = "vocab.json"
MAX_NAME_LEN = 20
DEVICE = "cpu"

class GenderCNN(torch.nn.Module):
    def __init__(self, vocab_size, embed_dim=32, num_filters=64):
        super().__init__()
        self.embedding = torch.nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.conv1 = torch.nn.Conv1d(embed_dim, num_filters, kernel_size=3, padding=1)
        self.conv2 = torch.nn.Conv1d(num_filters, num_filters, kernel_size=3, padding=1)
        self.pool = torch.nn.AdaptiveMaxPool1d(1)
        self.fc = torch.nn.Linear(num_filters, 1)
        self.sigmoid = torch.nn.Sigmoid()

    def forward(self, x):
        x = self.embedding(x)
        x = x.transpose(1, 2)
        x = torch.relu(self.conv1(x))
        x = torch.relu(self.conv2(x))
        x = self.pool(x).squeeze(-1)
        x = self.fc(x).squeeze(-1)
        return self.sigmoid(x)

# Load model and vocab
with open(VOCAB_PATH, 'r', encoding='utf-8') as f:
    char_to_idx = json.load(f)
vocab_size = len(char_to_idx)
model = GenderCNN(vocab_size).to(DEVICE)
model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
model.eval()

def predict_gender(name: str) -> dict:
    if not name or len(name) < 2:
        return {"name": name, "gender": None, "probability": 0, "count": 0}
    # Clean name
    name = re.sub(r'[^a-zA-Z\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF ]', '', name.lower())[:MAX_NAME_LEN]
    seq = [char_to_idx.get(c, 0) for c in name]
    seq += [0] * (MAX_NAME_LEN - len(seq))
    x = torch.tensor([seq], dtype=torch.long).to(DEVICE)
    with torch.no_grad():
        prob = model(x).item()
    gender = "female" if prob > 0.5 else "male"
    conf = prob if gender == "female" else (1 - prob)
    return {"name": name, "gender": gender, "probability": round(conf, 3), "count": 0}

# Test
print(predict_gender("Sirine"))
print(predict_gender("Yassine"))
print(predict_gender("Fatima"))
print(predict_gender("أماني"))  # Arabic example