# insta_clean_pretty.py
# Full app: login-first modal + prettier UI + per-account tokens & cache + dashboard + unfollow
# Now with local PyTorch gender model (no API limits)
import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import threading
import time
import random
import webbrowser
import traceback
import os
import sys
# For charting
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# For local model
import torch
import re

# ---- Local Model Files (must be in same folder) ----
MODEL_PATH = "gender_model.pth"
VOCAB_PATH = "vocab.json"
MAX_NAME_LEN = 20
DEVICE = "cpu"

# Load vocab
if os.path.exists(VOCAB_PATH):
    with open(VOCAB_PATH, 'r', encoding='utf-8') as f:
        char_to_idx = json.load(f)
else:
    print("Error: vocab.json not found. Train the model first.")
    char_to_idx = {}

vocab_size = len(char_to_idx)

# Model class (same as training)
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

# Load model
if os.path.exists(MODEL_PATH):
    model = GenderCNN(vocab_size).to(DEVICE)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
    model.eval()
else:
    print("Error: gender_model.pth not found. Train the model first.")
    model = None

def predict_gender(name: str) -> dict:
    if not model or not name or len(name) < 2:
        return {"name": name, "gender": None, "probability": 0, "count": 0}
    # Clean name (keep Arabic/Unicode letters)
    name = re.sub(r'[^a-zA-Z\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF ]', '', name.lower())[:MAX_NAME_LEN]
    seq = [char_to_idx.get(c, 0) for c in name]
    seq += [0] * (MAX_NAME_LEN - len(seq))
    x = torch.tensor([seq], dtype=torch.long).to(DEVICE)
    with torch.no_grad():
        prob = model(x).item()
    gender = "female" if prob > 0.5 else "male"
    conf = prob if gender == "female" else (1 - prob)
    return {"name": name, "gender": gender, "probability": round(conf, 3), "count": 0}

# ---- DEFAULT TOKENS (prefilled; can be changed in Login modal) ----
DEFAULT_CSRFTOKEN = ""
DEFAULT_SESSIONID = ""
DEFAULT_DS_USER_ID = ""

# ---- Filenames base (per-account) ----
TOKEN_FILE_BASE = "instacreds" # instacreds_<ds_user_id>.json
GENDER_CACHE_BASE = "gender_cache" # gender_cache_<ds_user_id>.json

# ---- Requests session & headers (will be updated by apply_tokens) ----
SESSION = requests.Session()
SESSION.headers.update({
"User-Agent": "Instagram 155.0.0.37.107",
"x-requested-with": "XMLHttpRequest",
"referer": "https://www.instagram.com/",
"accept": "*/*",
"accept-language": "en-US,en;q=0.9",
"content-type": "application/x-www-form-urlencoded; charset=UTF-8",
})

# Globals
CSRFTOKEN = DEFAULT_CSRFTOKEN
SESSIONID = DEFAULT_SESSIONID
DS_USER_ID = DEFAULT_DS_USER_ID
BASE_HEADERS = {
"x-csrftoken": CSRFTOKEN,
"User-Agent": SESSION.headers.get("User-Agent"),
"Referer": "https://www.instagram.com/"
}

# ---- Helpers: filenames per account ----
def token_filename_for(ds_user_id):
    return f"{TOKEN_FILE_BASE}_{ds_user_id}.json" if ds_user_id else f"{TOKEN_FILE_BASE}.json"

def cache_filename_for(ds_user_id):
    return f"{GENDER_CACHE_BASE}_{ds_user_id}.json" if ds_user_id else f"{GENDER_CACHE_BASE}.json"

# ---- Persist & apply tokens (per-account) ----
def apply_tokens(csrftoken, sessionid, ds_user_id):
    global CSRFTOKEN, SESSIONID, DS_USER_ID, BASE_HEADERS, GENDER_CACHE_FILE
    CSRFTOKEN = csrftoken or ""
    SESSIONID = sessionid or ""
    DS_USER_ID = ds_user_id or ""
    # set/clear cookies in requests session
    try:
        if SESSIONID:
            SESSION.cookies.set("sessionid", SESSIONID, domain=".instagram.com")
        else:
            SESSION.cookies.clear(domain=".instagram.com", name="sessionid")
    except Exception:
        pass
    try:
        if CSRFTOKEN:
            SESSION.cookies.set("csrftoken", CSRFTOKEN, domain=".instagram.com")
        else:
            SESSION.cookies.clear(domain=".instagram.com", name="csrftoken")
    except Exception:
        pass
    try:
        if DS_USER_ID:
            SESSION.cookies.set("ds_user_id", DS_USER_ID, domain=".instagram.com")
        else:
            SESSION.cookies.clear(domain=".instagram.com", name="ds_user_id")
    except Exception:
        pass
    BASE_HEADERS = {
"x-csrftoken": CSRFTOKEN,
"User-Agent": SESSION.headers.get("User-Agent"),
"Referer": "https://www.instagram.com/"
    }
    # save tokens to per-account file
    tf = token_filename_for(DS_USER_ID)
    try:
        with open(tf, "w", encoding="utf-8") as f:
            json.dump({"csrftoken": CSRFTOKEN, "sessionid": SESSIONID, "ds_user_id": DS_USER_ID}, f)
    except Exception as e:
        print("Failed to save tokens:", e)
    # set cache file name and load it
    load_gender_cache_into_global()

