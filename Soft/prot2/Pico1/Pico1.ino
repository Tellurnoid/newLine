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
const uint8_t IN_PINS[] = {2,3,4,5,6,7,8,9,10,11,12,13,14,15}; // 受信14本
const int RX_COUNT = 14;
#else
const uint8_t RX_PINS[18] = {
                             14, 15, 26, 27,  9, 
                             10,  1,  0, 11, 13,
                             12,  8,  4,  7,  3,
                              6,  2,  5
                            }; // 受信18本
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


//全センサー情報統合
bool sensors[32];


void setup() {
  Serial.begin(115200);      
  PIOSerial1.begin(115200);
  for (int i = 0; i < TX_COUNT; i++) pinMode(IN_PINS[i], INPUT_PULLUP);
  pinMode(conpPWM, OUTPUT);
  analogWriteFreq(1000);   // 周波数
  analogWriteRange(255);   // Duty比の分解能
}

// 一応相互通信用。実装時は必要なし
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

//受信関数
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


//0: Pico1から取得
//1: Pico2から取得
bool whichMCU[32]={0,0,1,1,1,1,1,1,1,1,
                   1,1,1,1,1,1,1,1,1,1,
                   0,0,0,0,0,0,0,0,0,0,
                   0,0};

//自分の取得と結合(整列済み)
void joinPico2(){
  int p = 32;//センサー総数
  int p_pico1 = 0;//1つ目のPicoの何番目か
  int p_pico2 = 0;//2つ目のPicoの何番目か
    for (int Q=0; Q<p; Q++){
      if(whichMCU[Q]==0){
        sensors[Q] = digitalRead(IN_PINS[p_pico1]);
        p_pico1++;
      }
      else{
        sensors[Q] = !rxPin[p_pico2];//逆転した論理修正
        p_pico2++;
      }
      // Serial.print(sensors[Q]);
      // Serial.print(",");
    }
    // Serial.println();
}

//シリアル出力
void rawDebug(){
  Serial.print(sensors[0]);
  for (int i=0+1; i<32-2; i++){
    Serial.print(sensors[i]);
    Serial.print(",");
  }
  Serial.print(sensors[31]);
  Serial.println();
}

//シリアル出力
void rawDebug_Q(){
  Serial.print("Q1:");
  Serial.print(sensors[0]);
  Serial.print(", ");
  for (int i=0+1; i<32-2; i++){
    Serial.print("Q");
    Serial.print(i+1);
    Serial.print(":");
    Serial.print(sensors[i]);
    Serial.print(", ");
  }
  Serial.print("Q31:");
  Serial.print(sensors[31]);
  Serial.println();
}

void loop() {
  static uint32_t tSend = 0, tPrint = 0;
  uint32_t now = millis();
  analogWrite(conpPWM,    50);
  sendBits();
  receiveBits();
  joinPico2();
  //rawDebug();
  rawDebug_Q();
  // for (int i = 0; i < RX_COUNT; i++) {
  //   Serial.print(rxPin[i]);
  //   Serial.print(",");
  // }

  //  Serial.print("  RP1_in(me)");
  //  for(int i=0; i<14; i++){
  //   Serial.print(digitalRead(IN_PINS[i]));Serial.print(",");
  //  }
  //  Serial.println();
}