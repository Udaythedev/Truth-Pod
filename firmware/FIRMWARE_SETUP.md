# TruthPod Firmware Setup Guide

This guide explains how to flash and configure the ESP32 firmware for the TruthPod device.

## Hardware Requirements

### ESP32 Main Board
- **ESP32 DevKit** (38-pin version recommended)
- **ILI9341 TFT Display** (240x320 SPI)
- **I2S Microphone** (INMP441 or similar)
- **I2S Speaker/Amplifier** (MAX98357A or similar)
- **3x Push Buttons** (Voice, Next, Back)
- **RGB LED** (common cathode) or 3 separate LEDs
- **Power Supply** (5V 2A recommended)
- **Breadboard and jumper wires** (for prototyping)

### ESP32-CAM Board
- **ESP32-CAM** (AI-Thinker module with OV2640)
- **FTDI programmer** (for initial flashing)
- **Push button** (for capture/enroll)
- **5V power supply** (separate from main board)

## Software Requirements

### Arduino IDE Setup
1. Install [Arduino IDE](https://www.arduino.cc/en/software) (version 2.0 or later)
2. Add ESP32 board support:
   - Go to **File → Preferences**
   - Add to "Additional Board Manager URLs":
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Go to **Tools → Board → Boards Manager**
   - Search for "ESP32" and install "ESP32 by Espressif Systems"

3. Install required libraries (via **Tools → Manage Libraries**):
   - **TFT_eSPI** by Bodmer
   - **ArduinoJson** by Benoit Blanchon (version 6.x)
   - **ESP32 Arduino Core** (installed with board support)

### PlatformIO Setup (Alternative)
1. Install [Visual Studio Code](https://code.visualstudio.com/)
2. Install PlatformIO extension
3. Create new project for ESP32
4. Add dependencies to `platformio.ini`:
   ```ini
   [env:esp32dev]
   platform = espressif32
   board = esp32dev
   framework = arduino
   lib_deps = 
       bodmer/TFT_eSPI@^2.5.0
       bblanchon/ArduinoJson@^6.21.0
   monitor_speed = 115200
   ```

## Pin Configuration

### ESP32 Main Board Wiring

### TFT Display (ILI9341 - SPI)
| Display Pin | ESP32 Pin | Description |
|-------------|-----------|-------------|
| VCC | 3.3V (or module VCC) | Power (verify shield VCC requirement) |
| GND | GND | Ground |
| SCLK / SD_SCK | GPIO 18 | SPI Clock |
| MOSI / SD_DI | GPIO 23 | SPI MOSI (Data Out to display) |
| MISO / SD_DO | GPIO 19 | SPI MISO (optional; required if reading/SD card) |
| CS / SD_SS | GPIO 5 | Chip Select for the display (or SD card) |
| DC / RS | GPIO 21 | Data/Command select (D/C or RS) |
| RESET | GPIO 22 | Reset |
| RD | Tie to 3.3V (permanent HIGH = write-only) | Prevents display from driving the bus |
| LED/BL | Tied to rail (no exposed MCU pin) | Backlight — many shields tie BL to the module rail. To control brightness, wire BL to a transistor and set `TFT_BL` in `lgfx_user_settings.h` to that GPIO. |

#### I2S Microphone (INMP441)
| Mic Pin | ESP32 Pin | Description |
|---------|-----------|-------------|
| VDD | 3.3V | Power |
| GND | GND | Ground |
| SD (digital I2S) | GPIO 33 | Serial Data (I2S data in) - used for INMP441 digital mic |
| WS (digital I2S) | GPIO 25 | Word Select (L/R Clock) - used for INMP441 |
| SCK (digital I2S) | GPIO 26 | Serial Clock (BCLK) - used for INMP441 |

Analog electret mic (MAX4466) wiring (recommended for this build):
| MAX4466 Pin | ESP32 Pin | Notes |
|-------------|-----------|-------|
| VCC | 3.3V | Power the amplifier with 3.3V (check module docs) |
| GND | GND | Common ground |
| OUT | GPIO 34 (ADC1_CH6) | Connect amplifier output to ADC pin (input-only). Use external bias/pull if required. |

Notes:
- The firmware supports either a digital I2S microphone (INMP441) or an analog MAX4466. The default build uses the analog mic on GPIO34. If you use the INMP441, wire SD/WS/SCK as shown above.
- GPIO34 and GPIO35 are input-only ADC pins and do not support internal pull-ups. Use an external pull-up or bias network as needed.

#### I2S Speaker/Amplifier (MAX98357A)
| Speaker Pin | ESP32 Pin | Description |
|-------------|-----------|-------------|
| VIN | 5V | Power (amp supply) |
| GND | GND | Ground |
| DIN (I2S amp) | GPIO 12 | Serial Data (I2S data out) - used for MAX98357A |
| BCLK (I2S amp) | GPIO 14 | Bit Clock |
| LRC (I2S amp) | GPIO 27 | Left/Right Clock (WS) |

LM386 analog amplifier wiring (recommended alternative):
| LM386 Pin | ESP32 Pin | Notes |
|-----------|-----------|-------|
| VCC | 5V | Power amplifier (provide stable 5V) |
| GND | GND | Common ground with ESP32 |
| IN | GPIO 25 (DAC1) | Connect ESP32 DAC output to LM386 input via a 10uF coupling capacitor and a series resistor (~100Ω) |

Notes:
- The firmware can output audio via I2S to an I2S amplifier (MAX98357A) or use the ESP32 built-in DAC to drive an LM386. The default build uses LM386 on GPIO25 (DAC1). Use a coupling capacitor and ensure LM386 gain is set appropriately.

#### Buttons
| Button | ESP32 Pin | Description |
|--------|-----------|-------------|
| Voice | GPIO 33 | Voice capture/play button |
| Next | GPIO 33 | Next article button |
| Back | GPIO 32 | Previous article button |

**Note**: Some revisions change the default voice/next pin assignments. Current firmware uses:
| Voice | GPIO 13 | Voice capture/play button |
| Next  | GPIO 33 | Next article button |
| Back  | GPIO 32 | Previous article button |

**Note**: Connect buttons between GPIO pin and GND (with internal pull-up resistors).

#### RGB LED
| LED Pin | ESP32 Pin | Description |
|---------|-----------|-------------|
| Red | GPIO 2 | Red LED (or cathode) |
| Green | GPIO 21 | Green LED |
| Blue | GPIO 4 | Blue LED |
| Common | 3.3V (or GND depending on common anode/cathode) | Wiring depends on LED type; use 220Ω resistors on each LED leg |

Notes:
- The firmware supports both common-cathode (normal) and common-anode (inverted) LED wiring. At runtime you can set the wiring mode via the device web server: `http://<device_ip>/led_set?invert=1` to enable inverted (common-anode) mode, or `?invert=0` for normal. The choice is persisted in device preferences.
- If your RGB LED does not light in the expected polarity during boot diagnostics, try flipping the polarity using the endpoint above.
#### UART to ESP32-CAM
| Main Board | ESP32-CAM | Description |
|------------|-----------|-------------|
| GPIO 16 (RX) | GPIO 1 (TX) | Receive from camera (Main RX <- CAM TX) |
| GPIO 17 (TX) | GPIO 3 (RX) | Send to camera (Main TX -> CAM RX) |
| GND | GND | Common ground |

### ESP32-CAM Wiring

The ESP32-CAM module has most components built-in. Only need to connect:

#### Camera Module
- **OV2640 camera** is built-in and connected

#### External Connections
| Function | GPIO Pin | Connection |
|----------|----------|------------|
| Flash Button | GPIO 13 | Built-in or external button to GND |
| Flash LED | GPIO 4 | Built-in flash LED |
| Status LED | GPIO 33 | Optional external LED + 220Ω resistor |
| UART TX | GPIO 1 | To main board RX (GPIO 19) |
| UART RX | GPIO 3 | To main board TX (GPIO 23) |

#### Power
- **5V** and **GND** from external power supply (ESP32-CAM requires stable 5V)
- Do NOT power from USB alone during WiFi/camera operations

## TFT_eSPI Configuration

The TFT_eSPI library requires configuration for your specific display.

1. Locate the library folder:
   - **Windows**: `Documents\Arduino\libraries\TFT_eSPI\`
   - **Mac/Linux**: `~/Arduino/libraries/TFT_eSPI/`

2. Edit `User_Setup.h` or create `User_Setup_Select.h`:

```cpp
// Uncomment only one display driver
#define ILI9341_DRIVER

// ESP32 pin configuration
#define TFT_MISO 19
#define TFT_MOSI 23
#define TFT_SCLK 18
#define TFT_CS   15
#define TFT_DC    2
#define TFT_RST   4

// Fonts (enable as needed)
#define LOAD_GLCD
#define LOAD_FONT2
#define LOAD_FONT4
#define LOAD_FONT6
#define LOAD_FONT7
#define LOAD_FONT8

#define SMOOTH_FONT

// SPI frequency
#define SPI_FREQUENCY  27000000
#define SPI_READ_FREQUENCY  20000000
```

## Flashing Instructions

### Flashing ESP32 Main Board

1. **Connect ESP32 to computer** via USB

2. **Open firmware** in Arduino IDE:
   - Open `firmware/esp32_main/esp32_main.ino`

3. **Configure WiFi and API**:
   ```cpp
   const char* WIFI_SSID = "YourWiFiName";
   const char* WIFI_PASSWORD = "YourWiFiPassword";
   const char* API_BASE_URL = "https://your-backend.onrender.com";
   ```

4. **Select board and port**:
   - **Tools → Board → ESP32 Arduino → ESP32 Dev Module**
   - **Tools → Port → [Select COM port]**

5. **Configure upload settings**:
   - Upload Speed: 921600
   - Flash Frequency: 80MHz
   - Flash Mode: QIO
   - Flash Size: 4MB (32Mb)
   - Partition Scheme: Default 4MB with spiffs

6. **Upload sketch**:
   - Click **Upload** button or press Ctrl+U
   - Wait for "Done uploading" message

7. **Monitor Serial output**:
   - **Tools → Serial Monitor**
   - Set baud rate to **115200**
   - You should see startup messages and WiFi connection status

### Flashing ESP32-CAM

ESP32-CAM doesn't have built-in USB, so you need an FTDI programmer.

1. **Connect FTDI to ESP32-CAM**:
   ```
   FTDI      ESP32-CAM
   -----     ---------
   GND   →   GND
   5V    →   5V
   TX    →   RX (GPIO 3)
   RX    →   TX (GPIO 1)
   ```

2. **Enter programming mode**:
   - Connect **GPIO 0** to **GND**
   - Press **Reset** button
   - This puts ESP32-CAM in flash mode

3. **Open firmware** in Arduino IDE:
   - Open `firmware/esp32_cam/esp32_cam.ino`

4. **Configure WiFi and API**:
   ```cpp
   const char* WIFI_SSID = "YourWiFiName";
   const char* WIFI_PASSWORD = "YourWiFiPassword";
   const char* API_BASE_URL = "https://your-backend.onrender.com";
   ```

5. **Select board and port**:
   - **Tools → Board → AI Thinker ESP32-CAM**
   - **Tools → Port → [Select COM port]**

6. **Configure upload settings**:
   - Upload Speed: 921600
   - Flash Frequency: 80MHz
   - Flash Mode: QIO
   - Flash Size: 4MB (32Mb)
   - Partition Scheme: Huge APP (3MB No OTA)

7. **Upload sketch**:
   - Click **Upload**
   - Wait for upload to complete

8. **Exit programming mode**:
   - Disconnect **GPIO 0** from **GND**
   - Press **Reset** button
   - Open Serial Monitor (115200 baud) to verify boot

## Configuration

### API Endpoint Configuration

Both firmware files need to be configured with your backend URL:

```cpp
// For production (deployed to Render)
const char* API_BASE_URL = "https://your-backend.onrender.com";

// For local testing
// const char* API_BASE_URL = "http://192.168.1.100:8000";
```

Replace `your-backend.onrender.com` with your actual backend URL.

### WiFi Credentials

Update WiFi credentials in both files:

```cpp
const char* WIFI_SSID = "YourNetworkName";
const char* WIFI_PASSWORD = "YourNetworkPassword";
```

**Security Note**: For production, consider using WiFiManager library to configure WiFi via AP mode instead of hardcoding credentials.

## Testing

### Testing ESP32 Main Board

1. **Power on** the device
2. **Watch Serial Monitor** (115200 baud):
   - Should connect to WiFi
   - Register with backend
   - Load trending news
   - Display first article on screen

3. **Test buttons**:
   - **Voice**: Should play TTS audio of current article
   - **Next**: Navigate to next article
   - **Back**: Navigate to previous article

4. **Test voice recording** (hold Voice button for 2+ seconds):
   - LED should turn red
   - Record for 5 seconds
   - Send to backend for transcription
   - Search news based on query

### Testing ESP32-CAM

1. **Power on** the device
2. **Watch Serial Monitor** (115200 baud):
   - Should connect to WiFi
   - Initialize camera
   - Wait for button press

3. **Test face recognition**:
   - **Short press** (<3 sec): Capture and recognize
   - LED flashes during capture
   - Check Serial Monitor for results
   - Main board should receive USER_ID message

4. **Test face enrollment**:
   - **Long press** (>3 sec): Enroll mode
   - LED blinks twice
   - Enter user name in Serial Monitor
   - Camera captures and sends to backend

## Troubleshooting

### ESP32 Main Board Issues

**Problem**: WiFi won't connect
- Check SSID and password are correct
- Verify WiFi is 2.4GHz (ESP32 doesn't support 5GHz)
- Try closer to router
- Check Serial Monitor for error messages

**Problem**: Display shows nothing
- Verify TFT_eSPI configuration matches your display
- Check wiring connections
- Test with TFT_eSPI example sketches
- Verify power supply is adequate (5V 2A)

**Problem**: No audio playback
- Check I2S speaker wiring
- Verify power to amplifier (5V for MAX98357A)
- Test with I2S example sketches
- Check volume (some amps have gain pins)

**Problem**: API calls fail
- Verify backend URL is correct
- Check backend is deployed and running
- Test backend health endpoint in browser: `{URL}/api/health`
- Check device token is saved (see Serial Monitor)

### ESP32-CAM Issues

**Problem**: Camera init failed
- Check camera module is seated properly
- Verify power supply is stable 5V (>500mA)
- Try re-seating camera ribbon cable
- Check for error code in Serial Monitor

**Problem**: Can't upload sketch
- Ensure GPIO 0 is connected to GND during upload
- Try lower upload speed (115200)
- Press Reset button before uploading
- Check FTDI connections (TX→RX, RX→TX)

**Problem**: Face recognition fails
- Check backend API is running
- Verify lighting conditions (avoid strong backlight)
- Ensure face is within 0.5-2 meters from camera
- Check image quality in Serial Monitor

**Problem**: UART communication not working
- Verify RX/TX crossover (Main TX → CAM RX, Main RX → CAM TX)
- Check common ground connection
- Verify baud rate matches (115200)
- Test with Serial Monitor on both devices

## Advanced Configuration

### Power Optimization

Add deep sleep for battery operation:

```cpp
// After displaying news
esp_sleep_enable_timer_wakeup(60 * 1000000);  // 60 seconds
esp_deep_sleep_start();
```

### OTA Updates

Enable Over-The-Air updates:

```cpp
#include <ArduinoOTA.h>

void setupOTA() {
  ArduinoOTA.setHostname("truthpod");
  ArduinoOTA.setPassword("your-ota-password");
  ArduinoOTA.begin();
}

void loop() {
  ArduinoOTA.handle();
  // ... rest of loop code
}
```

### Custom Display Themes

Modify colors in `displayNewsArticle()`:

```cpp
// For dark theme
tft.fillScreen(TFT_BLACK);
tft.setTextColor(TFT_WHITE, TFT_BLACK);

// For light theme
tft.fillScreen(TFT_WHITE);
tft.setTextColor(TFT_BLACK, TFT_WHITE);
```

### Audio Quality Settings

Adjust sample rate for quality vs. bandwidth:

```cpp
// Higher quality (more bandwidth)
const int SAMPLE_RATE = 22050;

// Lower bandwidth (lower quality)
const int SAMPLE_RATE = 8000;
```

## Production Considerations

1. **Use WiFiManager** for user-friendly WiFi setup
2. **Implement token rotation** handling from backend
3. **Add error recovery** and watchdog timers
4. **Enable OTA updates** for remote firmware updates
5. **Add local caching** for offline resilience
6. **Implement power management** for battery operation
7. **Add user settings** (brightness, volume, language)
8. **Secure credentials** (use ESP32 NVS encryption)

## Support

For issues or questions:
- Check project documentation: `TruthPod-Complete-Project-Document-V2.md`
- Review backend status: `BACKEND_STATUS.md`
- Check API documentation: `DEVICE_API.md`
- ESP32 Arduino Core: https://github.com/espressif/arduino-esp32
- TFT_eSPI Library: https://github.com/Bodmer/TFT_eSPI