def load_tokens_if_exist():
    global CSRFTOKEN, SESSIONID, DS_USER_ID
    candidates = []
    if DEFAULT_DS_USER_ID:
        candidates.append(token_filename_for(DEFAULT_DS_USER_ID))
    candidates.append(token_filename_for(""))
    for tf in candidates:
        if os.path.exists(tf):
            try:
                with open(tf, "r", encoding="utf-8") as f:
                    d = json.load(f)
                apply_tokens(d.get("csrftoken", CSRFTOKEN), d.get("sessionid", SESSIONID), d.get("ds_user_id", DS_USER_ID))
                return
            except Exception:
                continue
    # if nothing found, apply defaults but don't save
    apply_tokens(CSRFTOKEN, SESSIONID, DS_USER_ID)

# ---- Genderize cache (per-account) ----
GENDER_CACHE = {}
GENDER_CACHE_FILE = cache_filename_for(DS_USER_ID)
def load_gender_cache_into_global():
    global GENDER_CACHE, GENDER_CACHE_FILE
    GENDER_CACHE_FILE = cache_filename_for(DS_USER_ID)
    if os.path.exists(GENDER_CACHE_FILE):
        try:
            with open(GENDER_CACHE_FILE, "r", encoding="utf-8") as f:
                GENDER_CACHE = json.load(f)
                GENDER_CACHE = {k.lower(): v for k, v in GENDER_CACHE.items()}
            return
        except Exception:
            GENDER_CACHE = {}
    else:
        GENDER_CACHE = {}

