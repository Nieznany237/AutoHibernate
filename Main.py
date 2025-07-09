'''Automatic Hibernation Application
This application automatically puts the system into hibernation after a specified countdown.'''
# pylint: disable = W0718
# pylint: disable = C0103
import logging
import time
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import base64
import logging
import os
import json
from hPyT import maximize_minimize_button # https://pypi.org/project/hPyT/
from modules.b64assets import APP_ICON

VERSION = "1.10.0"
RELEASE_DATE = "04.07.2025"

# Global cache
DEBUG_MODE = False
DISABLE_HIBERNATION_CALL = False  # No more accidental hibernations durring development lol

FPS_Count_Sum = 0
Keybinds_enabled = True  # Set to False to disable keybinds
App_Start_time_DEBUG = time.time()  # Start measuring time
countdown_terminated = False

# Logger configuration
logging.basicConfig(
    level=logging.INFO, # INFO, DEBUG, WARNING, ERROR, CRITICAL
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    handlers=[
        #logging.FileHandler("AutoHibernate.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

if logging.getLogger().isEnabledFor(logging.DEBUG):
    logging.debug("Debug mode is enabled. Debug messages will be logged.")
    DEBUG_MODE = True

# Application settings
HIBERNATION_TIME = 10  # Countdown time to hibernation (in seconds)
TARGET_FPS = 20  # Target: 20 FPS (for smoothness)
DEFAULT_FONT = ("Arial", 13)  # Font used in the application
FOOTER_FONT = ("Arial", 8, "italic")  # Footer font
BUTTON_FONT = ("Helvetica", 10)
BUTTON_STYLE = "raised"
FRAME_STYLE = "groove"

# Load config: overrides defaults if present, creates config file if missing or invalid
def load_config_from_file():
    '''Load HIBERNATION_TIME, TARGET_FPS, and SHOW_DECIMAL_SECONDS from config.json, create file/folder if missing or invalid. Returns the loaded or default values.'''
    config_dir = os.path.join(os.path.expanduser("~"), "NiezPrograms", "AutoHibernate")
    config_file = os.path.join(config_dir, "config.json")
    logging.debug("Config directory: %s", config_file)
    defaults = {
        'HIBERNATION_TIME': HIBERNATION_TIME,
        'TARGET_FPS': TARGET_FPS,
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

# Global variable for caching hibernation support result
_hibernate_support_cache = None

# Function to check hibernation support
def check_hibernate_support():
    '''Function to check if hibernation is supported on the system'''
    global _hibernate_support_cache #pylint: disable=W0603
    # Check if result is already cached to avoid redundant checks
    if _hibernate_support_cache is not None:
        return _hibernate_support_cache

    try:
        # Run the 'powercfg /a' command to get available sleep states
        result = subprocess.run(
            ["powercfg", "/a"],
            capture_output=True,
            text=True,
            check=True
        ).stdout
        # Split output to find the relevant section
        split_text = result.split(
            "The following sleep states are available on this system:"
        )
        # Check if "Hibernate" is listed as available
        hibernate_supported = (
            "Hibernate" in split_text[1]
        )
        logging.info(
            "Hibernation supported: %s",
            hibernate_supported
        )
        # Cache the result for future calls
        _hibernate_support_cache = hibernate_supported
        return hibernate_supported
    except subprocess.CalledProcessError as e:
        # Log and cache failure if the command fails
        logging.exception("Error checking hibernation - %s", e)
        _hibernate_support_cache = False
        return False
    except IndexError as e:
        # Log and cache failure if output format is unexpected
        logging.exception("Unexpected output format from powercfg - %s", e)
        _hibernate_support_cache = False
        return False

# Function to call system hibernation
def hibernate_system_call():
    '''Function to call system hibernation and handle errors'''
    time_label.config(text="Hibernating...\n")
    logging.info("Calling system hibernation")
    if DISABLE_HIBERNATION_CALL:
        terminate_countdown()
        logging.info("| Hibernation call is disabled (DISABLE_HIBERNATION_CALL=True). Skipping system call. |")
        messagebox.showinfo("Info", "Hibernation is disabled (test mode). The system will not hibernate.")
        root.destroy()
        return
    try:
        # This function attempts to call system hibernation using subprocess with hidden window (cmd).
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        subprocess.run(
            ["shutdown", "/h"],
            check=True,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except subprocess.CalledProcessError as e:
        error_message = f"System error: exit code {e.returncode}"
        logging.error(error_message)
        messagebox.showerror("Error", error_message)
    except Exception as e:
        error_message = f"An error occurred while attempting to hibernate: {e}"
        logging.exception(error_message)
        messagebox.showerror("Error", error_message)
    finally:
        root.destroy()

def terminate_countdown():
    '''Set the flag to terminate the countdown.'''
    global countdown_terminated
    countdown_terminated = True

def on_closing():
    '''Function to handle window closing event'''
    logging.info("Window closing event triggered.")
    terminate_countdown()  # Set the flag to terminate the countdown
    root.destroy()  # Close the application window

# Countdown function to hibernation with progress bar update
def countdown(label: tk.Label, progress: ttk.Progressbar):
    '''Function to handle countdown to hibernation with progress bar update, with ability to terminate.'''
    total_time = HIBERNATION_TIME
    step_time = 1.0 / TARGET_FPS
    last_displayed_time = -1
    start_time = time.perf_counter()

    def update_time():
        global FPS_Count_Sum  # pylint: disable=W0603
        nonlocal last_displayed_time
        if countdown_terminated:
            label.config(text="Countdown terminated.")
            progress["value"] = 0
            return

        current_time = time.perf_counter()
        time_elapsed = current_time - start_time
        remaining_time = max(total_time - time_elapsed, 0)
        remaining_seconds = int(remaining_time)

        # Update text only when seconds change (or always if decimals enabled)
        if SHOW_DECIMAL_SECONDS:
            label.config(text=f"System will hibernate in\n{remaining_time:.1f} seconds")
        else:
            if remaining_seconds != last_displayed_time:
                label.config(text=f"System will hibernate in\n{int(remaining_seconds)} seconds")
                last_displayed_time = remaining_seconds

        # Progressbar updated every frame (for smoothness)
        progress["value"] = (time_elapsed / total_time) * 100

        if remaining_time > 0:
            # Calculate exact time to next frame (delay correction)
            next_frame_time = start_time + (FPS_Count_Sum + 1) * step_time
            delay = max(int((next_frame_time - current_time) * 1000), 0)

            root.after(delay, update_time)
            FPS_Count_Sum += 1
        else:
            progress["value"] = 100
            hibernate_system_call()

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

# Create main application window
root = tk.Tk()
root.title("Automatic Hibernation")
root.geometry("310x180+208+208")
root.resizable(False, False)
root.attributes("-topmost", True)
if current_os() == "Windows":
    maximize_minimize_button.hide(root)
    HIBERNATION_TIME, TARGET_FPS, SHOW_DECIMAL_SECONDS = load_config_from_file()
root.protocol("WM_DELETE_WINDOW", on_closing)

root.after(100, root.focus_force)  # Force focus after a short delay
# Key bindings
def on_return(event): # pylint: disable=unused-argument
    '''Function to handle Return key press'''
    hibernate_system_call()

def on_escape(event): # pylint: disable=unused-argument
    '''Function to handle Escape key press'''
    root.destroy()

if Keybinds_enabled is True:
    root.bind("<Escape>", on_escape)
    root.bind("<Return>", on_return)

# Set application icon if Base64 image is valid
app_icon = load_base64_image(APP_ICON)
if app_icon:
    root.iconphoto(True, app_icon)

Main_app_frame = tk.LabelFrame(
    root,
    width=300,
    height=150,
    relief=FRAME_STYLE
)

Main_app_frame.pack_propagate(False)
Main_app_frame.pack(padx=10, pady=10)

# Countdown label
time_label = tk.Label(
    Main_app_frame,
    text=f"System will hibernate in\n{HIBERNATION_TIME} seconds",
    font=DEFAULT_FONT
)
time_label.pack(pady=5)

# Progress bar
progress_bar = ttk.Progressbar(Main_app_frame, maximum=100, length=240, mode='determinate')
progress_bar.pack(pady=10)

# Button frame
button_frame = tk.Frame(Main_app_frame)
button_frame.pack(pady=0, side=tk.BOTTOM)

# Close button
close_button = tk.Button(
    button_frame, text="Close Application", font=BUTTON_FONT,
    width=20,
    height=2,
    relief=BUTTON_STYLE,
    border=2,
    command=on_closing
)

close_button.pack(side=tk.LEFT, padx=(3,3), pady=(0, 3))

# Hibernate button
hibernate_button = tk.Button(
    button_frame, text="Hibernate Now", font=BUTTON_FONT,
    width=25,
    height=2,
    relief=BUTTON_STYLE,
    border=2,
    command=hibernate_system_call
)
hibernate_button.pack(side=tk.LEFT, padx=(0, 3), pady=(0, 3))

# Footer with version info
version_label = tk.Label(
    root, text=f"By @Nieznany237 | Version {VERSION} Released {RELEASE_DATE}",
    font=FOOTER_FONT, fg="#7E7E7E", anchor="se", justify="right"
)
version_label.place(relx=1.0, rely=1.0, anchor="se", x=-8, y=0)

if current_os() != "Windows":
    logging.error(
        "Detected operating system: %s. This application is designed for Windows only.",
        current_os()
    )
    messagebox.showerror(
        "Error",
        "This application can only be run on Windows systems."
    )
    root.destroy()
else:
    # Check hibernation before starting (only on Windows)
    if not check_hibernate_support():
        logging.error("Hibernation is not available on this system.")
        messagebox.showerror("Error",
            "Hibernation is not available on this system.\n"
            "The program will close. Please check if your\n"
            "system supports hibernation.")
        root.destroy()
    else:
        countdown(time_label, progress_bar)

root.mainloop()

# DEBUG
if DEBUG_MODE is True:
    App_End_time_DEBUG = time.time()
    try:
        debug_elapsed_time = App_End_time_DEBUG - App_Start_time_DEBUG # pylint: disable=E0606
    except NameError:
        debug_elapsed_time = 0.0
    actual_fps = FPS_Count_Sum / HIBERNATION_TIME
    logging.debug("Application runtime: %.4f seconds", debug_elapsed_time)
    logging.debug("Average FPS: %.1f", actual_fps)
    logging.debug("Total FPS count: %d", FPS_Count_Sum)
