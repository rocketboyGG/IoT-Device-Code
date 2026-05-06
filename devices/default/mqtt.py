import network, ubinascii
from umqtt.simple import MQTTClient
from time import sleep
import ssl
import machine
import ujson

class MQTT:
    def __init__(self):
        with open('config.json', 'r') as f:
            config = ujson.load(f)

        self.DEVICE_ID = config.get("device_id")
        self.PUB_TOPIC  = f"sensors/{self.DEVICE_ID}/data"
        self.CMD_TOPIC  = f"sensors/{self.DEVICE_ID}/cmd"
        
        
        self.wifi = network.WLAN(network.STA_IF)
        self.connect_to_wifi(config.get("wifi_ssid"), config.get("wifi_password"))
        
        with open("ca.crt", "rb") as f:
            ca_data = f.read()
        with open("client.crt", "rb") as f:
            client_cert_data = f.read()
        with open("client.key", "rb") as f:
            client_key_data = f.read()
            
        # MQTT broker info
        self.mqtt_server_ip = config.get("broker_ip")
        
        # Opret en SSL Context (Den rigtige måde i moderne MicroPython)
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

        # Indlæs CA (Gatewayens tillid)
        ssl_context.load_verify_locations(cadata=ca_data)

        # Indlæs Klient-ID (mTLS - det her beviser hvem ESP32 er)
        # Bemærk: MicroPython kræver ofte at cert og key indlæses samtidigt
        ssl_context.load_cert_chain(client_cert_data, client_key_data)

        # Sørg for at den ikke tjekker hostname, hvis du bruger IP-adresse
        #ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_REQUIRED

        # Connect til MQTT broker
        self.client = MQTTClient(
            self.DEVICE_ID, 
            self.mqtt_server_ip, 
            port=8883, 
            keepalive=60,
            ssl=ssl_context
        )
        try:
            print("Forbinder til MQTTS Gateway...")
            self.client.connect()
            print("Succes! Forbindelsen er krypteret og verificeret via mTLS.")
            
        except Exception as e:
            print("Fejl ved forbindelse:", e)
        

    def connect_to_wifi(self, ssid, password):
        
        if self.wifi.isconnected():
            self.wifi.disconnect()
        
        self.wifi.active(False)  # Sluk helt for radioen
        sleep(1)
        self.wifi.active(True)
            
        self.wifi.connect(ssid, password)
        
        retry = 0
        while not self.wifi.isconnected() and retry < 20:
            status = self.wifi.status()
            print(f"Venter på WiFi... forsøg {retry+1}/20 | status: {status}")
        
            if status == 202:
                print("Auth fejl (202) - venter før nyt forsøg...")
                self.wifi.active(False)
                sleep(3)  
                break      
            
            if status == 201:
                print("AP ikke fundet (201) - venter...")
                sleep(2)
            
            sleep(1)
            retry += 1

        if self.wifi.isconnected():
            print("Connected to Wi-Fi:", self.wifi.ifconfig())
        else:
            print(f"FAILED TO CONNECT - final status: {self.wifi.status()}")
            machine.reset() 
        
    def send_message(self, telemetry):
        payload = ujson.dumps(telemetry)
        self.client.publish(self.PUB_TOPIC.encode(), payload.encode())
        print(f"Published: {payload}")
    
    def method_receive(self, method):
        self.client.set_callback(method)
        self.client.subscribe(self.CMD_TOPIC)
    
    def disconnect_wifi(self):
        if self.wifi.isconnected():
            print("Afbryder WiFi forbindelse...")
            self.wifi.disconnect()
            sleep(0.5) 
        
        self.wifi.active(False)
        print("WiFi radio slukket")