def save_gender_cache_global():
    global GENDER_CACHE, GENDER_CACHE_FILE
    try:
        with open(GENDER_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(GENDER_CACHE, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Failed to save gender cache:", e)

# load tokens & cache at startup (doesn't show UI)
load_tokens_if_exist()
load_gender_cache_into_global()

# ---- Instagram helpers ----
def fetch_users(query_hash, user_id, edge_type):
    url = "https://www.instagram.com/graphql/query/"
    results = []
    has_next = True
    end_cursor = None
    while has_next:
        variables = {
            "id": user_id,
            "include_reel": True,
            "fetch_mutual": False,
            "first": 50
        }
        if end_cursor:
            variables["after"] = end_cursor
        full_url = f"{url}?query_hash={query_hash}&variables={json.dumps(variables)}"
        try:
            res = SESSION.get(full_url, headers=BASE_HEADERS, timeout=15)
        except Exception as e:
            print("Network error fetching users:", e)
            break
        if res.status_code != 200:
            print(f"Non-200 while fetching users: {res.status_code} - {res.text[:200]}")
            break
        try:
            data = res.json()["data"]["user"][edge_type]
        except Exception as e:
            print("Failed to parse JSON while fetching users:", e)
            break
        edges = data.get("edges", [])
        for edge in edges:
            node = edge.get("node", {})
            results.append({
                "id": node.get("id"),
                "username": node.get("username"),
                "full_name": node.get("full_name")
            })
        page_info = data.get("page_info", {})
        has_next = page_info.get("has_next_page", False)
        end_cursor = page_info.get("end_cursor")
        time.sleep(1)
    return results

def get_nonfollowers():
    following_hash = "3dec7e2c57367ef3da3d987d89f9dbc8"
    followers_hash = "c76146de99bb02f6415203be841dd25a"
    following = fetch_users(following_hash, DS_USER_ID, "edge_follow")
    followers = fetch_users(followers_hash, DS_USER_ID, "edge_followed_by")
    follower_usernames = {u["username"] for u in followers if u.get("username")}
    nonfollowers = [u for u in following if u.get("username") not in follower_usernames]
    return nonfollowers

def fetch_followers_list():
    followers_hash = "c76146de99bb02f6415203be841dd25a"
    followers = fetch_users(followers_hash, DS_USER_ID, "edge_followed_by")
    return followers

def unfollow_user(user_id):
    url = f"https://www.instagram.com/web/friendships/{user_id}/unfollow/"
    try:
        res = SESSION.post(url, headers={"x-csrftoken": CSRFTOKEN, "Referer": "https://www.instagram.com/"}, timeout=15)
    except Exception as e:
        return False, None, f"Network exception: {e}"
    code = res.status_code
    text = res.text
    success = False
    try:
        j = res.json()
        success = (j.get("status") == "ok")
    except Exception:
        success = (code == 200)
    return success, code, text

# ---- Prepare name for model ----
def prepare_name_for_genderize(user):
    """
    Extract a sensible first-name token from the user's full_name or username.
    Normalizes common separators (underscore, dot, dash) into spaces so names
    like "Ghazi_sdi", "john.doe" or "mary-jane" yield "Ghazi", "john" and "mary".
    """
    def normalize_and_first_token(s):
        if not s:
            return ""
        # replace common non-letter separators with space
        for sep in ("_", ".", "-", "/"):
            s = s.replace(sep, " ")
        s = s.strip()
        if not s:
            return ""
        # take the first whitespace-separated token
        first = s.split()[0]
        # keep only alphabetic characters (protects against numbers/symbols)
        cleaned = ''.join([c for c in first if c.isalpha() or '\u0600' <= c <= '\u06FF'])  # Keep Arabic
        return cleaned or first

    full_name = (user.get("full_name") or "").strip()
    if full_name:
        token = normalize_and_first_token(full_name)
        return token[:50]

    username = (user.get("username") or "").strip()
    if username:
        token = normalize_and_first_token(username)
        return token[:50] if token else username[:50]
    return ""

# ---- Local Gender Prediction with Cache ----
def genderize_with_cache(names, progress_callback=None, cancel_event=None):
    global GENDER_CACHE
    results = []
    total = len(names)
    done = 0
    to_lookup = []
    lookup_indices = []
    for idx, n in enumerate(names):
        nkey = (n or "").lower()
        if nkey in GENDER_CACHE:
            results.append(GENDER_CACHE[nkey])
            done += 1
            if progress_callback:
                progress_callback(done, total)
        else:
            results.append(None)
            to_lookup.append(n)
            lookup_indices.append(idx)

    for i in range(len(to_lookup)):
        if cancel_event and cancel_event.is_set():
            break
        name = to_lookup[i]
        if not name:
            entry = {"name": name, "gender": None, "probability": 0, "count": 0}
        else:
            entry = predict_gender(name)
        key = name.lower()
        GENDER_CACHE[key] = entry
        original_idx = lookup_indices[i]
        results[original_idx] = entry
        done += 1
        if progress_callback:
            progress_callback(done, total)
    save_gender_cache_global()

    # Fill any None
    for idx, item in enumerate(results):
        if item is None:
            n = names[idx]
            results[idx] = {"name": n, "gender": None, "probability": 0, "count": 0}

    return results

# ---- PRETTY UI: styles & utilities ----
def setup_styles(root):
    style = ttk.Style(root)
    # try a modern-ish theme where available
    try:
        style.theme_use('clam')
    except Exception:
        pass
    # Colors
    primary = "#2e89ff"
    accent = "#E1306C"
    panel = "#1e1e1e"
    card = "#22272B"
    text = "#E6EDF3"
    subtext = "#B7C0C7"
    # Notebook style
    style.configure("TNotebook", background=panel, borderwidth=0)
    style.configure("TNotebook.Tab", background=card, foreground=text, padding=(12, 8))
    style.map("TNotebook.Tab", background=[("selected", primary)])
    # Button styles
    style.configure("Primary.TButton", background=primary, foreground="white", padding=(8,6), font=("Segoe UI", 10, "bold"))
    style.map("Primary.TButton", background=[("active", "#1e6fe8")])
    style.configure("Accent.TButton", background=accent, foreground="white", padding=(8,6), font=("Segoe UI", 10, "bold"))
    style.map("Accent.TButton", background=[("active", "#d63d73")])
    style.configure("Alt.TButton", background="#444", foreground="white", padding=(6,4), font=("Segoe UI", 9))
    # Progressbar
    style.configure("TProgressbar", troughcolor=card, background=primary, thickness=14)
    # Entry
    style.configure("TEntry", fieldbackground="#23282B", foreground=text)
    # Text widget uses normal tk config
    return {
"primary": primary,
"accent": accent,
"panel": panel,
"card": card,
"text": text,
"subtext": subtext
    }

# ---- APP CLASS ----
class InstaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("InstaClean — pretty")
        self.root.geometry("1020x880")
        self.root.configure(bg="#161616")
        self.colors = setup_styles(root)
        # Header
        header = tk.Frame(root, bg=self.colors["panel"], pady=8)
        header.pack(fill="x")
        logo = tk.Label(header, text="InstaClean", bg=self.colors["panel"], fg=self.colors["accent"], font=("Segoe UI", 18, "bold"))
        logo.pack(side="left", padx=14)
        subtitle = tk.Label(header, text="Manage followers · Dashboard", bg=self.colors["panel"], fg=self.colors["subtext"], font=("Segoe UI", 10))
        subtitle.pack(side="left", padx=8)
        # Top action row
        top_frame = tk.Frame(root, bg=self.colors["panel"])
        top_frame.pack(fill="x", padx=12, pady=(8,0))
        self.login_btn = ttk.Button(top_frame, text="🔐 Login / Tokens", style="Primary.TButton", command=self.open_login_modal)
        self.login_btn.pack(side="left", padx=(0,8))
        self.tip_btn = ttk.Button(top_frame, text="🛈 Where to get tokens?", style="Alt.TButton", command=self.show_token_tip)
        self.tip_btn.pack(side="left", padx=6)
        self.open_tokens_btn = ttk.Button(top_frame, text="📁 Open token file", style="Alt.TButton", command=self.open_token_file)
        self.open_tokens_btn.pack(side="left", padx=6)
        self.clear_btn = ttk.Button(top_frame, text="🧹 Clear tokens & cache", style="Alt.TButton", command=self.clear_tokens_and_cache)
        self.clear_btn.pack(side="left", padx=6)
        # Notebook (starts disabled until login)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill="both", padx=12, pady=12)
        # Unfollow and Dashboard frames — make them direct children of the Notebook
        self.unfollow_frame = tk.Frame(self.notebook, bg=self.colors["panel"])
        self.dashboard_frame = tk.Frame(self.notebook, bg=self.colors["panel"])
        # Add the frames as separate tabs (they are notebook children now)
        self.notebook.add(self.unfollow_frame, text="Unfollow")
        self.notebook.add(self.dashboard_frame, text="Dashboard")
        # Build both pages
        self._build_unfollow_tab()
        self._build_dashboard_tab()
        # Initially disable the notebook until tokens applied
        self._set_notebook_enabled(False)
        # If tokens present (non-empty) we still require the user to confirm them by Save & Apply.
        # So show the login modal on startup and force Save & Apply to enable pages.
        self.root.after(120, self.show_initial_login_prompt)
    # ----- UI builders -----
    def _build_unfollow_tab(self):
        card_pad = 10
        title = tk.Label(self.unfollow_frame, text="People Who Don't Follow You Back", bg=self.colors["panel"], fg=self.colors["accent"], font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w", padx=12, pady=(12,4))
        # search + scan row
        controls = tk.Frame(self.unfollow_frame, bg=self.colors["panel"])
        controls.pack(fill="x", padx=12, pady=(0,8))
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', self.filter_list)
        search_entry = tk.Entry(controls, textvariable=self.search_var, font=("Segoe UI", 11), width=30, bg="#23282B", fg=self.colors["text"], insertbackground=self.colors["text"], relief="flat")
        search_entry.pack(side="left", padx=(0,8))
        self.load_btn = ttk.Button(controls, text="🔍 Scan Now", style="Primary.TButton", command=self.start_scan)
        self.load_btn.pack(side="left", padx=6)
        self.unfollow_btn = ttk.Button(controls, text="🚫 Unfollow Selected", style="Accent.TButton", command=self.unfollow_selected)
        self.unfollow_btn.pack(side="left", padx=6)
        self.unfollow_btn.state(["disabled"])
        # list area (with canvas + scrollbar)
        list_holder = tk.Frame(self.unfollow_frame, bg=self.colors["panel"])
        list_holder.pack(expand=True, fill="both", padx=12, pady=(6,12))
        self.canvas = tk.Canvas(list_holder, bg=self.colors["panel"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(list_holder, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.colors["panel"])
        self.scrollable_frame.bind(
"<Configure>",
lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        # page nav
        nav = tk.Frame(self.unfollow_frame, bg=self.colors["panel"])
        nav.pack(fill="x", padx=12, pady=(0,12))
        self.prev_btn = ttk.Button(nav, text="← Prev", style="Alt.TButton", command=self.prev_page)
        self.prev_btn.pack(side="left")
        self.page_label = tk.Label(nav, text="Page 1", bg=self.colors["panel"], fg=self.colors["subtext"])
        self.page_label.pack(side="left", padx=8)
        self.next_btn = ttk.Button(nav, text="Next →", style="Alt.TButton", command=self.next_page)
        self.next_btn.pack(side="left")
        # low-level data
        self.users = []
        self.filtered_users = []
        self.check_vars = []
        self.selected_ids = set()
        self.page = 0
        self.per_page = 10
    def _build_dashboard_tab(self):
        title = tk.Label(self.dashboard_frame, text="Dashboard · Followers Stats", bg=self.colors["panel"], fg=self.colors["primary"] if "primary" in self.colors else self.colors["accent"], font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w", padx=12, pady=(12,4))
        controls = tk.Frame(self.dashboard_frame, bg=self.colors["panel"])
        controls.pack(fill="x", padx=12, pady=(0,8))
        self.fetch_followers_btn = ttk.Button(controls, text="📥 Fetch Followers & Analyze", style="Primary.TButton", command=self.start_dashboard_analysis)
        self.fetch_followers_btn.pack(side="left", padx=6)
        self.cancel_btn = ttk.Button(controls, text="✖ Cancel", style="Alt.TButton", command=self.cancel_dashboard)
        self.cancel_btn.pack(side="left", padx=6)
        self.cancel_btn.state(["disabled"])
        self.dashboard_status = tk.Label(controls, text="Idle", bg=self.colors["panel"], fg=self.colors["subtext"])
        self.dashboard_status.pack(side="left", padx=12)
        # progress bar
        self.progress_bar = ttk.Progressbar(self.dashboard_frame, orient="horizontal", length=760, mode="determinate")
        self.progress_label = tk.Label(self.dashboard_frame, text="", bg=self.colors["panel"], fg=self.colors["subtext"])
        self.progress_bar.pack(padx=12, pady=(8,0))
        self.progress_label.pack(padx=12, pady=(2,8))
        # chart & summary
        chart_wrap = tk.Frame(self.dashboard_frame, bg=self.colors["panel"])
        chart_wrap.pack(expand=True, fill="both", padx=12, pady=8)
        self.figure = Figure(figsize=(6,4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.text(0.5,0.5,"No data yet", horizontalalignment='center', verticalalignment='center', transform=self.ax.transAxes, color="#777")
        self.ax.axis('off')
        self.canvas_fig = FigureCanvasTkAgg(self.figure, master=chart_wrap)
        self.canvas_fig.get_tk_widget().pack(side="left", expand=True, fill="both", padx=(0,8))
        self.summary_text = tk.Text(chart_wrap, width=36, height=14, bg="#121212", fg="#ddd", bd=0, padx=8, pady=8)
        self.summary_text.pack(side="right", fill="y")
        self.dashboard_cancel_event = None
    # ----- Notebook enable/disable -----
    def _set_notebook_enabled(self, enabled: bool):
        # disable tab switching by disabling all tabs or the widget itself
        state = "normal" if enabled else "disabled"
        try:
            # ttk.Notebook doesn't directly support state, so disable tabs content
            for idx in range(len(self.notebook.tabs())):
                tab_id = self.notebook.tabs()[idx]
                self.notebook.tab(idx, state=state)
        except Exception:
            pass
        # also disable main action buttons
        if enabled:
            self.load_btn.state(["!disabled"])
            self.unfollow_btn.state(["!disabled"])
            self.fetch_followers_btn.state(["!disabled"])
            self.tip_btn.state(["!disabled"])
            self.login_btn.state(["!disabled"])
            self.open_tokens_btn.state(["!disabled"])
            self.clear_btn.state(["!disabled"])
        else:
            self.load_btn.state(["disabled"])
            self.unfollow_btn.state(["disabled"])
            self.fetch_followers_btn.state(["disabled"])
            self.tip_btn.state(["disabled"])
            self.open_tokens_btn.state(["disabled"])
            self.clear_btn.state(["disabled"])
    # ----- Initial login prompt that appears on startup -----
    def show_initial_login_prompt(self):
        # Force the login modal to appear and require Save & Apply to enable pages.
        self.open_login_modal(require_save=True)
    # ----- Token UI helpers -----
    def open_token_file(self):
        path = os.path.abspath(token_filename_for(DS_USER_ID))
        if os.path.exists(path):
            try:
                if sys.platform.startswith('win'):
                    os.startfile(os.path.dirname(path))
                elif sys.platform.startswith('darwin'):
                    os.system(f"open {os.path.dirname(path)}")
                else:
                    os.system(f"xdg-open {os.path.dirname(path)}")
                messagebox.showinfo("Token file", f"Token file location opened: {path}")
            except Exception:
                messagebox.showinfo("Token file", f"Token file: {path}")
        else:
            messagebox.showinfo("Token file", f"No token file found for this account. When you Save tokens they will be stored at:\n{path}")
    def open_login_modal(self, require_save=False):
        """
        show login modal. if require_save=True, user must press Save & Apply to enable app.
        """
        modal = tk.Toplevel(self.root)
        modal.title("Login / Tokens")
        modal.geometry("720x360")
        modal.configure(bg=self.colors["panel"])
        modal.transient(self.root)
        modal.grab_set()
        tk.Label(modal, text="Provide your Instagram tokens", bg=self.colors["panel"], fg=self.colors["subtext"], font=("Segoe UI", 11)).pack(anchor="w", padx=12, pady=(12,0))
        tk.Label(modal, text="(These values are copied from your browser cookies - see Tip)", bg=self.colors["panel"], fg=self.colors["subtext"], font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=(0,8))
        frm = tk.Frame(modal, bg=self.colors["panel"])
        frm.pack(fill="both", expand=True, padx=12, pady=6)
        tk.Label(frm, text="CSRFTOKEN", bg=self.colors["panel"], fg=self.colors["subtext"]).grid(row=0, column=0, sticky="w")
        csrf_entry = tk.Text(frm, height=2, bg="#222", fg=self.colors["text"], bd=0)
        csrf_entry.grid(row=0, column=1, sticky="we", padx=8, pady=6)
        csrf_entry.insert("1.0", CSRFTOKEN)
        tk.Label(frm, text="SESSIONID", bg=self.colors["panel"], fg=self.colors["subtext"]).grid(row=1, column=0, sticky="w")
        sess_entry = tk.Text(frm, height=2, bg="#222", fg=self.colors["text"], bd=0)
        sess_entry.grid(row=1, column=1, sticky="we", padx=8, pady=6)
        sess_entry.insert("1.0", SESSIONID)
        tk.Label(frm, text="DS_USER_ID (numeric)", bg=self.colors["panel"], fg=self.colors["subtext"]).grid(row=2, column=0, sticky="w")
        ds_entry = tk.Entry(frm, bg="#222", fg=self.colors["text"], bd=0)
        ds_entry.grid(row=2, column=1, sticky="we", padx=8, pady=6)
        ds_entry.insert(0, DS_USER_ID)
        frm.columnconfigure(1, weight=1)
        btn_frame = tk.Frame(modal, bg=self.colors["panel"])
        btn_frame.pack(fill="x", padx=12, pady=8)
        def save_and_apply():
            csrft = csrf_entry.get("1.0", "end").strip()
            sess = sess_entry.get("1.0", "end").strip()
            ds = ds_entry.get().strip()
            if not (csrft and sess and ds):
                messagebox.showwarning("Missing", "Please fill all three fields before saving.")
                return
            apply_tokens(csrft, sess, ds)
            messagebox.showinfo("Tokens applied", f"Tokens saved and applied for account {ds}.")
            # enable notebook and actions
            self._set_notebook_enabled(True)
            modal.destroy()
        def save_noapply():
            tf = token_filename_for(ds_entry.get().strip())
            try:
                with open(tf, "w", encoding="utf-8") as f:
                    json.dump({"csrftoken": csrf_entry.get("1.0", "end").strip(), "sessionid": sess_entry.get("1.0", "end").strip(), "ds_user_id": ds_entry.get().strip()}, f)
                messagebox.showinfo("Saved", f"Tokens saved to {os.path.abspath(tf)} (not applied).")
            except Exception as e:
                messagebox.showerror("Save failed", f"Could not save: {e}")
        def close_modal():
            if require_save:
                if messagebox.askyesno("Tokens required", "This app requires tokens to proceed. Close anyway?"):
                    modal.destroy()
                else:
                    return
            else:
                modal.destroy()
        save_btn = ttk.Button(btn_frame, text="💾 Save & Apply", style="Primary.TButton", command=save_and_apply)
        save_btn.pack(side="left", padx=6)
        save_only_btn = ttk.Button(btn_frame, text="💾 Save (no apply)", style="Alt.TButton", command=save_noapply)
        save_only_btn.pack(side="left", padx=6)
        tip_btn = ttk.Button(btn_frame, text="🛈 Tip: Where to get these?", style="Alt.TButton", command=self.show_token_tip)
        tip_btn.pack(side="left", padx=6)
        close_btn = ttk.Button(btn_frame, text="Close", style="Alt.TButton", command=close_modal)
        close_btn.pack(side="right", padx=6)
        # If require_save is True, user can't use the app until Save & Apply called.
        if require_save:
            self._set_notebook_enabled(False)
    def show_token_tip(self):
        tip = (
"How to get CSRFTOKEN, SESSIONID and DS_USER_ID from your browser (Chrome/Firefox):\n\n"
"1) Open the browser and log into Instagram[](https://www.instagram.com).\n"
"2) Press F12 (DevTools) -> go to the 'Application' tab (Chrome) or 'Storage' (Firefox).\n"
"3) In Cookies (left sidebar) select 'https://www.instagram.com'.\n"
"4) Look for cookies named:\n • sessionid (long session cookie)\n • csrftoken (short token used for POSTs)\n • ds_user_id (your numeric user id)\n"
"5) Copy and paste those values into the Login modal, then click 'Save & Apply'.\n\n"
"SECURITY:\nThese tokens grant access to your account. Keep them private. If you suspect misuse, log out from other sessions and change your password."
        )
        win = tk.Toplevel(self.root)
        win.title("Where to get tokens (Tip)")
        win.geometry("720x420")
        win.transient(self.root)
        txt = tk.Text(win, wrap="word", bg="#111", fg="white", padx=12, pady=12)
        txt.pack(expand=True, fill="both")
        txt.insert("1.0", tip)
        txt.config(state="disabled")
        ttk.Button(win, text="OK", command=win.destroy).pack(pady=8)
    def clear_tokens_and_cache(self):
        tf = token_filename_for(DS_USER_ID)
        cf = cache_filename_for(DS_USER_ID)
        confirm = messagebox.askyesno("Confirm clear", f"This will delete:\n\n{os.path.abspath(tf)}\n{os.path.abspath(cf)}\n\nProceed?")
        if not confirm:
            return
        errors = []
        for p in [tf, cf]:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception as e:
                errors.append(str(e))
        # clear in-memory cookies and cache
        try:
            SESSION.cookies.clear(domain=".instagram.com", name="sessionid")
            SESSION.cookies.clear(domain=".instagram.com", name="csrftoken")
            SESSION.cookies.clear(domain=".instagram.com", name="ds_user_id")
        except Exception:
            pass
        apply_tokens("", "", "")
        load_gender_cache_into_global()
        if errors:
            messagebox.showwarning("Partial success", f"Cleared files, but some errors occurred:\n{errors}")
        else:
            messagebox.showinfo("Cleared", "Tokens and cache cleared for current account. In-memory session reset.")
        # disable notebook until user logs in again
        self._set_notebook_enabled(False)
    # ----- Unfollow tab logic (UI + threading) -----
    def start_scan(self):
        self.load_btn.state(["disabled"])
        self.unfollow_btn.state(["disabled"])
        threading.Thread(target=self.load_nonfollowers, daemon=True).start()
    def load_nonfollowers(self):
        try:
            nonfollowers = get_nonfollowers()
        except Exception as e:
            print("Exception while loading nonfollowers:", e)
            traceback.print_exc()
            nonfollowers = []
        self.root.after(0, self.on_nonfollowers_loaded, nonfollowers)
    def on_nonfollowers_loaded(self, nonfollowers):
        self.users = nonfollowers
        self.filtered_users = nonfollowers
        self.page = 0
        self.selected_ids.clear()
        self.display_users()
        self.load_btn.state(["!disabled"])
        if self.filtered_users:
            self.unfollow_btn.state(["!disabled"])
        else:
            self.unfollow_btn.state(["disabled"])
    def display_users(self):
        # clear frame
        for w in self.scrollable_frame.winfo_children():
            w.destroy()
        self.check_vars.clear()
        start = self.page * self.per_page
        end = start + self.per_page
        users_to_display = self.filtered_users[start:end]
        if not users_to_display:
            lbl = tk.Label(self.scrollable_frame, text="No users found.", bg=self.colors["panel"], fg=self.colors["subtext"])
            lbl.pack(pady=14)
        else:
            for user in users_to_display:
                uid = user.get("id")
                username = user.get("username", "(unknown)")
                fullname = user.get("full_name") or ""
                card = tk.Frame(self.scrollable_frame, bg=self.colors["card"], bd=0, relief="flat")
                card.pack(fill="x", padx=8, pady=6)
                left = tk.Frame(card, bg=self.colors["card"])
                left.pack(side="left", fill="both", expand=True, padx=8, pady=8)
                name_lbl = tk.Label(left, text=username, bg=self.colors["card"], fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
                name_lbl.pack(anchor="w")
                if fullname:
                    sub = tk.Label(left, text=fullname, bg=self.colors["card"], fg=self.colors["subtext"], font=("Segoe UI", 9))
                    sub.pack(anchor="w")
                right = tk.Frame(card, bg=self.colors["card"])
                right.pack(side="right", padx=8, pady=8)
                var = tk.BooleanVar(value=(uid in self.selected_ids))
                chk = tk.Checkbutton(right, variable=var, bg=self.colors["card"], activebackground=self.colors["card"], selectcolor=self.colors["card"])
                chk.pack(side="right")
                # when toggled update selected_ids
                def on_toggle(u=uid, v=var):
                    if v.get():
                        self.selected_ids.add(u)
                    else:
                        self.selected_ids.discard(u)
                chk.config(command=on_toggle)
                # open profile on click
                name_lbl.bind("<Button-1>", lambda e, u=username: self.open_profile(u))
                self.check_vars.append((var, user))
        self.page_label.config(text=f"Page {self.page + 1}")
        self.prev_btn.state(["!disabled"] if self.page > 0 else ["disabled"])
        self.next_btn.state(["!disabled"] if end < len(self.filtered_users) else ["disabled"])
    def next_page(self):
        self.page += 1
        self.display_users()
    def prev_page(self):
        if self.page > 0:
            self.page -= 1
            self.display_users()
    def unfollow_selected(self):
        if not self.selected_ids:
            messagebox.showinfo("No selection", "No users selected to unfollow.")
            return
        if not messagebox.askyesno("Confirm", f"Are you sure you want to unfollow {len(self.selected_ids)} user(s)?"):
            return
        self.unfollow_btn.state(["disabled"])
        self.load_btn.state(["disabled"])
        threading.Thread(target=self.unfollow_thread, daemon=True).start()
    def unfollow_thread(self):
        id_to_user = {u["id"]: u for u in self.users if u.get("id")}
        to_unfollow_ids = [uid for uid in list(self.selected_ids) if uid in id_to_user]
        results = []
        for uid in to_unfollow_ids:
            user = id_to_user.get(uid)
            username = user.get("username", "(unknown)")
            try:
                success, code, text = unfollow_user(uid)
            except Exception as e:
                success, code, text = False, None, f"Exception: {e}"
            print(f"Attempt unfollow {username} ({uid}) -> success={success}, code={code}")
            results.append((username, success, code, text))
            if success:
                try:
                    self.users = [x for x in self.users if x.get("id") != uid]
                    self.filtered_users = [x for x in self.filtered_users if x.get("id") != uid]
                except Exception:
                    pass
                self.selected_ids.discard(uid)
            time.sleep(random.uniform(4.0, 6.0))
        self.root.after(0, self.on_unfollow_complete, results)
    def on_unfollow_complete(self, results):
        successes = [r for r in results if r[1]]
        failures = [r for r in results if not r[1]]
        self.page = 0
        self.display_users()
        self.unfollow_btn.state(["!disabled"] if self.filtered_users else ["disabled"])
        self.load_btn.state(["!disabled"])
        message = f"Finished. Unfollowed {len(successes)} user(s). {len(failures)} failed."
        messagebox.showinfo("Done", message)
    def filter_list(self, *args):
        search_term = self.search_var.get().lower()
        if search_term:
            self.filtered_users = [u for u in self.users if search_term in (u.get('username') or "").lower()]
        else:
            self.filtered_users = list(self.users)
        self.page = 0
        self.display_users()
    def open_profile(self, username):
        url = f"https://www.instagram.com/{username}/"
        webbrowser.open(url)
    # ----- Dashboard (progress + cancel + cache) -----
    def start_dashboard_analysis(self):
        self.fetch_followers_btn.state(["disabled"])
        self.cancel_btn.state(["!disabled"])
        self.dashboard_status.config(text="Fetching followers...")
        self.progress_bar['value'] = 0
        self.progress_label.config(text="")
        self.summary_text.delete("1.0", tk.END)
        self.dashboard_cancel_event = threading.Event()
        threading.Thread(target=self.dashboard_thread, args=(self.dashboard_cancel_event,), daemon=True).start()
    def cancel_dashboard(self):
        if self.dashboard_cancel_event:
            self.dashboard_cancel_event.set()
            self.dashboard_status.config(text="Cancel requested — stopping soon...")
            self.cancel_btn.state(["disabled"])
    def dashboard_thread(self, cancel_event):
        try:
            followers = fetch_followers_list()
        except Exception as e:
            followers = []
            print("Error fetching followers for dashboard:", e)
            traceback.print_exc()
        self.root.after(0, self.process_followers_for_dashboard, followers, cancel_event)
    def process_followers_for_dashboard(self, followers, cancel_event):
        count_total = len(followers)
        if count_total == 0:
            self.dashboard_status.config(text="No followers or failed to fetch")
            self.fetch_followers_btn.state(["!disabled"])
            self.cancel_btn.state(["disabled"])
            messagebox.showinfo("No data", "No followers were fetched. Check your tokens or network.")
            return
        self.dashboard_status.config(text=f"Preparing names ({count_total})...")
        names = []
        user_map = []
        for u in followers:
            name = prepare_name_for_genderize(u)
            if not name:
                name = u.get("username") or ""
            names.append(name)
            user_map.append(u)
        self.progress_bar['maximum'] = len(names)
        self.progress_bar['value'] = 0
        self.progress_label.config(text=f"0 / {len(names)}")
        def progress_cb(done, total):
            self.root.after(0, self._update_progress_ui, done, total)
        def run_genderize():
            results = genderize_with_cache(names, progress_callback=progress_cb, cancel_event=cancel_event)
            canceled = cancel_event.is_set()
            male = female = unknown = 0
            gender_details = []
            for idx, r in enumerate(results):
                gender = r.get("gender")
                prob = r.get("probability") or 0
                name_sent = r.get("name")
                username = user_map[idx].get("username")
                if gender == "male":
                    male += 1
                elif gender == "female":
                    female += 1
                else:
                    unknown += 1
                gender_details.append((username, name_sent, gender, prob))
            stats = {
"total": len(results),
"male": male,
"female": female,
"unknown": unknown,
"details": gender_details,
"canceled": canceled
            }
            self.root.after(0, self.show_dashboard_results, stats)
        threading.Thread(target=run_genderize, daemon=True).start()
    def _update_progress_ui(self, done, total):
        try:
            self.progress_bar['value'] = done
            self.progress_label.config(text=f"{done} / {total}")
            pct = (done/total*100) if total else 0
            self.dashboard_status.config(text=f"Analyzing names — {pct:.0f}%")
        except Exception:
            pass
    def show_dashboard_results(self, stats):
        total = stats["total"]
        male = stats["male"]
        female = stats["female"]
        unknown = stats["unknown"]
        canceled = stats.get("canceled", False)
        status_text = f"Done — analyzed {total} followers"
        if canceled:
            status_text = f"Stopped early — analyzed {total} followers (partial)"
        self.dashboard_status.config(text=status_text)
        self.fetch_followers_btn.state(["!disabled"])
        self.cancel_btn.state(["disabled"])
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, f"Total followers processed: {total}\n")
        if total:
            self.summary_text.insert(tk.END, f"Male: {male} ({(male/total*100):.1f}%)\n")
            self.summary_text.insert(tk.END, f"Female: {female} ({(female/total*100):.1f}%)\n")
            self.summary_text.insert(tk.END, f"Unknown/Undetected: {unknown} ({(unknown/total*100):.1f}%)\n")
        if canceled:
            self.summary_text.insert(tk.END, "\nAnalysis was canceled by the user. Partial results shown.\n")
        self.summary_text.insert(tk.END, "\nNote: Local PyTorch model — no API limits, offline predictions.\n")
        self.progress_label.config(text=f"{total} / {total}")
        self.progress_bar['value'] = total
        # draw pie chart
        labels = []
        sizes = []
        if male > 0:
            labels.append("Male"); sizes.append(male)
        if female > 0:
            labels.append("Female"); sizes.append(female)
        if unknown > 0:
            labels.append("Unknown"); sizes.append(unknown)
        self.figure.clf()
        ax = self.figure.add_subplot(111)
        if sizes:
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
            ax.set_title(f"Followers by predicted gender — {DS_USER_ID or 'unknown'}")
        else:
            ax.text(0.5,0.5,"No data to display", horizontalalignment='center', verticalalignment='center', transform=ax.transAxes, color="#777")
        ax.axis('off')
        self.canvas_fig.draw()
# ---- Run App ----
if __name__ == "__main__":
    root = tk.Tk()
    app = InstaApp(root)
    root.mainloop()
