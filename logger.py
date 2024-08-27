from datetime import datetime
import os

LOGLEVEL = int(os.getenv("LOGLEVEL", "0"))

def log(message, level):
    """Log messages with a timestamp and log level based on the current log level."""
    if LOGLEVEL >= level:
        if LOGLEVEL == 0:
            return  # No logging at all for level 0
        if level == 1 and LOGLEVEL < 1:
            return  # No error logging if log level is below 1
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{timestamp} [{level}] {message}")
