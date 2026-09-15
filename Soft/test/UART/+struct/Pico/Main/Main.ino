#include <Arduino.h>

SerialPIO PIOSerial1(6, 7);

// ===== パケット定義 =====
#define HEADER 0xAA
#define FOOTER 0x55

// Picoが送信するデータ
struct PicoToESP32 {
    int16_t motorSpeed;    // モーター速度 (-32768~32767)
    uint8_t flags;         // ビットフラグ
    float sensorValue;     // センサー値
};

// ESP32から受信するデータ
struct ESP32ToPico {
    int16_t servoAngle;    // サーボ角度
    uint8_t status;        // ステータス
    float voltage;         // 電圧
};

// ===== 送信関数 =====
void sendStruct(SerialPIO& serial, const PicoToESP32& data) {
    uint8_t* ptr = (uint8_t*)&data;
    uint8_t checksum = 0;

    serial.write(HEADER);
    serial.write((uint8_t)sizeof(PicoToESP32));

    for (size_t i = 0; i < sizeof(PicoToESP32); i++) {
        serial.write(ptr[i]);
        checksum ^= ptr[i];  // XORチェックサム
    }

    serial.write(checksum);
    serial.write(FOOTER);
}

// ===== 受信ステートマシン =====
enum RxState { WAIT_HEADER, WAIT_LEN, RECV_DATA, WAIT_CHECKSUM, WAIT_FOOTER };
RxState rxState = WAIT_HEADER;

uint8_t rxBuf[sizeof(ESP32ToPico)];
uint8_t rxIndex = 0;
uint8_t rxLen = 0;
uint8_t rxChecksum = 0;

bool recvStruct(SerialPIO& serial, ESP32ToPico& out) {
    while (serial.available()) {
        uint8_t byte = serial.read();

        switch (rxState) {
            case WAIT_HEADER:
                if (byte == HEADER) rxState = WAIT_LEN;
                break;

            case WAIT_LEN:
                if (byte == sizeof(ESP32ToPico)) {
                    rxLen = byte;
                    rxIndex = 0;
                    rxChecksum = 0;
                    rxState = RECV_DATA;
                } else {
                    rxState = WAIT_HEADER;  // 不正ならリセット
                }
                break;

            case RECV_DATA:
                rxBuf[rxIndex++] = byte;
                rxChecksum ^= byte;
                if (rxIndex >= rxLen) rxState = WAIT_CHECKSUM;
                break;

            case WAIT_CHECKSUM:
                if (byte == rxChecksum) {
                    rxState = WAIT_FOOTER;
                } else {
                    Serial.println("[ERR] Checksum mismatch");
                    rxState = WAIT_HEADER;
                }
                break;

            case WAIT_FOOTER:
                rxState = WAIT_HEADER;
                if (byte == FOOTER) {
                    memcpy(&out, rxBuf, sizeof(ESP32ToPico));
                    return true;  // 受信成功
                }
                break;
        }
    }
    return false;
}

// ===== メイン =====
void setup() {
    PIOSerial1.begin(9600);
    Serial.begin(115200);
}

PicoToESP32 txData = { 100, 0b00000011, 3.14f };
ESP32ToPico  rxData;
uint32_t lastSend = 0;

void loop() {
    // 10msごとに送信
    if (millis() - lastSend >= 10) {
        lastSend = millis();
        txData.motorSpeed++;  // テスト用にインクリメント
        sendStruct(PIOSerial1, txData);
    }

    // 受信チェック
    if (recvStruct(PIOSerial1, rxData)) {
        Serial.print("servoAngle: "); Serial.println(rxData.servoAngle);
        Serial.print("status:     "); Serial.println(rxData.status);
        Serial.print("voltage:    "); Serial.println(rxData.voltage);
    }
}