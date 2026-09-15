#include "readSensor.h"
#include <math.h>
#include <Arduino.h>
#include "LINE.h"

constexpr int NUM_LINE_SENSORS = 32;
int16_t minValue[32];
int16_t maxValue[32];

const int calibration_quantity = 400;
const float BORDER_LINE = 0.8;  // 大きいほど緩い

void calibrateLINE() {
  is_calibration = 1;
  digitalWrite(LED, HIGH);


  for (int i = 0; i < NUM_LINE_SENSORS; i++) {
    minValue[i] = 32767;   // int16_tの最大
    maxValue[i] = -32768;  // int16_tの最小
  }

  for (int k = 0; k < calibration_quantity; k++) {
    readLINE();

    for (int i = 0; i < NUM_LINE_SENSORS; i++) {
      minValue[i] = min(minValue[i], (int16_t)(sensorValue_LINE[i] * 0.5f + minValue[i] * 0.5f));
      maxValue[i] = max(maxValue[i], (int16_t)(sensorValue_LINE[i] * 0.5f + maxValue[i] * 0.5f));
    }
    Serial.println(k);
    delay(10);
  }

  digitalWrite(LED, LOW);
  is_calibration = 0;
}

int16_t lineValue[NUM_LINE_SENSORS];

void normalizeLINE() {
  readLINE();
  for (int i = 0; i < NUM_LINE_SENSORS; i++) {
    float normalized = (sensorValue_LINE[i] - minValue[i]) / (float)(maxValue[i] - minValue[i]);

    int diff = maxValue[i] - minValue[i];
    if (diff != 0) {
      normalized = (sensorValue_LINE[i] - minValue[i]) / (float)diff;
    }

    normalized = constrain(normalized, 0.0, 1.0);

    lineValue[i] = (normalized > BORDER_LINE) ? 1 : 0;

    Serial.print(lineValue[i]);
    Serial.print(" : ");
  }
  Serial.println(" ");
}

////////////////////////////////////////////////////////////////////////
int16_t line_angle;
int16_t line_distance;

const float lineSensorDeg[NUM_LINE_SENSORS] = {
0,
11.25,
22.5,
33.75,
45,
56.25,
67.5,
78.75,
90,
101.25,
112.5,
123.75,
135,
146.25,
157.5,
168.75,
180,
191.25,
202.5,
213.75,
225,
236.25,
247.5,
258.75,
270,
281.25,
292.5,
303.75,
315,
326.25,
337.5,
348.75
};

void getLineAngle() {
  normalizeLINE();


  int line_index[NUM_LINE_SENSORS];
  int data_size = 0;  // line_indexの要素数

  for (int i = 0; i < NUM_LINE_SENSORS; i++) { // line_index[]の要素を全て-1にする
    line_index[i] = -1;
  }

  for (int i = 0; i < NUM_LINE_SENSORS; i++) {
    if (lineValue[i] == 0) { 
      line_index[data_size++] = i;
    }
  }

  int max_index_in_array  = 0;
  int max_diff= 0;

  if (data_size == 0) { // = どのセンサーも反応していない
    line_angle = 400;
  }
  else {
    for (int x = 0; x < data_size; x++) { // 反応しているセンサーの数分for
      if (x == 0) {
        max_diff = line_index[0] + (NUM_LINE_SENSORS - line_index[data_size - 1]); // 端っこの部分をたす
        max_index_in_array = 0;
      }
      else {
        if (line_index[x] - line_index[x-1] > max_diff) { // indexの差が一番大きかったら
          max_index_in_array = x;  // そのindexを保存
          max_diff = line_index[x] - line_index[x-1];
        }
      }
    }
    if (data_size == 1) {
      line_angle = lineSensorDeg[line_index[0]] + 180;
    }
    else if (max_index_in_array  == 0) { // 角度計算
      line_angle = (lineSensorDeg[line_index[0]] + lineSensorDeg[line_index[data_size - 1]]) / 2 + 180; // 0を跨ぐ場合は180足して正規化
    }
    else {
      line_angle = (lineSensorDeg[line_index[max_index_in_array]] + lineSensorDeg[line_index[max_index_in_array - 1]]) / 2;
    }

    // line_angle += 180;  // なぜか180度ズレるから足してる

    while(line_angle > 180) line_angle -= 360;
    while(line_angle < -180) line_angle += 360; // -180~180に正規化

    // line_distance = cos(((float)max_diff / NUM_LINE_SENSORS * 360.0) / 2.0 * PI / 180.0) * 100.0;
    line_distance = -cos(((float)max_diff / NUM_LINE_SENSORS * 360.0) / 2.0 * PI / 180.0) * 100.0;  // なぜかマイナスになるからマイナスかけてる

    ////////クラスターの個数を調べる
    float start = -1; // -1 == none
    float end = -1;
    int num_c = 0;
    for (int i = 0; i < NUM_LINE_SENSORS; i++) {
      if (lineValue[i] == 0) {
        if (start == -1) {
          start = lineSensorDeg[i];
        }
        end = lineSensorDeg[i];
      }
      else {
        if (i != 0 && end == lineSensorDeg[i-1]) {  // 角度
          num_c++;
          start = -1;
          end = -1;
        }
      }
    }
    if (start != -1) {
      // num_c++;
      //追加、0を跨ぐときに、端を2つのクラスタとして捉えてしまうのを防止
      if (lineValue[0] != 0) num_c++; // 端が繋がっていなかったら、クラスタを一つ増やす
    }

    if (num_c >= 3) {
      line_angle = 500;
    }

    // line_dis = num_c;
  }
}


void initLINE() {
}

void LINE() {
  getLineAngle();
   Serial.println(line_angle);
}