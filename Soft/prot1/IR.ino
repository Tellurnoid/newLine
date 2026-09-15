#include "functions.h"
#include "readSensor.h"

class Ball {
  private:
    static constexpr uint8_t NUM_SENSORS = 16;
    static constexpr float sensorAngles[NUM_SENSORS] = {0, 22.5, 45, 67.5, 90, 112.5, 135, 157.5, 180, 202.5, 225, 247.5, 270, 292.5, 315, 337.5};
    static constexpr float ANGLE_DIFF = 11;

    static constexpr int16_t MAX_VALUE = 4095;
    static constexpr uint8_t NUM_AVE = 10;  // センサーの読み取り移動平均回数//10
    static constexpr uint8_t NUM_ANGLE_AVE = 3;  // 算出角度の移動平均回数//3
    

    static constexpr uint8_t NUM_SEARCH = 5;  // 奇数、一番強いセンサー+左右で調べるセンサーの合計
    static constexpr uint8_t NO_BALL_VALUE = 10;

    int sensorValues[NUM_SENSORS];

    struct ValueRecord {
      int sensorValueRecords[NUM_AVE] = {0};
      int sum_value = 0;
      int ave_index = 0;
    };
    ValueRecord value_records[NUM_SENSORS];

    struct VectorRecord {
      float vectorRecords[NUM_ANGLE_AVE] = {0};
      int ave_index = 0;
    };

    float total_vx = 0;
    float total_vy = 0;
    VectorRecord vx_record;
    VectorRecord vy_record;

    float total_sx = 0;
    float total_sy = 0;
    VectorRecord sx_record;
    VectorRecord sy_record;

  public:
    int getAveIRValue(int index) {
      ValueRecord &r = value_records[index];

      r.sum_value -= r.sensorValueRecords[r.ave_index];

      r.sensorValueRecords[r.ave_index] = MAX_VALUE - sensorValue_IR[index];

      r.sum_value += r.sensorValueRecords[r.ave_index];

      r.ave_index = (r.ave_index + 1) % NUM_AVE;

      return r.sum_value / NUM_AVE;
    }

    void updateIR() {
      for (int i = 0; i < NUM_SENSORS; i++) {
        sensorValues[i] = getAveIRValue(i);
      }
    }

    int getBallDistance() {
      int num_on_sensors = 0;
      for (int i = 0; i < NUM_SENSORS; i++) {
        if (sensorValues[i] != 0) num_on_sensors++;
      }
      return num_on_sensors;
    }

    int getMaxIndex() {
      int max_index = 0;
      int max_val = sensorValues[0];
      for (int i = 1; i < NUM_SENSORS; i++) {
        if (sensorValues[i] > max_val) {
          max_val = sensorValues[i];
          max_index = i;
        }
      }
      return max_index;
    }

    int getBallAngle() {
      int max_index = getMaxIndex();
      int num_next_sensor = (NUM_SEARCH - 1) / 2;

      Vector ball_v = {0, 0};

      for (int i = 0; i < NUM_SEARCH; i++) {
        int index = (max_index - num_next_sensor + i + NUM_SENSORS) % NUM_SENSORS;  // %は負の値だとバグるから、NUM_SENSORS足して対策
        Vector sensor_v = makeV(sensorAngles[index], sensorValues[index]);
        ball_v = addV(ball_v, sensor_v);
      }
      if (ball_v.y * ball_v.y + ball_v.x * ball_v.x < NO_BALL_VALUE * NO_BALL_VALUE)  return 400;
      
      VectorRecord &vx = vx_record;
      total_vx -= vx.vectorRecords[vx.ave_index]; // 古いデータを削除
      total_vx += ball_v.x; //新データを追加
      vx.vectorRecords[vx.ave_index] = ball_v.x; // 新データを保存

      vx.ave_index = (vx.ave_index + 1) % NUM_ANGLE_AVE;


      VectorRecord &vy = vy_record;
      total_vy -= vy.vectorRecords[vy.ave_index]; // 古いデータを削除
      total_vy += ball_v.y; //新データを追加
      vy.vectorRecords[vy.ave_index] = ball_v.y; // 新データを保存

      vy.ave_index = (vy.ave_index + 1) % NUM_ANGLE_AVE;

      int angle = atan2((float)total_vy , (float)total_vx) * 180 / PI;
      angle += ANGLE_DIFF;
      angle = (angle + 360) % 360;
      return angle;
    }

    //   int k = getMaxIndex();
    //   if (sensorValues[k] < NO_BALL_VALUE)  return 400;
    //   int kL = (k - 1 + NUM_SENSORS) % NUM_SENSORS;
    //   int kR = (k + 1) % NUM_SENSORS;

