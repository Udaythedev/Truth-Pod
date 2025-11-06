// LovyanGFX setup wrapper for parallel ILI9341
#pragma once
#include <LovyanGFX.hpp>
// lgfx_user_settings.h is stored in a subdirectory (lgfx_user_settings.h/lgfx_user_settings.h)
// so include it via the relative subpath so the Arduino/PlatformIO compiler can find it.
#include "lgfx_user_settings.h/lgfx_user_settings.h"

class LGFX : public lgfx::LGFX_Device {
public:
  lgfx::Bus_Parallel8 _bus_instance;
  lgfx::Panel_ILI9341 _panel_instance;

  LGFX() {
    // Configure parallel bus pins from lgfx_user_settings.h
    {
      auto cfg = _bus_instance.config();
      cfg.pin_wr = TFT_WR;
      cfg.pin_rs = TFT_RS;
      cfg.pin_rd = TFT_RD;
      cfg.pin_cs = TFT_CS;
      cfg.pin_rst = TFT_RST;
      cfg.pin_d0 = TFT_D0;
      cfg.pin_d1 = TFT_D1;
      cfg.pin_d2 = TFT_D2;
      cfg.pin_d3 = TFT_D3;
      cfg.pin_d4 = TFT_D4;
      cfg.pin_d5 = TFT_D5;
      cfg.pin_d6 = TFT_D6;
      cfg.pin_d7 = TFT_D7;
      // keep default bus frequency; adjust if needed
      cfg.freq_write = 20000000;
      _bus_instance.config(cfg);
    }

    // Configure panel
    {
      auto pcfg = _panel_instance.config();
      pcfg.pin_cs = TFT_CS;
      pcfg.pin_rst = TFT_RST;
      pcfg.pin_busy = -1;
      pcfg.panel_width = LCD_WIDTH;
      pcfg.panel_height = LCD_HEIGHT;
      // attach bus to panel
      _panel_instance.config(pcfg);
    }

    _panel_instance.setBus(&_bus_instance);
    setPanel(&_panel_instance);
  }
};

// instantiate
LGFX tft;
