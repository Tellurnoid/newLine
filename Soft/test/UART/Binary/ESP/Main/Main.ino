
//UART共通事項------------------------------------------------------------------------------------------
// ===== 送受信する変数をまとめた構造体 =====
struct DataPacket {
  int32_t counter;
  float   temperature;
  uint16_t status;
};

// ===== フレーミング設定 =====
const uint8_t START_BYTE = 0xAA;
const uint8_t PKT_LEN = sizeof(DataPacket);

// 受信用パーサの状態
enum class RxState { WAIT_START, WAIT_LEN, WAIT_DATA, WAIT_CHK };
RxState rxState = RxState::WAIT_START;
uint8_t rxBuf[64];
uint8_t rxIndex = 0;
uint8_t rxLen = 0;

uint8_t calcChecksum(const uint8_t* data, uint8_t len) {
  uint8_t chk = 0;
  for (uint8_t i = 0; i < len; i++) chk ^= data[i];
  return chk;
}

// ===== 送信 =====
void sendPacket(HardwareSerial &port, const DataPacket &pkt) {
  const uint8_t* raw = (const uint8_t*)&pkt;
  port.write(START_BYTE);
  port.write(PKT_LEN);
  port.write(raw, PKT_LEN);
  port.write(calcChecksum(raw, PKT_LEN));
}

// ===== 受信(1バイトずつ状態機械で処理) =====
bool receivePacket(HardwareSerial &port, DataPacket &out) {
  while (port.available()) {
    uint8_t b = port.read();
    switch (rxState) {
      case RxState::WAIT_START:
        if (b == START_BYTE) rxState = RxState::WAIT_LEN;
        break;

      case RxState::WAIT_LEN:
        rxLen = b;
        rxIndex = 0;
        if (rxLen == PKT_LEN && rxLen <= sizeof(rxBuf)) {
          rxState = RxState::WAIT_DATA;
        } else {
          rxState = RxState::WAIT_START; // 想定外の長さは破棄
        }
        break;

      case RxState::WAIT_DATA:
        rxBuf[rxIndex++] = b;
        if (rxIndex >= rxLen) rxState = RxState::WAIT_CHK;
        break;

      case RxState::WAIT_CHK:
        if (b == calcChecksum(rxBuf, rxLen)) {
          memcpy(&out, rxBuf, sizeof(DataPacket));
          rxState = RxState::WAIT_START;
          return true; // 1パケット完成
        }
        rxState = RxState::WAIT_START; // チェックサム不一致は破棄
        break;
    }
  }
  return false;
}
//------------------------------------------------------------------------------------------

// Serial2: RX=16, TX=17 (適宜変更可)
DataPacket txPkt = {0, 25.0f, 1};
DataPacket rxPkt;
unsigned long lastSend = 0;

void setup() {
  Serial.begin(115200);           // デバッグ用USB
  Serial2.begin(115200, SERIAL_8N1, 16, 17); // 通信用UART
}

void loop() {
  // 受信チェック
  if (receivePacket(Serial2, rxPkt)) {
    Serial.printf("Rx: counter=%ld temp=%.2f status=%u\n",
                  rxPkt.counter, rxPkt.temperature, rxPkt.status);
  }

  // 1秒ごとに送信
  if (millis() - lastSend >= 5) {
    lastSend = millis();
    txPkt.counter++;
    txPkt.temperature += 0.1f;
    sendPacket(Serial2, txPkt);
  }
}