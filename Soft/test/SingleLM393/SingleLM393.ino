
#define in19 2    //2
#define in20 5//5

#define conpPWM 29

void setup(){
  pinMode(in19, INPUT);
  pinMode(in20, INPUT);
  pinMode(conpPWM, OUTPUT);
  analogWriteFreq(1000);   // 周波数はグローバル設定(全ピン共通)
  analogWriteRange(255);   // Duty比の分解能も共通設定

  Serial.begin(115200);
}

char data = 1;
void loop(){
  if(Serial.available() > 0){
    data = Serial.read();
  }
  analogWrite(conpPWM, data * 30);
  Serial.print(digitalRead(in19));Serial.print(",");Serial.print(digitalRead(in20));
  Serial.println();
}