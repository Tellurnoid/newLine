struct Vector {
  float x;
  float y;
};

Vector makeV(float deg, float speed) {  //角度と速さからベクトルを作る
  Vector v;
  float rad = deg * M_PI / 180.0;
  v.x = cos(rad) * speed;
  v.y = sin(rad) * speed;
  return v;
}

// float getCom(Vector v, float deg) {
//   float rad = deg * PI / 180.0f;
//   return v.x * cos(rad) + v.y * sin(rad);
// }


Vector addV(Vector a, Vector b) {  //ベクトルの足し算
  Vector result;
  result.x = a.x + b.x;
  result.y = a.y + b.y;
  return result;
}

Vector assembleV(Vector a, Vector b, int16_t max_len) { // a > bの優先度
  float a_len = sqrt(a.x * a.x + a.y * a.y);

  float rest_len = max_len - a_len;

  float b_len = sqrt(b.x * b.x + b.y * b.y);
}

Vector normalizeV(Vector v) { // 正規化（単位ベクトル化）
  float len = sqrt(v.x * v.x + v.y * v.y);
  if (len == 0) return {0, 0};
  return { v.x / len, v.y / len };
}

Vector changeLenV(Vector v, int len_v) {  // 正規化（単位ベクトル化）
  float len = sqrt(v.x * v.x + v.y * v.y);
  if (len == 0) return {0, 0};
  return { v.x / len * len_v, v.y / len * len_v };
}

float lenV(Vector v, int deg) { // vのdeg方向のベクトルの大きさを調べる
  float rad = deg * PI / 180.0f;
  float dir_x = cos(rad);
  float dir_y = sin(rad);

  float result = v.x * dir_x + v.y * dir_y;
  return result;
}

int angleDiff(int a, int b) {
  int d = a - b;
  while (d > 180) d -= 360;
  while (d < -180) d += 360;
  return d;
}

// -180〜180 に正規化
float wrap180(float angle) {
  angle = fmod(angle + 180.0, 360.0);
  if (angle < 0) angle += 360.0;
  return angle - 180.0;
}

// 0〜360 に正規化
float wrap360(float angle) {
  angle = fmod(angle, 360.0);
  if (angle < 0) angle += 360.0;
  return angle;
}

// 元 → 変換後
float convertAngle(float theta) {
  return wrap180(90.0 - theta);
}

// 逆変換
float reverseAngle(float theta_p) {
  return wrap360(90.0 - theta_p);
}