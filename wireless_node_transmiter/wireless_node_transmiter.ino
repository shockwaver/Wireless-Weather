/*
  Wireless node transmitter
  
  Transmits to base node (non acknowledged) once every X minutes
  before entering super low power mode.
  
  Reads from DS18B20 sensor and broadcasts temp, uptime
  and battery voltage.
  
  DS18B20 will have precision at 9 bits so measure time is approx 80ms
  instead of approx 750ms
  
  Address is selectable using analog pins
  9 and 5 to GND to select
  9/6 no gnd = 1
  9 gnd, 6 no gnd = 2
  9/6 gnd = 3
  
  NRF24L01+ Wiring:
  MISO -> 12
  MOSI -> 11
  SCK -> 13
  
  CSN -> 8
  CE -> 7
  
*/

#include <JeeLib.h>
#include <SPI.h>
#include "nRF24L01.h"
#include "RF24.h"
#include "printf.h"
#include <OneWire.h>
#include <DallasTemperature.h>

// sleep watchdog
ISR(WDT_vect) { Sleepy::watchdogEvent(); }

OneWire ds(4);
DallasTemperature sensor(&ds);

const int timePeriod = 5; // minutes to sleep

byte address[][6] = {"0node","1node","2node","3node"};
// master radio in address[]
byte master = 0;
int myAddress;
char buf[10];
String output;
float temp;
byte addr[8];
byte tempData[12];
const int tempPrec = 9;

// Address Select pins
const int addrPin1 = 9;
const int addrPin2 = 5;

// Vbat input pin
const int VbatPin = 0;

 
struct dataStruct{
  unsigned long _micros;
  float temp;
  int Vbat;
  int Vcc;
  byte address;
  long uptime;
} dataPackage;

const int rPin1 = 7; // radio pins, SPI plus 7,8
const int rPin2 = 8; 
  
RF24 radio(rPin1,rPin2);
const int ledPin = 3;

// debug mode
//#define DEBUG

// Sleep for X minutes
void sleepFor(int minutes) 
{
    for (byte i = 0; i < minutes; ++i) {
        Sleepy::loseSomeTime(60000);
  }
}

byte getAddress()
{
  pinMode(addrPin1, INPUT);
  pinMode(addrPin2, INPUT);
  digitalWrite(addrPin1,HIGH);
  digitalWrite(addrPin2,HIGH);
  
  delay(20);
  int newAddress = 0;
  /*
  if (a && b) {
    //node 3
    newAddress = 3;
  } else if (a && ~b) {
    //node 2
    newAddress = 2;
  } else if (~a && b) {
    //node 1
    newAddress = 1;
  } else if (~a && ~b) {
    //node 0
    newAddress = 1;
  }*/
  if (digitalRead(addrPin1)) {
    newAddress = 1;
  } else if (digitalRead(addrPin2)) {
    newAddress = 2;
  } else {
    newAddress = 3;
  }
  digitalWrite(addrPin1, LOW);
  digitalWrite(addrPin2, LOW);
  return newAddress;
}

void setup(){
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, HIGH);
  delay(500);
  #if defined DEBUG
    Serial.begin(115200);
    Serial.println("start");
  #endif
  
  // get my address based on pin inputs
  myAddress = getAddress();
  #if defined DEBUG
    Serial.print("address: ");Serial.println(myAddress);
  #endif
  printf_begin();
  
  radio.begin();
  radio.setAutoAck(false);
  
  sensor.begin();
  
  // open pipes for communication
  radio.openWritingPipe(address[myAddress]);
  radio.openReadingPipe(1, address[master]);
  radio.powerUp();
  delay(10);
  //radio.startListening();
  #if defined DEBUG
    //Serial.println("Radio details:");
    radio.printDetails();
  #endif
  
  // Set up temp sensor
  ds.reset_search();
  ds.search(addr);
  sensor.setResolution(addr, tempPrec);
  
  #if defined DEBUG
    Serial.println(sensor.getResolution(addr));
  #endif
  delay(1000);
  digitalWrite(ledPin, LOW);
}

void queryTemp() {
  // send query command to sensor
  sensor.setWaitForConversion(false);  // makes it async
  sensor.requestTemperatures();
  sensor.setWaitForConversion(true);
}

float getTemp(){
  float tempRead = sensor.getTempCByIndex(0);
  // Get temp from sensor
  return tempRead;
}

void loop() {
    digitalWrite(ledPin, HIGH);
  #if defined DEBUG
    Serial.println("Loop");
  #endif
  
  // Query temp sensor - max time for read is 90ms
  queryTemp();
  
  // power up radio
  // this takes up to 5ms
  radio.powerUp();

  Sleepy::loseSomeTime(90); // wait 90 ms for sensor/radio
  
  #if defined DEBUG
    Serial.println("Stop listening");
  #endif
  
  radio.stopListening(); // make sure we're not listening
  
  // Assemble package //////////////////
  dataPackage.temp = getTemp();
  dataPackage._micros = micros();
  dataPackage.address = myAddress;
  dataPackage.Vcc = readVcc()/10;
  dataPackage.uptime = millis()/1000/60;
  
  // Read battery voltage
  analogRead(VbatPin); // ignore first read
  int voltage = analogRead(VbatPin);
  voltage = map(voltage, 0, 1023, 0, readVcc()/10); // map value to 0 - Vcc*100
  voltage *= 2;  // Battery is on 50% voltage divider, so multiply by 2
  dataPackage.Vbat = voltage;
  ///////////////////////////////////////
  
  #if defined DEBUG
    Serial.println("Sending:");
    Serial.println(dataPackage.temp);
    Serial.println(dataPackage._micros);
  #endif

  // send package///////////////////////
  radio.write( &dataPackage, sizeof(dataPackage) );
  //////////////////////////////////////
  
  // Power down to low power mode
  radio.powerDown();
  ////////////////////////////////
  //delay(1000);
  #if defined DEBUG
    Serial.println("end");
  #endif
  digitalWrite(ledPin, LOW);
  sleepFor(timePeriod);
  //delay(5000);
}

long readVcc() {
  long result;
  // Read 1.1V reference against AVcc
  ADMUX = _BV(REFS0) | _BV(MUX3) | _BV(MUX2) | _BV(MUX1);
  delay(2); // Wait for Vref to settle
  ADCSRA |= _BV(ADSC); // Convert
  while (bit_is_set(ADCSRA,ADSC));
  result = ADCL;
  result |= ADCH<<8;
  result = 1126400L / result; // Back-calculate AVcc in mV
  return result;
}
