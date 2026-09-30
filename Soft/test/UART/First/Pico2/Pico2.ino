// ============================================================
//  Raspberry Pi Pico 2 W 
// ============================================================
#include <Arduino.h>
#include <SerialPIO.h>
SerialPIO PIOSerial1(28, 29); // Motor

void setup(){
    PIOSerial1.begin(9600);
    Serial.begin(115200);
}
char data;
void loop(){
    if(PIOSerial1.available()){
        data = PIOSerial1.read();
        Serial.println(data);
    }
    PIOSerial1.write('a');
}

