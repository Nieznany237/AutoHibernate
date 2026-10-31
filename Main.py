'''Automatic Hibernation Application
This application automatically puts the system into hibernation after a specified countdown.'''

import sys
import logging
import time
import ctypes
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import base64
import os
import json
from hPyT import maximize_minimize_button # https://pypi.org/project/hPyT/
from modules.b64assets import APP_ICON

VERSION = "1.12.0"
RELEASE_DATE = "25.10.2026"

DEV_MODE = False  # No more accidental hibernations durring development lol
LOGGING_LEVEL = "INFO" # INFO, DEBUG, WARNING, ERROR, CRITICAL

# Logger configuration
logging.basicConfig(
    level=getattr(logging, LOGGING_LEVEL),
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    handlers=[
        #logging.FileHandler("AutoHibernate.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

if DEV_MODE:
    logging.warning("Development mode is enabled and Hibernation call is disabled. Please disable it before pushing into production!\n\n")

# Application settings
DEFAULT_HIBERNATION_TIME = 10  # Countdown time to hibernation (in seconds)
DEFAULT_TARGET_FPS = 25  # Target: 20 FPS
KEYBINDS_ENABLED = True  # Set to False to disable keybinds
DEFAULT_FONT = ("Arial", 13)  # Font used in the application
FOOTER_FONT = ("Arial", 8, "italic")  # Footer font
BUTTON_FONT = ("Helvetica", 10) # Button font
BUTTON_STYLE = "raised" # Button style
FRAME_STYLE = "groove" # Frame style

def parse_arguments(args, default_time):
    """Return the configured countdown time, honoring a command-line override."""
    if len(args) >= 3 and args[1] in ("/t", "-t", "--time"):
        try:
            custom_time = int(args[2])
            if custom_time > 0:
                logging.info("Using hibernation time from arguments: %d", custom_time)
                return custom_time
            elif custom_time == 0:
                logging.warning("Custom time [arg] is 0. Setting hibernation time to minimum of 0.1 second.")
                return 0.1
            else:
                logging.warning("Custom time [arg] is less than 0. Using default settings")
        except ValueError:
            logging.error("Invalid argument for time: %s", args[2])
    return default_time

# Load config: overrides defaults if present, creates config file if missing or invalid
def load_config_from_file():
    '''Load HIBERNATION_TIME, TARGET_FPS, and SHOW_DECIMAL_SECONDS from config.json, create file/folder if missing or invalid. Returns the loaded or default values.'''
    
    # C:\Users\{USERNAME}\AppData\Roaming\Nieznany237\AutoHibernate
    config_dir = os.path.join(
        os.getenv("APPDATA"),
        "Nieznany237",
        "AutoHibernate"
    )
    config_file = os.path.join(config_dir, "config.json")
    logging.debug("Config directory: %s", config_file)
    defaults = {
        'HIBERNATION_TIME': DEFAULT_HIBERNATION_TIME,
        'TARGET_FPS': DEFAULT_TARGET_FPS,
        'SHOW_DECIMAL_SECONDS': False,
    }
    hib_time = defaults['HIBERNATION_TIME']
    target_fps = defaults['TARGET_FPS']
    show_decimal_seconds = defaults['SHOW_DECIMAL_SECONDS']

    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
        logging.info("Created config directory: %s", config_dir)
    if not os.path.exists(config_file):
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(defaults, f, indent=4)
        logging.info("Created config file with defaults: %s", config_file)
    else:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            hib_time = data.get('HIBERNATION_TIME', hib_time)
            target_fps = data.get('TARGET_FPS', target_fps)
            show_decimal_seconds = data.get('SHOW_DECIMAL_SECONDS', show_decimal_seconds)
        except Exception as e:
            logging.warning("Failed to load config.json, using defaults. Error: %s", e)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(defaults, f, indent=4)
            logging.info("Recreated config file with defaults: %s", config_file)
            hib_time = defaults['HIBERNATION_TIME']
            target_fps = defaults['TARGET_FPS']
            show_decimal_seconds = defaults['SHOW_DECIMAL_SECONDS']

    # Validate hib_time
    if hib_time is None or not isinstance(hib_time, int) or hib_time <= 0:
        logging.warning("HIBERNATION_TIME is set to %s, which is invalid. Using default value of %d seconds.", hib_time, defaults['HIBERNATION_TIME'])
        hib_time = defaults['HIBERNATION_TIME']

    # Validate target_fps
    if target_fps is None or not isinstance(target_fps, int) or target_fps <= 0:
        logging.warning("TARGET_FPS is set to %s, which is invalid. Using default value of %d.", target_fps, defaults['TARGET_FPS'])
        target_fps = defaults['TARGET_FPS']

    # Validate show_decimal_seconds
    if not isinstance(show_decimal_seconds, bool):
        logging.warning("SHOW_DECIMAL_SECONDS is set to %s, which is invalid. Using default value of %s.", show_decimal_seconds, defaults['SHOW_DECIMAL_SECONDS'])
        show_decimal_seconds = defaults['SHOW_DECIMAL_SECONDS']

    logging.info("Loaded HIBERNATION_TIME from config: %s", hib_time)
    logging.info("Loaded TARGET_FPS from config: %s", target_fps)
    logging.info("Loaded SHOW_DECIMAL_SECONDS from config: %s", show_decimal_seconds)
    return hib_time, target_fps, show_decimal_seconds

class AutoHibernateApp:
    """Own the application window, configuration, and countdown lifecycle."""

    def __init__(self, root):
        self.root = root
        self.dev_mode = DEV_MODE
        self.hibernation_time = DEFAULT_HIBERNATION_TIME
        self.target_fps = DEFAULT_TARGET_FPS
        self.show_decimal_seconds = False
        self.countdown_terminated = False
        self.hibernate_support_cache = None
        self.time_label = None
        self.progress_bar = None
        self.countdown_after_id = None

        self.root.title(
            "Automatic Hibernation [DEV MODE]"
            if self.dev_mode else "Automatic Hibernation"
        )
        self.root.geometry("310x180+208+208")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        if current_os() != "Windows":
            logging.error(
                "Detected operating system: %s. This application is designed for Windows only.",
                current_os()
            )
            messagebox.showerror(
                "Error",
                "This application can only be run on Windows systems.",
                parent=self.root
            )
            self.root.destroy()
            return

        maximize_minimize_button.hide(self.root)
        self.hibernation_time, self.target_fps, self.show_decimal_seconds = load_config_from_file()
        self.hibernation_time = parse_arguments(sys.argv, self.hibernation_time)
        self._build_widgets()

        if not self.check_hibernate_support():
            logging.error("Hibernation is not available on this system.")
            messagebox.showerror(
                "Error",
                "Hibernation is not available on this system.\n"
                "The program will close. Please check if your\n"
                "system supports hibernation.",
                parent=self.root
            )
            self.root.destroy()
            return

        self.countdown()

    def _build_widgets(self):
        self.root.after(100, self.root.focus_force)
        if KEYBINDS_ENABLED:
            self.root.bind("<Escape>", self.on_escape)
            self.root.bind("<Return>", self.on_return)

        app_icon = load_base64_image(APP_ICON)
        if app_icon:
            self.root.iconphoto(True, app_icon)

        main_app_frame = tk.LabelFrame(
            self.root,
            width=300,
            height=150,
            relief=FRAME_STYLE
        )
        main_app_frame.pack_propagate(False)
        main_app_frame.pack(padx=10, pady=10)

        self.time_label = tk.Label(
            main_app_frame,
            text=f"System will hibernate in\n{self.hibernation_time} seconds",
            font=DEFAULT_FONT
        )
        self.time_label.pack(pady=5)

        self.progress_bar = ttk.Progressbar(
            main_app_frame,
            maximum=100,
            length=240,
            mode="determinate"
        )
        self.progress_bar.pack(pady=10)

        button_frame = tk.Frame(main_app_frame)
        button_frame.pack(pady=0, side=tk.BOTTOM)

        close_button = tk.Button(
            button_frame, text="Close Application", font=BUTTON_FONT,
            width=20,
            height=2,
            relief=BUTTON_STYLE,
            border=2,
            command=self.on_closing
        )
        close_button.pack(side=tk.LEFT, padx=(3, 3), pady=(0, 3))

        hibernate_button = tk.Button(
            button_frame, text="Hibernate Now", font=BUTTON_FONT,
            width=25,
            height=2,
            relief=BUTTON_STYLE,
            border=2,
            command=self.hibernate_system_call
        )
        hibernate_button.pack(side=tk.LEFT, padx=(0, 3), pady=(0, 3))

        version_label = tk.Label(
            self.root,
            text=f"Release {VERSION} ({RELEASE_DATE}) | by @Nieznany237",
            font=FOOTER_FONT,
            fg="#7E7E7E",
            anchor="se",
            justify="right"
        )
        version_label.place(relx=1.0, rely=1.0, anchor="se", x=-8, y=0)

    def check_hibernate_support(self):
        """Check and cache whether Windows allows hibernation."""
        if self.hibernate_support_cache is not None:
            return self.hibernate_support_cache

        try:
            hibernate_check = ctypes.WinDLL("powrprof.dll").IsPwrHibernateAllowed
            hibernate_check.argtypes = []
            hibernate_check.restype = ctypes.c_ubyte
            self.hibernate_support_cache = bool(hibernate_check())
        except (AttributeError, OSError) as error:
            logging.exception("Error checking hibernation support - %s", error)
            self.hibernate_support_cache = False

        logging.info("Hibernation supported: %s", self.hibernate_support_cache)
        return self.hibernate_support_cache

    def hibernate_system_call(self):
        """Request system hibernation and close the application."""
        self.time_label.config(text="Hibernating...\n")
        logging.info("Calling system hibernation")
        if self.dev_mode:
            self.countdown_terminated = True
            logging.info("| Hibernation call is disabled (DEV_MODE=True). Skipping system call. |")
            self.root.destroy()
            return

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(
                ["shutdown", "/h"],
                check=True,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except subprocess.CalledProcessError as error:
            error_message = f"System error: exit code {error.returncode}"
            logging.error(error_message)
            messagebox.showerror("Error", error_message, parent=self.root)
        except Exception as error:
            error_message = f"An error occurred while attempting to hibernate: {error}"
            logging.exception(error_message)
            messagebox.showerror("Error", error_message, parent=self.root)
        finally:
            self.root.destroy()

    def on_closing(self):
        """Stop pending countdown work and close the window."""
        logging.info("Window closing event triggered.")
        self.countdown_terminated = True
        if self.countdown_after_id is not None:
            self.root.after_cancel(self.countdown_after_id)
            self.countdown_after_id = None
        self.root.destroy()

    def on_return(self, _event):
        del _event
        self.hibernate_system_call()

    def on_escape(self, _event):
        del _event
        self.on_closing()

    def countdown(self):
        """Update the countdown from a monotonic deadline."""
        total_time = self.hibernation_time
        update_interval_ms = max(1, round(1000 / self.target_fps))
        deadline = time.monotonic() + total_time
        last_displayed_time = -1

        def update_time():
            nonlocal last_displayed_time
            self.countdown_after_id = None
            if self.countdown_terminated:
                self.time_label.config(text="Countdown terminated.")
                self.progress_bar["value"] = 0
                return

            remaining_time = max(deadline - time.monotonic(), 0)
            time_elapsed = total_time - remaining_time
            remaining_seconds = int(remaining_time)

            if self.show_decimal_seconds:
                self.time_label.config(
                    text=f"System will hibernate in\n{remaining_time:.1f} seconds"
                )
            elif remaining_seconds != last_displayed_time:
                self.time_label.config(
                    text=f"System will hibernate in\n{remaining_seconds} seconds"
                )
                last_displayed_time = remaining_seconds

            self.progress_bar["value"] = min((time_elapsed / total_time) * 100, 100)
            if remaining_time > 0:
                self.countdown_after_id = self.root.after(
                    update_interval_ms,
                    update_time
                )
            else:
                self.progress_bar["value"] = 100
                self.hibernate_system_call()

        update_time()

def current_os():
    '''Function to get the current operating system name'''
    os_name = os.name
    if os_name == 'nt':
        return "Windows"
    if os_name == 'posix':
        return "Linux"
    return "Unknown OS"

# Function to load a Base64 image as application icon
def load_base64_image(base64_data: str):
    '''Function to load a Base64 image and return it as a PhotoImage object'''
    try:
        image_bytes = base64.b64decode(base64_data.split(',')[1])
        return tk.PhotoImage(data=image_bytes)
    except Exception as e:
        logging.exception("Error loading image %s", e)
        return None

def main():
    """Create the application and start the Tk event loop."""
    root = tk.Tk()
    AutoHibernateApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()