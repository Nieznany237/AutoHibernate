'''
Version 1.7 - 13.03.2025
- Improved the function “countdown” for the progress bar where it now uses time.perf_counter() instead of a fixed step time, making the progress bar smoother and more accurate.
- Hidden the 'maximize/minimize' buttons from the titlebar using maximize_minimize_button.hide(root)
'''

import tkinter as tk
from tkinter import ttk, messagebox
import os
import base64
import time
from hPyT import maximize_minimize_button

# Application settings
HIBERNATION_TIME = 10  # Countdown time to hibernation (in seconds)
DEFAULT_FONT = ("Arial", 13)  # Font used in the application
FOOTER_FONT = ("Arial", 8, "italic")  # Footer font
BUTTON_FONT = ("Helvetica", 10)
BUTTON_STYLE = "raised"
FRAME_STYLE = "groove"
version = "1.7"
release_date = "13.03.2025"

# Function to check hibernation support
def check_hibernate_support():
    """
    Checks if Windows supports the hibernation feature.
    Returns True if hibernation is available, otherwise False.
    """
    try:
        # Run the 'powercfg /a' command and get the result
        result = os.popen("powercfg /a").read()
        # Debug: display command result
        print("Result of 'powercfg /a':")
        print(result)

        # Check if the phrase "Hibernate" appears in the list of available states
        if "Hibernate" in result.split("The following sleep states are available on this system:")[1]:
            return True
        
        # If the phrase is not found, hibernation is unavailable
        return False
    except Exception as e:
        print(f"An error occurred while checking hibernation: {e}")
        return False

# Function to trigger system hibernation
def hibernate_system_call():
    """
    Executes the Windows hibernation command with error handling.
    """
    try:
        if not check_hibernate_support():
            messagebox.showerror("Error", "Hibernation is not available on this system.")
            return

        exit_code = os.system("shutdown /h")
        if exit_code != 0:
            raise Exception(f"System error: exit code {exit_code}")

        print("Hibernation command executed.")
        root.destroy()
    except Exception as e:
        error_message = f"An error occurred while attempting to hibernate: {e}"
        print(error_message)
        messagebox.showerror("Error", error_message)

# Countdown function with progress bar update
def countdown(label, progress):
    """
    Performs a countdown to hibernation, updating the progress bar and label.
    :param label: Label object displaying time
    :param progress: Progress bar object
    """
    total_time = HIBERNATION_TIME  # Total countdown time
    step_time = 0.01  # Time between updates in seconds
    last_displayed_time = [-1]  # Helper variable to store the last displayed time
    start_time = time.perf_counter()

    def update_time():
        elapsed_time = time.perf_counter() - start_time
        remaining_time = max(total_time - elapsed_time, 0)
        remaining_seconds = int(remaining_time)
        
        if remaining_seconds != last_displayed_time[0]:
            label.config(text=f"System will hibernate in\n{remaining_seconds} seconds")
            last_displayed_time[0] = remaining_seconds
        
        progress["value"] = (elapsed_time / total_time) * 100  # Synchronize progress with real time
        
        if remaining_time > 0:
            root.after(int(step_time * 1000), update_time)
        else:
            progress["value"] = 100 
            hibernate_system_call()
            root.destroy()

    progress["value"] = 0
    update_time()

# Start measuring time
#start_time = time.time()

# Funkcja do ładowania obrazu w formacie Base64 jako ikonę aplikacji
def load_base64_image(base64_string):
    """
    Decodes a Base64 string into an image usable in Tkinter.
    :param base64_string: Base64 image string
    :return: PhotoImage object or None in case of error
    """
    try:
        image_bytes = base64.b64decode(base64_string.split(',')[1])
        return tk.PhotoImage(data=image_bytes)
    except Exception as e:
        print(f"Error loading image: {e}")
        return None

# Base64 encoded image (currently empty, replace with actual code)
base64_image_1 = '''
data:image/png;base64,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
'''

# Create main application window
root = tk.Tk()
root.title("Automatic Hibernation")  # Window title
root.geometry("310x180+208+208")  # Window size + position
root.resizable(False, False)  # Disable window resizing
root.attributes("-topmost", True)  # Keep window on top
maximize_minimize_button.hide(root)

# Set application icon if Base64 image is valid
app_icon = load_base64_image(base64_image_1)
if app_icon:
    root.iconphoto(True, app_icon)

frame = tk.LabelFrame(root, width=300, height=150)
frame.pack_propagate(False)
frame.pack(padx=10, pady=10)

# Countdown label
time_label = tk.Label(frame, text=f"System will hibernate in\n{HIBERNATION_TIME} seconds", font=DEFAULT_FONT)
time_label.pack(pady=5)

# Progress bar
progress_bar = ttk.Progressbar(frame, maximum=100, length=240, mode='determinate')
progress_bar.pack(pady=11)

# Button frame
button_frame = tk.Frame(frame)
button_frame.pack(pady=0)

# Close button
close_button = tk.Button(
    button_frame, text="Close Application", font=BUTTON_FONT, 
    width=20,
    height=2, 
    relief=BUTTON_STYLE,
    border=2,
    command=root.destroy
)
close_button.pack(side=tk.LEFT, padx=3)

# Hibernate button
hibernate_button = tk.Button(
    button_frame, text="Hibernate Now", font=BUTTON_FONT, 
    width=25,
    height=2,
    relief=BUTTON_STYLE,
    border=2,
    command=hibernate_system_call
)
hibernate_button.pack(side=tk.LEFT, padx=3)

# Footer with version info
version_label = tk.Label(
    root, text=f"By @Nieznany237 | Version {version} released {release_date}",
    font=FOOTER_FONT, fg="#7E7E7E", anchor="se", justify="right"
)
version_label.place(relx=1.0, rely=1.0, anchor="se", x=-7, y=0)

# Check hibernation before starting
if not check_hibernate_support():
    messagebox.showerror("Error", "Hibernation is not available on this system. The program will close. Please check if your system supports hibernation.")
    root.destroy()
else:
    countdown(time_label, progress_bar)

# Run the main application loop

#root.update()  # For debug
#print(f"Default coordinates: x={root.winfo_x()}, y={root.winfo_y()}")

root.mainloop()

# DEBUG
#end_time = time.time()
#elapsed_time = end_time - start_time
#print(f"Application runtime: {elapsed_time:.2f} seconds")
