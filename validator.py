
import re
import socket
import sys

def validate_mqtt_host(host):
    # Prüfen ob es sich um eine gültige IPv4-Adresse handelt
    try:
        socket.inet_pton(socket.AF_INET, host)
        return True
    except socket.error:
        pass
    
    # Prüfen ob es sich um eine gültige IPv6-Adresse handelt
    try:
        socket.inet_pton(socket.AF_INET6, host)
        return True
    except socket.error:
        pass
    
    # Prüfen ob es sich um einen gültigen Hostnamen handelt
    if re.match(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$", host):
        return True
    
    return False

def validate_mqtt_port(port):
    # Prüfen ob der Port eine Zahl ist und im gültigen Bereich liegt
    if isinstance(port, int) and 1 <= port <= 65535:
        return True
    return False

def validate_interval(interval):
    # Prüfen ob der Interval ein Integer ist und zwischen 0 und dem maximalen Integer-Wert von Python liegt
    if isinstance(interval, int) and 0 <= interval <= sys.maxsize:
        return True
    return False
