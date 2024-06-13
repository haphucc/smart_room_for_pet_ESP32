# Import library
import dht
from machine import Pin, ADC, SoftI2C, unique_id, reset
import ntptime
import network
from time import sleep, time, localtime
from hx711 import HX711 
from i2c_lcd import I2cLcd
from lcd_api import LcdApi
from servo import Servo
import ubinascii
from umqtt.simple import MQTTClient
# Set the debug to None and activate the garbage collector
import esp
esp.osdebug(None)     # debug set to none
import gc             # garbage collector
gc.collect()
import sys

# LCD Configure 
AddLcd = 0x27
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=400000) 
lcd = I2cLcd(i2c, AddLcd, 2, 16)

'''
# Connect to Wi-Fi network
wifi_ssid = "LUN 1"
wifi_pass = "Xomtro179"

wlan = network.WLAN(network.STA_IF)
def connect_wifi():
    wlan.active(True)
    wlan.scan()
    print('Connecting to:', wifi_ssid)
    wlan.connect(wifi_ssid, wifi_pass)
    while not wlan.isconnected():
        pass   #wait till connection
    print("Wi-Fi connected:", wlan.ifconfig())
connect_wifi()
'''

# Default MQTT server to connect
SERVER = "22b3450b2590409fa7d64cb9e3087bdd.s1.eu.hivemq.cloud"
server_name = "HiveMQ.com"
CLIENT_ID = ubinascii.hexlify(unique_id())     # get the ESP unique ID
PORT = 0
USER = "PetIoT"
PASSWORD = "PetIoT2023"

# Topic send data
# Sensors
TIME_TOPIC  = b"timeRTC"
DHT_TOPIC1  = b"sensor/DHT/Temp"
DHT_TOPIC2  = b"sensor/DHT/Hum"
LC_TOPIC    = b"sensor/Loadcell"
WATER_TOPIC = b"sensor/WaterLv"

# Topic receive data
Threshold_CAN_TOPIC     = b"threshold/can"
Threshold_QUAT_TOPIC    = b"threshold/quat"

# Connect to broker
def connect_broker():
    mqttClient = MQTTClient(CLIENT_ID, SERVER,
                            PORT, USER, PASSWORD,
                            keepalive=60, ssl=True,
                            ssl_params={'server_hostname':'22b3450b2590409fa7d64cb9e3087bdd.s1.eu.hivemq.cloud'})
    mqttClient.connect()
    print(f"Connected to MQTT Broker :: {server_name}", '\n') 
    return mqttClient
def restart_and_reconnect():
    print('Failed to connect to MQTT broker. Reconnecting...')
    sleep(10)
    reset()

try:
    mqttClient = connect_broker()
      
    lcd.clear()
    lcd.move_to(2,0) 
    lcd.putstr("Connected to")
    lcd.move_to(2,1) 
    lcd.putstr("MQTT Broker")
except OSError as e:
    restart_and_reconnect()

time_loop = 0
 
#NTP Time
ntptime.host = "1.asia.pool.ntp.org"
ntptime.settime()
UTC_OFFSET = 7*3600
time_ntp = 0
hour = 0
minute = 0
second = 0
def gettime_ntp():
    global time_ntp 
    global hour, minute, second
    if (time() - time_ntp) >= 1:
        time_now = localtime(time() + UTC_OFFSET)
        hour = time_now[3]
        minute = time_now[4]
        second = time_now[5]
        try:
            mqttClient.publish(TIME_TOPIC, str("{:02d}:{:02d}:{:02d}".format(hour, minute, second)).encode())
        except OSError as e:
            print("Get time error!")
        time_ntp = time()

#DHT22 Sensor
cb_dht = dht.DHT22(Pin(33))
time_dht = 0
doC = 0
doam = 0
motor_quat = Pin(23, Pin.OUT, value = 1)
nhietdo_nguong = 29
def get_dht():
    global time_dht
    global doC, doam
    if time() - time_dht >= 1:
        try:
            cb_dht.measure()
            doC = cb_dht.temperature()
            mqttClient.publish(DHT_TOPIC1, str("{:.1f}".format(doC)).encode())
            doam = cb_dht.humidity()
            mqttClient.publish(DHT_TOPIC2, str("{:.1f}".format(doam)).encode())
        except OSError as e:
            print('Failed to read sensor DHT22.')
        time_dht = time()
