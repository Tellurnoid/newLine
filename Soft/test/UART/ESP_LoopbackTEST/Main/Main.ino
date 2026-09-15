void setup() {
    Serial.begin(115200);
    Serial2.begin(115200, SERIAL_8N1, 16, 17);
}
void loop() {
    Serial2.write(0xAA);
    delay(100);
    while (Serial2.available()) {
        Serial.printf("loopback: 0x%02X\n", Serial2.read());
    }
}