    //   int SL = max(sensorValues[kL] * sensorValues[kL], (int)1);  // log(0)対策
    //   int S0 = max(sensorValues[k] * sensorValues[k], (int)1);
    //   int SR = max(sensorValues[kR] * sensorValues[kR], (int)1);

    //   float d = 0.5 * (log(SL) - log(SR)) / (log(SL) - 2*log(S0) + log(SR));
    //   if (!isfinite(d)) d = 0;  // 異常値対策

    //   float angle = sensorAngles[k] + d * 22.5;

    //   float sx = cos(angle * PI / 180.0);
    //   float sy = sin(angle * PI / 180.0);

    //   total_sx -= sx_record.vectorRecords[sx_record.ave_index]; // 古いデータを削除
    //   total_sx += sx; //新データを追加
    //   sx_record.vectorRecords[sx_record.ave_index] = sx; // 新データを保存

    //   sx_record.ave_index = (sx_record.ave_index + 1) % NUM_ANGLE_AVE;

    //   total_sy -= sy_record.vectorRecords[sy_record.ave_index]; // 古いデータを削除
    //   total_sy += sy; //新データを追加
    //   sy_record.vectorRecords[sy_record.ave_index] = sy; // 新データを保存

    //   sy_record.ave_index = (sy_record.ave_index + 1) % NUM_ANGLE_AVE;

    //   angle = atan2(total_sy,total_sx) * 180.0 / M_PI;

    //   angle += ANGLE_DIFF;
    //   angle = (int)(angle + 360) % 360;
    //   return angle;
    // }

    // int getBallDistance() {
    //   int num_search = 5;
    //   int k = 1000;

    //   int max_index = getMaxIndex();
    //   if (sensorValues[max_index] == 0) return 0;
    //   Vector max_v = makeV(sensorAngles[max_index], k / sqrt(sensorValues[max_index]));

    //   float dis_x = 0;
    //   float dis_y = 0;

    //   for (int i = 0; i < num_search; i++) {
    //     int this_index = (max_index - ((num_search - 1) / 2) + i + NUM_SENSORS) % NUM_SENSORS;
    //     float this_rad = sensorAngles[this_index] * M_PI / 180;
    //     int this_value = sensorValues[this_index];
    //     if (this_value == 0)  continue;
    //     // float x = max_v.x - (k / sqrt((this_value))) * cos(this_rad);
    //     // float y = max_v.y - (k / sqrt((this_value))) * sin(this_rad);
    //     float x = (k / sqrt((this_value))) * cos(this_rad);
    //     float y = (k / sqrt((this_value))) * sin(this_rad);

    //     dis_x += x;
    //     dis_y += y;
    //   }

    //   float dis = sqrt(dis_x * dis_x + dis_y * dis_y);
    //   return dis;

      // int max_index = getMaxIndex();
      // int num_next_sensor = (NUM_SEARCH - 1) / 2;

      // Vector ball_v = {0, 0};

      // for (int i = 0; i < NUM_SEARCH; i++) {
      //   int index = (max_index - num_next_sensor + i + NUM_SENSORS) % NUM_SENSORS;  // %は負の値だとバグるから、NUM_SENSORS足して対策
      //   Vector sensor_v = makeV(sensorAngles[index], sensorValues[index]);
      //   ball_v = addV(ball_v, sensor_v);
      // }
      // // if (ball_v.y * ball_v.y + ball_v.x * ball_v.x < NO_BALL_VALUE * NO_BALL_VALUE)  return 400;
      
      // VectorRecord &vx = vx_record;
      // total_vx -= vx.vectorRecords[vx.ave_index]; // 古いデータを削除
      // total_vx += ball_v.x; //新データを追加
      // vx.vectorRecords[vx.ave_index] = ball_v.x; // 新データを保存

      // vx.ave_index = (vx.ave_index + 1) % NUM_ANGLE_AVE;


      // VectorRecord &vy = vy_record;
      // total_vy -= vy.vectorRecords[vy.ave_index]; // 古いデータを削除
      // total_vy += ball_v.y; //新データを追加
      // vy.vectorRecords[vy.ave_index] = ball_v.y; // 新データを保存

      // vy.ave_index = (vy.ave_index + 1) % NUM_ANGLE_AVE;

      // int distance = sqrt((total_vx / NUM_ANGLE_AVE) * (total_vx / NUM_ANGLE_AVE) + (total_vy / NUM_ANGLE_AVE) * (total_vy / NUM_ANGLE_AVE));
      // return distance;
    // }
};

Ball ball;

void initIR() {

}

int ball_angle;
int ball_distance;

void IR() {
  readIR();
  ball.updateIR();
  ball_angle = ball.getBallAngle();
  ball_distance = ball.getBallDistance();
}