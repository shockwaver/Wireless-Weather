#ifndef structs_h
#define structs_h

typedef struct {
  volatile unsigned long _micros;
  volatile float temp;
  volatile long Vcc;
  volatile int address;
  volatile long uptime;
} dataPacket;
#endif
