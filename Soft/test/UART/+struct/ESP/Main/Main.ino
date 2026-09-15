// ============================================================
//  ESP32  
// ============================================================
#include <Arduino.h>

#include "SensorPacket.h"

// ESP32: Serial2 = UART2 (RX=GPIO16, TX=GPIO17)
#define UART_PORT Serial2
#define BAUD      115200

#define RX_PIN 16
#define TX_PIN 17

// 受信バッファ
uint8_t  rxBuf[PKT_SIZE];
uint8_t  rxIdx = 0;

void sendPacket(SensorPacket &pkt) {
    pkt.header   = PKT_HEADER;
    pkt.checksum = calcChecksum((uint8_t*)&pkt, PKT_CHK_LEN);
    UART_PORT.write((uint8_t*)&pkt, PKT_SIZE);
}

// 戻り値: true=正常受信, false=未完 or エラー
bool receivePacket(SensorPacket &out) {
    while (UART_PORT.available()) {
        uint8_t b = UART_PORT.read();

        // 先頭バイトの同期
        if (rxIdx == 0 && b != PKT_HEADER) {
            Serial.printf("[SYNC] skip byte: 0x%02X\n", b);
            continue;
        }

        rxBuf[rxIdx++] = b;

        if (rxIdx == PKT_SIZE) {
            rxIdx = 0;  // バッファリセット

            // チェックサム検証
            uint8_t expected = calcChecksum(rxBuf, PKT_CHK_LEN);
            if (rxBuf[PKT_SIZE - 1] != expected) {
                Serial.printf("[ERROR] Checksum: got 0x%02X, expected 0x%02X\n",
                              rxBuf[PKT_SIZE - 1], expected);
                return false;
            }

            memcpy(&out, rxBuf, PKT_SIZE);
            return true;
        }
    }
    return false;
}

void setup() {
    Serial.begin(115200);
    UART_PORT.begin(BAUD, SERIAL_8N1, RX_PIN, TX_PIN);  // RX=16, TX=17
}

void loop() {
    SensorPacket pktr = {};
    pktr.packet_id   = 1;
    pktr.sensor_id   = 42;
    pktr.temperature = 25.3f;
    pktr.humidity    = 60.5f;
    pktr.pressure    = 1013;
    sendPacket(pktr);

    SensorPacket pkt;
    if (receivePacket(pkt)) {
        Serial.printf("=== Packet Received ===\n");
        Serial.printf("  ID   : %d\n",   pkt.sensor_id);
        Serial.printf("  Temp : %.1f C\n", pkt.temperature);
        Serial.printf("  Hum  : %.1f %%\n", pkt.humidity);
        Serial.printf("  Pres : %d hPa\n", pkt.pressure);
    }
}