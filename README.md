# data2mqtt
A Python script that can read data in various formats from an URL and publish the data to an MQTT broker

    usage: data2mqtt.py [-h] [--configfile CONFIGFILE] [--config CONFIG] [--prefix PREFIX] [--username USERNAME]
                        [--password PASSWORD] [--mqttuser MQTTUSER] [--mqttpassword MQTTPASSWORD] [--verify VERIFY]
                        [--interval INTERVAL]
                        [url] [mqtt_ip] [mqtt_port]
    
    Fetch data from a URL and publish it via MQTT.
    
    positional arguments:
      url                   The URL from which to fetch data (supports HTTP/HTTPS). (default: None)
      mqtt_ip               The IP address of the MQTT server. (default: None)
      mqtt_port             The port of the MQTT server. (default: None)
    
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

