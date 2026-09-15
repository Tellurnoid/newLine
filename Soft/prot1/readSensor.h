#ifndef READSENSOR_H
#define READSENSOR_H

void initMUX();
void readIR();
void readLINE();
void printIR();
void printLINE();

// 読み取り結果格納用(半時計回り)
extern int16_t sensorValue_IR[16];
extern int16_t sensorValue_LINE[32];

#endif
