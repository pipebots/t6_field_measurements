import ipaddress
import random
import socket
import time
import subprocess

import paho.mqtt.client as mqtt


def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Connected to MQTT broker with code {rc}")


def on_publish(client, userdata, mid, properties=None):
    print(f"Published payload, Message ID: {mid}")


mqtt_broker = "broker.hivemq.com"
mqtt_broker_port = 1883

prefix_ipv6 = ipaddress.IPv6Address("64:ff9b::")

mqtt_topics_base = "pipebots/demo/icair/sc/16062022"

battery_value = 100

hostname = socket.gethostname()
print(f"Hostname is {hostname}")

mqtt_broker_ipv4 = socket.gethostbyname(mqtt_broker)
mqtt_broker_ipv4 = ipaddress.IPv4Address(mqtt_broker_ipv4)
mqtt_broker_ipv6 = ipaddress.IPv6Address(
    int(prefix_ipv6) | int(mqtt_broker_ipv4)
)

print(f"Broker's translated IPv6 address is {mqtt_broker_ipv6}")

mqtt_client = mqtt.Client(
    client_id="pipebots_icair_demo", userdata=None, protocol=mqtt.MQTTv311
)

mqtt_client.on_connect = on_connect
mqtt_client.on_publish = on_publish

mqtt_client.connect(str(mqtt_broker_ipv6), mqtt_broker_port)

print("Beginning publishing loop")

mqtt_client.loop_start()

try:
    while True:
        rssi_value = subprocess.run(
            "sudo wpanctl get Thread:NeighborTable",
            shell=True, capture_output=True
        )
        rssi_value = rssi_value.stdout.decode().split("\n")[1].strip().split(",")[4].split(":")[1]

        publish_topic = "/".join([mqtt_topics_base, hostname, "imag_batt"])
        (rc, mid) = mqtt_client.publish(publish_topic, str(battery_value), qos=1)
        print(f"Published on {publish_topic} with payload of {battery_value}")
        battery_value -= 1
        if battery_value <= 0:
            battery_value = 100

        time.sleep(5)
        publish_topic = "/".join([mqtt_topics_base, hostname, "rssi"])
        (rc, mid) = mqtt_client.publish(publish_topic, str(rssi_value), qos=1)
        print(f"Published on {publish_topic} with payload of {rssi_value}")

        time.sleep(30)
except KeyboardInterrupt:
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
