import os
import sys
import argparse
import yaml
from flask import Flask, render_template, request, redirect, url_for, flash
from logger import log  # Importiere die gemeinsame Log-Funktion
from validator import validate_mqtt_host, validate_mqtt_port, validate_interval

cli = sys.modules['flask.cli']
cli.show_server_banner = lambda *x: None

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Not for production use!

CFGFILE = os.getenv('CFGFILE', 'config.yaml')

# Lade die Konfigurationsdatei
def load_config():
    if not os.path.exists(CFGFILE):
        return []

    with open(CFGFILE, 'r') as file:
        try:
            config_data = yaml.safe_load(file)
            return config_data.get('configurations', [])
        except yaml.YAMLError as e:
            flash(f"Error loading YAML file: {e}", "danger")
            return []

# Speichere die Konfigurationsdatei
def save_config(configurations):
    # Überprüfe, ob jede Konfiguration den 'name'-Schlüssel hat
    for config in configurations:
        if 'name' not in config or not config['name']:
            flash(f"Error: Configuration is missing the 'name' field: {config}", "danger")
            return  # Abbrechen, falls ein Name fehlt

    # Speichere die Konfigurationen in die YAML-Datei
    try:
        with open(CFGFILE, 'w') as file:
            yaml.dump({'configurations': configurations}, file)
            flash("Configurations saved successfully!", "success")
    except Exception as e:
        flash(f"Error saving configurations: {e}", "danger")

# Startseite - Liste aller Konfigurationssätze
@app.route('/')
def index():
    log(f"Accessed index page.", 10)
    configurations = load_config()
    return render_template('index.html', configurations=configurations)

# Neuer Konfigurationssatz
@app.route('/new', methods=['GET', 'POST'])
def new_config():
    if request.method == 'POST':
        configurations = load_config()

        # Erstelle einen neuen Konfigurationssatz basierend auf den Formulardaten
        new_config = {
            'name': request.form['name'].strip(),  # Achte darauf, dass der Name nicht leer ist
            'url': request.form['url'],
            'mqtt_server': request.form['mqtt_server'],
            'mqtt_port': int(request.form['mqtt_port']),
            'mqtt_version': request.form['mqtt_version'],
            'prefix': request.form.get('prefix', ''),
            'username': request.form.get('username', ''),
            'password': request.form.get('password', ''),
            'mqttuser': request.form.get('mqttuser', ''),
            'mqttpassword': request.form.get('mqttpassword', ''),
            'verify': request.form.get('verify', 'true'),
            'interval': int(request.form['interval']) if request.form.get('interval') else None
        }

        # Überprüfe, ob der Name gesetzt ist
        if not new_config['name']:
            flash("Error: 'name' field cannot be empty.", "danger")
            return render_template('config_form.html', \
                                   config=new_config, action="New Configuration")

        # Validierung
        if not validate_mqtt_host(mqtt_host):
            flash("Invalid MQTT Host. Please enter a valid IP address or hostname.", "danger")
            return redirect(url_for('new_config'))

        if not validate_mqtt_port(mqtt_port):
            flash("Invalid MQTT Port. Please enter a port number between 1 and 65535.", "danger")
            return redirect(url_for('new_config'))

        if not validate_interval(interval):
            flash("Invalid interval. Please enter a non-negative integer.", "danger")
            return redirect(url_for('new_config'))

        configurations.append(new_config)
        save_config(configurations)

        log(f"Added new configuration: {new_config['name']}", 5)
        log(f"Configuration parameters: {new_config}", 11)

        return redirect(url_for('index'))

    return render_template('config_form.html', config=None, action="New Configuration")

# Konfigurationssatz editieren
@app.route('/edit/<string:name>', methods=['GET', 'POST'])
def edit_config(name):
    configurations = load_config()
    config = next((c for c in configurations if c['name'] == name), None)

    if not config:
        flash(f"Configuration '{name}' not found!", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Update the configuration set with the form data
        config['name'] = request.form['name'].strip()  # Achte darauf, dass der Name nicht leer ist
        config['url'] = request.form['url']
        config['mqtt_server'] = request.form['mqtt_server']
        config['mqtt_version'] = request.form['mqtt_version']
        config['mqtt_port'] = int(request.form['mqtt_port'])
        config['prefix'] = request.form.get('prefix', '')
        config['username'] = request.form.get('username', '')
        config['password'] = request.form.get('password', '')
        config['mqttuser'] = request.form.get('mqttuser', '')
        config['mqttpassword'] = request.form.get('mqttpassword', '')
        config['verify'] = request.form.get('verify', 'true')
        config['interval'] = int(request.form['interval']) if request.form.get('interval') else None

        # Überprüfe, ob der Name gesetzt ist
        if not config['name']:
            flash("Error: 'name' field cannot be empty.", "danger")
            return render_template('config_form.html', config=config, action="Edit Configuration")

        save_config(configurations)

        log(f"Edited configuration: {config['name']}", 5)
        log(f"Updated configuration parameters: {config}", 11)

        return redirect(url_for('index'))

    return render_template('config_form.html', config=config, action="Edit Configuration")

# Konfigurationssatz löschen
@app.route('/delete/<string:name>', methods=['POST'])
def delete_config(name):
    configurations = load_config()
    configurations = [c for c in configurations if c['name'] != name]

    save_config(configurations)

    log(f"Deleted configuration: {name}", 5)

    return redirect(url_for('index'))

if __name__ == '__main__':
    # Argumentparser für den --port Parameter
    parser = argparse.ArgumentParser(description="Start the configuration editor web server.")
    parser.add_argument('--port', type=int, \
                        help="Port to run the web server on. Overrides WEBPORT environment \
                        variable if set.")
    args = parser.parse_args()

    # Lese den Port entweder aus dem --port Argument oder der WEBPORT-Umgebungsvariablen
    port = args.port if args.port else int(os.getenv('WEBPORT', '5000'))

    # Lese die Konfigurationsdatei aus der Umgebungsvariablen
    CFGFILE = os.getenv('CFGFILE', 'config.yaml')

    # Log initiale Parameter bei Loglevel >= 2
    log(f"Starting configeditor.py with port={port}, CFGFILE={CFGFILE}", 2)

    # Starte den Webserver
    app.run(host='0.0.0.0', port=port)
