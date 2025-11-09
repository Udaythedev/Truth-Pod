/*
  Minimal TFT hardware test using LovyanGFX
  - Uses the project's lgfx_user_settings.h for pin mapping
  - Runs a color-fill cycle at slow SPI speed to help detect timing/wiring issues
*/
#include <Arduino.h>
#include "../lgfx_setup.h"

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("TFT Test: Starting");
  Serial.print("TFT WIDTH: "); Serial.println(tft.width());
  Serial.print("TFT HEIGHT: "); Serial.println(tft.height());

  // Try slow writes to improve compatibility
  // The LGFX instance already configures the bus; just run a visible test
  for (int i = 0; i < 3; ++i) {
    tft.fillScreen(TFT_RED);
    delay(500);
    tft.fillScreen(TFT_GREEN);
    delay(500);
    tft.fillScreen(TFT_BLUE);
    delay(500);
  }

  tft.fillScreen(TFT_BLACK);
  tft.setTextSize(2);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setCursor(10, 10);
  tft.println("TFT Test Complete");
}

void loop() {
  // nothing - visual check only
}
