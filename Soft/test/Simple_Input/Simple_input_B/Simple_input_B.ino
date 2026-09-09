int pin[21] = {-1 ,-1, -1, 14, 15, 26, 27, 9, 10, 1, 0,//0~10
                   11, 13, 12,  8,  4,  7, 3,  6, 2, 5//11~20
              };//-1になっている0,1,2はpicoAに接続
// int pin[33] = {
//   -1, 7, 8, -1, -1, -1, -1, -1, -1, -1, -1,//0~10
//   -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, //11~20
//   26, 15, 14, 9, 3, 10, 13, 4, 11, 12, //21~30
//   5, 6//31~32 
// };


#define conpPWM 2
void setup(){
  for (int i=0; i<22; i++){
    if(pin[i]!=-1){
      pinMode(pin[i], INPUT);
    }
  }
//  pinMode(conpPWM, OUTPUT);
//  analogWriteFreq(1000);   // 周波数はグローバル設定(全ピン共通)
//  analogWriteRange(255);   // Duty比の分解能も共通設定

  Serial.begin(115200);
}

char data = 0;
void loop(){
  if(Serial.available() > 0){
    data = Serial.read();
  }

  //analogWrite(conpPWM, 0);
  for(int i=0;i<22;i++){
    if(pin[i]!=-1){
      Serial.print(digitalRead(pin[i]));Serial.print(",");
    }
  }
  Serial.println();
}