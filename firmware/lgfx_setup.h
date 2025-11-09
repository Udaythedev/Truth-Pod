// LovyanGFX setup wrapper for SPI ILI9341
#pragma once
#include <LovyanGFX.hpp>
// lgfx_user_settings.h is stored in a subdirectory so include via subpath
#include "lgfx_user_settings.h/lgfx_user_settings.h"

class LGFX : public lgfx::LGFX_Device {
public:
  lgfx::Bus_SPI _bus_instance;
  lgfx::Panel_ILI9341 _panel_instance;

  LGFX() {
    // Configure SPI bus pins from lgfx_user_settings.h
    {
      auto cfg = _bus_instance.config();
      cfg.spi_host = HSPI_HOST; // use HSPI
  // Lower SPI frequency to improve compatibility on some shields/modules
  // Try an even slower clock for problematic modules that show garbled output
  cfg.freq_write = 10000000; // 10 MHz (try this if display shows garbage)
  cfg.freq_read = 16000000;
      cfg.spi_mode = 0;
      cfg.spi_3wire = false;
      cfg.use_lock = true;
      cfg.dma_channel = 1;
      cfg.pin_sclk = TFT_SCLK;
      cfg.pin_mosi = TFT_MOSI;
      cfg.pin_miso = -1; // not used for write-only display
      _bus_instance.config(cfg);
    }

    // Configure panel
    {
      auto pcfg = _panel_instance.config();
      pcfg.pin_cs  = TFT_CS;
      pcfg.pin_rst = TFT_RST;
      // Note: some LovyanGFX releases name the D/C pin differently in the
      // panel config struct. If your library version exposes a pin for D/C
      // (often named pin_dcx or pin_dc), add the assignment here. Leaving
      // it unset will rely on the bus/panel defaults in your LovyanGFX build.
      // pcfg.pin_dcx = TFT_DC; // DC (data/command)  // uncomment if available
      pcfg.pin_busy = -1;
      pcfg.panel_width = LCD_WIDTH;
      pcfg.panel_height = LCD_HEIGHT;
      // Backlight pin may not exist in all versions of the panel config.
      // pcfg.pin_bl = TFT_BL; // uncomment if available in your LovyanGFX
      pcfg.readable = false;
      pcfg.bus_shared = false;
      _panel_instance.config(pcfg);
    }

    _panel_instance.setBus(&_bus_instance);
    setPanel(&_panel_instance);
  }
};

// instantiate
LGFX tft;
