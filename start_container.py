import os
import subprocess
import sys
import time
import hashlib
import random
from logger import log

# Funktion, um eine Fehlermeldung auszugeben und das Skript zu beenden
def log_error(message):
    log(f"ERROR: {message}", 1)
    sys.exit(1)

# Funktion, um die Konfigurationsdatei auszugeben
def print_config_file(cfgfile):
    if os.path.isfile(cfgfile):
        log(f"\n--- Content of {cfgfile} ---", 1)
        with open(cfgfile, 'r') as file:
            log(file.read(), 1)
        log(f"--- End of {cfgfile} ---\n", 1)
    else:
        log(f"WARNING: {cfgfile} does not exist.", 1)

# Funktion, um die Checksumme einer Datei zu berechnen
def calculate_checksum(cfgfile):
    if not os.path.isfile(cfgfile):
        return None
    
    hasher = hashlib.md5()
    with open(cfgfile, 'rb') as file:
        buf = file.read()
        hasher.update(buf)
    return hasher.hexdigest()

# Funktion, um den data2mqtt-Prozess zu starten
def start_data2mqtt(cfgfile):
    try:
        process = subprocess.Popen(["python", "data2mqtt.py", "--configfile", cfgfile])
        log("data2mqtt.py started successfully", 1)
        return process
    except Exception as e:
        log_error(f"Failed to start data2mqtt.py: {e}")

# Funktion, um den data2mqtt-Prozess zu beenden
def stop_data2mqtt(process):
    if process and process.poll() is None:  # Prozess läuft noch
        process.terminate()  # Sendet SIGTERM
        process.wait()  # Warten, bis der Prozess beendet ist
        log("data2mqtt.py stopped successfully", 1)

# Überprüfe, ob die Umgebungsvariablen gesetzt sind, ansonsten setze Standardwerte
loglevel = os.getenv("LOGLEVEL", "1")
webport = os.getenv("WEBPORT", "8833")
cfgfile = os.getenv("CFGFILE", "/opt/config.yaml")

# Setze die Umgebungsvariablen, falls sie nicht gesetzt sind
os.environ["LOGLEVEL"] = loglevel
os.environ["WEBPORT"] = webport
os.environ["CFGFILE"] = cfgfile

# Debugging-Ausgabe für Umgebungsvariablen
log(f"Starting with LOGLEVEL={loglevel}, WEBPORT={webport}, CFGFILE={cfgfile}", 1)

# Gebe die Konfigurationsdatei beim Start aus
print_config_file(cfgfile)

# Initiale Checksumme berechnen
previous_checksum = calculate_checksum(cfgfile)

# Starte data2mqtt.py im Hintergrund
data2mqtt_process = start_data2mqtt(cfgfile)

# Starte configeditor.py im Hintergrund
try:
    subprocess.Popen(["python", "configeditor.py", "--port", webport])
    log("configeditor.py started successfully", 1)
except Exception as e:
    log_error(f"Failed to start configeditor.py: {e}")

try:
    # Überprüfe alle 5 Sekunden, ob sich die Konfigurationsdatei geändert hat
    while True:
        time.sleep(5)
        
        # Füge eine zufällige Wartezeit von 100-900 ms hinzu
        random_wait_time = random.uniform(0.1, 0.9)
        time.sleep(random_wait_time)
        
        current_checksum = calculate_checksum(cfgfile)
        if current_checksum != previous_checksum:
            log(f"{cfgfile} has been modified.", 1)
            print_config_file(cfgfile)
            
            # Beende den aktuellen data2mqtt-Prozess
            stop_data2mqtt(data2mqtt_process)
            
            # Starte data2mqtt.py neu
            data2mqtt_process = start_data2mqtt(cfgfile)
            
            # Aktualisiere die Checksumme
            previous_checksum = current_checksum

except KeyboardInterrupt:
    log("Shutting down container.", 1)
    stop_data2mqtt(data2mqtt_process)
