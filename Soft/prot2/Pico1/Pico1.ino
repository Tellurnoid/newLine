#include <Arduino.h>
#include <SerialPIO.h>
SerialPIO PIOSerial1(0, 1); 
//arduino-cli monitor -p /dev/ttyACM0 -c baudrate=115200

#define conpPWM 2  

//#define BOARD_B          // ← A(RP1)のボードに書くときはこの行をコメントアウト

#ifdef BOARD_B
const uint8_t IN_PINS[18] = {
                             14, 15, 26, 27,  9, 
                             10,  1,  0, 11, 13,
                             12,  8,  4,  7,  3,
                              6,  2,  5
                            }; // 送信18本
const int RX_COUNT = 14;
#else
const uint8_t IN_PINS[] =   {
                             7,8,26,15,14,9,3,10,13,4,11,12,5,6
                            }; // 送信14本
const int RX_COUNT = 18;
#endif
const int TX_COUNT = sizeof(IN_PINS) / sizeof(IN_PINS[0]);

const int PAYLOAD = 3;          // 最大24bit
const int FRAME_LEN = PAYLOAD + 2;

uint32_t rxBits = 0;
bool rxPin[18]; 




void setup() {
  Serial.begin(115200);          // USBデバッグ用
  PIOSerial1.begin(115200);
  for (int i = 0; i < TX_COUNT; i++) pinMode(IN_PINS[i], INPUT_PULLUP);
  pinMode(conpPWM, OUTPUT);
  analogWriteFreq(1000);   // 周波数はグローバル設定(全ピン共通)
  analogWriteRange(255);   // Duty比の分解能も共通設定

}

void sendBits() {
  uint32_t bits = 0;
  for (int i = 0; i < TX_COUNT; i++) {
    if (!digitalRead(IN_PINS[i])) bits |= (1UL << i);
  }
  uint8_t frame[FRAME_LEN];
  frame[0] = 0xAA;
  uint8_t x = 0;
  for (int i = 0; i < PAYLOAD; i++) {
    frame[1 + i] = (bits >> (8 * i)) & 0xFF;
    x ^= frame[1 + i];
  }
  frame[FRAME_LEN - 1] = x;
  PIOSerial1.write(frame, FRAME_LEN);
}


void receiveBits() {
  static uint8_t buf[FRAME_LEN - 1];
  static uint8_t n = 0;
  while (PIOSerial1.available()) {
    uint8_t b = PIOSerial1.read();
    if (n == 0) {
      if (b == 0xAA) n = 1;
      continue;
    }
    buf[n - 1] = b;
    if (++n == FRAME_LEN) {
      uint8_t x = 0;
      for (int i = 0; i < PAYLOAD; i++) x ^= buf[i];
      if (x == buf[PAYLOAD]) {
        rxBits = buf[0] | ((uint32_t)buf[1] << 8) | ((uint32_t)buf[2] << 16);
        for (int i = 0; i < RX_COUNT; i++) rxPin[i] = (rxBits >> i) & 1;
      }
      n = 0;
    }
  }
}


void loop() {
  static uint32_t tSend = 0, tPrint = 0;
  uint32_t now = millis();
  //if (now - tSend >= 10) { tSend = now; sendBits(); }
  sendBits();
  receiveBits();
  analogWrite(conpPWM, 90);



  for (int i = 0; i < RX_COUNT; i++) {
    Serial.print(rxPin[i]);
    Serial.print(",");
  }

   Serial.print("  RP1_in(me)");
   for(int i=0; i<14; i++){
    Serial.print(digitalRead(IN_PINS[i]));Serial.print(",");
   }
   Serial.println();
}