def bat_quat():
    if doC >= nhietdo_nguong:
        motor_quat.off()
    else:
        motor_quat.on()
        
#Loadcell Sensor
hx = HX711(dout = 15, pd_sck = 4)
hx.set_scale(200380)            #Calibration for Loadcell
hx.tare()
time_weight = 0
weight_gram = 0
motor_can = Servo(pin = 18)
motor_can.move(70)
can_nguong = 100
def get_weight():
    global time_weight
    global weight_gram
    if time() - time_weight >= 1:
        weight_kg = hx.get_units(10)
        weight_gram = 0
        for i in range(9):
            weight_gram += weight_kg*1000
        if (weight_gram/10) < 0:
            weight_gram = 0
        mqttClient.publish(LC_TOPIC, str("{} gram".format(round(weight_gram/10))).encode())
        time_weight = time()
def can_thuc_an():
    phutMoCan = 30
    gioMoCan = [3, 7, 11, 15, 19, 23]
    for flag in gioMoCan:
        if hour == flag and minute == phutMoCan and round(weight_gram/10) <= can_nguong:
            motor_can.move(100)
        else:
            motor_can.move(70)

#Water Sensor
cb_mucnuoc = ADC(Pin(32))
cb_mucnuoc.atten(ADC.ATTN_11DB)
cb_mucnuoc.width(ADC.WIDTH_10BIT)
time_mucnuoc = 0
mucnuoc = "High"
motor_bomnuoc = Pin(5, Pin.OUT, value = 1)
value = 0
def get_mucnuoc():
    global time_mucnuoc
    global mucnuoc, value
    if time() - time_mucnuoc >= 1:
        value = 0
        for i in range(9):
            value += cb_mucnuoc.read()
        if (value/10) < 150:
            mucnuoc = "Low"
            mqttClient.publish(WATER_TOPIC, str("{}".format(mucnuoc)).encode())
        elif (value/10) >= 300:
            mucnuoc = "High"
            mqttClient.publish(WATER_TOPIC, str("{}".format(mucnuoc)).encode())
        time_mucnuoc = time()
def bom_nuoc():
    if (value/10) < 150:
        motor_bomnuoc.off()
    elif (value/10) >= 300:
        motor_bomnuoc.on()        

def lcd_print():
    lcd.move_to(0,0)
    lcd.putstr("{:.1f}C".format(doC))
    lcd.move_to(0,1)
    lcd.putstr("{:.1f}%".format(doam))
    lcd.move_to(7,0)
    lcd.putstr(mucnuoc)
    lcd.move_to(12,0)
    lcd.putstr("{}".format(round(weight_gram/10)))
    lcd.move_to(15,0)
    lcd.putstr("g")
    lcd.move_to(8,1)
    lcd.putstr("{:02d}:{:02d}:{:02d}".format(hour, minute, second))
def shell_print():
    print("Time now: {:02d}:{:02d}:{:02d}".format(hour, minute, second))
    print("Temp: {:.1f}C".format(doC), "    ", "Hum: {:.1f}%".format(doam))
    print("Can thuc an: {} g".format(round(weight_gram/10)))
    print("CB_mucnuoc: {}".format(round(value/10)), "     ", "Muc nuoc: {}".format(mucnuoc))
    print("=================================")

def callback(topic, msg):
    global nhietdo_nguong
    global can_nguong
    print('\n', "Received message on topic: {}, message: {}".format(topic, msg))
    if topic == b"threshold/quat":
        nhietdo_nguong = int(msg)
        print ("nhietdo_nguong:", msg, '\n')
    elif topic == b"threshold/can":
        can_nguong = int(msg)
        print ("can_nguong:", msg, '\n')

mqttClient.set_callback(callback)
mqttClient.subscribe(Threshold_CAN_TOPIC)
mqttClient.subscribe(Threshold_QUAT_TOPIC)
   
while True:
    try:
        '''
        if not wlan.isconnected():
            print("WiFi connection lost. Reconnecting...")
            wlan = connect_wifi()
        '''
        mqttClient.check_msg()
        if time() - time_loop >= 1:
            shell_print()
            lcd.clear()
            lcd_print()
            
            gettime_ntp()

            get_dht()
            bat_quat()

            get_weight()
            can_thuc_an()

            get_mucnuoc()
            bom_nuoc()   
                
            time_loop = time()   
    except:
        print('\n',"===============Client is Disconnect===============", '\n')
        mqttClient.disconnect()
        sys.exit()

