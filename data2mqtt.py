import requests
import json
import yaml
import csv
import xmltodict
import paho.mqtt.client as mqtt
import argparse
import time
from io import StringIO
import os
import sys
from urllib.parse import urlparse
from datetime import datetime
from logger import log  

LOGLEVEL = int(os.getenv("LOGLEVEL", "0"))

def publish_to_mqtt(client, topic, value, prefix=""):
    full_topic = f"{prefix}.{topic}" if prefix else topic
    if LOGLEVEL >= 4:
        log(f"Publishing to MQTT: Topic: {full_topic}, Value: {value}", 4)
    client.publish(full_topic, value)

def process_json(client, json_obj, parent_key="", prefix=""):
    if isinstance(json_obj, dict):
        for key, value in json_obj.items():
            full_key = f"{parent_key}.{key}" if parent_key else key
            if isinstance(value, dict):
                process_json(client, value, full_key, prefix)
            else:
                publish_to_mqtt(client, full_key, str(value), prefix)
    else:
        log("The JSON object is not structured as expected.", 1)

def process_xml(client, xml_data, prefix=""):
    try:
        json_data = xmltodict.parse(xml_data)
        process_json(client, json_data, prefix=prefix)
    except Exception as e:
        log(f"Error processing XML data: {e}", 1)

def process_yaml(client, yaml_data, prefix=""):
    try:
        json_data = yaml.safe_load(yaml_data)
        process_json(client, json_data, prefix=prefix)
    except yaml.YAMLError as e:
        log(f"Error processing YAML data: {e}", 1)

def process_csv(client, csv_data, prefix=""):
    try:
        csv_reader = csv.DictReader(StringIO(csv_data))
        for row in csv_reader:
            for key, value in row.items():
                publish_to_mqtt(client, key, value, prefix)
    except Exception as e:
        log(f"Error processing CSV data: {e}", 1)

def detect_and_process_data(client, data, content_type, prefix=""):
    if content_type == 'application/json' or content_type == 'text/json':
        try:
            json_data = json.loads(data)
            process_json(client, json_data, prefix=prefix)
        except json.JSONDecodeError as e:
            log(f"Error processing JSON data: {e}", 1)
    elif content_type == 'application/xml' or content_type == 'text/xml':
        process_xml(client, data, prefix=prefix)
    elif content_type == 'application/x-yaml' or content_type == 'text/yaml':
        process_yaml(client, data, prefix=prefix)
    elif content_type == 'text/csv' or content_type == 'application/csv':
        process_csv(client, data, prefix=prefix)
    else:
        log("Unable to determine or process data format.", 1)

def fetch_and_publish_data(client, url, auth, verify, prefix):
    parsed_url = urlparse(url)

    if parsed_url.scheme == 'file':
        # Handle local file
        file_path = parsed_url.path
        if not os.path.exists(file_path):
            log(f"Error: Local file {file_path} not found.", 1)
            return

        try:
            with open(file_path, 'r') as file:
                data = file.read()
                content_type = guess_content_type(file_path)
                detect_and_process_data(client, data, content_type, prefix)
        except Exception as e:
            log(f"Error reading local file {file_path}: {e}", 1)
    else:
        # Handle HTTP/HTTPS
        try:
            response = requests.get(url, auth=auth, verify=verify)
            response.raise_for_status()  # Raise an exception for HTTP errors
            content_type = response.headers.get('Content-Type', '').lower()
            data = response.text
            detect_and_process_data(client, data, content_type, prefix)
        except requests.exceptions.RequestException as e:
            log(f"Error fetching data from the URL: {e}", 1)

def guess_content_type(file_path):
    """Guess the content type based on file extension."""
    _, ext = os.path.splitext(file_path)
    if ext in ['.json']:
        return 'application/json'
    elif ext in ['.xml']:
        return 'application/xml'
    elif ext in ['.yaml', '.yml']:
        return 'application/x-yaml'
    elif ext in ['.csv']:
        return 'text/csv'
    else:
        return 'text/plain'

def load_config_file(config_file):
    try:
        with open(config_file, 'r') as file:
            config_data = yaml.safe_load(file)
            return config_data.get('configurations', [])
    except FileNotFoundError:
        log(f"Error: Configuration file {config_file} not found.", 1)
        sys.exit(1)
    except yaml.YAMLError as e:
        log(f"Error: Failed to parse YAML configuration file: {e}", 1)
        sys.exit(1)

def get_config_by_name(configurations, name):
    for config in configurations:
        if config.get('name') == name:
            return config
    log(f"Error: Configuration with name '{name}' not found in the configuration file.", 1)
    sys.exit(1)

def merge_configs(base_config, override_config):
    return {**base_config, **{k: v for k, v in override_config.items() if v is not None}}

def parse_mqtt_host_and_port(mqtt_host):
    """Parses the MQTT host and port if specified as part of the host string."""
    if ':' in mqtt_host:
        host, port = mqtt_host.rsplit(':', 1)
        try:
            return host, int(port)
        except ValueError:
            log(f"Error: Invalid port number '{port}' in MQTT host.", 1)
            sys.exit(1)
    else:
        return mqtt_host, 1883  # Default MQTT port

