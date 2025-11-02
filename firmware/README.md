# TruthPod Firmware

This directory contains the firmware for TruthPod's ESP32-based hardware.

## Contents

- **`esp32_main/`** - Main board firmware (ESP32 DevKit)
  - WiFi connection and device management
  - Voice recording and transcription
  - News fetching and display
  - TTS audio playback
  - Button handling and LED control
  - UART communication with camera module

- **`esp32_cam/`** - Camera module firmware (ESP32-CAM)
  - Camera initialization and image capture
  - Face recognition and enrollment
  - UART communication with main board
  - LED status indicators

## Quick Start

1. **Install Arduino IDE** with ESP32 support
2. **Install libraries**: TFT_eSPI, ArduinoJson
3. **Configure** WiFi and API URL in both `.ino` files
4. **Wire hardware** according to pin diagrams
5. **Flash firmware** to both boards
6. **Test** functionality via Serial Monitor

See **[QUICK_START.md](QUICK_START.md)** for step-by-step instructions.

## Documentation

- **[FIRMWARE_SETUP.md](FIRMWARE_SETUP.md)** - Complete setup guide with detailed wiring, configuration, and troubleshooting
- **[QUICK_START.md](QUICK_START.md)** - Quick reference card for rapid deployment
- **[../DEVICE_API.md](../DEVICE_API.md)** - Backend API endpoints reference
- **[../backend/API_KEYS.md](../backend/API_KEYS.md)** - API key configuration guide

## Features

### ESP32 Main Board
✅ Cloud-first stateless architecture  
✅ WiFi connectivity with auto-reconnect  
✅ Device registration with JWT authentication  
✅ I2S voice recording (16kHz, 16-bit)  
✅ Speech-to-text with backend integration  
✅ News fetching (trending and search)  
✅ TFT display with color-coded confidence scores  
✅ TTS audio playback via I2S speaker  
✅ Button navigation (Voice, Next, Back)  
✅ RGB LED indicators (Green/Yellow/Red)  
✅ UART communication with camera module  

### ESP32-CAM
✅ OV2640 camera initialization  
✅ JPEG image capture (QVGA 320x240)  
✅ Face recognition via backend API  
✅ Face enrollment with user names  
✅ UART communication with main board  
✅ LED status indicators  
✅ Button-triggered capture  
✅ Dual-mode operation (recognize/enroll)  

## Hardware Requirements

### Main Board Components
- ESP32 DevKit (38-pin)
- ILI9341 TFT Display (2.8" or 3.2")
- INMP441 I2S Microphone
- MAX98357A I2S Amplifier + Speaker (4Ω 3W)
- 3x Push Buttons
- RGB LED (common anode) or 3 separate LEDs
- Resistors: 3x 220Ω (for LEDs)
- Breadboard and jumper wires
- 5V 2A Power Supply

### Camera Module
- ESP32-CAM (AI-Thinker)
- OV2640 Camera (included)
- FTDI Programmer (for initial flashing)
- Push Button (optional - use built-in)
- 5V Power Supply (>500mA)

## Pin Configuration Summary

### ESP32 Main Board

**Display (SPI):** CS=15, DC=2, RST=4, MOSI=23, CLK=18, MISO=19  
**Microphone (I2S):** SD=33, WS=25, SCK=26  
**Speaker (I2S):** DIN=12, BCLK=14, LRC=27  
**Buttons:** Voice=34, Next=35, Back=32  
**LEDs:** Red=16, Green=17, Blue=18  
**UART:** TX=23, RX=19  

### ESP32-CAM

**Camera:** Built-in pins (see code for OV2640 configuration)  
**Button:** GPIO 13 (built-in flash button)  
**Flash LED:** GPIO 4 (built-in)  
**Status LED:** GPIO 33 (optional external)  
**UART:** TX=1, RX=3  

See [FIRMWARE_SETUP.md](FIRMWARE_SETUP.md) for detailed wiring diagrams.

## Configuration

### 1. WiFi Credentials

Edit both `esp32_main.ino` and `esp32_cam.ino`:

```cpp
const char* WIFI_SSID = "YourWiFiName";
const char* WIFI_PASSWORD = "YourWiFiPassword";
```

### 2. Backend URL

```cpp
// For production (Render deployment)
const char* API_BASE_URL = "https://your-backend.onrender.com";

// For local testing
// const char* API_BASE_URL = "http://192.168.1.100:8000";
```

### 3. TFT_eSPI Library

Edit `Arduino/libraries/TFT_eSPI/User_Setup.h`:

```cpp
#define ILI9341_DRIVER
#define TFT_MISO 19
#define TFT_MOSI 23
#define TFT_SCLK 18
#define TFT_CS   15
#define TFT_DC    2
#define TFT_RST   4
```

## Testing

### Serial Monitor Output

**Main Board (115200 baud):**
```
=== TruthPod Starting ===
Device MAC: XX:XX:XX:XX:XX:XX
Connecting to WiFi...
WiFi connected!
Device registered successfully!
Loading news...
Parsed 10 articles
```

**ESP32-CAM (115200 baud):**
```
=== TruthPod ESP32-CAM Starting ===
Camera MAC: XX:XX:XX:XX:XX:XX
Camera initialized successfully!
WiFi connected!
ESP32-CAM ready!
Press button to capture and recognize face
```

### Functional Tests

1. **Display Test**: Should show TruthPod logo and news articles
2. **Button Test**: Next/Back buttons should navigate articles
3. **Voice Test**: Press Voice button to hear article audio
4. **LED Test**: Color should match article confidence (Green/Yellow/Red)
5. **Camera Test**: Short press = recognize, Long press = enroll
6. **UART Test**: Camera should send USER_ID to main board

## Troubleshooting

### Compilation Errors

**"TFT_eSPI.h: No such file"**
- Install TFT_eSPI library via Library Manager

**"ArduinoJson.h: No such file"**
- Install ArduinoJson library (version 6.x)

**"base64.h: No such file"**
- This is built into ESP32 Arduino Core
- Try: `#include <mbedtls/base64.h>` if needed

### Runtime Issues

**WiFi won't connect**
- Verify SSID/password
- Ensure 2.4GHz network (ESP32 doesn't support 5GHz)
- Check signal strength

**Display blank**
- Check TFT_eSPI configuration
- Verify all SPI wiring
- Test with TFT_eSPI examples first

**No audio**
- Check I2S amp has 5V power
- Verify speaker polarity
- Test with tone generator sketch

**Camera fails**
- ESP32-CAM needs stable 5V supply (>500mA)
- Don't power from USB during WiFi operations
- Re-seat camera ribbon cable

**API calls fail**
- Check backend is deployed and running
- Test: `curl https://your-backend.onrender.com/api/health`
- Verify device is registered (check Serial Monitor)

## Development

### Adding New Features

1. **Custom news categories**: Modify `fetchTrendingNews()` endpoint
2. **Personalization**: Use user preferences from backend
3. **Offline mode**: Cache news articles locally
4. **Voice commands**: Add keyword detection before recording
5. **Display themes**: Customize colors in `displayNewsArticle()`

### Debugging

Enable verbose logging:

```cpp
// Add at top of file
#define DEBUG_MODE 1

// Use throughout code
#ifdef DEBUG_MODE
  Serial.println("Debug: some information");
#endif
```

### OTA Updates

Add Over-The-Air update capability:

```cpp
#include <ArduinoOTA.h>

void setup() {
  // ... existing setup code
  ArduinoOTA.setHostname("truthpod-main");
  ArduinoOTA.begin();
}

void loop() {
  ArduinoOTA.handle();
  // ... existing loop code
}
```

## Production Deployment

### Security Enhancements
- [ ] Use WiFiManager for AP-mode configuration
- [ ] Implement secure boot
- [ ] Enable NVS encryption for credentials
- [ ] Add certificate pinning for HTTPS

### Performance Optimizations
- [ ] Implement display buffering
- [ ] Add audio buffering for streaming
- [ ] Use PSRAM for image processing
- [ ] Enable task scheduling with FreeRTOS

### Power Management
- [ ] Implement deep sleep between updates
- [ ] Add battery voltage monitoring
- [ ] Reduce WiFi power during idle
- [ ] Dim display after timeout

### User Experience
- [ ] Add boot animation
- [ ] Implement touch screen support
- [ ] Add volume control
- [ ] Create settings menu
- [ ] Add multi-language support

## Contributing

When contributing firmware improvements:

1. Test on actual hardware, not just simulator
2. Verify power consumption changes
3. Update documentation with any pin changes
4. Test all button combinations
5. Verify backward compatibility with backend API

## License

See main project LICENSE file.

## Support

- **Documentation**: [FIRMWARE_SETUP.md](FIRMWARE_SETUP.md)
- **Quick Start**: [QUICK_START.md](QUICK_START.md)
- **Project Spec**: [../TruthPod-Complete-Project-Document-V2.md](../TruthPod-Complete-Project-Document-V2.md)
- **Backend API**: [../DEVICE_API.md](../DEVICE_API.md)

For issues or questions, refer to the project documentation or create an issue in the repository.

---

**TruthPod** - Cloud-First IoT News Verification Device 🎯
