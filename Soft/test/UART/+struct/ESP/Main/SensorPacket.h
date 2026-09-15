// SensorPacket.h
#pragma once
#include <stdint.h>

// packed でパディングを無効化（両デバイスで構造を一致させる）
typedef struct __attribute__((packed)) {
    uint8_t  header;       // 同期バイト固定値: 0xAA
    uint8_t  packet_id;    // パケット種別（拡張用）
    uint16_t sensor_id;
    float    temperature;
    float    humidity;
    int16_t  pressure;
    uint8_t  checksum;     // header〜pressureの合計の下位8bit
} SensorPacket;

// チェックサム計算（checksum フィールド自身を除く）
inline uint8_t calcChecksum(const uint8_t* data, size_t len) {
    uint8_t sum = 0;
    for (size_t i = 0; i < len; i++) sum += data[i];
    return sum;
}

#define PKT_HEADER    0xAA
#define PKT_SIZE      sizeof(SensorPacket)
#define PKT_CHK_LEN   (PKT_SIZE - 1)  // checksum を除いたバイト数