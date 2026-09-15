// ============================================================
//  Raspberry Pi Pico 2 W 
// ============================================================
#include <Arduino.h>
// #include <SerialPIO.h>
// SerialPIO PIOSerial1(0, 1); 

// void setup(){
//     PIOSerial1.begin(9600);
//     Serial.begin(115200);
// }
// char data;
// void loop(){
//     if(PIOSerial1.available()){
//         data = PIOSerial1.read();
//         Serial.println(data);
//     }
//     PIOSerial1.write('a');
// }



// void setup(){
//   Serial.begin(115200);
// }
// void loop(){
//   Serial.println("NEW_CODE_TEST_v2 " + String(millis()));
//   delay(500);
// }


// #include <Adafruit_NeoPixel.h>

// #define PIN        12   // XIAO RP2040のRGB LEDピン
// #define POWER_PIN  11   // RGB LED電源制御ピン
// #define NUMPIXELS  1

// Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

// void setup() {
//   pinMode(POWER_PIN, OUTPUT);
//   digitalWrite(POWER_PIN, HIGH);  // LEDに電源供給

//   pixels.begin();
//   pixels.setBrightness(50);  // 明るさ調整(0〜255)
// }

// void loop() {
//   pixels.setPixelColor(0, pixels.Color(255, 0, 0)); // 赤
//   pixels.show();
//   delay(500);

//   pixels.setPixelColor(0, pixels.Color(0, 255, 0)); // 緑
//   pixels.show();
//   delay(500);

//   pixels.setPixelColor(0, pixels.Color(0, 0, 255)); // 青
//   pixels.show();
//   delay(500);
// }