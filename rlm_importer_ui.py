import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import sys
import pathlib
import platform
import threading
import subprocess
import pystray
from PIL import Image, ImageDraw
import ctypes

# Import background tasks to package them into the standalone executable
try:
    import raidlootmatrix_mplus
    import rlm_discord_sync
except ImportError as e:
    # Fallback/logging if running locally and missing dependencies
    print(f"Warning: Failed to import background task modules: {e}")

try:
    # Set unique AppUserModelID so Windows taskbar displays the correct custom window icon
    myappid = "raidlootmatrix.desktop.companion"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

import socket
SINGLE_INSTANCE_PORT = 55919

def check_single_instance(app_instance_callback=None):
    try:
        # Try to bind to localhost port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', SINGLE_INSTANCE_PORT))
        s.listen(1)
        
        # We got the lock! Start a background thread to listen for wake signals
        def listen_for_wake():
            while True:
                try:
                    conn, addr = s.connect_accept_wait_loop() if False else s.accept()
                    conn.close()
                    # Wake up callback
                    if app_instance_callback:
                        app_instance_callback()
                except Exception:
                    break
                    
        t = threading.Thread(target=listen_for_wake, daemon=True)
        t.start()
        return s # Keep socket open for the lifetime of the process
    except socket.error:
        # Binding failed -> another instance is already running!
        try:
            # Connect to the existing instance to wake it up
            s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s2.connect(('127.0.0.1', SINGLE_INSTANCE_PORT))
            s2.close()
        except Exception:
            pass
        # Exit immediately
        sys.exit(0)

# ─────────────────────────────────────────────────────────────────────────────
# UI Styling Constants
# ─────────────────────────────────────────────────────────────────────────────
BG_DARK = "#1e1e1e"
BG_PANEL = "#252526"
BG_ENTRY = "#2d2d30"
FG_TEXT = "#d4d4d4"
FG_ACCENT = "#ffcc00"
FG_HEADER = "#ff9900"
BORDER_COLOR = "#3f3f46"

class RLMImporterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RLM Importer — Desktop Control Panel")
        self.root.geometry("840x760")
        self.root.configure(bg=BG_DARK)
        self.root.minsize(750, 680)

        # Config paths
        if getattr(sys, 'frozen', False):
            self.addon_dir = pathlib.Path(sys.executable).parent
        else:
            self.addon_dir = pathlib.Path(__file__).parent
        self.config_path = self.addon_dir / "rlm_importer_config.json"
        
        # Load existing settings
        self.settings = self.load_settings()

        # Build UI Elements
        self.setup_styles()
        self.create_widgets()
        
        # Log init
        self.log_message("RLM Importer control panel loaded.")
        self.log_message(f"Working directory: {self.addon_dir}")

        # Generate custom logo icon if missing
        self.icon_path_png = self.addon_dir / "rlm_icon.png"
        self.icon_path_ico = self.addon_dir / "rlm_icon.ico"
        self.logo_source = self.addon_dir / "rlm_logo_source.png"
        
        if not self.icon_path_ico.exists() or not self.icon_path_png.exists():
            try:
                if self.logo_source.exists():
                    img = Image.open(self.logo_source)
                    img = img.convert("RGBA")
                    datas = img.getdata()
                    new_data = []
                    for item in datas:
                        if item[0] < 20 and item[1] < 20 and item[2] < 20:
                            new_data.append((0, 0, 0, 0))
                        else:
                            new_data.append(item)
                    img.putdata(new_data)
                    
                    # Resize to 128x128 for high-quality window/tray icon
                    img_png = img.resize((128, 128), Image.Resampling.LANCZOS)
                else:
                    img = self.create_tray_image()
                    img_png = img
                
                img_png.save(self.icon_path_png)
                img.save(self.icon_path_ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
            except Exception as e:
                print(f"Failed to generate icons: {e}")

        # Set window icon bitmap (Windows native)
        if self.icon_path_ico.exists():
            try:
                self.root.iconbitmap(str(self.icon_path_ico))
            except Exception as e:
                # Fallback to PNG iconphoto if iconbitmap fails
                try:
                    icon_img = tk.PhotoImage(file=str(self.icon_path_png))
                    self.root.iconphoto(True, icon_img)
                except Exception:
                    pass

        # Create desktop shortcut if missing
        desktop_dir = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
        if not os.path.exists(desktop_dir):
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            
        # Clean up old shortcut if it exists to avoid caching and clutter
        old_shortcut = os.path.join(desktop_dir, "RLM Companion.lnk")
        if os.path.exists(old_shortcut):
            try:
                os.remove(old_shortcut)
            except Exception:
                pass
                
        desktop_shortcut = os.path.join(desktop_dir, "RLM Desktop Companion.lnk")
        if not os.path.exists(desktop_shortcut):
            self.create_desktop_shortcut()

        # Intercept closing action to hide to system tray
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        # Start background system tray loop
        try:
            self.start_tray_icon()
        except Exception as e:
            self.log_message(f"[ERROR] Failed to start system tray icon: {e}")

    def load_settings(self):
        defaults = {
            "account": "APSU14RYNE",
            "region": "us",
            "season": "season-tww-2",
            "wow_path": "",
            "rio_delay": 0.35,
            "schedule_am": "06:00",
            "schedule_pm": "18:00",
            "schedule_logon": True,
            "discord_sync_key": "",
            "discord_sync_url": "https://rlm-desktop-companion-production.up.railway.app/api/sync",
            "sync_on_import": True,
            "sync_on_wow_exit": True
        }
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    defaults.update(data)
            except Exception as e:
                print(f"Failed to read config file: {e}")
        return defaults

    def save_settings(self):
        # Gather inputs
        self.settings["account"] = self.ent_account.get().strip()
        self.settings["region"] = self.ent_region.get().strip()
        self.settings["season"] = self.ent_season.get().strip()
        self.settings["wow_path"] = self.ent_wow_path.get().strip()
        
        try:
            self.settings["rio_delay"] = float(self.ent_rio_delay.get().strip())
        except ValueError:
            self.settings["rio_delay"] = 0.35

        self.settings["schedule_am"] = self.ent_sched_am.get().strip()
        self.settings["schedule_pm"] = self.ent_sched_pm.get().strip()
        self.settings["schedule_logon"] = self.var_sched_logon.get()
        self.settings["discord_sync_key"] = self.ent_discord_key.get().strip()
        self.settings["discord_sync_url"] = self.ent_discord_url.get().strip()
        self.settings["sync_on_import"] = self.var_sync_on_import.get()
        self.settings["sync_on_wow_exit"] = self.var_sync_on_wow_exit.get()

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
            self.log_message("Settings saved successfully to config JSON.")
            messagebox.showinfo("Success", "Settings saved successfully!")
        except Exception as e:
            self.log_message(f"Error saving settings: {e}")
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Configure standard widgets colors
        self.style.configure(".", background=BG_DARK, foreground=FG_TEXT)
        self.style.configure("TFrame", background=BG_DARK)
        self.style.configure("Panel.TFrame", background=BG_PANEL, borderwidth=1, relief="solid")
        
        self.style.configure("TLabel", background=BG_DARK, foreground=FG_TEXT, font=("Segoe UI", 9))
        self.style.configure("Panel.TLabel", background=BG_PANEL, foreground=FG_TEXT, font=("Segoe UI", 9))
        self.style.configure("Header.TLabel", background=BG_PANEL, foreground=FG_HEADER, font=("Segoe UI", 11, "bold"))
        self.style.configure("Title.TLabel", background=BG_DARK, foreground=FG_ACCENT, font=("Segoe UI", 15, "bold"))

        self.style.configure("TButton", background=BG_PANEL, foreground=FG_TEXT, borderwidth=1, focuscolor=FG_ACCENT, font=("Segoe UI", 9))
        self.style.map("TButton", 
                       background=[("active", "#3e3e42"), ("pressed", "#505054")],
                       foreground=[("active", FG_ACCENT)])

        self.style.configure("Accent.TButton", background=BG_PANEL, foreground=FG_ACCENT, borderwidth=1, font=("Segoe UI", 10, "bold"))
        self.style.map("Accent.TButton", 
                       background=[("active", "#3e3e42")],
                       foreground=[("active", FG_ACCENT)])

        self.style.configure("TCheckbutton", background=BG_PANEL, foreground=FG_TEXT, font=("Segoe UI", 9))
        self.style.map("TCheckbutton", background=[("active", BG_PANEL)], foreground=[("active", FG_ACCENT)])

    def create_widgets(self):
        # Header banner
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill="x", padx=15, pady=10)
        
        lbl_title = ttk.Label(header_frame, text="RLM Importer", style="Title.TLabel")
        lbl_title.pack(side="left")
        lbl_subtitle = ttk.Label(header_frame, text=" — Raider.IO Mythic+ Settings & Automation Hub", font=("Segoe UI", 10, "italic"))
        lbl_subtitle.pack(side="left", padx=5, pady=4)

        # Main Layout frame (left = options, right = console logs)
        main_pane = ttk.Frame(self.root)
        main_pane.pack(fill="both", expand=True, padx=15, pady=5)

        # Left Column: Configuration Cards
        left_col = ttk.Frame(main_pane)
        left_col.pack(side="left", fill="both", padx=(0, 10))

        # Card 1: WoW & Account Config
        card_wow = ttk.Frame(left_col, style="Panel.TFrame")
        card_wow.pack(fill="x", pady=(0, 10))
        
        lbl_card_wow_hdr = ttk.Label(card_wow, text=" WoW & Account Settings", style="Header.TLabel")
        lbl_card_wow_hdr.pack(fill="x", padx=10, pady=(10, 5))
        
        self.create_wow_settings_fields(card_wow)

        # Card 2: Background Task Scheduler Automation
        card_sched = ttk.Frame(left_col, style="Panel.TFrame")
        card_sched.pack(fill="x", pady=(0, 10))
        
        lbl_card_sched_hdr = ttk.Label(card_sched, text=" Background Task Automation", style="Header.TLabel")
        lbl_card_sched_hdr.pack(fill="x", padx=10, pady=(10, 5))
        
        self.create_scheduler_fields(card_sched)

        # Card 3: Discord Bot Sync Settings
        card_discord = ttk.Frame(left_col, style="Panel.TFrame")
        card_discord.pack(fill="x", pady=(0, 10))
        
        lbl_card_discord_hdr = ttk.Label(card_discord, text=" Discord Bot Sync Settings", style="Header.TLabel")
        lbl_card_discord_hdr.pack(fill="x", padx=10, pady=(10, 5))
        
        self.create_discord_sync_fields(card_discord)

        # Save Button Card
        card_save = ttk.Frame(left_col, style="Panel.TFrame")
        card_save.pack(fill="x")
        
        btn_save = ttk.Button(card_save, text="Save Current Settings", command=self.save_settings, width=30)
        btn_save.pack(padx=10, pady=10, fill="x")

        # Right Column: Console/Console Log Card
        right_col = ttk.Frame(main_pane, style="Panel.TFrame")
        right_col.pack(side="right", fill="both", expand=True)

        lbl_console_hdr = ttk.Label(right_col, text=" Import Action & Console Logs", style="Header.TLabel")
        lbl_console_hdr.pack(fill="x", padx=10, pady=(10, 5))

        self.create_console_view(right_col)

    def create_wow_settings_fields(self, parent):
        grid = ttk.Frame(parent, style="Panel.TFrame")
        grid.pack(fill="x", padx=10, pady=5)

        # Account Name
        ttk.Label(grid, text="WTF Account Name:", style="Panel.TLabel").grid(row=0, column=0, sticky="w", pady=4)
        self.ent_account = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_TEXT, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.ent_account.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=4)
        self.ent_account.insert(0, self.settings["account"])

        # Region
        ttk.Label(grid, text="Raider.IO Region (us/eu):", style="Panel.TLabel").grid(row=1, column=0, sticky="w", pady=4)
        self.ent_region = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_TEXT, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.ent_region.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=4)
        self.ent_region.insert(0, self.settings["region"])

        # Season
        ttk.Label(grid, text="Mythic+ Season Slug:", style="Panel.TLabel").grid(row=2, column=0, sticky="w", pady=4)
        self.ent_season = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_TEXT, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.ent_season.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=4)
        self.ent_season.insert(0, self.settings["season"])

        # RIO API Delay
        ttk.Label(grid, text="API Delay (seconds):", style="Panel.TLabel").grid(row=3, column=0, sticky="w", pady=4)
        self.ent_rio_delay = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_TEXT, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.ent_rio_delay.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=4)
        self.ent_rio_delay.insert(0, str(self.settings["rio_delay"]))

        # WoW Directory Selector
        ttk.Label(grid, text="Custom WTF Folder Path:", style="Panel.TLabel").grid(row=4, column=0, sticky="w", pady=4)
        dir_frame = ttk.Frame(grid, style="Panel.TFrame")
        dir_frame.grid(row=4, column=1, sticky="ew", padx=(10, 0), pady=4)
        dir_frame.columnconfigure(0, weight=1)

        self.ent_wow_path = tk.Entry(dir_frame, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_TEXT, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.ent_wow_path.grid(row=0, column=0, sticky="ew")
        self.ent_wow_path.insert(0, self.settings["wow_path"])

        btn_browse = ttk.Button(dir_frame, text="Browse...", command=self.browse_wow_directory, width=8)
        btn_browse.grid(row=0, column=1, padx=(5, 0))

        grid.columnconfigure(1, weight=1)

    def create_scheduler_fields(self, parent):
        grid = ttk.Frame(parent, style="Panel.TFrame")
        grid.pack(fill="x", padx=10, pady=5)

        # AM Run Time
        ttk.Label(grid, text="AM Scan (24h HH:MM):", style="Panel.TLabel").grid(row=0, column=0, sticky="w", pady=4)
        self.ent_sched_am = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_TEXT, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, width=10)
        self.ent_sched_am.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=4)
        self.ent_sched_am.insert(0, self.settings["schedule_am"])

        # PM Run Time
        ttk.Label(grid, text="PM Scan (24h HH:MM):", style="Panel.TLabel").grid(row=1, column=0, sticky="w", pady=4)
        self.ent_sched_pm = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_TEXT, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, width=10)
        self.ent_sched_pm.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=4)
        self.ent_sched_pm.insert(0, self.settings["schedule_pm"])

        # Run on Logon Trigger
        self.var_sched_logon = tk.BooleanVar(value=self.settings["schedule_logon"])
        chk_logon = ttk.Checkbutton(grid, text="Run daily scans 5 minutes after logging into Windows", variable=self.var_sched_logon)
        chk_logon.grid(row=2, column=0, columnspan=2, sticky="w", pady=6)

        # Run UI on Startup
        self.var_run_on_startup = tk.BooleanVar(value=self.settings.get("run_on_startup", True))
        chk_startup = ttk.Checkbutton(grid, text="Start RLM Desktop UI automatically on Windows logon (Tray)", variable=self.var_run_on_startup)
        chk_startup.grid(row=3, column=0, columnspan=2, sticky="w", pady=6)

        # Sync on WoW Exit
        self.var_sync_on_wow_exit = tk.BooleanVar(value=self.settings.get("sync_on_wow_exit", True))
        chk_wow_exit = ttk.Checkbutton(grid, text="Sync immediately when WoW closes (Wow.exe Close Watcher)", variable=self.var_sync_on_wow_exit)
        chk_wow_exit.grid(row=4, column=0, columnspan=2, sticky="w", pady=6)

        # OS Task Register Actions
        task_action_frame = ttk.Frame(parent, style="Panel.TFrame")
        task_action_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        btn_register = ttk.Button(task_action_frame, text="Register Background Tasks", command=self.register_background_tasks)
        btn_register.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        btn_unregister = ttk.Button(task_action_frame, text="Remove Tasks", command=self.unregister_background_tasks)
        btn_unregister.pack(side="right", fill="x", expand=True, padx=(5, 0))

    def create_discord_sync_fields(self, parent):
        grid = ttk.Frame(parent, style="Panel.TFrame")
        grid.pack(fill="x", padx=10, pady=5)

        # Sync Key
        ttk.Label(grid, text="Discord Sync Key:", style="Panel.TLabel").grid(row=0, column=0, sticky="w", pady=4)
        self.ent_discord_key = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_TEXT, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.ent_discord_key.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=4)
        self.ent_discord_key.insert(0, self.settings.get("discord_sync_key", ""))

        # Sync URL
        ttk.Label(grid, text="Discord Sync URL:", style="Panel.TLabel").grid(row=1, column=0, sticky="w", pady=4)
        self.ent_discord_url = tk.Entry(grid, bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_TEXT, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.ent_discord_url.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=4)
        self.ent_discord_url.insert(0, self.settings.get("discord_sync_url", "https://rlm-desktop-companion-production.up.railway.app/api/sync"))

        # Checkbutton to auto-sync on import
        self.var_sync_on_import = tk.BooleanVar(value=self.settings.get("sync_on_import", True))
        chk_sync_on_import = ttk.Checkbutton(grid, text="Run Discord Sync after M+ import", variable=self.var_sync_on_import)
        chk_sync_on_import.grid(row=2, column=0, columnspan=2, sticky="w", pady=6)

        grid.columnconfigure(1, weight=1)

        # Button inside Card 3 to run sync now
        self.btn_sync_now = ttk.Button(parent, text="Run Discord Sync Now", command=self.trigger_discord_sync)
        self.btn_sync_now.pack(padx=10, pady=(5, 10), fill="x")

    def create_console_view(self, parent):
        action_bar = ttk.Frame(parent, style="Panel.TFrame")
        action_bar.pack(fill="x", padx=10, pady=5)

        ttk.Label(action_bar, text="Import Week Mode:", style="Panel.TLabel").pack(side="left", pady=4)
        
        self.cb_week_mode = ttk.Combobox(action_bar, values=["both", "current", "last"], state="readonly", width=10)
        self.cb_week_mode.set("both")
        self.cb_week_mode.pack(side="left", padx=5)

        self.btn_run = ttk.Button(action_bar, text="Run Import Now", style="Accent.TButton", command=self.trigger_live_import)
        self.btn_run.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # Console Text Box
        console_frame = ttk.Frame(parent, style="Panel.TFrame")
        console_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.txt_console = tk.Text(console_frame, bg="#0d0d0d", fg=FG_TEXT, insertbackground=FG_TEXT, 
                                   font=("Consolas", 9), relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, wrap="word")
        self.txt_console.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(console_frame, orient="vertical", command=self.txt_console.yview)
        scrollbar.pack(side="right", fill="y")
        self.txt_console.configure(yscrollcommand=scrollbar.set)

    def browse_wow_directory(self):
        dir_selected = filedialog.askdirectory(title="Select your World of Warcraft Retail WTF Account folder", initialdir="C:\\Program Files (x86)\\World of Warcraft")
        if dir_selected:
            self.ent_wow_path.delete(0, tk.END)
            self.ent_wow_path.insert(0, os.path.normpath(dir_selected))

    def log_message(self, msg):
        self.txt_console.insert(tk.END, f"{msg}\n")
        self.txt_console.see(tk.END)

    def trigger_live_import(self):
        # Concurrency check
        if str(self.btn_run.cget("state")) == "disabled":
            self.log_message("\n[INFO] An import/sync task is already active. Skipping request.")
            return

        # Save first before running to ensure python reads latest fields
        self.save_settings()

        self.btn_run.configure(state="disabled")
        self.log_message("\n--- Starting Mythic+ Importer Process ---")
        
        week_mode = self.cb_week_mode.get()
        script_file = self.addon_dir / "raidlootmatrix_mplus.py"

        def worker():
            if getattr(sys, 'frozen', False):
                cmd = [sys.executable, "--run-mplus", "--week", week_mode]
            else:
                cmd = ["python", str(script_file), "--week", week_mode]
            self.log_message(f"Executing: {' '.join(cmd)}")
            try:
                # Set stdout / stderr flags to read directly
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True, 
                    bufsize=1,
                    universal_newlines=True,
                    encoding="utf-8",
                    creationflags=0x08000000 if sys.platform == "win32" else 0
                )
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    self.log_message(line.rstrip())
                
                process.wait()
                self.log_message(f"Importer finished with exit code {process.returncode}")
                if process.returncode == 0:
                    self.log_message("Mythic+ data updated! Log into WoW and open /rlm UI to apply changes.")
                    
                    if self.var_sync_on_import.get():
                        self.log_message("\n--- Running Automatic Discord RLM Sync ---")
                        sync_script = self.addon_dir / "rlm_discord_sync.py"
                        if getattr(sys, 'frozen', False):
                            sync_cmd = [sys.executable, "--run-sync", "--non-interactive"]
                        else:
                            sync_cmd = ["python", str(sync_script), "--non-interactive"]
                        self.log_message(f"Executing: {' '.join(sync_cmd)}")
                        sync_proc = subprocess.Popen(
                            sync_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1,
                            universal_newlines=True,
                            encoding="utf-8",
                            creationflags=0x08000000 if sys.platform == "win32" else 0
                        )
                        while True:
                            line = sync_proc.stdout.readline()
                            if not line:
                                break
                            self.log_message(line.rstrip())
                        sync_proc.wait()
                        self.log_message(f"Discord sync finished with exit code {sync_proc.returncode}")
            except Exception as e:
                self.log_message(f"Process crashed: {e}")
            finally:
                self.root.after(0, lambda: self.btn_run.configure(state="normal"))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def trigger_discord_sync(self):
        # Concurrency check
        if str(self.btn_run.cget("state")) == "disabled":
            self.log_message("\n[INFO] An import/sync task is already active. Skipping request.")
            return

        # Save first before running to ensure python reads latest fields
        self.save_settings()

        self.log_message("\n--- Starting Discord RLM Sync Process ---")
        
        script_file = self.addon_dir / "rlm_discord_sync.py"

        # Disable buttons while running
        self.btn_run.configure(state="disabled")
        if hasattr(self, "btn_sync_now"):
            self.btn_sync_now.configure(state="disabled")
        
        def worker():
            if getattr(sys, 'frozen', False):
                cmd = [sys.executable, "--run-sync", "--non-interactive"]
            else:
                cmd = ["python", str(script_file), "--non-interactive"]
            self.log_message(f"Executing: {' '.join(cmd)}")
            try:
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True, 
                    bufsize=1,
                    universal_newlines=True,
                    encoding="utf-8",
                    creationflags=0x08000000 if sys.platform == "win32" else 0
                )
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    self.log_message(line.rstrip())
                
                process.wait()
                self.log_message(f"Sync finished with exit code {process.returncode}")
            except Exception as e:
                self.log_message(f"Process crashed: {e}")
            finally:
                self.root.after(0, lambda: self.btn_run.configure(state="normal"))
                if hasattr(self, "btn_sync_now"):
                    self.root.after(0, lambda: self.btn_sync_now.configure(state="normal"))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def register_background_tasks(self):
        if platform.system() != "Windows":
            messagebox.showinfo("Automation Task Info", "Background task automation controls (schtasks) are only supported on Windows.\nOn macOS, you can configure plist or launchd actions.")
            return

        # Setup variables
        am_time = self.ent_sched_am.get().strip()
        pm_time = self.ent_sched_pm.get().strip()
        silent_bat = self.addon_dir / "raidlootmatrix_mplus_silent.bat"
        task_folder = "RaidLootMatrix"

        # Generate/overwrite the silent batch runner
        try:
            mplus_py = self.addon_dir / "raidlootmatrix_mplus.py"
            sync_py = self.addon_dir / "rlm_discord_sync.py"
            with open(silent_bat, "w", encoding="utf-8") as f:
                f.write('@echo off\n')
                f.write('set RAIDLOOTMATRIX_SCHEDULED=1\n')
                if getattr(sys, 'frozen', False):
                    f.write(f'"{sys.executable}" --run-mplus --week both > "{self.addon_dir / "raidlootmatrix_mplus_auto.log"}" 2>&1\n')
                    if self.var_sync_on_import.get():
                        f.write(f'"{sys.executable}" --run-sync --non-interactive >> "{self.addon_dir / "raidlootmatrix_mplus_auto.log"}" 2>&1\n')
                else:
                    f.write(f'python "{mplus_py}" --week both > "{self.addon_dir / "raidlootmatrix_mplus_auto.log"}" 2>&1\n')
                    if self.var_sync_on_import.get():
                        f.write(f'python "{sync_py}" --non-interactive >> "{self.addon_dir / "raidlootmatrix_mplus_auto.log"}" 2>&1\n')
        except Exception as e:
            self.log_message(f"Failed to generate silent runner: {e}")
            return

        self.log_message("\n--- Registering Scheduled Tasks ---")
        
        # Helper to execute task commands
        def run_task_cmd(cmd_args, desc):
            try:
                res = subprocess.run(cmd_args, capture_output=True, text=True,
                                     creationflags=0x08000000 if sys.platform == "win32" else 0)
                if res.returncode == 0:
                    self.log_message(f"SUCCESS: Created task: {desc}")
                else:
                    self.log_message(f"FAILED: Task: {desc}\nError: {res.stderr.strip()}")
            except Exception as e:
                self.log_message(f"Execution Error: {e}")

        vbs_runner = self.addon_dir / "raidlootmatrix_mplus_run.vbs"

        # Task 1: AM Time
        cmd_am = ["schtasks", "/create", "/tn", f"{task_folder}\\M+ Import - Daily AM", "/tr", f"wscript.exe \"{vbs_runner}\"", "/sc", "DAILY", "/st", am_time, "/f"]
        run_task_cmd(cmd_am, f"Daily at {am_time}")

        # Task 2: PM Time
        cmd_pm = ["schtasks", "/create", "/tn", f"{task_folder}\\M+ Import - Daily PM", "/tr", f"wscript.exe \"{vbs_runner}\"", "/sc", "DAILY", "/st", pm_time, "/f"]
        run_task_cmd(cmd_pm, f"Daily at {pm_time}")

        # Task 3: Logon if enabled
        if self.var_sched_logon.get():
            cmd_logon = ["schtasks", "/create", "/tn", f"{task_folder}\\M+ Import - At Logon", "/tr", f"wscript.exe \"{vbs_runner}\"", "/sc", "ONLOGON", "/delay", "0005:00", "/f"]
            run_task_cmd(cmd_logon, "At logon (5 min delay)")
        else:
            # Delete if disabled
            subprocess.run(["schtasks", "/delete", "/tn", f"{task_folder}\\M+ Import - At Logon", "/f"], capture_output=True,
                           creationflags=0x08000000 if sys.platform == "win32" else 0)

        # Task 4: WoW Watcher
        watcher_vbs = self.addon_dir / "raidlootmatrix_watcher_run.vbs"
        if self.var_sync_on_wow_exit.get():
            # Generate VBScript to run watcher silently
            vbs_script = (
                "' raidlootmatrix_watcher_run.vbs\n"
                "' Launches RLM_Companion.exe --watch-wow with a completely hidden window.\n"
                "Dim shell, fso, scriptDir, exe\n"
                "Set shell = CreateObject(\"WScript.Shell\")\n"
                "Set fso = CreateObject(\"Scripting.FileSystemObject\")\n"
                "scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)\n\n"
                "If fso.FileExists(scriptDir & \"\\RLM_Companion.exe\") Then\n"
                "    exe = \"\"\"\" & scriptDir & \"\\RLM_Companion.exe\"\" --watch-wow\"\n"
                "Else\n"
                "    exe = \"python \"\"\" & scriptDir & \"\\rlm_importer_ui.py\"\" --watch-wow\"\n"
                "End If\n\n"
                "shell.Run exe, 0, False\n"
                "Set shell = Nothing\n"
                "Set fso = Nothing\n"
            )
            try:
                with open(watcher_vbs, "w", encoding="utf-8") as f:
                    f.write(vbs_script)
            except Exception as e:
                self.log_message(f"Failed to generate watcher VBS: {e}")

            cmd_watcher = ["schtasks", "/create", "/tn", f"{task_folder}\\M+ Import - WoW Watcher", "/tr", f"wscript.exe \"{watcher_vbs}\"", "/sc", "ONLOGON", "/f"]
            run_task_cmd(cmd_watcher, "WoW Watcher (runs on WoW exit)")
            
            # Start it immediately so they don't need to log out/in
            subprocess.run(["schtasks", "/run", "/tn", f"{task_folder}\\M+ Import - WoW Watcher"], capture_output=True,
                           creationflags=0x08000000 if sys.platform == "win32" else 0)
        else:
            # Delete task and cleanup file
            subprocess.run(["schtasks", "/delete", "/tn", f"{task_folder}\\M+ Import - WoW Watcher", "/f"], capture_output=True,
                           creationflags=0x08000000 if sys.platform == "win32" else 0)
            if watcher_vbs.exists():
                try:
                    os.remove(watcher_vbs)
                except Exception:
                    pass

        messagebox.showinfo("Tasks Updated", "Scheduled Tasks updated in Task Scheduler!")

    def unregister_background_tasks(self):
        if platform.system() != "Windows":
            messagebox.showinfo("Automation Task Info", "Controls are only supported on Windows.")
            return

        self.log_message("\n--- Removing Scheduled Tasks ---")
        task_folder = "RaidLootMatrix"
        
        tasks = [
            f"{task_folder}\\M+ Import - Daily AM",
            f"{task_folder}\\M+ Import - Daily PM",
            f"{task_folder}\\M+ Import - At Logon",
            f"{task_folder}\\M+ Import - WoW Watcher"
        ]

        for t in tasks:
            try:
                res = subprocess.run(["schtasks", "/delete", "/tn", t, "/f"], capture_output=True, text=True,
                                     creationflags=0x08000000 if sys.platform == "win32" else 0)
                if res.returncode == 0:
                    self.log_message(f"SUCCESS: Deleted task: {t}")
                else:
                    self.log_message(f"INFO: Task {t} was not found or already deleted.")
            except Exception as e:
                self.log_message(f"Execution Error: {e}")

        # Cleanup watcher VBScript
        watcher_vbs = self.addon_dir / "raidlootmatrix_watcher_run.vbs"
        if watcher_vbs.exists():
            try:
                os.remove(watcher_vbs)
            except Exception:
                pass

        messagebox.showinfo("Tasks Removed", "RaidLootMatrix scheduled tasks removed.")

    def create_tray_image(self):
        # Generate a clean 64x64 transparent icon
        image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        dc = ImageDraw.Draw(image)
        # Gold circular border
        dc.ellipse([6, 6, 58, 58], outline=(255, 204, 0, 255), width=4)
        # Gold inner square
        dc.rectangle([18, 18, 46, 46], fill=(255, 204, 0, 255))
        # Transparent center details
        dc.rectangle([26, 26, 38, 38], fill=(0, 0, 0, 0))
        return image

    def start_tray_icon(self):
        # Define menu items
        menu = pystray.Menu(
            pystray.MenuItem("Open Control Panel", self.show_window, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Run M+ Import Now", lambda: self.root.after(0, self.trigger_live_import)),
            pystray.MenuItem("Run Discord Sync Now", lambda: self.root.after(0, self.trigger_discord_sync)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit RLM Companion", self.quit_app)
        )
        
        # Load custom icon if available, otherwise generate fallback
        if self.icon_path_png.exists():
            try:
                image = Image.open(self.icon_path_png)
            except Exception:
                image = self.create_tray_image()
        else:
            image = self.create_tray_image()
            
        self.tray_icon = pystray.Icon("RLM Companion", image, "RLM Desktop Companion", menu)
        
        # Run tray loop in a background daemon thread
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    def hide_window(self):
        # Hide the main Tkinter window
        self.root.withdraw()
        self.log_message("Minimized to system tray. Double-click the tray icon to reopen.")

    def show_window(self, icon=None, item=None):
        # Restore the Tkinter window safely from tray thread
        self.root.after(0, self._restore_window)

    def _restore_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def quit_app(self, icon=None, item=None):
        # Fully shutdown everything
        if hasattr(self, "tray_icon") and self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.root.destroy)

    def update_startup_shortcut(self):
        startup_dir = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        vbs_path = os.path.join(startup_dir, "RLM_Desktop_Companion_Startup.vbs")
        
        if self.settings.get("run_on_startup", True):
            try:
                if getattr(sys, 'frozen', False):
                    # Compiled EXE runs itself directly
                    run_cmd = f'"""{sys.executable}"""'
                else:
                    # Dev mode runs pythonw.exe
                    python_dir = os.path.dirname(sys.executable)
                    pythonw_exe = os.path.join(python_dir, "pythonw.exe")
                    if not os.path.exists(pythonw_exe):
                        pythonw_exe = "pythonw.exe"
                    run_cmd = f'"""{pythonw_exe}"" ""{self.addon_dir / "rlm_importer_ui.py"}"""'
                
                with open(vbs_path, "w", encoding="utf-8") as f:
                    f.write(f'Set WshShell = CreateObject("WScript.Shell")\n')
                    f.write(f'WshShell.Run {run_cmd}, 0, False\n')
                self.log_message("Windows startup shortcut registered successfully.")
            except Exception as e:
                self.log_message(f"Error creating startup shortcut: {e}")
        else:
            if os.path.exists(vbs_path):
                try:
                    os.remove(vbs_path)
                    self.log_message("Windows startup shortcut removed.")
                except Exception as e:
                    self.log_message(f"Error removing startup shortcut: {e}")

    def create_desktop_shortcut(self):
        desktop_dir = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
        if not os.path.exists(desktop_dir):
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        shortcut_lnk = os.path.join(desktop_dir, "RLM Desktop Companion.lnk")
        
        if getattr(sys, 'frozen', False):
            # Compiled EXE shortcut points directly to itself
            target_path = sys.executable
            arguments = ""
        else:
            # Dev mode shortcut points to pythonw.exe
            python_dir = os.path.dirname(sys.executable)
            pythonw_exe = os.path.join(python_dir, "pythonw.exe")
            if not os.path.exists(pythonw_exe):
                pythonw_exe = "pythonw.exe"
            target_path = pythonw_exe
            arguments = f'"""{self.addon_dir / "rlm_importer_ui.py"}"""'
            
        vbs_script = (
            f'Set WshShell = CreateObject("WScript.Shell")\n'
            f'Set oMyShortcut = WshShell.CreateShortcut("{shortcut_lnk}")\n'
            f'oMyShortcut.TargetPath = "{target_path}"\n'
        )
        if arguments:
            vbs_script += f'oMyShortcut.Arguments = {arguments}\n'
        vbs_script += (
            f'oMyShortcut.WorkingDirectory = "{self.addon_dir}"\n'
            f'oMyShortcut.IconLocation = "{self.icon_path_ico},0"\n'
            f'oMyShortcut.Save\n'
        )
        
        try:
            vbs_tmp = self.addon_dir / "create_shortcut_temp.vbs"
            with open(vbs_tmp, "w", encoding="utf-8") as f:
                f.write(vbs_script)
            
            subprocess.run(["cscript", "/nologo", str(vbs_tmp)], capture_output=True,
                           creationflags=0x08000000 if sys.platform == "win32" else 0)
            if vbs_tmp.exists():
                os.remove(vbs_tmp)
            self.log_message("Desktop shortcut created successfully.")
        except Exception as e:
            self.log_message(f"Could not create desktop shortcut: {e}")

def watch_wow_process():
    import time
    import subprocess
    
    executable = sys.executable
    script_dir = os.path.dirname(os.path.abspath(executable))
    
    # Resolve log path
    log_file = os.path.join(script_dir, "raidlootmatrix_mplus_auto.log")
    
    def log_msg(msg):
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watcher] {msg}\n")
        except Exception:
            pass

    log_msg("WoW Close Watcher process started.")
    
    # Determine the execution arguments (python vs compiled exe)
    if getattr(sys, 'frozen', False):
        executable_args = [sys.executable]
    else:
        executable_args = [sys.executable, sys.argv[0]]

    def is_wow_running():
        try:
            # CREATE_NO_WINDOW = 0x08000000
            output = subprocess.check_output('tasklist /FI "IMAGENAME eq Wow.exe"', shell=True, creationflags=0x08000000).decode('utf-8', errors='ignore')
            return "Wow.exe" in output
        except Exception:
            return False

    was_running = False
    while True:
        try:
            running = is_wow_running()
            if running:
                if not was_running:
                    log_msg("Wow.exe detected running.")
                    was_running = True
            else:
                if was_running:
                    log_msg("Wow.exe closed! Starting synchronization...")
                    
                    # Run Mythic+ runs parser and Discord Sync, outputting to the log file
                    with open(log_file, "a", encoding="utf-8") as lf:
                        lf.write("\n--- Running M+ Import ---\n")
                        lf.flush()
                        subprocess.run(executable_args + ["--run-mplus", "--week", "both"], stdout=lf, stderr=lf, cwd=script_dir, creationflags=0x08000000)
                        
                        lf.write("\n--- Running Discord Sync ---\n")
                        lf.flush()
                        subprocess.run(executable_args + ["--run-sync", "--non-interactive"], stdout=lf, stderr=lf, cwd=script_dir, creationflags=0x08000000)
                    
                    log_msg("Synchronization completed.")
                    was_running = False
        except Exception as e:
            log_msg(f"Error in watcher loop: {e}")
            
        time.sleep(15)

