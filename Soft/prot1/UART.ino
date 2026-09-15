#include "UART.h"

ToMain to_main;
FromMain from_main;

void initUART() {
  Serial.begin(115200);
  Serial1.begin(115200, SERIAL_8N1, 17, 16);
}

void UART() {
  if (readPacket(Serial1, from_main) == READ_OK) {
    data.dp.id = from_main.id; // dpに通信でゲットした値を代入して、dpから使えるようにする
    data.dp.ack = from_main.ack;
    data.dp.content_id = from_main.content_id;
    data.dp.content = from_main.content;
  }

  to_main.ball_angle = ball_angle;
  to_main.ball_distance = ball_distance;
  to_main.line_angle = line_angle;
  to_main.line_distance = line_distance;
  sendPacket(Serial1, to_main);
}