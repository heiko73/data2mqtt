from datetime import datetime
import os

LOGLEVEL = int(os.getenv("LOGLEVEL", "0"))

def log(message, level):
    """Log messages with a timestamp and log level based on the current log level."""
    if LOGLEVEL < level:
        return
    else:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{timestamp} [{level}] {message}")
