#define BLYNK_TEMPLATE_ID "TMPL6pOI6Qx2w"
#define BLYNK_TEMPLATE_NAME "Pet IoT"
#define BLYNK_AUTH_TOKEN "p6iQTPF4NxJLmzt6AmjKwnwnTSCbE0lr"

#include <WiFi.h>
#include <WiFiClient.h>
#include <BlynkSimpleEsp32.h>
#include <DHT.h>
#include <Wire.h> 
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <HX711.h>
#include <ESP32Servo.h>
#include <LiquidCrystal_I2C.h>
LiquidCrystal_I2C lcd(0x27, 16, 2);
#include <SimpleKalmanFilter.h>
SimpleKalmanFilter bo_loc(2, 2, 0.001);

//wifi_blynk
#define BLYNK_PRINT Serial
char auth[] = BLYNK_AUTH_TOKEN;
const char ssid[] = "LUN1";
const char pass[] = "Xomtro179";

//cac bien virtual Blynk
int che_do = 0;
int gt_can = 0;
int gt_bomnuoc = 0;
int gt_quat = 0;

//define time RTC
WiFiUDP ntpUDP;
// VN UTC+7 : 7hx60mx60s 
NTPClient timeClient(ntpUDP, "1.asia.pool.ntp.org", 7*60*60); 
unsigned long time_rtc = 0;
int gio = 0, phut = 0, giay = 0;

//define DHT
#define cb_dht 33
const int DHTTYPE = DHT22;
DHT dht(cb_dht, DHTTYPE);
float doam, doC;
#define motor_quat 23
int nhietdo_nguong = 30;
unsigned long time_dht = 0;

//define loadcell hx711
#define DOUT 15
#define CLK 4
HX711 scale(DOUT, CLK);
 float weight_gram, weight_kilo;
float calibration_factor = -(114275);
int rbut = 19;     
#define motor_can 18
Servo servo_can; 
unsigned long time_weight = 0;

//define water level
#define cb_mucnuoc 32
#define motor_bomnuoc 5
unsigned long time_mucnuoc = 0;
String mucnuoc = "Low";
int value_filter = 0;

//functions
void get_rtc();
void get_dht(); void bat_quat();
void get_weight(); void can_thuc_an();
void get_mucnuoc(); void bom_nuoc();
void serial_print();
void lcd_print();

BLYNK_WRITE(V8){
  int adjust_temp = param.asInt();
  nhietdo_nguong = adjust_temp;
}

//thiet lap che do thu cong/tu dong
BLYNK_WRITE(V9){
  che_do = param.asInt();
}
BLYNK_WRITE(V5){
  gt_quat = param.asInt();
  digitalWrite(motor_quat, !gt_quat);
}
BLYNK_WRITE(V6){
  gt_bomnuoc = param.asInt();
  digitalWrite(motor_bomnuoc, !gt_bomnuoc);
}
BLYNK_WRITE(V7){
  gt_can = param.asInt();
  if (gt_can){
    servo_can.write(100);
  }
  else{
    servo_can.write(70);
  }
}

void setup_wifi(){
  lcd.clear();
  lcd.setCursor(1,0);
  lcd.print("Connecting to:");
  lcd.setCursor(5,1);
  lcd.print(ssid);
  
  Serial.println("Connecting to: " + String(ssid));
  Blynk.begin(auth, ssid, pass);
  Serial.print("AP IP address: ");
  Serial.println(WiFi.localIP());
  
  lcd.clear();
  lcd.setCursor(1,0);
  lcd.print("AP IP address:");
  lcd.setCursor(2,1);
  lcd.print(WiFi.localIP());
  delay(3000);
  lcd.clear();
}

#define led_mode 14

void setup() {
  Serial.begin(115200);
  lcd.begin();                    
  lcd.backlight();
  setup_wifi();
  timeClient.begin();
  dht.begin();
  pinMode(motor_quat, OUTPUT);
  digitalWrite(motor_quat, HIGH);
  scale.set_scale();
  scale.tare(); 
  long zero_factor = scale.read_average();
  pinMode(rbut, INPUT_PULLUP);
  pinMode(motor_can, OUTPUT);
  servo_can.attach(motor_can);
  //servo_can.write(70);
  pinMode(motor_bomnuoc, OUTPUT);
  digitalWrite(motor_bomnuoc, HIGH);

  pinMode(led_mode, OUTPUT);
  digitalWrite(led_mode, LOW);
  Blynk.syncVirtual(V5);
  Blynk.syncVirtual(V6);
  Blynk.syncVirtual(V7);
  Blynk.syncVirtual(V8);
  Blynk.syncVirtual(V9);
}

