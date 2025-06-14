import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import json
import time
import datetime
import pystray
from PIL import Image, ImageDraw

# --- File Categories ---
FILE_CATEGORIES = {
    'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp'],
    'Documents': ['.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx', '.ppt', '.pptx'],
    'Videos': ['.mp4', '.mkv', '.mov', '.avi'],
    'Music': ['.mp3', '.wav', '.aac'],
    'Archives': ['.zip', '.rar', '.tar', '.gz'],
    'Scripts': ['.py', '.js', '.sh', '.bat'],
    'Others': []
}

# --- Helper Functions ---
def get_category(filename):
    name = filename.lower()
    ext = os.path.splitext(name)[1]
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    return 'Others'

def apply_custom_rules(filename, rules):
    for rule in rules:
        if rule['keyword'].lower() in filename.lower():
            return rule['destination']
    return None


def organize_folder(folder_path, rules, log_file):
    log_entries = []
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isfile(item_path):
            dest = apply_custom_rules(item, rules) or get_category(item)
            dest_folder = os.path.join(folder_path, dest)
            os.makedirs(dest_folder, exist_ok=True)
            new_path = os.path.join(dest_folder, item)
            shutil.move(item_path, new_path)
            log_entries.append(f"{datetime.datetime.now()} - Moved: {item} --> {dest}/")

    with open(log_file, 'a') as log:
        for entry in log_entries:
            log.write(entry + '\n')

# --- Watchdog Handler ---
class Handler(FileSystemEventHandler):
    def __init__(self, folder_path, rules, log_file):
        self.folder_path = folder_path
        self.rules = rules
        self.log_file = log_file

    def on_modified(self, event):
        if not event.is_directory:
            organize_folder(self.folder_path, self.rules, self.log_file)

# --- System Tray Icon ---
def create_image():
    image = Image.new('RGB', (64, 64), color=(0, 100, 200))
    draw = ImageDraw.Draw(image)
    draw.rectangle([16, 16, 48, 48], fill=(255, 255, 255))
    return image

def show_tray_icon():
    icon = pystray.Icon("AutoOrganizer", create_image(), "Auto File Organizer")
    icon.menu = pystray.Menu(pystray.MenuItem("Quit", lambda: icon.stop()))
    icon.run()

# --- GUI Setup ---
def run_gui():
    config = {
        'rules': [],
        'log_file': 'organizer_log.txt'
    }

    def load_rules():
        if os.path.exists('rules.json'):
            with open('rules.json', 'r') as f:
                config['rules'] = json.load(f)

    def save_rules():
        with open('rules.json', 'w') as f:
            json.dump(config['rules'], f, indent=4)

    def start_monitoring():
        folder = filedialog.askdirectory()
        if folder:
            threading.Thread(target=watch_folder, args=(folder,), daemon=True).start()
            messagebox.showinfo("Started", f"Now monitoring: {folder}")

    def watch_folder(folder):
        observer = Observer()
        event_handler = Handler(folder, config['rules'], config['log_file'])
        observer.schedule(event_handler, folder, recursive=False)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    def manual_organize():
        folder = filedialog.askdirectory()
        if folder:
            organize_folder(folder, config['rules'], config['log_file'])
            messagebox.showinfo("Done", f"Organized files in: {folder}")

    def add_rule():
        keyword = keyword_entry.get()
        destination = destination_entry.get()
        if keyword and destination:
            config['rules'].append({"keyword": keyword, "destination": destination})
            save_rules()
            keyword_entry.delete(0, tk.END)
            destination_entry.delete(0, tk.END)
            load_rules()
            update_rules_view()

    def update_rules_view():
        rule_list.delete(0, tk.END)
        for rule in config['rules']:
            rule_list.insert(tk.END, f"'{rule['keyword']}' --> {rule['destination']}")

    # Main window
    root = tk.Tk()
    root.title("Modern File Organizer")
    root.geometry("500x500")

    ttk.Label(root, text="Automatic File Organizer", font=("Arial", 16)).pack(pady=10)

    ttk.Button(root, text="Organize Folder Now", command=manual_organize).pack(pady=5)
    ttk.Button(root, text="Start Real-Time Monitoring", command=start_monitoring).pack(pady=5)

    ttk.Label(root, text="Add Custom Rule (Keyword -> Folder)").pack(pady=10)
    keyword_entry = ttk.Entry(root)
    keyword_entry.pack(pady=2)
    destination_entry = ttk.Entry(root)
    destination_entry.pack(pady=2)
    ttk.Button(root, text="Add Rule", command=add_rule).pack(pady=2)

    ttk.Label(root, text="Current Rules:").pack(pady=5)
    rule_list = tk.Listbox(root, height=8, width=50)
    rule_list.pack()

    load_rules()
    update_rules_view()

    # Run tray icon in background
    threading.Thread(target=show_tray_icon, daemon=True).start()

    root.mainloop()

if __name__ == "__main__":
    run_gui()