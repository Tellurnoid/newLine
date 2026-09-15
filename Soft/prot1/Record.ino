#include "Record.h"

void Record::initRecord(){
  if (!EEPROM.begin(256)) {
    Serial.println("LINE EEPROM init failed");
  }
}

void Record::getLineRecord(){
  EEPROM.get(LINE_ADDRESS, line_record);
  for(int i = 0; i < 32; i++){
    minValue[i] = line_record.RomMinValue[i];
    maxValue[i] = line_record.RomMaxValue[i];
  }
}

void Record::recordLine(){
  // キャリブレーション後の値を line_record にコピー
  for(int i = 0; i < 32; i++){
    line_record.RomMinValue[i] = minValue[i];
    line_record.RomMaxValue[i] = maxValue[i];
  }

  // EEPROM に保存
  EEPROM.put(LINE_ADDRESS, line_record);
  EEPROM.commit(); 
}
