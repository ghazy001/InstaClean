# Instagram Unfollowers GUI App - All-in-One (Instagram-Like Style with Dark Mode, Cards, and Pagination)
# Author: Ghazi's Assistant 💻

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import requests
import json
import threading
import time
import random

# ---- Configuration ----

CSRFTOKEN = "votre_csrftoken"
SESSIONID = "votre_sessionid"
DS_USER_ID = "votre_user_id"

HEADERS = {
    "cookie": f"csrftoken={CSRFTOKEN}; sessionid={SESSIONID}; ds_user_id={DS_USER_ID}",
    "x-csrftoken": CSRFTOKEN,
    "user-agent": "Instagram 155.0.0.37.107"
}

# ---- Helper Functions ----
def fetch_users(query_hash, user_id, edge_type):
    url = f"https://www.instagram.com/graphql/query/"
    results = []
    has_next = True
    end_cursor = ""

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
        res = requests.get(full_url, headers=HEADERS)
        if res.status_code != 200:
            break

        try:
            data = res.json()["data"]["user"][edge_type]
        except:
            break

        edges = data["edges"]
        for edge in edges:
            node = edge["node"]
            results.append({"id": node["id"], "username": node["username"]})

        has_next = data["page_info"]["has_next_page"]
        end_cursor = data["page_info"]["end_cursor"]
        time.sleep(1)

    return results

def get_nonfollowers():
    following = fetch_users("3dec7e2c57367ef3da3d987d89f9dbc8", DS_USER_ID, "edge_follow")
    followers = fetch_users("c76146de99bb02f6415203be841dd25a", DS_USER_ID, "edge_followed_by")

    follower_usernames = {u["username"] for u in followers}
    nonfollowers = [u for u in following if u["username"] not in follower_usernames]
    return nonfollowers

def unfollow_user(user_id):
    url = f"https://www.instagram.com/web/friendships/{user_id}/unfollow/"
    res = requests.post(url, headers=HEADERS)
    return res.status_code == 200

# ---- GUI App ----
class InstaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Instagram Unfollowers")
        self.root.geometry("700x750")
        self.root.configure(bg="#1e1e1e")

        self.users = []
        self.filtered_users = []
        self.check_vars = []
        self.page = 0
        self.per_page = 10

        title = tk.Label(root, text="People Who Don't Follow You Back", font=("Helvetica Neue", 18, "bold"), bg="#1e1e1e", fg="#E1306C")
        title.pack(pady=10)

        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', self.filter_list)
        search_entry = tk.Entry(root, textvariable=self.search_var, font=("Arial", 12), width=30, bg="#2e2e2e", fg="white", insertbackground="white")
        search_entry.pack(pady=5)

        self.load_btn = tk.Button(root, text="🔍 Scan Now", command=self.start_scan, bg="#E1306C", fg="black", font=("Arial", 12, "bold"), relief="flat", padx=20, pady=5)
        self.load_btn.pack(pady=10)

        self.list_frame = tk.Frame(root, bg="#1e1e1e")
        self.list_frame.pack(expand=True, fill="both")

        self.nav_frame = tk.Frame(root, bg="#1e1e1e")
        self.nav_frame.pack(pady=5)
        self.prev_btn = tk.Button(self.nav_frame, text="← Prev", command=self.prev_page, bg="#444", fg="black", state="disabled")
        self.prev_btn.grid(row=0, column=0, padx=5)
        self.page_label = tk.Label(self.nav_frame, text="Page 1", bg="#1e1e1e", fg="white")
        self.page_label.grid(row=0, column=1, padx=10)
        self.next_btn = tk.Button(self.nav_frame, text="Next →", command=self.next_page, bg="#444", fg="black", state="disabled")
        self.next_btn.grid(row=0, column=2, padx=5)

        self.unfollow_btn = tk.Button(root, text="🚫 Unfollow Selected", command=self.unfollow_selected, state="disabled", bg="#833AB4", fg="white", font=("Arial", 12, "bold"), relief="flat", padx=20, pady=5)
        self.unfollow_btn.pack(pady=10)

    def start_scan(self):
        self.load_btn.config(text="Scanning...", state="disabled")
        threading.Thread(target=self.load_nonfollowers).start()

    def load_nonfollowers(self):
        nonfollowers = get_nonfollowers()
        self.users = nonfollowers
        self.filtered_users = nonfollowers
        self.page = 0
        self.display_users()

    def display_users(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        self.check_vars.clear()

        start = self.page * self.per_page
        end = start + self.per_page
        users_to_display = self.filtered_users[start:end]

        if not users_to_display:
            msg = tk.Label(self.list_frame, text="No users found.", bg="#1e1e1e", fg="#888", font=("Arial", 12))
            msg.pack(pady=20)
        else:
            for user in users_to_display:
                var = tk.BooleanVar()
                card = tk.Frame(self.list_frame, bg="#2e2e2e", bd=1, relief="groove")
                card.pack(fill="x", padx=10, pady=5)

                lbl = tk.Label(card, text=user['username'], font=("Arial", 12, "bold"), bg="#2e2e2e", fg="white")
                lbl.pack(side="left", padx=10, pady=5)
                chk = tk.Checkbutton(card, variable=var, bg="#2e2e2e", activebackground="#2e2e2e", selectcolor="#2e2e2e")
                chk.pack(side="right", padx=10)
                self.check_vars.append((var, user))

        self.page_label.config(text=f"Page {self.page + 1}")
        self.prev_btn.config(state="normal" if self.page > 0 else "disabled")
        self.next_btn.config(state="normal" if end < len(self.filtered_users) else "disabled")
        self.unfollow_btn.config(state="normal")
        self.load_btn.config(text="🔍 Rescan", state="normal")

    def next_page(self):
        self.page += 1
        self.display_users()

    def prev_page(self):
        if self.page > 0:
            self.page -= 1
            self.display_users()

    def unfollow_selected(self):
        self.unfollow_btn.config(text="Unfollowing...", state="disabled")
        threading.Thread(target=self.unfollow_thread).start()

    def unfollow_thread(self):
        for var, user in self.check_vars:
            if var.get():
                success = unfollow_user(user["id"])
                print(f"Unfollowed {user['username']} ✅" if success else f"Failed to unfollow {user['username']} ❌")
                time.sleep(random.uniform(4, 6))

        messagebox.showinfo("Done", "Finished unfollowing selected users.")
        self.unfollow_btn.config(text="🚫 Unfollow Selected", state="normal")

    def filter_list(self, *args):
        search_term = self.search_var.get().lower()
        self.filtered_users = [u for u in self.users if search_term in u['username'].lower()]
        self.page = 0
        self.display_users()

# ---- Run App ----
if __name__ == "__main__":
    root = tk.Tk()
    app = InstaApp(root)
    root.mainloop()