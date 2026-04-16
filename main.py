#define BLYNK_TEMPLATE_ID "TMPL29tlZweT2"
#define BLYNK_TEMPLATE_NAME "IrrigacaoSojaESP32"
#define BLYNK_AUTH_TOKEN "RXPVhz5h0KpgmQaWz0Il9k-TiVPW9-0p"

import network, time, ujson
from machine import Pin, ADC
import dht
from umqtt.simple import MQTTClient
try:
    import urequests as requests
except:
    import requests

# ===== Config Wi-Fi =====
SSID = "Wokwi-GUEST"
PASS = ""

# ===== Config MQTT =====
BROKER = "broker.hivemq.com"
TOPIC_SENSORES = b"soja/sensores"
TOPIC_CMD = b"soja/comandos/valvula"
TOPIC_ESTADO = b"soja/atuadores/valvula"

# ===== Config Blynk =====
TOKEN = "RXPVhz5h0KpgmQaWz0Il9k-TiVPW9-0p"   # <-- cole aqui o token do seu Device
BLYNK = "https://blynk.cloud/external/api"

# ===== Hardware =====
d = dht.DHT22(Pin(15))          # DHT22 no GPIO15
solo = ADC(Pin(34))             # Potenciômetro no GPIO34
solo.atten(ADC.ATTN_11DB)       # range 0–3.6V
valvula = Pin(2, Pin.OUT)       # LED no GPIO2

# ===== Funções =====
def wifi():
    w = network.WLAN(network.STA_IF)
    w.active(True)
    w.connect(SSID, PASS)
    print("Conectando Wi-Fi...")
    while not w.isconnected():
        time.sleep(0.5)
    print("Wi-Fi conectado:", w.ifconfig())

def blynk_update(vpin, val):
    try:
        requests.get(f"{BLYNK}/update?token={TOKEN}&{vpin}={val}").close()
    except Exception as e:
        print("Erro Blynk:", e)

def on_msg(t, m):
    msg = m.decode().lower()
    if msg == "on":
        valvula.value(1)
        blynk_update("V3", 1)
    elif msg == "off":
        valvula.value(0)
        blynk_update("V3", 0)

# ===== Inicialização =====
wifi()
cli = MQTTClient("esp32-soja", BROKER)
cli.set_callback(on_msg)
cli.connect()
cli.subscribe(TOPIC_CMD)
print("MQTT conectado.")

# ===== Loop principal =====
while True:
    cli.check_msg()  # verifica comandos recebidos

    # Leitura dos sensores
    d.measure()
    t, h = d.temperature(), d.humidity()
    umisolo = int(solo.read() * 100 / 4095)

    # Publica no MQTT
    dados = ujson.dumps({"temp": t, "umid_ar": h, "umid_solo": umisolo})
    cli.publish(TOPIC_SENSORES, dados)
    print("Publicado:", dados)

    # Atualiza Blynk
    blynk_update("V0", t)
    blynk_update("V1", h)
    blynk_update("V2", umisolo)

    # Regra automática
    if umisolo < 30:
        valvula.value(1)
        blynk_update("V3", 1)
    else:
        valvula.value(0)
        blynk_update("V3", 0)

    time.sleep(0.5)