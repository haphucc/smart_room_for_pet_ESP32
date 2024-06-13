# Import library
import dht
from machine import Pin, ADC, SoftI2C
import ntptime
import utime
import network
from time import sleep, time
from hx711 import HX711
import BlynkLib 
from i2c_lcd import I2cLcd
from lcd_api import LcdApi
from servo import Servo
import esp32          # import all needed libraries
import esp
# Set the debug to None and activate the garbage collector
esp.osdebug(None)     # debug set to none
import gc             # garbage collector
gc.collect()

'''
# Connect to Wi-Fi network
wifi_ssid = "XomTro179"
wifi_pass = "troiendone"

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

time_loop = 0

#NTP Time
ntptime.host = "1.asia.pool.ntp.org"
ntptime.settime()
time_rtc = 0
hour = 0
minute = 0
second = 0
def get_rtc():
    global time_rtc 
    global hour, minute, second
    if (time() - time_rtc) >= 1:
        utc_offset = 7 * 3600  # 7 giờ * 3600 giây/giờ
        current_time = utime.time() + utc_offset
        # Tính giờ, phút, giây từ thời gian đã được bù đắp
        hour = (current_time // 3600) % 24
        minute = (current_time % 3600) // 60
        second = current_time % 60
        time_rtc = time()

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
            doam = cb_dht.humidity()          
        except OSError as e:
            print('Failed to read sensor.')
        time_dht = time()
def bat_quat():
    if doC >= nhietdo_nguong:
        motor_quat.off()
#         blynk.virtual_write(5, not motor_quat.value())
    else:
        motor_quat.on()
#         blynk.virtual_write(5, not motor_quat.value())
        
#Loadcell Sensor
hx = HX711(dout = 15, pd_sck = 4)
hx.set_scale(206380) #208460
hx.tare()
time_weight = 0
weight_gram = 0
motor_can = Servo(pin = 18)
motor_can.move(70)
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
        
        time_weight = time()
def can_thuc_an():
    phutMoCan = 22
    gioMoCan = [7, 12, 17, 22,9]
    for flag in gioMoCan:
        if hour == flag and minute == phutMoCan and weight_gram <= 100:
            motor_can.move(100)
#             blynk.virtual_write(7, 1)
        else:
            motor_can.move(70)
#             blynk.virtual_write(7, 1)

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
        elif (value/10) >= 300:
            mucnuoc = "High"
        time_mucnuoc = time()
def bom_nuoc():
    if (value/10) < 150:
        motor_bomnuoc.off()        
#         blynk.virtual_write(6, not motor_bomnuoc.value())
    elif (value/10) >= 300:
        motor_bomnuoc.on()
#         blynk.virtual_write(6, 0)        
 
while True:
    if time() - time_loop >= 2:
        get_rtc()
        print("{:02d}:{:02d}:{:02d}".format(hour, minute, second))
        get_dht()
        print("T: {:.1f} C".format(doC), "    ", "H: {:.1f} %".format(doam))
        bat_quat()
        get_weight()
        print("Can thuc an: {} g".format(round(weight_gram/10)))
        can_thuc_an()
        get_mucnuoc()
        print("CB_mucnuoc: {}".format(round(value/10)), "     ", "Muc nuoc: {}".format(mucnuoc))
        bom_nuoc()
        
        print("================================")
        time_loop = time()
