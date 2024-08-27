# Verwende das offizielle Python-Image als Basis
FROM python:3.9-slim

# Setze das Arbeitsverzeichnis
WORKDIR /app

# Kopiere die Python-Dateien in den Container
COPY . /app

# Installiere die erforderlichen Python-Abhängigkeiten
RUN pip install --upgrade pip 
RUN pip install --no-cache-dir -r requirements.txt

# Standardmäßig soll die Konfigurationsdatei in /opt liegen
VOLUME ["/opt"]

# Setze den Befehl, der beim Start des Containers ausgeführt wird
CMD ["python", "start_container.py"]

ENV PYTHONUNBUFFERED=1
