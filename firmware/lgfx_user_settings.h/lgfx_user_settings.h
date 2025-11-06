  #pragma once
#define LGFX_USE_PARALLEL    // Enable parallel bus mode (disable if using SPI)

// Pin configuration for parallel ILI9341 shield
#define LCD_WIDTH      240
#define LCD_HEIGHT     320

#define TFT_D0  16
#define TFT_D1  17
#define TFT_D2  18
#define TFT_D3  19
#define TFT_D4  21
#define TFT_D5  22
#define TFT_D6  23
#define TFT_D7  25

#define TFT_WR  33
#define TFT_RD  -1   // Tie RD to 3.3V
#define TFT_RS  32   // (DC pin)
#define TFT_CS  27
#define TFT_RST 26

// Setup for ILI9341 parallel
#define LGFX_PARALLEL_I8080
#define LGFX_PANEL_ILI9341

// NOTE: The parallel pin assignments below may conflict with other peripherals
// (I2S, UART, buttons). If you observe pin conflicts, either remap the TFT
// pins here or switch LGFX to use SPI mode instead (comment out LGFX_USE_PARALLEL
// and configure SPI pins). Review `firmware/esp32_main/esp32_main.ino` for other
// component pin assignments and choose non-overlapping GPIOs.
