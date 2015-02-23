/*
  Wireless node master
  
  Base node - receives data from 3 other nodes
  
  DS18B20 will have precision at 9 bits so measure time is approx 80ms
  instead of approx 750ms
  
  Address is "0node"
  
*/
#include <SPI.h>
#include "nRF24L01.h"
#include "RF24.h"
#include "printf.h"
#include "structs.h"

byte address[][6] = {"0node","1node","2node","3node"};
// master radio in address[]
byte master = 0;
int myAddress;

const int rPin1 = 6; // radio pins, SPI plus 7,8
const int rPin2 = 7; 
RF24 radio(rPin1,rPin2);
unsigned int startTime = 0;
unsigned int endTime = 0;
unsigned int interval = 60; // seconds between messages

// debug mode
#define DEBUG
/*
struct dataStruct{
  unsigned long _micros;
  float temp;
  long Vcc;
  int address;
} dataPackage, node1, node2, empty;*/
dataPacket dataPackage;
dataPacket node1;
dataPacket node2;
dataPacket empty;

String data;

byte getAddress()
{
  delay(20);
  int a = digitalRead(A0);
  int b = digitalRead(A1);
  int newAddress = 0;
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
  }
  return newAddress;
}

void setup(){
  #if defined DEBUG
    Serial.begin(38400);
  #endif
  Serial.println("Start");
  printf_begin();
  radio.begin();
  radio.setAutoAck(false);
  
  // open pipes for communication
  for (int i=1; i < sizeof(address) - 1; i++) {
    radio.openReadingPipe(i, address[i]);
  }
  radio.openWritingPipe(address[master]);
  // power up radio
  // this takes up to 5ms
  radio.powerUp();
  delay(10);
  radio.startListening();
  
  radio.printDetails();
  
  //interrupt on pin 2 (interrupt 0)
  // Will be pulled LOW when receiving
  attachInterrupt(0, check_radio, LOW);
  
}

void printInfo(dataPacket data) {
  Serial.print("Up: ");Serial.print(data.uptime);Serial.print("s, ");
    Serial.print(data._micros);Serial.print(", ");
    Serial.print(data.temp);Serial.print(", ");
    //Serial.print(dataPackage.chipTemp);Serial.print(", ");
    Serial.print(data.Vcc);Serial.print(", ");
    Serial.println(data.address);
    return;
}

void loop() {
  startTime = millis()/1000;
  int elapsed = startTime - endTime;
  if (elapsed == interval) {
    Serial.print("heartbeat (s): ");
    Serial.println(startTime);
    endTime = startTime;
    
    // every interval, display current information
    if (node1.address) {
      Serial.print("Node 1 -  ");
      //Serial.println(time);
      printInfo(node1);
    }
    if (node2.address) {
      Serial.print("Node 2 -  ");
      //Serial.println(time);
      printInfo(node2);
    }
  }
  
  
}

void check_radio(void)       
{
  #ifdef DEBUG
  Serial.println("IRQ received");
  #endif
  
  bool tx,fail,rx;
  radio.whatHappened(tx,fail,rx);                     // What happened?
  
  if ( tx ) {                                         // Have we successfully transmitted?
      
  }
  
  if ( fail ) {                                       // Have we failed to transmit?
      printf("Failure\n");
  }
  
  if ( rx || radio.available()){                      // Did we receive a message?
    radio.read(&dataPackage, sizeof(dataPackage));
    //Serial.println(data);
    unsigned long time = millis() / 1000;
    //Serial.println("Package received");
    // Which node? /////////////
    //node1 = empty;
    //node2 = empty;
    if (dataPackage.address == 1) {
      node1 = dataPackage;
    } else if (dataPackage.address == 2) {
      node2 = dataPackage;
    }
    ////////////////////////////
    /*
    Serial.print("Received from: ");
    if (node1.address) {
      Serial.print("Node 1 - at (s) ");
      Serial.println(time);
      printInfo(node1);
    } else if (node2.address) {
      Serial.print("Node 2 - at (s) ");
      Serial.println(time);
      printInfo(node2);
    }*/
  }
      
}
