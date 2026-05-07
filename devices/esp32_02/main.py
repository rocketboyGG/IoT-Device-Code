from machine import I2C, Pin
from lib.battery_status import BatteryStatus
from lib.mqtt import MQTT
from time import sleep, time
from random import randint
import ujson

def sub_cb(topic, msg):
    try:
        cmd    = ujson.loads(msg)
        method = cmd.get("method")
        params = cmd.get("params")
        print(f"CMD received — {method}: {params}")

    except Exception as e:
        print("Fejl i behandling af besked:", e)
    

#battery_status = BatteryStatus(34)
mqtt = MQTT()
mqtt.method_receive(sub_cb)

INTERVAL = 5
last_publish = 0

while True:
    try:
        mqtt.client.check_msg()  
        now = time()
        if now - last_publish >= INTERVAL:
            print("New updates: ", check_update())
            telemetry = {
                "device_id": mqtt.DEVICE_ID,
                "timestamp": now,
                "temperature": randint(0,30),
            }
            mqtt.send_message(telemetry)
            last_publish = now
    except KeyboardInterrupt:
        print("\nCtrl+C fanget - lukker ned...")
        mqtt.disconnect_wifi()

