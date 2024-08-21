import requests
import json
import yaml
import csv
import xmltodict
import paho.mqtt.client as mqtt
import argparse
from io import StringIO
import os
import sys
import time

def publish_to_mqtt(client, topic, value, prefix=""):
    full_topic = f"{prefix}.{topic}" if prefix else topic
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
        print("The JSON object is not structured as expected.")

def process_xml(client, xml_data, prefix=""):
    try:
        json_data = xmltodict.parse(xml_data)
        process_json(client, json_data, prefix=prefix)
    except Exception as e:
        print(f"Error processing XML data: {e}")

def process_yaml(client, yaml_data, prefix=""):
    try:
        json_data = yaml.safe_load(yaml_data)
        process_json(client, json_data, prefix=prefix)
    except yaml.YAMLError as e:
        print(f"Error processing YAML data: {e}")

def process_csv(client, csv_data, prefix=""):
    try:
        csv_reader = csv.DictReader(StringIO(csv_data))
        for row in csv_reader:
            for key, value in row.items():
                publish_to_mqtt(client, key, value, prefix)
    except Exception as e:
        print(f"Error processing CSV data: {e}")

def detect_and_process_data(client, data, content_type, prefix=""):
    if content_type == 'application/json' or content_type == 'text/json':
        try:
            json_data = json.loads(data)
            process_json(client, json_data, prefix=prefix)
        except json.JSONDecodeError as e:
            print(f"Error processing JSON data: {e}")
    elif content_type == 'application/xml' or content_type == 'text/xml':
        process_xml(client, data, prefix=prefix)
    elif content_type == 'application/x-yaml' or content_type == 'text/yaml':
        process_yaml(client, data, prefix=prefix)
    elif content_type == 'text/csv' or content_type == 'application/csv':
        process_csv(client, data, prefix=prefix)
    else:
        try:
            json_data = json.loads(data)
            process_json(client, json_data, prefix=prefix)
        except json.JSONDecodeError:
            try:
                yaml_data = yaml.safe_load(data)
                process_yaml(client, yaml_data, prefix=prefix)
            except yaml.YAMLError:
                try:
                    process_xml(client, data, prefix=prefix)
                except Exception:
                    try:
                        process_csv(client, data, prefix=prefix)
                    except Exception:
                        print("Unable to determine or process data format.")

def fetch_and_publish_data(client, url, auth, verify, prefix):
    try:
        response = requests.get(url, auth=auth, verify=verify)
        response.raise_for_status()  # Raise an exception for HTTP errors
        content_type = response.headers.get('Content-Type', '').lower()
        data = response.text
        detect_and_process_data(client, data, content_type, prefix)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from the URL: {e}")

def load_config_file(config_file):
    try:
        with open(config_file, 'r') as file:
            config_data = yaml.safe_load(file)
            return config_data.get('configurations', [])
    except FileNotFoundError:
        print(f"Error: Configuration file {config_file} not found.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error: Failed to parse YAML configuration file: {e}")
        sys.exit(1)

def get_config_by_name(configurations, name):
    for config in configurations:
        if config.get('name') == name:
            return config
    print(f"Error: Configuration with name '{name}' not found in the configuration file.")
    sys.exit(1)

def merge_configs(base_config, override_config):
    return {**base_config, **{k: v for k, v in override_config.items() if v is not None}}

def process_config(client, config, interval):
    # Certificate verification configuration
    verify = config.get('verify', 'true')
    if verify.lower() == "false":
        verify = False
    elif os.path.isfile(verify):
        verify = verify
    elif verify.lower() != "true":
        print(f"Error: The path provided for --verify does not exist or is not a file: {verify}")
        sys.exit(1)

    # Set up URL authentication if credentials are provided
    auth = None
    if config.get('username') and config.get('password'):
        auth = (config['username'], config['password'])

    # Connect to the MQTT server
    client.username_pw_set(config.get('mqttuser', ''), config.get('mqttpassword', ''))
    try:
        client.connect(config['mqtt_ip'], config['mqtt_port'], 60)
    except Exception as e:
        print(f"Error connecting to the MQTT server: {e}")
        sys.exit(1)

    # Fetch and publish data
    fetch_and_publish_data(client, config['url'], auth, verify, config.get('prefix', ''))

    # Wait for the interval if specified
    if interval:
        time.sleep(interval)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Fetch data from a URL and publish it via MQTT.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--configfile", type=str, help="Path to YAML configuration file.")
    parser.add_argument("--config", type=str, help="Name of the configuration set to use, or 'all' to process all configurations. Can also be a comma-separated list of configuration names.")
    parser.add_argument("url", type=str, nargs='?', help="The URL from which to fetch data (supports HTTP/HTTPS).")
    parser.add_argument("mqtt_ip", type=str, nargs='?', help="The IP address of the MQTT server.")
    parser.add_argument("mqtt_port", type=int, nargs='?', help="The port of the MQTT server.")
    parser.add_argument("--prefix", type=str, help="Optional prefix for all MQTT topics.")
    parser.add_argument("--username", type=str, help="Username for URL authentication (optional).")
    parser.add_argument("--password", type=str, help="Password for URL authentication (optional).")
    parser.add_argument("--mqttuser", type=str, help="Username for MQTT authentication (optional).")
    parser.add_argument("--mqttpassword", type=str, help="Password for MQTT authentication (optional).")
    parser.add_argument("--verify", type=str, help="SSL certificate verification for HTTPS requests ('false' to disable, or path to a custom CA bundle).")
    parser.add_argument("--interval", type=int, help="Interval in seconds to repeatedly fetch data from the URL (optional).")

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

    # Main processing loop
    while True:
        for config in config_sets:
            final_config = merge_configs(config, vars(args))
            
            # Validate username and password for URL authentication
            if (final_config.get('username') and not final_config.get('password')) or (final_config.get('password') and not final_config.get('username')):
                print("Error: Both --username and --password must be provided for URL authentication.")
                sys.exit(1)

            # Validate MQTT username and password
            if (final_config.get('mqttuser') and not final_config.get('mqttpassword')) or (final_config.get('mqttpassword') and not final_config.get('mqttuser')):
                print("Error: Both --mqttuser and --mqttpassword must be provided for MQTT authentication.")
                sys.exit(1)

            # Validate interval (if provided)
            if final_config.get('interval') is not None and final_config.get('interval') <= 0:
                print("Error: The --interval value must be a positive integer.")
                sys.exit(1)

            # Process the current configuration
            process_config(client=mqtt.Client(), config=final_config, interval=final_config.get('interval'))

        # If no interval is provided, break the loop after processing all configurations
        if not final_config.get('interval'):
            break

if __name__ == "__main__":
    main()
