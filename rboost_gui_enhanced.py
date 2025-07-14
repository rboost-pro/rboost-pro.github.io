
import sys
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import os
import psutil
import logging
import threading
import subprocess
import re
import platform
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import time
import getpass
import json
import ctypes
import shutil
from collections import defaultdict
import glob
import winshell
import winreg as reg
import urllib.request
from packaging.version import parse as parse_version
import win32event
import win32api
import winerror

# --- Logging Configuration ---
# Configure logging to write to a file and console with timestamps.
log_filename = "rboost_app.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)

logging.info("--- Application startup initiated ---")
logging.info(f"Python Version: {sys.version}")
logging.info(f"Platform: {platform.platform()}")
logging.info(f"CustomTkinter Version: {ctk.__version__}")
logging.info(f"psutil Version: {psutil.__version__}")

# --- Global Settings & Paths ---
APP_VERSION = "1.1" # Updated version number
SETTINGS_FILE = "rboost_settings.json"


class RBoostApp(ctk.CTk):
    """
    Main application window and logic for RBoost PRO.
    """
    def __init__(self, *args, **kwargs):
        logging.info("Creating RBoostApp instance.")
        logging.info("Entering RBoostApp __init__ method.")
        super().__init__(*args, **kwargs)
        logging.info("super().__init__() called successfully.")

        # --- Window Configuration ---
        self.title("RBoost PRO")
        self.geometry(f"{1280}x{1024}")
        self.minsize(1000, 600)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        logging.info("Window close protocol set.")

        # Center the window on the screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width / 2) - (1280 / 2)
        y = (screen_height / 2) - (1024 / 2)
        self.geometry(f'+{int(x)}+{int(y)}')
        logging.info("Window geometry and properties configured.")

        # Set icon
        self.base_path = "."
        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS
            logging.info(f"PyInstaller bundle detected. Base path: {self.base_path}")
        
        icon_path = os.path.join(self.base_path, 'rboost_logo.ico')
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
            logging.info(f"Icon set successfully from path: {icon_path}")

        # --- Class Variables ---
        self.settings = {}
        self.load_settings()
        self.is_admin = self.check_admin()
        self.running_tasks = {}
        self.after_ids = {}
        self.cleanup_thread = None
        self.cleanup_stop_event = threading.Event()
        self.restore_point_manager_window = None

        # --- System Monitor Data ---
        self.max_data_points = 60
        self.time_data = []
        self.cpu_usage = []
        self.ram_usage = []
        self.net_usage = []
        self.disk_usage = []
        self.network_bytes_sent_prev = 0
        self.network_bytes_recv_prev = 0
        self.start_time = time.time()

        # --- UI Layout ---
        logging.info("Starting to build main UI layout.")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Let the main_frame expand inside root window
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Main frame
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)

        # Sidebar frame
        self.sidebar_frame = ctk.CTkFrame(self.main_frame, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="ns")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        # Tabview (main screen area)
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")


        # Sidebar buttons
        self.dashboard_button = ctk.CTkButton(self.sidebar_frame, text="Dashboard", command=lambda: self.tabview.set("Dashboard"))
        self.dashboard_button.grid(row=0, column=0, padx=20, pady=10)
        self.toolbox_button = ctk.CTkButton(self.sidebar_frame, text="Toolbox", command=lambda: self.tabview.set("Toolbox"))
        self.toolbox_button.grid(row=1, column=0, padx=20, pady=10)
        self.startup_manager_button = ctk.CTkButton(self.sidebar_frame, text="Startup Manager", command=lambda: self.tabview.set("Startup Manager"))
        self.startup_manager_button.grid(row=2, column=0, padx=20, pady=10)
        self.system_manager_button = ctk.CTkButton(self.sidebar_frame, text="System Manager", command=lambda: self.tabview.set("System Manager"))
        self.system_manager_button.grid(row=3, column=0, padx=20, pady=10)
        self.speed_test_button = ctk.CTkButton(self.sidebar_frame, text="Speed Test", command=lambda: self.tabview.set("Speed Test"))
        self.speed_test_button.grid(row=4, column=0, padx=20, pady=10)
        self.command_console_button = ctk.CTkButton(self.sidebar_frame, text="Command Console", command=lambda: self.tabview.set("Command Console"))
        self.command_console_button.grid(row=5, column=0, padx=20, pady=10)
        self.settings_button = ctk.CTkButton(self.sidebar_frame, text="Settings", command=lambda: self.tabview.set("Settings"))
        self.settings_button.grid(row=6, column=0, padx=20, pady=10)
        self.about_button = ctk.CTkButton(self.sidebar_frame, text="About", command=lambda: self.tabview.set("About"))
        self.about_button.grid(row=7, column=0, padx=20, pady=10)

        # Tabview
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        logging.info("Tabview created.")

        # Add tabs
        self.tabview.add("Dashboard")
        self.tabview.add("Toolbox")
        self.tabview.add("Startup Manager")
        self.tabview.add("System Manager")
        self.tabview.add("Speed Test")
        self.tabview.add("Command Console")
        self.tabview.add("Settings")
        self.tabview.add("About")
        logging.info("Tabs added to tabview.")

        # Status Box and Progress Bar
        self.status_box = ctk.CTkTextbox(self, height=100, state="disabled")
        self.status_box.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")
        logging.info("Status box created.")
        self.progress_bar = ctk.CTkProgressBar(self, mode="determinate")
        self.progress_bar.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew")
        self.progress_bar.set(0)
        logging.info("Progress bar created.")
        
        # Call build functions for each tab
        logging.info("Calling build functions for each tab...")
        self.build_dashboard()
        self.build_toolbox()
        self.build_startup_manager()
        self.build_system_manager()
        self.build_speed_test()
        self.build_command_console()
        self.build_settings()
        self.build_about()
        logging.info("All UI elements built successfully.")

        # Initial check for updates and dependencies
        threading.Thread(target=self.install_dependencies, daemon=True).start()
        
        # --- Start Background Tasks ---
        logging.info("Scheduling background threads and updates.")
        self.after(100, self.update_system_metrics)
        
        # Start silent cleanup if setting is enabled
        #if self.settings.get("silent_cleanup_enabled"):
        #self.start_silent_cleanup()

        logging.info("Background tasks scheduled.")
        
        logging.info("RBoostApp __init__ method finished. Ready for mainloop.")

    # --- UI Helper Functions ---
    def log_status(self, message):
        """Logs a message to the status box."""
        self.status_box.configure(state="normal")
        self.status_box.insert("end", f"{message}\n")
        self.status_box.see("end")
        self.status_box.configure(state="disabled")

    def update_progress(self, value, message=None):
        """Updates the progress bar and status message."""
        self.progress_bar.set(value)
        if message:
            self.log_status(message)
        self.update_idletasks()

    def on_close(self):
        """Handles the application shutdown sequence."""
        logging.info("on_close method called. Starting shutdown sequence.")
        self.save_settings()
        
        # Stop background cleanup thread
        self.stop_silent_cleanup()

        # Cancel scheduled `after` calls
        for after_id in list(self.after_ids.keys()):
            if self.after_ids[after_id]:
                try:
                    self.after_cancel(self.after_ids[after_id])
                    logging.info(f"Cancelled after ID for {after_id}")
                except Exception as e:
                    logging.error(f"Failed to cancel after ID {after_id}: {e}")

        logging.info("Destroying main window.")
        self.destroy()
        logging.info("Main window destroyed. Exiting application.")
        sys.exit(0)

    # --- System & File System Functions ---
    def check_admin(self):
        """
        Checks if the script is running with administrative privileges on Windows.
        """
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            logging.info(f"Is running as a Windows admin: {is_admin}")
            return is_admin
        except Exception as e:
            logging.warning(f"Could not determine admin status: {e}. Assuming not admin.")
            return False

    def load_settings(self):
        """Loads settings from a JSON file."""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    self.settings = json.load(f)
                logging.info("Settings loaded successfully.")
                self.update_ui_theme()
            else:
                self.settings = {"theme": "dark", "auto_reboot_prompt": True, "silent_cleanup_enabled": False}
                logging.warning("Settings file not found. Using default settings.")
        except Exception as e:
            self.settings = {"theme": "dark", "auto_reboot_prompt": True, "silent_cleanup_enabled": False}
            logging.error(f"Failed to load settings: {e}. Using default.")
            
    def save_settings(self):
        """Saves settings to a JSON file."""
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.settings, f, indent=4)
            logging.info("Settings saved successfully.")
        except Exception as e:
            logging.error(f"Failed to save settings: {e}")

    def import_settings(self):
        """Allows importing settings from a file."""
        file_path = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                with open(file_path, "r") as f:
                    new_settings = json.load(f)
                self.settings.update(new_settings)
                self.save_settings()
                self.load_settings() # Reload to apply
                messagebox.showinfo("Success", "Settings imported successfully!")
                self.log_status("Settings imported from file.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import settings: {e}")
                self.log_status(f"Error importing settings: {e}")
                
    def export_settings(self):
        """Allows exporting settings to a file."""
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                with open(file_path, "w") as f:
                    json.dump(self.settings, f, indent=4)
                messagebox.showinfo("Success", "Settings exported successfully!")
                self.log_status("Settings exported to file.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export settings: {e}")
                self.log_status(f"Error exporting settings: {e}")
                
    def reset_settings(self):
        """Resets settings to default values."""
        self.settings = {"theme": "dark", "auto_reboot_prompt": True, "silent_cleanup_enabled": False}
        self.save_settings()
        self.load_settings()
        messagebox.showinfo("Success", "Settings have been reset to default.")
        self.log_status("Settings have been reset to default.")

    def update_ui_theme(self):
        """Applies the theme from settings."""
        ctk.set_appearance_mode(self.settings.get("theme", "dark"))

    def prompt_reboot(self):
        """Prompts the user to reboot the system."""
        if self.settings.get("auto_reboot_prompt"):
            if messagebox.askyesno("Reboot Required", "Some changes require a system reboot to take effect. Would you like to reboot now?"):
                self.log_status("Rebooting system...")
                subprocess.Popen(['shutdown', '/r', '/t', '0'])

    # --- UI Build Functions ---
    def build_dashboard(self):
        """Builds the Dashboard tab UI."""
        logging.info("Building Dashboard tab.")
        dashboard_frame = self.tabview.tab("Dashboard")
        dashboard_frame.grid_columnconfigure(0, weight=1)
        dashboard_frame.grid_rowconfigure(1, weight=1)
        
        # Welcome message
        username = getpass.getuser()
        welcome_label = ctk.CTkLabel(dashboard_frame, text=f"Welcome, {username}!", font=ctk.CTkFont(size=28, weight="bold"))
        welcome_label.grid(row=0, column=0, padx=20, pady=20, sticky="n")

        # System Monitor Graphs
        logging.info("Setting up Matplotlib for Dashboard.")
        self.fig = Figure(figsize=(10, 8))
        self.fig.patch.set_facecolor("#2b2b2b") # Match CTk background
        self.ax_cpu = self.fig.add_subplot(3, 1, 1)
        self.ax_ram = self.fig.add_subplot(3, 1, 2)
        self.ax_net = self.fig.add_subplot(3, 1, 3)

        # Configure axes
        for ax in [self.ax_cpu, self.ax_ram, self.ax_net]:
            ax.set_facecolor("#2b2b2b")
            ax.tick_params(axis='both', colors='white')
            ax.spines['bottom'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.spines['right'].set_visible(False)
            ax.spines['top'].set_visible(False)
            ax.title.set_color('white')
            ax.set_ylabel('Usage (%)', color='white')
            ax.tick_params(axis='x', labelbottom=False)

        self.ax_cpu.set_title("CPU Usage (%)")
        self.ax_ram.set_title("RAM Usage (%)")
        self.ax_net.set_title("Network Usage (KB/s)")
        self.ax_net.set_ylabel("Usage (KB/s)", color='white')

        self.line_cpu, = self.ax_cpu.plot([], [], color='#4CAF50')
        self.line_ram, = self.ax_ram.plot([], [], color='#2196F3')
        self.line_net, = self.ax_net.plot([], [], color='#FFC107')

        self.canvas = FigureCanvasTkAgg(self.fig, master=dashboard_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        logging.info("Matplotlib canvas created successfully.")

        # Disk Usage Pie Chart
        disk_chart_frame = ctk.CTkFrame(dashboard_frame, fg_color="transparent")
        disk_chart_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        # This will be updated later with the actual plot
        self.disk_label = ctk.CTkLabel(disk_chart_frame, text="Disk Usage: C:\\ (0%)", font=ctk.CTkFont(size=16))
        self.disk_label.pack(pady=5)
        
        logging.info("Dashboard built.")

    def build_toolbox(self):
        """Builds the Toolbox tab UI."""
        logging.info("Building Toolbox tab.")
        toolbox_frame = self.tabview.tab("Toolbox")
        toolbox_frame.grid_columnconfigure(0, weight=1)
        
        # Tweak buttons based on the script
        title_label = ctk.CTkLabel(toolbox_frame, text="System Optimization Toolbox", font=ctk.CTkFont(size=24, weight="bold"))
        title_label.grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="n")

        # One-click Boost button
        boost_frame = ctk.CTkFrame(toolbox_frame)
        boost_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.one_click_boost_btn = ctk.CTkButton(boost_frame, text="🚀 One-Click Boost", font=ctk.CTkFont(size=18, weight="bold"), height=50, command=lambda: self.run_task(self.one_click_boost, "Applying one-click boost..."))
        self.one_click_boost_btn.pack(fill="x", padx=10, pady=10)

        # Create a container frame for other buttons
        buttons_frame = ctk.CTkFrame(toolbox_frame, fg_color="transparent")
        buttons_frame.grid(row=2, column=0, padx=20, pady=10)
        buttons_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Toolbox buttons
        ctk.CTkButton(buttons_frame, text="🧹 Clean Temp Files", command=lambda: self.run_task(self.clean_temp_files, "Cleaning temporary files...")).grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(buttons_frame, text="🛡️ Create Restore Point", command=lambda: self.run_task(self.create_restore_point, "Creating system restore point...")).grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(buttons_frame, text="📦 Debloat Windows", command=lambda: self.run_task(self.debloat_windows_apps, "Debloating Windows apps...")).grid(row=0, column=2, padx=10, pady=10, sticky="ew")
        
        ctk.CTkButton(buttons_frame, text="⚙️ Optimize Services", command=lambda: self.run_task(self.deep_service_optimizer, "Optimizing services...")).grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(buttons_frame, text="📁 Disk Usage Analyzer", command=lambda: self.run_task(self.analyze_disk_usage, "Analyzing disk usage...")).grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(buttons_frame, text="🗃️ Clear Browser Cache", command=lambda: self.run_task(self.clear_browser_cache, "Clearing browser caches...")).grid(row=1, column=2, padx=10, pady=10, sticky="ew")
        
        ctk.CTkButton(buttons_frame, text="💾 Flush Standby RAM", command=lambda: self.run_task(self.flush_standby_ram, "Flushing standby RAM...")).grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(buttons_frame, text="Kill Background Bloat", command=lambda: self.run_task(self.kill_background_apps, "Killing background apps...")).grid(row=2, column=2, padx=10, pady=10, sticky="ew")
        
        ctk.CTkButton(buttons_frame, text="Control Panel", command=self.launch_control_panel).grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(buttons_frame, text="App Uninstaller", command=self.launch_app_uninstaller).grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(buttons_frame, text="⏳ Manage Restore Points", command=self.open_restore_point_manager).grid(row=3, column=2, padx=10, pady=10, sticky="ew") # New button

        logging.info("Toolbox built.")

    def build_startup_manager(self):
        """Builds the Startup Manager tab UI."""
        logging.info("Building Startup Manager tab.")
        startup_frame = self.tabview.tab("Startup Manager")
        startup_frame.grid_columnconfigure(0, weight=1)
        startup_frame.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(startup_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)
        
        header_label = ctk.CTkLabel(header_frame, text="Startup Applications", font=ctk.CTkFont(size=20, weight="bold"))
        header_label.grid(row=0, column=0, sticky="w")
        
        refresh_button = ctk.CTkButton(header_frame, text="Refresh", command=self.load_startup_items)
        refresh_button.grid(row=0, column=1, padx=(10, 0), sticky="e")
        
        self.startup_scroll_frame = ctk.CTkScrollableFrame(startup_frame)
        self.startup_scroll_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        self.load_startup_items()
        logging.info("Startup Manager built.")

    def build_system_manager(self):
        """Builds the System Manager tab UI."""
        logging.info("Building System Manager tab.")
        system_manager_tab = self.tabview.tab("System Manager")
        system_manager_tab.grid_columnconfigure(0, weight=1)
        system_manager_tab.grid_rowconfigure(0, weight=1)
        
        # Tabview for Services and Processes
        self.system_manager_tabview = ctk.CTkTabview(system_manager_tab)
        self.system_manager_tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        self.system_manager_tabview.add("Services")
        self.system_manager_tabview.add("Processes")
        
        self.build_services_tab()
        self.build_processes_tab()
        logging.info("System Manager built.")

    def build_services_tab(self):
        """Builds the Services tab within System Manager."""
        services_frame = self.system_manager_tabview.tab("Services")
        services_frame.grid_columnconfigure(0, weight=1)
        services_frame.grid_rowconfigure(1, weight=1)
        
        # Placeholder for services list
        services_label = ctk.CTkLabel(services_frame, text="Services List will be here.", font=ctk.CTkFont(size=16))
        services_label.grid(row=0, column=0, padx=20, pady=20)
        
    def build_processes_tab(self):
        processes_frame = self.system_manager_tabview.tab("Processes")
        processes_frame.grid_columnconfigure(0, weight=1)
        processes_frame.grid_rowconfigure(1, weight=1)

        self.process_listbox = tk.Listbox(
            processes_frame,
            bg="#2b2b2b",
            fg="white",
            selectbackground="#4CAF50",
            activestyle="dotbox",
            height=25
        )
        self.process_listbox.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.process_data = {}

        def load_processes():
            self.process_listbox.delete(0, tk.END)
            self.process_data.clear()
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    pid = proc.info['pid']
                    name = proc.info['name']
                    display = f"{name} (PID: {pid})"
                    self.process_listbox.insert(tk.END, display)
                    self.process_data[display] = pid
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            self.log_status("✅ Process list refreshed.")

        def on_left_click(event):
            try:
                index = self.process_listbox.nearest(event.y)
                if index == -1:
                    return
                self.process_listbox.selection_clear(0, tk.END)
                self.process_listbox.selection_set(index)
                selected_item = self.process_listbox.get(index)
                pid = self.process_data.get(selected_item)
                if not pid:
                    return

                def kill():
                    if not self.is_admin:
                        messagebox.showerror("Permission Denied", "Administrator rights required.")
                        return
                    confirm = messagebox.askyesno("Confirm Kill", f"Kill process:\n{selected_item}?")
                    if confirm:
                        try:
                            proc = psutil.Process(pid)
                            proc.terminate()
                            self.log_status(f"✅ Killed: {selected_item}")
                            load_processes()
                        except Exception as e:
                            self.log_status(f"❌ Failed to kill: {e}")

                menu = tk.Menu(self, tearoff=0, bg="#333", fg="white",
                               activebackground="#4CAF50", activeforeground="white")
                menu.add_command(label="❌ Kill Process", command=kill)
                menu.post(event.x_root, event.y_root)

            except Exception as e:
                self.log_status(f"❌ Error: {e}")

        self.process_listbox.bind("<Button-1>", on_left_click)

        refresh_btn = ctk.CTkButton(processes_frame, text="🔄 Refresh", command=load_processes)
        refresh_btn.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        load_processes()



    def build_speed_test(self):
        """Builds the Speed Test tab UI."""
        speed_test_frame = self.tabview.tab("Speed Test")
        speed_test_frame.grid_columnconfigure(0, weight=1)
        speed_test_frame.grid_rowconfigure(1, weight=1)

        title_label = ctk.CTkLabel(speed_test_frame, text="Internet Speed Test", font=ctk.CTkFont(size=24, weight="bold"))
        title_label.grid(row=0, column=0, padx=20, pady=20)
        
        self.speed_test_output = ctk.CTkTextbox(speed_test_frame, height=400, state="disabled")
        self.speed_test_output.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        start_button = ctk.CTkButton(speed_test_frame, text="Start Speed Test", command=lambda: self.run_task(self.run_speed_test, "Starting speed test..."))
        start_button.grid(row=2, column=0, padx=20, pady=10)

    def build_command_console(self):
        console_frame = self.tabview.tab("Command Console")
        console_frame.grid_columnconfigure(0, weight=1)
        console_frame.grid_rowconfigure(1, weight=1)

        title_label = ctk.CTkLabel(console_frame, text="Command Console", font=ctk.CTkFont(size=24, weight="bold"))
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.console_output = ctk.CTkTextbox(console_frame, height=400, state="disabled")
        self.console_output.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        input_frame = ctk.CTkFrame(console_frame)
        input_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        self.command_entry = ctk.CTkEntry(input_frame, placeholder_text="Enter command (e.g. ipconfig /all)")
        self.command_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        execute_button = ctk.CTkButton(input_frame, text="Execute", command=self.execute_command)
        execute_button.grid(row=0, column=1, sticky="e")


    def build_settings(self):
        """Builds the Settings tab UI."""
        logging.info("Building Settings tab.")
        settings_frame = self.tabview.tab("Settings")
        settings_frame.grid_columnconfigure(0, weight=1)
        
        title_label = ctk.CTkLabel(settings_frame, text="Application Settings", font=ctk.CTkFont(size=24, weight="bold"))
        title_label.grid(row=0, column=0, padx=20, pady=20)
        
        # Theme Switcher
        theme_frame = ctk.CTkFrame(settings_frame)
        theme_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        ctk.CTkLabel(theme_frame, text="Theme:").pack(side="left", padx=10)
        theme_options = ["dark", "light"]
        self.theme_switcher = ctk.CTkOptionMenu(theme_frame, values=theme_options, command=self.change_theme)
        self.theme_switcher.set(self.settings.get("theme", "dark"))
        self.theme_switcher.pack(side="right", padx=10)
        
        # Reboot Prompt Toggle
        reboot_prompt_frame = ctk.CTkFrame(settings_frame)
        reboot_prompt_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        ctk.CTkLabel(reboot_prompt_frame, text="Prompt to reboot after tweaks:").pack(side="left", padx=10)
        self.reboot_prompt_switch = ctk.CTkSwitch(reboot_prompt_frame, text="", command=self.toggle_reboot_prompt)
        self.reboot_prompt_switch.pack(side="right", padx=10)
        if self.settings.get("auto_reboot_prompt", True):
            self.reboot_prompt_switch.select()

        # Silent Background Cleanup Toggle (New Feature)
        silent_cleanup_frame = ctk.CTkFrame(settings_frame)
        silent_cleanup_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        ctk.CTkLabel(silent_cleanup_frame, text="Enable silent background cleanup:").pack(side="left", padx=10)
        self.silent_cleanup_switch = ctk.CTkSwitch(silent_cleanup_frame, text="", command=self.toggle_silent_cleanup)
        self.silent_cleanup_switch.pack(side="right", padx=10)
        if self.settings.get("silent_cleanup_enabled", False):
            self.silent_cleanup_switch.select()

        # Config Import/Export/Reset
        config_frame = ctk.CTkFrame(settings_frame)
        config_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        ctk.CTkButton(config_frame, text="Import Settings", command=self.import_settings).pack(side="left", expand=True, padx=10, pady=10)
        ctk.CTkButton(config_frame, text="Export Settings", command=self.export_settings).pack(side="left", expand=True, padx=10, pady=10)
        ctk.CTkButton(config_frame, text="Reset Settings", command=self.reset_settings).pack(side="left", expand=True, padx=10, pady=10)
        
        logging.info("Settings page built.")

    def change_theme(self, new_theme):
        """Changes the UI theme."""
        ctk.set_appearance_mode(new_theme)
        self.settings["theme"] = new_theme
        self.save_settings()

    def toggle_reboot_prompt(self):
        """Toggles the reboot prompt setting."""
        self.settings["auto_reboot_prompt"] = self.reboot_prompt_switch.get() == 1
        self.save_settings()
        
    def toggle_silent_cleanup(self):
        """Toggles the silent background cleanup setting."""
        enabled = self.silent_cleanup_switch.get() == 1
        self.settings["silent_cleanup_enabled"] = enabled
        self.save_settings()
        if enabled:
            self.start_silent_cleanup()
            self.log_status("Silent background cleanup enabled. Will run every 12 hours.")
        else:
            self.stop_silent_cleanup()
            self.log_status("Silent background cleanup disabled.")

    def build_about(self):
        about_frame = self.tabview.tab("About")
        about_frame.grid_rowconfigure(0, weight=1)
        about_frame.grid_columnconfigure(0, weight=1)

        about_text = (
            f"RBoost PRO v{APP_VERSION}\n\n"
            "Developed by Rudra Purohit\n"
            "----------------------------------------\n"
            "RBoost PRO is an advanced, all-in-one PC optimization utility designed to enhance\n"
            "your Windows experience by improving speed, stability, and overall system health.\n\n"
            "🔧 Key Features:\n"
            "- One-Click Boost\n"
            "- System Cleanup\n"
            "- Deep Service Optimizer\n"
            "- RAM Booster\n"
            "- Restore Point Manager\n"
            "- Registry Tweaks\n"
            "- Startup Manager\n"
            "- Speed Test\n"
            "- Command Console\n"
            "- And much more...\n\n"
            "🛡️ Safety & Transparency:\n"
            "No data collection, no ads. Everything runs offline and locally.\n\n"
            "📧 Feedback: rudrakshpu8@gmail.com\n"
            "© 2025 Rudraksh Purohit. All rights reserved.\n"
        "----------------------------------------"
    )

        # Make the about_frame expandable
        about_frame.grid_rowconfigure(0, weight=1)
        about_frame.grid_columnconfigure(0, weight=1)

        # Scrollbar directly in the about_frame
        scrollbar = ctk.CTkScrollbar(about_frame, orientation="vertical")
        scrollbar.grid(row=0, column=1, sticky="ns", pady=20)

        # Full-size scrollable textbox
        about_box = ctk.CTkTextbox(
            about_frame,
            wrap="word",
            yscrollcommand=scrollbar.set,
            font=ctk.CTkFont(size=14)
        )
        about_box.grid(row=0, column=0, padx=(20, 0), pady=20, sticky="nsew")
        about_box.insert("1.0", about_text)
        about_box.configure(state="disabled")
        scrollbar.configure(command=about_box.yview)


    # --- System Metrics & Update Functions ---
    def update_system_metrics(self):
        """Fetches and updates system metrics."""
        try:
            # CPU, RAM, and Disk usage
            self.time_data.append(time.time() - self.start_time)
            self.cpu_usage.append(psutil.cpu_percent(interval=None))
            self.ram_usage.append(psutil.virtual_memory().percent)

            # Network usage (per second)
            net_io_counters = psutil.net_io_counters()
            bytes_sent = net_io_counters.bytes_sent
            bytes_recv = net_io_counters.bytes_recv
            
            if self.network_bytes_sent_prev == 0:
                self.network_bytes_sent_prev = bytes_sent
                self.network_bytes_recv_prev = bytes_recv
            
            sent_rate_kb = (bytes_sent - self.network_bytes_sent_prev) / 1024
            recv_rate_kb = (bytes_recv - self.network_bytes_recv_prev) / 1024
            
            self.network_bytes_sent_prev = bytes_sent
            self.network_bytes_recv_prev = bytes_recv
            
            total_rate_kb = sent_rate_kb + recv_rate_kb
            self.net_usage.append(total_rate_kb)
            
            # Keep data lists at a maximum size for a rolling window
            if len(self.time_data) > self.max_data_points:
                self.time_data.pop(0)
                self.cpu_usage.pop(0)
                self.ram_usage.pop(0)
                self.net_usage.pop(0)
            
            # Update plots
            self.line_cpu.set_data(self.time_data, self.cpu_usage)
            self.line_ram.set_data(self.time_data, self.ram_usage)
            self.line_net.set_data(self.time_data, self.net_usage)
            
            for ax in [self.ax_cpu, self.ax_ram, self.ax_net]:
                ax.relim()
                ax.autoscale_view()
            
            self.canvas.draw()
            
            # Update disk label
            c_disk = psutil.disk_usage('C:\\')
            self.disk_label.configure(text=f"Disk Usage: C:\\ ({c_disk.percent:.1f}%)")

        except Exception as e:
            logging.error(f"Error updating system metrics: {e}")
            
        self.after_ids["system_metrics"] = self.after(1000, self.update_system_metrics)

    # --- Startup Manager Functions ---
    def load_startup_items(self):
        """Loads startup items from the registry."""
        logging.info("Starting to load startup items from registry.")
        
        # Clear existing items from the UI
        for widget in self.startup_scroll_frame.winfo_children():
            widget.destroy()

        reg_paths = [
            (reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
            (reg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run")
        ]
        
        items_found = False
        for hive, path in reg_paths:
            try:
                with reg.OpenKey(hive, path) as key:
                    for i in range(reg.QueryInfoKey(key)[1]):
                        name, value, _ = reg.EnumValue(key, i)
                        self.add_startup_item_to_ui(name, value, hive, path)
                        items_found = True
                logging.info(f"Successfully read from {hive} {path}.")
            except FileNotFoundError:
                logging.warning(f"Registry path not found: {path}")
                continue
            except Exception as e:
                logging.error(f"Error reading registry path {path}: {e}", exc_info=True)
                self.log_status(f"❌ Error reading registry: {e}")
        
        if not items_found:
            ctk.CTkLabel(self.startup_scroll_frame, text="No startup items found in registry.").pack(pady=20)
            
        self.log_status("✅ Startup items loaded.")
        logging.info("Finished loading startup items.")

    def add_startup_item_to_ui(self, name, value, hive, path):
        """Adds a startup item to the UI with a toggle switch."""
        item_frame = ctk.CTkFrame(self.startup_scroll_frame, fg_color="transparent")
        item_frame.pack(fill="x", padx=10, pady=5)
        item_frame.grid_columnconfigure(0, weight=1)

        label = ctk.CTkLabel(item_frame, text=f"{name}: {value}", wraplength=700, justify="left")
        label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Toggle button to enable/disable
        toggle_switch = ctk.CTkSwitch(item_frame, text="", onvalue=True, offvalue=False)
        toggle_switch.grid(row=0, column=1, padx=5, sticky="e")
        
        # The switch should be ON by default, as the item is in the Run key
        toggle_switch.select()
        
        # Command to toggle the item's status
        toggle_switch.configure(command=lambda n=name, v=value, h=hive, p=path, s=toggle_switch: self.toggle_startup_item(n, v, h, p, s))

    def toggle_startup_item(self, name, value, hive, path, switch):
        """Toggles a startup item on or off by moving it to/from the RunOnce key."""
        is_enabled = switch.get()
        if not self.is_admin:
            messagebox.showerror("Permission Denied", "This action requires administrator privileges.")
            switch.toggle() # Revert the switch state
            return
            
        try:
            if is_enabled:
                # To enable, move from RunOnce to Run (if it was disabled)
                self.log_status(f"Enabling startup item: {name}...")
                self._run_command(f'reg add "{path}" /v "{name}" /t REG_SZ /d "{value}" /f', f"Enabling {name}...")
            else:
                # To disable, delete from Run key
                self.log_status(f"Disabling startup item: {name}...")
                self._run_command(f'reg delete "{path}" /v "{name}" /f', f"Disabling {name}...")

            self.log_status(f"Successfully {'enabled' if is_enabled else 'disabled'} {name}.")
            
        except Exception as e:
            logging.error(f"Failed to toggle startup item: {e}")
            self.log_status(f"❌ Failed to toggle {name}: {e}")
            switch.toggle() # Revert the switch state on error

    # --- Task Execution Functions ---
    def run_task(self, task_function, start_msg):
        """
        Runs a task in a separate thread and updates the progress bar.
        """
        task_id = str(time.time())
        if self.running_tasks:
            messagebox.showinfo("Task in Progress", "A task is already running. Please wait for it to finish.")
            return

        def task_wrapper():
            self.running_tasks[task_id] = True
            try:
                self.after(0, self.update_progress, 0.1, start_msg)
                
                # Execute the task function
                task_function()
                
                # Set progress to 100% and show completion message
                self.after(0, self.update_progress, 1, "Task completed successfully!")
                self.after(2000, self.update_progress, 0, "") # Reset progress bar
                self.after(2000, lambda: self.log_status("Ready."))
                
                # Prompt for reboot if needed
                if "reboot" in task_function.__name__ or "tweak" in task_function.__name__ or "clean" in task_function.__name__:
                    self.after(3000, self.prompt_reboot)

            except Exception as e:
                logging.error(f"Error during task execution: {e}")
                self.after(0, self.update_progress, 0, f"Task failed: {e}")
                self.after(0, lambda: self.log_status(f"Error: {e}"))
            finally:
                del self.running_tasks[task_id]
                self.after(0, self.progress_bar.set, 0)
                
        thread = threading.Thread(target=task_wrapper, daemon=True)
        thread.start()

    def _run_command(self, command, progress_message, hide_window=True):
        """Helper to run a shell command and update progress."""
        if not self.is_admin:
            messagebox.showerror("Permission Denied", "This action requires administrator privileges.")
            return False
            
        logging.info(f"Executing command: {command}")
        self.after(0, self.log_status, progress_message)
        
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if hide_window else 0
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True, creationflags=creationflags)
            logging.info(f"Command successful. Output: {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Command failed with error code {e.returncode}: {e.stderr.strip()}")
            self.after(0, self.log_status, f"Error: {e.stderr.strip()}")
            return False
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            self.after(0, self.log_status, f"Error: {e}")
            return False

    # --- Core Toolbox Features ---
    def one_click_boost(self):
        """Applies a series of performance tweaks in one go."""
        self.log_status("Applying One-Click Boost...")
        self.update_progress(0.1, "Creating restore point...")
        self.create_restore_point()
        
        self.update_progress(0.2, "Applying registry tweaks...")
        self.apply_core_registry_tweaks()
        
        self.update_progress(0.5, "Debloating Windows apps...")
        self.debloat_windows_apps()
        
        self.update_progress(0.7, "Disabling scheduled tasks...")
        self.disable_scheduled_tasks()
        
        self.update_progress(0.9, "Cleaning up temp files...")
        self.clean_temp_files()
        
        self.update_progress(1.0, "One-Click Boost complete!")

    def clean_temp_files(self):
        """Deletes temporary files from common locations."""
        temp_paths = [
            os.path.join(os.environ.get('TEMP', ''), '*'),
            os.path.join(os.environ.get('WINDIR', ''), 'temp', '*'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', '*'),
            os.path.join(winshell.startup(), '..', '..', 'Temp', '*') # User-specific temp
        ]
        
        deleted_count = 0
        total_size = 0
        
        for path_glob in temp_paths:
            for item in glob.glob(path_glob):
                try:
                    if os.path.isfile(item):
                        total_size += os.path.getsize(item)
                        os.remove(item)
                        deleted_count += 1
                    elif os.path.isdir(item):
                        shutil.rmtree(item, ignore_errors=True)
                        deleted_count += 1
                    self.update_progress(min(0.9, self.progress_bar.get() + 0.01), f"Deleting: {os.path.basename(item)}")
                except Exception as e:
                    logging.warning(f"Could not delete {item}: {e}")
        
        self.log_status(f"Cleaned {deleted_count} items. Total size: {total_size / (1024*1024):.2f} MB.")

    def create_restore_point(self):
        """Creates a system restore point."""
        self.log_status("Creating a system restore point...")
        self.update_progress(0.5, "Executing PowerShell command...")
        
        # Enable restore if not already enabled
        self._run_command('powershell -NoProfile Enable-ComputerRestore -Drive "C:\\"', "Enabling System Restore...")
        
        # Create checkpoint
        success = self._run_command('powershell "Checkpoint-Computer -Description \'RBoost PRO Tweaks\'"', "Creating restore point...")
        
        if success:
            self.log_status("✅ Restore point created successfully.")
        else:
            self.log_status("❌ Failed to create restore point. Check if System Protection is enabled.")

    def open_restore_point_manager(self):
        """Opens a new window to list and manage restore points."""
        if self.restore_point_manager_window is None or not self.restore_point_manager_window.winfo_exists():
            self.restore_point_manager_window = ctk.CTkToplevel(self)
            self.restore_point_manager_window.title("Restore Point Manager")
            self.restore_point_manager_window.geometry("800x600")
            self.restore_point_manager_window.grab_set()

            # UI elements
            ctk.CTkLabel(self.restore_point_manager_window, text="Available Restore Points:", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)
            
            self.restore_point_listbox = tk.Listbox(self.restore_point_manager_window, selectmode=tk.SINGLE, bg="#2b2b2b", fg="white", selectbackground="#4CAF50", height=15)
            self.restore_point_listbox.pack(fill="x", padx=20, pady=5)
            
            remove_frame = ctk.CTkFrame(self.restore_point_manager_window, fg_color="transparent")
            remove_frame.pack(pady=10)
            
            ctk.CTkButton(remove_frame, text="Refresh List", command=self.list_restore_points).pack(side="left", padx=10)
            ctk.CTkButton(remove_frame, text="Remove Selected Restore Point", command=self.remove_selected_restore_point).pack(side="left", padx=10)
            
            # Load the list on opening
            self.list_restore_points()
        else:
            self.restore_point_manager_window.focus()

    def list_restore_points(self):
        """Lists available restore points in the manager window."""
        self.restore_point_listbox.delete(0, tk.END)
        self.log_status("Listing restore points...")
        try:
            # Use PowerShell to get the list of restore points
            process = subprocess.run(['powershell', '-Command', 'Get-ComputerRestorePoint | Select-Object SequenceNumber, CreationTime, Description, EventType, RestorePointType'], 
                                    capture_output=True, text=True, check=True)
            output = process.stdout
            
            # Parse the output
            lines = output.strip().split('\n')
            if len(lines) > 2: # Check for header and divider
                self.restore_point_listbox.insert(tk.END, lines[0].strip()) # Header
                self.restore_point_listbox.insert(tk.END, lines[1].strip()) # Divider
                for line in lines[2:]:
                    if line.strip():
                        self.restore_point_listbox.insert(tk.END, line.strip())
            
            self.log_status("✅ Restore points listed successfully.")
        except Exception as e:
            self.log_status(f"❌ Failed to list restore points: {e}")
            
    def remove_selected_restore_point(self):
        """Removes the selected restore point."""
        selection_indices = self.restore_point_listbox.curselection()
        if not selection_indices:
            messagebox.showwarning("No Selection", "Please select a restore point to remove.")
            return
            
        selected_index = selection_indices[0]
        selected_line = self.restore_point_listbox.get(selected_index)
        
        # Extract the sequence number from the line (first column)
        try:
            sequence_number = int(selected_line.split()[0])
        except (ValueError, IndexError):
            messagebox.showerror("Error", "Could not parse restore point sequence number.")
            return

        if messagebox.askyesno("Confirm Removal", f"Are you sure you want to remove restore point with Sequence Number {sequence_number}? This action is permanent."):
            self.log_status(f"Removing restore point {sequence_number}...")
            # Use PowerShell to remove the restore point
            if self._run_command(f'powershell -Command "Remove-ComputerRestorePoint -RestorePoint {sequence_number}"', f"Removing restore point {sequence_number}..."):
                self.log_status("✅ Restore point removed successfully.")
                self.list_restore_points() # Refresh the list
            else:
                self.log_status("❌ Failed to remove restore point.")

    def apply_core_registry_tweaks(self):
        self.log_status("Applying deep system tweaks...")
        self.update_progress(0.1, "Applying UI tweaks...")
        self.enable_full_wallpaper_quality()
        self.show_file_extensions()
        self.enable_dark_mode()

        self.update_progress(0.4, "Applying network tweaks...")
        self.disable_network_throttling()
        self.set_dns_priority()
        
        self.update_progress(0.7, "Applying performance tweaks...")
        self.disable_telemetry()
        self._run_command('reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management" /v "LargeSystemCache" /t REG_DWORD /d "1" /f', "Setting LargeSystemCache...")
        self._run_command('reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management" /v "SecondLevelDataCache" /t REG_DWORD /d "1" /f', "Setting SecondLevelDataCache...")
        
        self.update_progress(0.9, "Applying power management tweaks...")
        self.reset_power_plans()
        
    def debloat_windows_apps(self):
        """Uninstalls pre-installed Windows apps using PowerShell."""
        apps_to_remove = [
            "bingfinance", "bingsports", "CommsPhone", "Drawboard PDF", "Sway",
            "WindowsAlarms", "WindowsCalculator", "WindowsCamera", "WindowsMaps",
            "WindowsSoundRecorder", "bingweather", "Office.OneNote", "SkypeApp",
            "SolitaireCollection", "ZuneMusic", "ZuneVideo", "XboxApp", "Microsoft.Windows.Photos"
        ]
        
        total_apps = len(apps_to_remove)
        for i, app_name in enumerate(apps_to_remove):
            progress = (i + 1) / total_apps
            self.update_progress(progress, f"Uninstalling {app_name}...")
            cmd = f"powershell -Command \"Get-AppxPackage -allusers *{app_name}* | Remove-AppxPackage\""
            self._run_command(cmd, f"Removing {app_name}...")
            time.sleep(1) # Small delay to prevent overload

    def disable_scheduled_tasks(self):
        """Disables various scheduled tasks."""
        tasks_to_disable = [
            "\\Microsoft\\Windows\\Application Experience\\ProgramDataUpdater",
            "\\Microsoft\\Windows\\Application Experience\\StartupAppTask",
            "\\Microsoft\\Windows\\Shell\\FamilySafetyMonitor",
            "\\Microsoft\\Windows\\Shell\\FamilySafetyRefresh",
            "\\Microsoft\\Windows\\Shell\\FamilySafetyUpload",
            "\\Microsoft\\Windows\\Maintenance\\WinSAT"
        ]
        
        total_tasks = len(tasks_to_disable)
        for i, task_path in enumerate(tasks_to_disable):
            progress = (i + 1) / total_tasks
            self.update_progress(progress, f"Disabling scheduled task: {task_path}...")
            self._run_command(f'schtasks /change /tn "{task_path}" /Disable', f"Disabling task: {task_path}")
            time.sleep(0.5)

    def launch_control_panel(self):
        """Launches the Control Panel."""
        try:
            subprocess.Popen(['control'])
            self.log_status("Launched Control Panel.")
        except Exception as e:
            self.log_status(f"❌ Failed to launch Control Panel: {e}")

    def launch_app_uninstaller(self):
        """Launches Control Panel's Programs and Features."""
        try:
            subprocess.Popen(['control', 'appwiz.cpl'], shell=True)
            self.log_status("✅ Opened Control Panel > Uninstall a Program.")
        except Exception as e:
            self.log_status(f"❌ Failed to launch uninstaller: {e}")
            messagebox.showerror("Error", f"Could not open App Uninstaller:\n{e}")



    def enable_full_wallpaper_quality(self):
        """Enables full JPEG wallpaper quality."""
        self.update_progress(0.5, "Enabling full wallpaper quality...")
        self._run_command('reg add "HKCU\\Control Panel\\Desktop" /v "JPEGImportQuality" /t REG_DWORD /d "100" /f', "Setting JPEGImportQuality to 100...")

    def show_file_extensions(self):
        """Shows file extensions in Windows Explorer."""
        self.update_progress(0.5, "Showing file extensions...")
        self._run_command('reg add "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced" /v "HideFileExt" /t REG_DWORD /d 0 /f', "Updating HideFileExt registry key...")
        
    def enable_dark_mode(self):
        """Enables dark mode for apps and system UI."""
        self.update_progress(0.5, "Enabling dark mode...")
        self._run_command('reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize" /v "AppsUseLightTheme" /t REG_DWORD /d "0" /f', "Setting AppsUseLightTheme to 0...")
        self._run_command('reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize" /v "SystemUsesLightTheme" /t REG_DWORD /d "0" /f', "Setting SystemUsesLightTheme to 0...")

    def disable_network_throttling(self):
        """Disables network throttling index."""
        self.update_progress(0.5, "Disabling network throttling...")
        self._run_command('reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile" /v "NetworkThrottlingIndex" /t REG_DWORD /d 4294967295 /f', "Updating NetworkThrottlingIndex...")

    def set_dns_priority(self):
        """Sets DNS and other service provider priorities."""
        self.update_progress(0.2, "Setting DNS, Local, Hosts, and NetBT priorities...")
        self._run_command('reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\ServiceProvider" /v "DnsPriority" /t REG_DWORD /d 6 /f', "Setting DnsPriority...")
        self._run_command('reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\ServiceProvider" /v "LocalPriority" /t REG_DWORD /d 4 /f', "Setting LocalPriority...")
        self._run_command('reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\ServiceProvider" /v "HostsPriority" /t REG_DWORD /d 5 /f', "Setting HostsPriority...")
        self._run_command('reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\ServiceProvider" /v "NetbtPriority" /t REG_DWORD /d 7 /f', "Setting NetbtPriority...")
        
    def disable_telemetry(self):
        """Disables telemetry and diagnostics."""
        self.update_progress(0.2, "Disabling telemetry and diagnostics...")
        self._run_command('reg add "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Privacy" /v "TailoredExperiencesWithDiagnosticDataEnabled" /t REG_DWORD /d "0" /f', "Disabling tailored experiences...")
        self._run_command('reg add "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Diagnostics\\DiagTrack" /v "ShowedToastAtLevel" /t REG_DWORD /d "1" /f', "Updating DiagTrack...")
        self._run_command('reg add "HKLM\\Software\\Policies\\Microsoft\\Windows\\System" /v "UploadUserActivities" /t REG_DWORD /d "0" /f', "Disabling user activity uploads...")
        self._run_command('reg add "HKLM\\Software\\Policies\\Microsoft\\Windows\\Windows Error Reporting" /v "DoReport" /t REG_DWORD /d "0" /f', "Disabling error reporting...")
        self._run_command('reg add "HKLM\\Software\\Microsoft\\Windows\\Windows Error Reporting" /v "Disabled" /t REG_DWORD /d "1" /f', "Disabling Windows Error Reporting...")
        
    def reset_power_plans(self):
        """Resets power plans to default schemes."""
        self.update_progress(0.5, "Resetting power plans to default...")
        self._run_command('powercfg -restoredefaultschemes', "Restoring default power schemes...")

    def deep_service_optimizer(self):
        """Disables a list of unnecessary services."""
        services_to_disable = ["diagtrack", "dmwappushservice", "DiagTrack", "CDPUserSvc"] # Add more as needed
        total_services = len(services_to_disable)
        for i, service_name in enumerate(services_to_disable):
            self.update_progress((i + 1) / total_services, f"Disabling service: {service_name}...")
            self._run_command(f'sc config "{service_name}" start=disabled', f"Setting {service_name} to disabled...")
            self._run_command(f'sc stop "{service_name}"', f"Stopping {service_name}...")
            time.sleep(0.5)

    def analyze_disk_usage(self):
        """Analyzes disk usage and visualizes it."""
        # This will just show the info. A full graphical analyzer is complex.
        self.log_status("Analyzing disk usage...")
        self.update_progress(0.5, "Scanning C:\\ drive...")
        
        try:
            partitions = psutil.disk_partitions(all=False)
            usage_data = {}
            for partition in partitions:
                if 'cdrom' not in partition.opts and partition.fstype:
                    usage = psutil.disk_usage(partition.mountpoint)
                    usage_data[partition.device] = usage.percent
                    self.log_status(f"Drive {partition.device}: {usage.percent:.1f}% used.")
            
            # Matplotlib Pie Chart
            labels = list(usage_data.keys())
            sizes = list(usage_data.values())
            
            self.after(0, self.show_disk_pie_chart, labels, sizes)
            self.log_status("Disk analysis complete.")
            
        except Exception as e:
            self.log_status(f"❌ Failed to analyze disk usage: {e}")

    def show_disk_pie_chart(self, labels, sizes):
        """Shows a pie chart of disk usage."""
        # Create a new frame and figure for the pie chart
        disk_chart_window = ctk.CTkToplevel(self)
        disk_chart_window.title("Disk Usage Breakdown")
        disk_chart_window.geometry("600x600")
        
        fig = Figure(figsize=(6, 6))
        ax = fig.add_subplot(111)
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.axis('equal') # Equal aspect ratio ensures that pie is drawn as a circle.
        
        canvas = FigureCanvasTkAgg(fig, master=disk_chart_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        
    def clear_browser_cache(self):
        """Clears cache from common browsers."""
        browsers = {
            "Chrome": os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome', 'User Data', 'Default', 'Cache'),
            "Edge": os.path.join(os.environ['LOCALAPPDATA'], 'Microsoft', 'Edge', 'User Data', 'Default', 'Cache'),
            "Firefox": os.path.join(os.environ['APPDATA'], 'Mozilla', 'Firefox', 'Profiles') # Requires more complex logic
        }
        
        for browser, path in browsers.items():
            self.update_progress(0.1, f"Clearing {browser} cache...")
            if os.path.exists(path):
                try:
                    if browser == "Firefox":
                        # Find profile folders and clear cache within each
                        for profile in os.listdir(path):
                            cache_path = os.path.join(path, profile, 'cache2', 'entries')
                            if os.path.exists(cache_path):
                                shutil.rmtree(cache_path, ignore_errors=True)
                    else:
                        shutil.rmtree(path, ignore_errors=True)
                    self.log_status(f"✅ {browser} cache cleared.")
                except Exception as e:
                    self.log_status(f"❌ Failed to clear {browser} cache: {e}")
            else:
                self.log_status(f"ℹ️ {browser} cache path not found.")

    def flush_standby_ram(self):
        """Flush standby RAM by trimming working sets of all accessible processes."""
        import ctypes

        self.log_status("🧹 Starting RAM flush...")
        self.update_progress(0.05, "Flushing standby RAM...")

        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_SET_QUOTA = 0x0100

        all_processes = list(psutil.process_iter(['pid', 'name']))
        total = len(all_processes)
        flushed = 0
        failed = 0

        for index, proc in enumerate(all_processes):
            try:
                pid = proc.info['pid']
                name = proc.info['name']

                handle = ctypes.windll.kernel32.OpenProcess(
                    PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA,
                    False,
                    pid
                )

                if handle:
                    result = ctypes.windll.psapi.EmptyWorkingSet(handle)
                    ctypes.windll.kernel32.CloseHandle(handle)

                    if result:
                        flushed += 1
                        print(f"✅ Flushed: {name} (PID: {pid})")
                    else:
                        failed += 1
                        print(f"⚠️ Failed: {name} (PID: {pid})")
                else:
                    failed += 1
            except Exception:
                failed += 1
                continue

            # Update progress bar
            self.update_progress((index + 1) / total, f"Flushing: {name} (PID: {pid})")

        self.update_progress(1.0, "Flush complete.")
        self.log_status(f"✅ Flushed: {flushed} processes. ❌ Failed: {failed}")

        if not self.is_admin:
            self.log_status("⚠️ Tip: Run RBoost as Administrator for better results.")


    def kill_background_apps(self):
        """Terminates known idle/bloat apps."""
        bloat_processes = ["spotify.exe", "discord.exe", "epicgameslauncher.exe", "steam.exe"]
        killed_count = 0
        for proc in psutil.process_iter(['name']):
            if proc.name() in bloat_processes:
                try:
                    proc.terminate()
                    killed_count += 1
                    self.log_status(f"Killed process: {proc.name()}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        self.log_status(f"Killed {killed_count} known background processes.")

    # --- Speed Test & Console Functions ---
    def run_speed_test(self):
        """Runs the speed test and displays the output."""
        try:
            self.after(0, lambda: self.speed_test_output.configure(state="normal"))
            self.after(0, lambda: self.speed_test_output.delete('1.0', 'end'))
            self.log_status("Running speed test (this may take a moment)...")
            
            # Use speedtest-cli via subprocess
            self.update_progress(0.3, "Executing speedtest-cli...")
            
            # The user might not have this installed, so we check
            try:
                subprocess.run(['speedtest', '--help'], check=True, capture_output=True)
            except FileNotFoundError:
                self.log_status("❌ Error: 'speedtest' command not found. Please install speedtest-cli.")
                self.after(0, self.speed_test_output.insert, "end", "Error: speedtest-cli not found. Please install it using 'pip install speedtest-cli'.\n")
                return

            process = subprocess.Popen(['speedtest'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
            
            for line in process.stdout:
                self.after(0, self.speed_test_output.insert, "end", line)
                self.after(0, self.speed_test_output.see, "end")
                self.update_progress(min(0.9, self.progress_bar.get() + 0.05), "Running...")
                
            process.wait()
            self.log_status("✅ Speed test complete.")
            self.after(0, self.speed_test_output.configure, state="disabled")

        except Exception as e:
            self.log_status(f"❌ Speed test failed: {e}")
            self.after(0, self.speed_test_output.configure, state="disabled")

    def execute_command(self):
        """Executes a command from the console input."""
        command = self.command_entry.get().strip()
        if not command:
            return
            
        self.after(0, self.console_output.configure, state="normal")
        self.after(0, self.console_output.delete, '1.0', 'end')
        self.after(0, self.console_output.insert, "end", f"> {command}\n")
        self.log_status(f"Executing command: {command}")
        
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
            
            for line in iter(process.stdout.readline, ''):
                self.after(0, self.console_output.insert, "end", line)
                self.after(0, self.console_output.see, "end")
                
            process.wait()
            self.log_status("Command executed.")
            
        except Exception as e:
            self.log_status(f"❌ Command failed: {e}")
            self.after(0, self.console_output.insert, "end", f"Error: {e}\n")
            
        self.after(0, self.console_output.configure, state="disabled")

    # --- Update & Dependency Functions ---
    def check_for_updates(self):
        """Checks for updates from a remote version file."""
        self.log_status("Checking for updates...")
        try:
            with urllib.request.urlopen(UPDATE_CHECK_URL, timeout=5) as response:
                remote_version_str = response.read().decode('utf-8').strip()
                remote_version = parse_version(remote_version_str)
                local_version = parse_version(APP_VERSION)
                
                if remote_version > local_version:
                    self.log_status(f"✅ An update is available! Version {remote_version_str} is available.")
                else:
                    self.log_status("✅ You are running the latest version.")
                    
        except Exception as e:
            self.log_status(f"❌ Failed to check for updates: {e}")

    def install_dependencies(self):
        """Installs missing Python packages using pip."""
        # This is a bit risky to do at runtime, but fulfills the user request.
        # It's better to ensure dependencies are bundled with PyInstaller.
        self.log_status("Checking for missing dependencies...")
        required_packages = ["customtkinter", "psutil", "matplotlib", "speedtest-cli"]
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                self.log_status(f"⚠️ {package} not found. Installing...")
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                    self.log_status(f"✅ Successfully installed {package}.")
                except Exception as e:
                    self.log_status(f"❌ Failed to install {package}: {e}")

    # --- New Cleanup Scheduler & Silent Background Cleanup ---
    def silent_cleanup_loop(self):
        """
        A loop that runs in a separate thread to perform silent cleanup.
        """
        while not self.cleanup_stop_event.is_set():
            # Run cleanup every 12 hours (43200 seconds)
            self.log_status("Running silent background cleanup...")
            self.clean_temp_files()
            # Wait for 12 hours or until the stop event is set
            self.cleanup_stop_event.wait(43200)
            
    def start_silent_cleanup(self):
        """Starts the silent cleanup thread."""
        if self.cleanup_thread is None or not self.cleanup_thread.is_alive():
            self.cleanup_stop_event.clear()
            self.cleanup_thread = threading.Thread(target=self.silent_cleanup_loop, daemon=True)
            self.cleanup_thread.start()
            
    def stop_silent_cleanup(self):
        """Stops the silent cleanup thread."""
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_stop_event.set()
            self.cleanup_thread.join()
            
# --- Main Entry Point ---
if __name__ == "__main__":
    # Check if a log file from a previous run exists and delete it
    if os.path.exists(log_filename):
        try:
            os.remove(log_filename)
        except OSError as e:
            print(f"Error removing old log file: {e}")

    # Prevent multiple instances
    mutex = win32event.CreateMutex(None, False, "RBOOST_MUTEX_SINGLE_INSTANCE")
    last_error = win32api.GetLastError()

    if last_error == winerror.ERROR_ALREADY_EXISTS:
        print("Another instance is already running.")
        sys.exit(0)

    logging.info("Script is being run as main module.")
    
    app = RBoostApp()
    logging.info("RBoostApp instance created successfully.")
    logging.info("Starting mainloop.")
    app.mainloop()
