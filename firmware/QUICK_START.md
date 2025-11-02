# TruthPod Quick Start Guide

## What You Need

### Hardware
- ✅ ESP32 DevKit (main board)
- ✅ ESP32-CAM (camera module)  
- ✅ ILI9341 TFT Display (2.8" or 3.2")
- ✅ INMP441 I2S Microphone
- ✅ MAX98357A I2S Amplifier + Speaker
- ✅ 3x Push Buttons
- ✅ RGB LED (common anode)
- ✅ Breadboard + Jumper Wires
- ✅ 5V 2A Power Supply
- ✅ USB cables for programming

### Software
- ✅ Arduino IDE with ESP32 support
- ✅ Libraries: TFT_eSPI, ArduinoJson
- ✅ Backend deployed (Render/Railway/AWS)

## Step-by-Step Setup

### 1. Backend Deployment

```bash
# Deploy to Render
1. Push code to GitHub
2. Create new Blueprint in Render
3. Point to repository
4. Add API keys in dashboard
5. Note your backend URL
```

Your backend URL will be: `https://your-service.onrender.com`

### 2. Configure Firmware

Edit `esp32_main.ino` and `esp32_cam.ino`:

```cpp
// WiFi credentials
const char* WIFI_SSID = "YourWiFiName";
const char* WIFI_PASSWORD = "YourPassword";

// Backend URL
const char* API_BASE_URL = "https://your-backend.onrender.com";
```

### 3. Wire Hardware

#### Minimal Setup (Testing)
```
ESP32 Main Board:
├─ Power: USB or 5V adapter
├─ Display: Use SPI pins (see table below)
├─ 1 Button: GPIO 34 → GND (Voice)
└─ 1 LED: GPIO 17 → 220Ω → GND (Green)

ESP32-CAM:
├─ Power: 5V adapter (NOT USB!)
├─ FTDI for programming
└─ Built-in button on GPIO 13
```

#### Full Setup
See `FIRMWARE_SETUP.md` for complete wiring diagram.

### 4. Flash Firmware

**ESP32 Main:**
```
1. Connect USB
2. Open esp32_main.ino
3. Select: Tools → Board → ESP32 Dev Module
4. Select: Tools → Port → [Your COM port]
5. Click Upload
6. Open Serial Monitor (115200 baud)
```

**ESP32-CAM:**
```
1. Connect GPIO 0 → GND (programming mode)
2. Connect FTDI (5V, GND, RX→TX, TX→RX)
3. Open esp32_cam.ino
4. Select: Tools → Board → AI Thinker ESP32-CAM
5. Click Upload
6. Disconnect GPIO 0, press Reset
7. Open Serial Monitor (115200 baud)
```

### 5. Test

**Main Board:**
- Should connect to WiFi
- Display shows "TruthPod"
- Loads and displays news
- Press buttons to navigate

**Camera:**
- Should connect to WiFi
- LED ready indicator
- Short press = recognize face
- Long press (3s) = enroll new face

## Quick Reference

### Pin Connections (Main Board)

| Component | Pins | Notes |
|-----------|------|-------|
| TFT Display | CS=15, DC=2, RST=4, MOSI=23, CLK=18 | SPI |
| Microphone | SD=33, WS=25, SCK=26 | I2S input |
| Speaker | DIN=12, BCLK=14, LRC=27 | I2S output |
| Voice Button | GPIO 34 → GND | Pull-up |
| Next Button | GPIO 35 → GND | Pull-up |
| Back Button | GPIO 32 → GND | Pull-up |
| Red LED | GPIO 16 → 220Ω → GND | |
| Green LED | GPIO 17 → 220Ω → GND | |
| Blue LED | GPIO 18 → 220Ω → GND | |
| UART to CAM | TX=23, RX=19 | To ESP32-CAM |

### Button Functions

| Button | Short Press | Long Press | Function |
|--------|-------------|------------|----------|
| Voice | Play current article audio | Record voice query | TTS / Voice search |
| Next | Next article | - | Navigate forward |
| Back | Previous article | - | Navigate backward |
| CAM Button | Recognize face | Enroll new face | Face recognition |

### LED Status Indicators

| Color | Meaning |
|-------|---------|
| 🟢 Green | Verified news (confidence ≥80%) |
| 🟡 Yellow | Questionable (50-79%) |
| 🔴 Red | Fake/Unverified (<50%) |
| 🔵 Blue | Loading/Processing |
| 🟣 Cyan | Recording audio |

### Serial Commands (for debugging)

**Main Board:**
```
Monitor at 115200 baud
Watch for:
- "WiFi connected!"
- "Device registered!"
- "Parsed X articles"
- "Response code: 200"
```

**ESP32-CAM:**
```
Monitor at 115200 baud
Watch for:
- "WiFi connected!"
- "Camera initialized!"
- "Face recognized: User ID X"
- "Enrollment successful"
```

## Common Issues

### "WiFi connection failed"
- ✅ Check SSID and password
- ✅ Ensure 2.4GHz network (not 5GHz)
- ✅ Move closer to router

### "Display shows nothing"
- ✅ Check TFT_eSPI configuration
- ✅ Verify wiring (especially CS, DC, RST)
- ✅ Test with example sketch first

### "Camera init failed"
- ✅ ESP32-CAM needs stable 5V power
- ✅ Re-seat camera ribbon cable
- ✅ Don't power from USB alone

### "API calls fail"
- ✅ Check backend is deployed
- ✅ Test: `curl https://your-backend.onrender.com/api/health`
- ✅ Verify API_BASE_URL in code

### "No audio"
- ✅ Check I2S amp has 5V power
- ✅ Verify wiring (DIN, BCLK, LRC)
- ✅ Test speaker separately

## API Keys Required

Add these in Render dashboard (see `backend/API_KEYS.md`):

```
Required:
- SECRET_KEY (auto-generated)
- NEWSAPI_KEY (from newsapi.org)

Optional but recommended:
- GOOGLE_CLOUD_PROJECT (for voice)
- GOOGLE_APPLICATION_CREDENTIALS (for voice)
- AWS_ACCESS_KEY_ID (for TTS storage)
- AWS_SECRET_ACCESS_KEY (for TTS storage)
- S3_BUCKET_NAME (for TTS storage)
```

Without optional keys, backend uses fallback modes.

## Next Steps

1. ✅ Test basic functionality
2. ✅ Enroll faces via ESP32-CAM
3. ✅ Test voice queries
4. ✅ Customize display themes
5. ✅ Add enclosure/case
6. ✅ Configure OTA updates
7. ✅ Deploy to users!

## Documentation

- **Complete Setup**: `firmware/FIRMWARE_SETUP.md`
- **Backend API**: `DEVICE_API.md`
- **API Keys**: `backend/API_KEYS.md`
- **Project Spec**: `TruthPod-Complete-Project-Document-V2.md`
- **Backend Status**: `BACKEND_STATUS.md`

## Support Resources

- **ESP32 Arduino**: https://github.com/espressif/arduino-esp32
- **TFT_eSPI**: https://github.com/Bodmer/TFT_eSPI
- **ESP32-CAM Guide**: https://randomnerdtutorials.com/esp32-cam-ai-thinker-pinout/
- **NewsAPI**: https://newsapi.org/docs

---

**TruthPod** - Fight fake news with confidence! 🎯