if __name__ == "__main__":
    # Check for command line argument routing
    if len(sys.argv) > 1:
        arg1 = sys.argv[1]
        if arg1 == "--run-mplus":
            # Shift sys.argv to remove --run-mplus so raidlootmatrix_mplus parses its options normally
            sys.argv = [sys.argv[0]] + sys.argv[2:]
            try:
                raidlootmatrix_mplus.main()
            except Exception as e:
                print(f"[ERROR] Mythic+ importer failed: {e}")
                sys.exit(1)
            sys.exit(0)
        elif arg1 == "--run-sync":
            # Shift sys.argv to remove --run-sync so rlm_discord_sync parses its options normally
            sys.argv = [sys.argv[0]] + sys.argv[2:]
            try:
                rlm_discord_sync.main()
            except Exception as e:
                print(f"[ERROR] Discord sync failed: {e}")
                sys.exit(1)
            sys.exit(0)
        elif arg1 == "--watch-wow":
            try:
                watch_wow_process()
            except Exception as e:
                print(f"[ERROR] WoW watcher failed: {e}")
                sys.exit(1)
            sys.exit(0)

    root = tk.Tk()
    app = RLMImporterApp(root)
    
    # Enforce single instance of UI, wake up existing window if duplicate launched
    app_lock = check_single_instance(lambda: root.after(0, app.show_window))
    
    root.mainloop()
