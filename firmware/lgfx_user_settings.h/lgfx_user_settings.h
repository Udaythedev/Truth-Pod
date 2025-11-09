#pragma once

// Default: SPI mode for the ILI9341 panel. Parallel mode is commented out.
// SPI uses fewer MCU pins and avoids conflicts with I2S/UART.

// --- Display geometry ---
#define LCD_WIDTH      240
#define LCD_HEIGHT     320

// --- SPI pin configuration for ILI9341 ---
// Use the shield SD header for MOSI/SCLK when available
#define TFT_MOSI  23
#define TFT_SCLK  18
#define TFT_CS    5
#define TFT_DC    21   // (RS / D/C)
#define TFT_RST   22

// Backlight: set to -1 if BL is tied to the board rail (no MCU control)
#ifndef TFT_BL
#define TFT_BL   -1
#endif

// RD is tied to 3.3V (write-only). Keep as -1 so driver does not attempt to toggle it.
#ifndef TFT_RD
#define TFT_RD  -1
#endif

// --- Parallel configuration (legacy) ---
/*
If you need to use the parallel 8-bit bus, uncomment LGFX_USE_PARALLEL and
edit the pin mappings below. Parallel mode uses many GPIOs and frequently
conflicts with I2S, UART, or other peripherals on the ESP32. We recommend
keeping SPI mode for most builds.

// #define LGFX_USE_PARALLEL

#define TFT_D0  16
#define TFT_D1  17
#define TFT_D2  18
#define TFT_D3  19
#define TFT_D4  21
#define TFT_D5  22
#define TFT_D6  23
#define TFT_D7  25

#define TFT_WR  33
// TFT_RD should be tied to 3.3V when using write-only operation
// #define TFT_RD  -1

// Backlight and control pins for parallel mode (example)
// #define TFT_BL -1
// #define TFT_RS  32   // (DC pin)
// #define TFT_CS  27
// #define TFT_RST 26

*/

// Panel selection (keep as ILI9341)
#define LGFX_PANEL_ILI9341

// NOTE: If you switch modes, update `firmware/lgfx_setup.h` accordingly and
// ensure no pin conflicts with I2S, UART or other peripherals.
#define LGFX_PANEL_ILI9341
