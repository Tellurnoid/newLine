#include <Arduino.h>
#include <SerialPIO.h>
SerialPIO PIOSerial1(0, 1); 
const uint8_t IN_PINS[16] = {2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17};
#define conpPWM 2   
uint16_t rxBits = 0;   // 相手から受信した16bit
bool rxPin[16];   
void setup() {
  Serial.begin(115200);          // USBデバッグ用
  PIOSerial1.begin(115200);
  for (int i = 0; i < 16; i++) pinMode(IN_PINS[i], INPUT_PULLUP);
    pinMode(conpPWM, OUTPUT);
  analogWriteFreq(1000);   // 周波数はグローバル設定(全ピン共通)
  analogWriteRange(255);   // Duty比の分解能も共通設定

}

void sendBits() {
  uint16_t bits = 0;
  for (int i = 0; i < 16; i++) {
    if (!digitalRead(IN_PINS[i])) bits |= (1u << i);  // LOW=1
  }
  uint8_t lo = bits & 0xFF, hi = bits >> 8;
  uint8_t frame[4] = {0xAA, lo, hi, (uint8_t)(lo ^ hi)};
  PIOSerial1.write(frame, 4);
}

void receiveBits() {
  static uint8_t buf[3];
  static uint8_t n = 0;
  while (PIOSerial1.available()) {
    uint8_t b = PIOSerial1.read();
    if (n == 0) {                       // ヘッダ待ち
      if (b == 0xAA) n = 1;
      continue;
    }
    buf[n - 1] = b;
    if (++n == 4) {                     // 4バイト揃った
      if ((buf[0] ^ buf[1]) == buf[2]) rxBits = buf[0] | (buf[1] << 8);
      n = 0;
    }
    for (int i = 0; i < 16; i++) rxPin[i] = (rxBits >> i) & 1;
  }
}

void loop() {
  static uint32_t tSend = 0, tPrint = 0;
  uint32_t now = millis();
    analogWrite(conpPWM, 90);
  if (now - tSend >= 10) { tSend = now; sendBits(); }   // 10msごとに送信
  receiveBits();

//   if (now - tPrint >= 500) {                            // 確認用表示
//     tPrint = now;
//     Serial.println(rxBits, BIN);
//   }

   //以下デバッグ用
   for(int i=0; i<16; i++){
    Serial.print(rxPin[i]);Serial.print(",");
   }
   Serial.print("  ");
   for(int i=0; i<16; i++){
    Serial.print(digitalRead(IN_PINS[i]));Serial.print(",");
   }
   Serial.println();
}