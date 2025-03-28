import re
import time
import threading
import queue
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from collections import deque
import os
from tkinter import Tk, Button

# Folder containing log files
LOG_FOLDER = "C:\\ProgramData\\ASA\\Autoslew\\ClServoLogs"

# Regular expression to match log entries
LOG_PATTERN = re.compile(r"(\d{2}:\d{2}:\d{2}\.\d{3}): Axis (\d) .* Curr:([+-]?\d+\.\d+)A")

# Data storage
timestamps = deque(maxlen=3600)
current_de = deque(maxlen=3600)
current_ra = deque(maxlen=3600)

# Thread-safe queue for communication between threads
log_queue = queue.Queue()

# Flag to control the program
running = True

def get_latest_log_file():
    """Find the latest .txt file in the log folder."""
    txt_files = [f for f in os.listdir(LOG_FOLDER) if f.endswith(".txt")]
    if not txt_files:
        raise FileNotFoundError("No .txt files found in the log folder.")
    latest_file = max(txt_files, key=lambda f: os.path.getmtime(os.path.join(LOG_FOLDER, f)))
    return os.path.join(LOG_FOLDER, latest_file)

def update_plot():
    plt.clf()
    plt.title("Axis Current Over Time")
    plt.xlabel("Time")
    plt.ylabel("Current (A)")
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.gca().xaxis.set_major_locator(mdates.MinuteLocator(interval=10))
    plt.xticks(rotation=45)
    
    if timestamps:
        plt.plot(timestamps, current_de, label="Axis 1 (DE)", color='b')
        plt.plot(timestamps, current_ra, label="Axis 2 (RA)", color='r')
    
    plt.legend()
    plt.pause(0.1)

def process_log_line(line):
    match = LOG_PATTERN.search(line)
    if match:
        time_str, axis, curr = match.groups()
        log_time = datetime.strptime(time_str, "%H:%M:%S.%f")
        current = float(curr)

        # Append timestamp only once per unique time entry
        if not timestamps or timestamps[-1] != log_time:
            timestamps.append(log_time)
            current_de.append(current_de[-1] if current_de else None)  # Keep last known value
            current_ra.append(current_ra[-1] if current_ra else None)

        # Update current values
        if axis == '1':
            current_de[-1] = current
        elif axis == '2':
            current_ra[-1] = current

def tail_log_file(log_file):
    with open(log_file, 'r') as f:
        f.seek(0, 2)  # Move to the end of file
        while running:
            line = f.readline()
            if line:
                log_queue.put(line.strip())  # Pass log line to the main thread
            else:
                time.sleep(0.5)  # Avoid busy-waiting

# Run the log monitoring in a separate thread
def start_log_monitoring():
    log_file = get_latest_log_file()
    log_thread = threading.Thread(target=tail_log_file, args=(log_file,), daemon=True)
    log_thread.start()

def stop_program():
    """Stop the program gracefully."""
    global running
    running = False
    plt.close()

# Setup Matplotlib interactive mode
plt.ion()

# Create a simple GUI with a "Close" button
root = Tk()
root.title("ASA Current Monitor")
close_button = Button(root, text="Close", command=stop_program)
close_button.pack()

# Start log monitoring
start_log_monitoring()

# Main loop to process log lines and update the plot
def main_loop():
    while running:
        try:
            # Process all log lines in the queue
            while not log_queue.empty():
                line = log_queue.get()
                process_log_line(line)
            
            # Update the plot
            update_plot()
            time.sleep(0.1)
        except KeyboardInterrupt:
            stop_program()
            break
    root.quit()

# Run the main loop in the Tkinter mainloop
threading.Thread(target=main_loop, daemon=True).start()
root.mainloop()