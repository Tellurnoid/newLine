#pragma once

void initLINE();
void LINE();
void calibrateLINE();

// constexpr int NUM_LINE_SENSORS = 32;
extern int16_t minValue[32];
extern int16_t maxValue[32];

extern int16_t line_angle;
extern int16_t line_distance;