void loop() {
  Blynk.run();
  if (che_do == 0){
    get_rtc(); 
    get_dht(); bat_quat();
    get_weight(); can_thuc_an();
    get_mucnuoc(); bom_nuoc();
    digitalWrite(led_mode, HIGH);
    serial_print();
    lcd_print();
  }
  else if(che_do == 1){
    get_rtc(); 
    get_dht();
    get_weight();
    get_mucnuoc();
    digitalWrite(led_mode, LOW);
    serial_print();
    lcd_print();
  }
}

void get_rtc(){
  if (millis() - time_rtc >= 1000){
    lcd.clear();
    timeClient.update();
    gio = timeClient.getHours();
    phut = timeClient.getMinutes();
    giay = timeClient.getSeconds();
    Blynk.virtualWrite(V0,timeClient.getFormattedTime());
    time_rtc = millis();
  }
}

void get_dht(){
  if (millis() - time_dht >= 2000){
    doam = dht.readHumidity();
    doC = dht.readTemperature();
    if (isnan(doam)||isnan(doC)){
      Serial.println("Khong co gia tri tra ve tu cam bien");
      delay(50);
      return;
    }    
    Blynk.virtualWrite(V1, doC);
    Blynk.virtualWrite(V2, doam);
    time_dht = millis();
  }    
}
void bat_quat(){
  if (doC >= nhietdo_nguong){
    digitalWrite(motor_quat, LOW);
    Blynk.virtualWrite(V5, HIGH);
  }
  else if (doC < nhietdo_nguong){
    digitalWrite(motor_quat, HIGH);
    Blynk.virtualWrite(V5, LOW);
  }
}

void get_weight(){
   if (millis() - time_weight >= 1000){
    scale.set_scale(calibration_factor); 
    weight_kilo = scale.get_units(10);
    weight_gram = weight_kilo*1000;    
    if (weight_gram < 0) weight_gram = 0;
    Blynk.virtualWrite(V3, round(weight_gram));  //g
    if (digitalRead(rbut) == LOW){
      scale.set_scale();
      scale.tare(); 
    }
    time_weight = millis();
  }
}


void can_thuc_an(){
  int phutMoCan = 28;
  const int gioMoCan[] = {7, 12, 17, 22};
  for (int i = 0; i < sizeof(gioMoCan) / sizeof(gioMoCan[0]); i++){
    if (timeClient.getHours() == gioMoCan[i] && timeClient.getMinutes() == phutMoCan && weight_gram <= 100){
      servo_can.write(120);
      Blynk.virtualWrite(V7, HIGH);
      delay(15);
    }
    else{ 
      servo_can.write(70);
      Blynk.virtualWrite(V7, LOW);
      delay(15);
    }
  }
}

void get_mucnuoc(){
  if (millis() - time_mucnuoc >= 100){
    analogReadResolution(10);
    int value = 0;
    for (int i = 0; i < 9; i++){
      value += analogRead(cb_mucnuoc);
    }
    value_filter = bo_loc.updateEstimate((value/10));
    time_mucnuoc = millis();
  }
}
void bom_nuoc(){
  if (value_filter < 200){
    mucnuoc = "Low";
    do{
      digitalWrite(motor_bomnuoc, LOW);
      Blynk.virtualWrite(V4, "Low");
      Blynk.virtualWrite(V6, HIGH);
    }while(value_filter == 350);
  }
  else if(value_filter > 350){
    mucnuoc = "High";
    digitalWrite(motor_bomnuoc, HIGH);
    Blynk.virtualWrite(V4, "High");
    Blynk.virtualWrite(V6, LOW);
  }
}

void serial_print(){
  int time_serial = 0;
  if(millis() - time_serial>=2000){
    Serial.print("Bay gio la: ");
    Serial.println(timeClient.getFormattedTime());
    Serial.println("");
    Serial.print("Nhiet do C: ");
    Serial.print(doC);
    Serial.print("      ");
    Serial.print("Do am %: ");
    Serial.println(doam);
    Serial.println("Can nang: " + String(round(weight_gram)));
    Serial.println("");
    Serial.println("value_filter: " + String(value_filter));
    Serial.println("Muc nuoc: " + String(mucnuoc));
    Serial.println("=====================");
    time_serial = millis();
  }
}

void lcd_print(){
  lcd.setCursor(8,1);
  lcd.print(timeClient.getFormattedTime());
  lcd.setCursor(0,0);
  lcd.print(String(doC));
  lcd.setCursor(0,1);
  lcd.print(String(doam));
  lcd.setCursor(7,0);
  lcd.print(String(mucnuoc));
  lcd.setCursor(13,0);
  lcd.print(String(int(round(weight_gram))));
}
