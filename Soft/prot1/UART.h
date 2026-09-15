#pragma once

enum ID : uint8_t {
  MAIN,
  SUB,
  MOTOR,
  CAMERA
};

enum Sub_UI : uint8_t {
  LINE_CALIBRATE = 0
};

struct __attribute__((packed)) ToMain {  // attributeでパディング(データの途中になんか入る)のを禁止、sizeOf Tが壊れないようにするため
  int16_t ball_angle;
  int16_t ball_distance;
  int16_t line_angle;
  int16_t line_distance;
};

struct __attribute__((packed)) FromMain {
  int16_t ball_angle;
  int16_t ball_distance;
  int16_t line_angle;

  uint8_t id;
  uint8_t ack;
  uint8_t content_id;
  int16_t content;
};
// ==== utility ====

uint8_t calcChecksum(uint8_t* data, uint8_t len) {
  uint8_t sum = 0;
  for (int i = 0; i < len; i++) sum ^= data[i];
  return sum;
}

void flushUntilHeader(HardwareSerial *s) {  // ヘッダーがくるまでデータを破棄し続ける
  while (s->available()) {
    if (s->read() == 0xAA) break;
  }
}

// ==== sendUART ====
template <typename sendT>
void sendPacket(HardwareSerial &seri, const sendT &d) { // *ポインタ、ではなく&参照で安全に
  // static_assert(condition, "message"); 通信バイトが255バイトを超えるとコンパイルエラーでmessageを表示する
  static_assert(sizeof(sendT) <= 255, "Packet too large");

  const uint8_t* p = reinterpret_cast<const uint8_t*>(&d);  // Serial.writeに必要なunit8_t*の型に、reinterpret_castで変換する
  const uint8_t len = sizeof(sendT);

  uint8_t cs = len;  // checkSumにid、len、中身のデータをかける
  for (uint8_t i = 0; i < len; i++) {
    cs ^= p[i];
  }

  seri.write(0xAA); // 参照 、ポインタの場合はseri->write();
  seri.write(0x55);
  seri.write(len);
  seri.write(p, len);
  seri.write(cs);
}

// ==== readUART ====

enum ReadResult : uint8_t {
  READ_OK = 0,
  READ_NO_HEADER,
  READ_ID_MISMATCH,
  READ_LEN_MISMATCH,
  READ_NOT_ENOUGH_DATA,
  READ_CHECKSUM_ERROR,
  READ_INVALID_SERIAL
};

template <typename readT>
ReadResult readPacket(HardwareSerial &seri, readT &d) {
    enum State { WAIT_HEADER, WAIT_HEADER2, WAIT_LEN, WAIT_DATA, WAIT_CHECKSUM };
    static uint8_t buf[sizeof(readT)];
    static uint8_t idx = 0;
    static uint8_t len = 0;
    static State state = WAIT_HEADER;

    ReadResult result = READ_NOT_ENOUGH_DATA;

    if (seri.available() > 128) {   // 64は目安、パケットサイズに応じて調整、溜まりすぎてたらデータ捨ててリセット
      while (seri.available()) seri.read();
      idx = 0;
      state = WAIT_HEADER;
      return READ_NOT_ENOUGH_DATA;  // データ破棄したので次回読み直し
    }

    while (seri.available()) {  // バッファにある全てのデータを処理
        uint8_t c = seri.read();

        switch (state) {
            case WAIT_HEADER:
                if (c == 0xAA) state = WAIT_HEADER2;
                break;

            case WAIT_HEADER2:
                if (c == 0x55) state = WAIT_LEN;
                else state = WAIT_HEADER;
                break;

            case WAIT_LEN:
                if (c == sizeof(readT)) {
                    len = c;
                    idx = 0;
                    state = WAIT_DATA;
                } else state = WAIT_HEADER;
                break;

            case WAIT_DATA:
                buf[idx++] = c;
                if (idx >= len) state = WAIT_CHECKSUM;
                break;

            case WAIT_CHECKSUM: {
                uint8_t cs = len;
                for (uint8_t i = 0; i < len; i++) cs ^= buf[i];

                state = WAIT_HEADER;

                if (cs == c) {
                    memcpy(&d, buf, len);
                    result = READ_OK;  // 最新値がここでセットされる
                }
                break;
            }
        }
    }

    return result;
}

void initUART();
void UART();

class Data{
  public:
    struct DataPacket { // ここに、処理で使うようなデータを全部宣言、UART.cpp等で代入
      uint8_t id;
      uint8_t ack;
      uint8_t content_id;
      int16_t content;
    };

    DataPacket dp;  // DataPacketの実体を作成、このdpから引き出す
    void init();
    void update();
};