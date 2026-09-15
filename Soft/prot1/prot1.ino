#include "IR.h"
#include "LINE.h"
#include "Record.h"
#include "UART.h" // UART()でいろんなファイルの変数使うから最後にincludeする必要あり

Record record;
Data data;

#define BUTTON 25
#define LED 21

#define LINE_LED 27

void setup() {
  pinMode(BUTTON, INPUT_PULLUP);
  pinMode(LED, OUTPUT);
  pinMode(LINE_LED, OUTPUT);

  initMUX();
  initIR();
  initLINE();
  initUART();

  record.initRecord();

  record.getLineRecord();


  // analogWrite(LINE_LED, 255);
  // calibrateLINE();
  // digitalWrite(LED, HIGH);
  // delay(1000);
  // digitalWrite(LED, LOW);
  // record.recordLine();  //キャリブレーションが終わったら記録
}

int8_t is_calibration = 0;
int8_t last_is_calibration = 0;

uint8_t ack = 0;

void loop() {
  analogWrite(LINE_LED, 255);
  // digitalWrite(LINE_LED, HIGH);
  IR();
  LINE();
  UART();
  
  if(data.dp.ack != ack && data.dp.id == SUB) {
      if(data.dp.content_id == LINE_CALIBRATE && data.dp.content == 1 && is_calibration == 0) {
      calibrateLINE();
      digitalWrite(LED, HIGH);
      delay(1000);
      digitalWrite(LED, LOW);
      record.recordLine();  //キャリブレーションが終わったら記録
      // digitalWrite(LED, HIGH);
      // delay(1000);
      // digitalWrite(LED, LOW);
      Serial.println("recorded");
    }
    ack = data.dp.ack;
  }


  if(digitalRead(BUTTON) == 0 && is_calibration == 0) {
    calibrateLINE();
    digitalWrite(LED, HIGH);
    delay(1000);
    digitalWrite(LED, LOW);
    record.recordLine();  //キャリブレーションが終わったら記録
    // digitalWrite(LED, HIGH);
    // delay(1000);
    // digitalWrite(LED, LOW);
    // Serial.println("recorded");
  }

  if (last_is_calibration == 1 && is_calibration == 0) {
    digitalWrite(LED, HIGH);
    delay(1000);
    digitalWrite(LED, LOW);
    record.recordLine();  //キャリブレーションが終わったら記録
    // digitalWrite(LED, HIGH);
    // delay(1000);
    // digitalWrite(LED, LOW);
    // Serial.println("recorded");
  }
  last_is_calibration = is_calibration;
  
  Serial.println(ball_angle);
}