def process_config(client, config, config_name):
    # Log the configuration name at Loglevel 2 or higher
    log(f"Processing config: {config_name}", 2)

    # Log the URL at Loglevel 3 or higher
    log(f"Fetching data from URL: {config['url']}", 3)

    # Log all defined parameters at Loglevel 10
    if LOGLEVEL >= 10:
        log(f"Defined parameters: {config}", 10)

    # Log all parameters including defaults at Loglevel 11
    if LOGLEVEL >= 11:
        log(f"All parameters (including defaults): {config}", 11)

    # Certificate verification configuration
    verify = config.get('verify', 'true')
    if verify.lower() == "false":
        verify = False
    elif os.path.isfile(verify):
        verify = verify
    elif verify.lower() != "true":
        log(f"Error: The path provided for --verify does not exist or is not a file: {verify}", 1)
        return

    # Set up URL authentication if credentials are provided
    auth = None
    if config.get('username') and config.get('password'):
        auth = (config['username'], config['password'])

    # Parse MQTT host and port
    mqtt_host, mqtt_port = parse_mqtt_host_and_port(config.get('mqtt_ip', '127.0.0.1'))

    # Connect to the MQTT server
    try:
        client.connect(mqtt_host, mqtt_port, 60)
    except Exception as e:
        log(f"Error connecting to the MQTT server: {e}", 1)
        return

    # Fetch and publish data
    try:
        fetch_and_publish_data(client, config['url'], auth, verify, config.get('prefix', ''))
    except Exception as e:
        log(f"Error during data fetch and publish: {e}", 1)


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Fetch data from a URL or a local file and publish it via MQTT.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--configfile", type=str, help="Path to YAML configuration file.")
    parser.add_argument("--config", type=str, help="Name of the configuration set to use, or 'all' to process all configurations. Can also be a comma-separated list of configuration names.")
    parser.add_argument("url", type=str, nargs='?', help="The URL or file path from which to fetch data (supports HTTP/HTTPS and file://).")
    parser.add_argument("mqtt_ip", type=str, nargs='?', help="The IP address or hostname of the MQTT server, optionally with port (e.g., '192.168.1.100:1884').", default="127.0.0.1")
    parser.add_argument("mqtt_port", type=int, nargs='?', help="The port of the MQTT server (if not specified as part of the MQTT host).")
    parser.add_argument("--prefix", type=str, help="Optional prefix for all MQTT topics.")
    parser.add_argument("--username", type=str, help="Username for URL authentication (optional).")
    parser.add_argument("--password", type=str, help="Password for URL authentication (optional).")
    parser.add_argument("--mqttuser", type=str, help="Username for MQTT authentication (optional).")
    parser.add_argument("--mqttpassword", type=str, help="Password for MQTT authentication (optional).")
    parser.add_argument("--verify", type=str, help="SSL certificate verification for HTTPS requests ('false' to disable, or path to a custom CA bundle).")
    parser.add_argument("--interval", type=int, help="Interval in seconds to repeatedly fetch data from the URL or file (optional).")

    args = parser.parse_args()

    # Load configurations from a file if provided
    config_sets = []
    if args.configfile:
        configurations = load_config_file(args.configfile)

        # Default to --config="all" if --config is not specified
        if not args.config:
            args.config = "all"

        if args.config.lower() == "all":
            config_sets = configurations
        else:
            config_names = [name.strip() for name in args.config.split(",")]
            config_sets = [get_config_by_name(configurations, name) for name in config_names]
    else:
        # If no configfile is provided, create a single configuration from command-line arguments
        config_sets = [vars(args)]
        config_name = "commandline"

    # Dictionary to store the next execution time for each config
    next_run_times = {}

    # Initialize next_run_times with the current time for all configs
    current_time = time.time()
    for config in config_sets:
        # Überprüfe, ob der 'name'-Schlüssel in der Konfiguration vorhanden ist
        if 'name' not in config:
            log(f"Error: Missing 'name' key in one of the configuration sets: {config}", 1)
            continue  # Überspringe diese Konfiguration

        interval = config.get('interval')
        if interval:
            next_run_times[config['name']] = current_time + interval
        else:
            next_run_times[config['name']] = current_time  # Execute immediately if no interval

    while True:
        current_time = time.time()
        for config in config_sets:
            config_name = config.get('name', "commandline")
            next_run_time = next_run_times.get(config_name)

            if next_run_time and current_time >= next_run_time:
                # Execute the config
                final_config = merge_configs(config, vars(args))
                mqtt_version = config.get('mqtt_version', 'v3.1.1')  # Default to v3.1.1
                log(f"Using MQTT version '{mqtt_version}'", 5)
                if mqtt_version == "v5":
                    client = mqtt.Client(protocol=mqtt.MQTTv5)
                else:
                    client = mqtt.Client(protocol=mqtt.MQTTv311)
                client.username_pw_set(final_config.get('mqttuser', ''), final_config.get('mqttpassword', ''))
                process_config(client, final_config, config_name)

                # Update the next run time
                interval = final_config.get('interval')
                if interval:
                    next_run_times[config_name] = current_time + interval

        # Sleep for a short period to avoid busy waiting
        time.sleep(1)



if __name__ == "__main__":
    main()

