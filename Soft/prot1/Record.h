#pragma once

#include <Arduino.h>
#include <EEPROM.h>
#include "LINE.h"

class Record {
  private:

    struct LineRecord {
      int16_t RomMinValue[32];
      int16_t RomMaxValue[32];
    };

    //Configの部分を使用するstructの名前に置き換える///////////////////////
    static constexpr uint16_t LINE_SIZE = sizeof(LineRecord) + 16;
    //データの位置。struct一つの場合は0固定 二つ目以降は、前のデータ数+1にする
    static constexpr uint8_t LINE_ADDRESS = 0;

  public:
    LineRecord line_record;

    void initRecord();
    void getLineRecord();
    void recordLine();
};
