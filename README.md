# data2mqtt
A Python script that can read data in various formats from an URL and publishes the data to an MQTT broker

## Features

The script allows to specify an URL (optional: username / password) from where it fetches data. Once the data has been successfully received, data2mqtt tries to detect the format of it. In addition to JSON, the program also supports XML, CSV and YAML. As soon as the format has been identified, the data is parsed and each found data point is published to a specified MQTT broker, which can be defined by IP address/hostname and port. Optionally, credentials for the broker can be provided if it is required. 

The URL processing is handled by the requests library, with one exception: if it starts with file:// , data2mqtt reads the specified file directly. 

## Installation / Dependencies

The following Python libraries are required and might need to be installed (e.g. using pip):

    requests:        handling HTTP and HTTPS URLs
    json:            for JSON parsing
    yaml:            for YAML parsing
    csv:             for CSV parsing
    xmltodict:       for XML parsing
    paho:            for implementing a MQTT client
    argparse:        to parse commandline arguments
    io:              for CSV handling 

Once all libraries are available, the script can be directly started using python. A usage message (see below) is available with --help and the script can either be called directly, using a crontab entry or, optionally, offers to pull data from the specified URL(s) in a defined interval until it is interrupted.

## Usage

    usage: data2mqtt.py [-h] [--configfile CONFIGFILE] [--config CONFIG] [--prefix PREFIX] [--username USERNAME]
                        [--password PASSWORD] [--mqttuser MQTTUSER] [--mqttpassword MQTTPASSWORD] [--verify VERIFY]
                        [--interval INTERVAL]
                        [url] [mqtt_ip] [mqtt_port]
    
    Fetch data from a URL and publish it via MQTT.
    
    positional arguments:
      url                   The URL from which to fetch data (supports HTTP/HTTPS). 
      mqtt_ip               The IP address of the MQTT server (default: localhost)
      mqtt_port             The port of the MQTT server (default: 1883). You can also specify the port by adding it to the mqtt_ip 
                            parameter, separated by a colon (e.g. 192.168.0.1:1883).
    
    options:
      -h, --help            show this help message and exit
      --configfile CONFIGFILE
                            Path to YAML configuration file. (default: None)
      --config CONFIG       Name of the configuration set to use, or 'all' to process all configurations. Can also be a comma-
                            separated list of configuration names. (default: all)
      --prefix PREFIX       Optional prefix for all MQTT topics. (default: None)
      --username USERNAME   Username for URL authentication (optional). (default: None)
      --password PASSWORD   Password for URL authentication (optional). (default: None)
      --mqttuser MQTTUSER   Username for MQTT authentication (optional). (default: None)
      --mqttpassword MQTTPASSWORD
                            Password for MQTT authentication (optional). (default: None)
      --verify VERIFY       SSL certificate verification for HTTPS requests ('false' to disable, or path to a custom CA bundle).
                            (default: None)
      --interval INTERVAL   Interval in seconds to repeatedly fetch data from the URL (optional). (default: None)


## Configuration File Format and Use

The configuration file must look like this:

    configurations:
      - name: "default"
        url: "https://example.com/data.json"
        mqtt_ip: "192.168.1.100"
        mqtt_port: 1883
        prefix: "my/prefix"
        username: "user"
        password: "pass"
        mqttuser: "mqtt_user"
        mqttpassword: "mqtt_pass"
        verify: "/path/to/ca_bundle.pem"
      - name: "backup"
        url: "https://backup.example.com/data.json"
        mqtt_ip: "192.168.1.101"
        mqtt_port: 1884
        prefix: "backup/prefix"

You can choose to only use one of the configuration sets in the configfile using the --config parameter:
    python data2mqtt.py --configfile config.yaml --config "default"

Or specify a comma-separated list if you want to use more than one configuration set:
    python data2mqtt.py --configfile config.yaml --config "default,backup"

(It is also possible to process all configuration sets in the specified configfile by using --config=all)

By using the --interval parameter, data2mqtt will enter an loop and will process the commandline parameters or the specified configuration sets in the configfile every X seconds (X is the intervall in seconds specified with --interval).

