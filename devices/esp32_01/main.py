from machine import I2C, Pin
from lib.battery_status import BatteryStatus
from mqtt import MQTT
from time import sleep, time
from random import randint
import ujson
import urequests
import ssl, socket

CURRENT_VERSION = "1.0.1"
HOST = "192.168.4.1"
PORT = 5001

def make_request(path):
    addr = socket.getaddrinfo(HOST, PORT)[0][-1]
    sock = socket.socket()
    sock.connect(addr)
    
    # wrap_socket is available in your build
    sock = ssl.wrap_socket(
        sock,
        server_hostname=HOST,
        cert=open("client.crt", "rb").read(),    # mTLS client cert
        key=open("client.key", "rb").read(),      # mTLS client key
        cadata=open("ca.crt", "rb").read(),       # verify server
        cert_reqs=ssl.CERT_REQUIRED               # enforce server verification
    )
    
    request = (
        f"GET {path} HTTP/1.0\r\n"
        f"Host: {HOST}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    )
    sock.write(request.encode())
    
    response = b""
    while True:
        chunk = sock.read(1024)
        if not chunk:
            break
        response += chunk
    
    sock.close()
    
    headers_raw, body = response.split(b"\r\n\r\n", 1)
    headers = {}
    for line in headers_raw.split(b"\r\n")[1:]:
        if b":" in line:
            k, v = line.split(b":", 1)
            headers[k.strip().decode()] = v.strip().decode()
    
    return headers, body

def check_update():
    headers, body = make_request("/ota/version")
    latest = ujson.loads(body)["version"]
    print(f"Current: {CURRENT_VERSION}, Latest: {latest}")
    return latest != CURRENT_VERSION

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

