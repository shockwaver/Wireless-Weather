#ifndef node_h
#define node_h

typedef struct {
  volatile unsigned long _micros;
  volatile float temp;
  volatile int Vbat;
  volatile int Vcc;
  volatile byte address;
  volatile long uptime;
} dataPacket;

typedef struct {
  volatile int humidity;
  volatile int temp;
  volatile int windDir;
  volatile int windSpeed;
  volatile int rainfall;
  volatile int stationID;
} laCrosse;
#endif


