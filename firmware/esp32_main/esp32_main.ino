/**
 * TruthPod ESP32 Main Board Firmware
 * Cloud-first IoT News Verification Device
 *
 * Features:
 * - WiFi onboarding and device registration with token persistence
 * - Streaming voice capture via analog MAX4466 mic + base64 upload
 * - LovyanGFX SPI display with mirror web UI and diagnostics endpoints
 * - Dual-channel status LED mapping with browser calibration tools
 * - Fallback newsroom content persisted locally when backend is empty
 * - UART communication with ESP32-CAM for token sharing
 * - On-device hardware test mode (display, audio, LED, inputs)
 *
 * Hardware:
 * - ESP32 DevKit (38-pin)
 * - ILI9341 TFT Display (SPI, LovyanGFX)
 * - MAX4466 analog microphone into ADC (I2S ADC mode)
 * - LM386 speaker amplifier driven by DAC (optional)
 * - Three buttons or TTP223 touch sensors (voice/next/back)
 * - Two status LEDs (red + green) or bi-colour package
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include "../lgfx_setup.h"
#include <LovyanGFX.hpp>
#include <WebServer.h>

// Define color constants used by the code (compatibility with TFT_eSPI names)
#define TFT_BLACK 0x0000
#define TFT_WHITE 0xFFFF
#define TFT_BLUE  0x001F
#define TFT_GREEN 0x07E0
#define TFT_RED   0xF800
#define TFT_YELLOW 0xFFE0
#define TFT_CYAN  0x07FF
#define TFT_DARKGREEN 0x03E0
#include <driver/i2s.h>
#include <driver/dac.h>
#include <base64.h>

// Simple base64 encode/decode helpers (self-contained)
// These provide the functions used elsewhere in this sketch:
//   String base64_encode(const uint8_t* data, size_t len)
//   int base64_dec_len(const char* input, int inputLen)
//   int base64_decode(char* output, const char* input, int inputLen)
// Implemented here to avoid dependency issues with different base64 libraries.

static const char b64_table[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

String base64_encode(const uint8_t* data, size_t len) {
  String out;
  out.reserve(((len + 2) / 3) * 4);
  unsigned int i = 0;
  while (i < len) {
    uint32_t octet_a = i < len ? data[i++] : 0;
    uint32_t octet_b = i < len ? data[i++] : 0;
    uint32_t octet_c = i < len ? data[i++] : 0;

    uint32_t triple = (octet_a << 16) | (octet_b << 8) | octet_c;

    out += b64_table[(triple >> 18) & 0x3F];
    out += b64_table[(triple >> 12) & 0x3F];
    out += (i - 2 <= len) ? b64_table[(triple >> 6) & 0x3F] : '=';
    out += (i - 1 <= len) ? b64_table[triple & 0x3F] : '=';
  }
  return out;
}

// Streaming base64 encoder for two-part data (header + audio) to avoid
// allocating a contiguous WAV buffer when memory is tight.
String base64_encode_two_parts(const uint8_t* part1, size_t len1, const uint8_t* part2, size_t len2) {
  size_t total = len1 + len2;
  String out;
  out.reserve(((total + 2) / 3) * 4);
  unsigned int idx = 0;
  int rem = 0; // number of bytes currently in the buffer
  uint8_t buf[3];
  auto getByte = [&](size_t p)->uint8_t {
    if (p < len1) return part1[p];
    return part2[p - len1];
  };

  while (idx < total) {
    // fill buf with up to 3 bytes
    rem = 0;
    for (int j = 0; j < 3 && idx < total; ++j, ++idx) {
      buf[j] = getByte(idx);
      rem++;
    }

    uint32_t triple = 0;
    if (rem > 0) {
      triple = ((rem > 0 ? (uint32_t)buf[0] : 0) << 16) | ((rem > 1 ? (uint32_t)buf[1] : 0) << 8) | (rem > 2 ? (uint32_t)buf[2] : 0);
      out += b64_table[(triple >> 18) & 0x3F];
      out += b64_table[(triple >> 12) & 0x3F];
      if (rem >= 2) out += b64_table[(triple >> 6) & 0x3F]; else out += '=';
      if (rem >= 3) out += b64_table[triple & 0x3F]; else out += '=';
    }
  }

  return out;
}

int base64_dec_len(const char* input, int inputLen) {
  if (!input || inputLen <= 0) return 0;
  int padding = 0;
  if (inputLen >= 1 && input[inputLen - 1] == '=') padding++;
  if (inputLen >= 2 && input[inputLen - 2] == '=') padding++;
  return (inputLen / 4) * 3 - padding;
}

static inline int _b64_val(char c) {
  if (c >= 'A' && c <= 'Z') return c - 'A';
  if (c >= 'a' && c <= 'z') return c - 'a' + 26;
  if (c >= '0' && c <= '9') return c - '0' + 52;
  if (c == '+') return 62;
  if (c == '/') return 63;
  return -1;
}

int base64_decode(char* output, const char* input, int inputLen) {
  if (!input || !output || inputLen <= 0) return 0;
  int outIndex = 0;
  int i = 0;
  while (i < inputLen) {
    // read 4 valid base64 chars
    int vals[4] = {-1, -1, -1, -1};
    int found = 0;
    for (int j = 0; j < 4 && i < inputLen; i++) {
      char c = input[i];
      if (c == '\r' || c == '\n' || c == ' ') continue; // skip whitespace
      vals[j++] = _b64_val(c);
      found++;
    }
    if (found == 0) break;

    int v0 = vals[0] < 0 ? 0 : vals[0];
    int v1 = vals[1] < 0 ? 0 : vals[1];
    int v2 = vals[2] < 0 ? 0 : vals[2];
    int v3 = vals[3] < 0 ? 0 : vals[3];

    uint32_t triple = (v0 << 18) | (v1 << 12) | (v2 << 6) | v3;

    output[outIndex++] = (triple >> 16) & 0xFF;
    if (vals[2] != -1) output[outIndex++] = (triple >> 8) & 0xFF;
    if (vals[3] != -1) output[outIndex++] = triple & 0xFF;
  }
  return outIndex;
}

// ===== Configuration =====
// WiFi Credentials (hardcoded for now - use WiFiManager in production)
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Backend API Configuration
const char* API_BASE_URL = "https://truth-pod.onrender.com";  // Change to your deployed backend URL
// const char* API_BASE_URL = "http://192.168.1.100:8000";  // Or use local IP for testing

// Device Configuration
String deviceMAC = "";
String deviceToken = "";

// ===== Pin Definitions =====
// I2S Microphone (INMP441)
// You can use either the digital I2S microphone (INMP441) or an analog
// electret microphone with MAX4466 amplifier. Select one by defining
// USE_ANALOG_MIC or leave USE_ANALOG_MIC undefined to use the INMP441.
#define USE_ANALOG_MIC 1
// If you're using TTP223 touch modules for buttons, enable this define
// TTP223 modules drive their OUT HIGH when touched; they should be wired
// to MCU pins configured as INPUT (no internal pull-up) to avoid forcing
// the line HIGH. Enable when you wire TTP223 modules to the button pins.
#define USE_TOUCH_MODULES 1

// Analog MIC (MAX4466) - connect MAX4466 OUT -> ADC pin (input-only)
#define ANALOG_MIC_ADC_PIN 34 // ADC1_CH6 (GPIO34) - input-only

#define USE_LM386 1

// LM386 input should be driven from the ESP32 DAC (GPIO25 or GPIO26).
#define LM386_DAC_PIN 25 // DAC1

// (I2S speaker support removed - firmware now assumes analog MAX4466 mic + LM386)

#define BUTTON_VOICE 13 // moved to GPIO13 (was 33)
#define BUTTON_BACK 32
#define BUTTON_NEXT 33  // moved to GPIO33 (was 13)
// RGB LED (or use 3 separate pins)
// Note: default parallel TFT pins may conflict with some GPIOs. Use pins that do not
// overlap with display/data lines. Adjust as needed to match your wiring.
#define LED_RED 2
#define LED_GREEN 21

// UART for ESP32-CAM communication
// Remapped from GPIO19/23 to free SPI pins (avoid conflict with TFT SPI)
// Use GPIO16 (RX) and GPIO17 (TX) for Serial2
#define UART_RX 16
#define UART_TX 17

// ===== Display Configuration =====
// The LovyanGFX instance `tft` is defined in firmware/lgfx_setup.h

// ===== Global State =====
Preferences preferences;
HTTPClient http;
int lastHttpResponseCode = 0;
WebServer webServer(80);

// Runtime config
bool ledInverted = false; // persisted in preferences (key: "led_inverted")
// Runtime LED pin mappings (persisted keys: led_r, led_g)
int ledPinR = LED_RED;
int ledPinG = LED_GREEN;

struct NewsArticle {
  String id;
  String title;
  String source;
  String description;
  float confidence;
  String publishedAt;
};

NewsArticle newsArticles[10];
int currentArticleIndex = 0;
int totalArticles = 0;

// Built-in fallback news (used when backend/trending fails)
NewsArticle fallbackNews[] = {
  {"fb1", "Local demo: Community garden opens in neighborhood", "Local Times", "Community garden opens", 0.85, "2025-11-09"},
  {"fb2", "City council approves new bike lanes", "CityNews", "Bike lanes approved", 0.65, "2025-11-08"},
  {"fb3", "Startup announces open-source AI tool for students", "TechDaily", "Open-source AI tool announced", 0.92, "2025-11-07"}
};
int fallbackCount = sizeof(fallbackNews) / sizeof(fallbackNews[0]);

// Button active level detection (some touch modules drive HIGH on touch)
bool btnVoiceActiveHigh = false;
bool btnNextActiveHigh = false;
bool btnBackActiveHigh = false;

bool isRecording = false;
bool isPlayingAudio = false;
bool testMode = false;
bool dacAvailable = false;

// ===== I2S Configuration =====
const int SAMPLE_RATE = 16000;
const int BITS_PER_SAMPLE = 16;
// Reduce default record time to avoid large single-buffer allocations on
// devices without PSRAM. Lower from 3s to 2s to reduce peak heap usage.
// Consider implementing streamed base64 encoding later to avoid double buffers.
const int RECORD_TIME = 2;  // seconds
const int RECORD_SIZE = SAMPLE_RATE * RECORD_TIME * (BITS_PER_SAMPLE / 8);

// ===== Function Prototypes =====
void setupWiFi();
void setupDisplay();
void drawStartupGraphics();
void setupButtons();
void setupLEDs();
void setupI2S();
void setupUART();
void registerDevice();
bool loadDeviceToken();
void saveDeviceToken(String token);
void displayStatus(String message, uint16_t color);
void displayNewsArticle(int index);
void setLEDByConfidence(float confidence);
void setLED(bool red, bool green);
void handleVoiceButton();
void handleNextButton();
void handleBackButton();
void recordAndTranscribe();
void fetchTrendingNews();
void fetchSearchNews(String query);
void parseNewsResponse(String response);
void playNewsAudio(String newsId);
void handleCameraData();
bool makeAPICall(String endpoint, String method, String payload, String& response);
String urlEncode(String str);
String jsonEscape(const String &s);

// ===== Setup =====
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("=== TruthPod Starting ===");
  
  // Device MAC address will be read after WiFi connects to ensure a valid MAC
  
  // Initialize preferences storage
  preferences.begin("truthpod", false);
  // Load persisted LED inversion preference (default: false)
  ledInverted = preferences.getBool("led_inverted", false);
  Serial.print("LED inverted (from prefs): "); Serial.println(ledInverted ? "yes" : "no");

  // Initialize testMode flag from prefs if ever persisted (future)
  testMode = preferences.getBool("test_mode", false);
  // Load persisted LED pin mapping if present
  unsigned int pr = preferences.getUInt("led_r", 0);
  unsigned int pg = preferences.getUInt("led_g", 0);
  if (pr != 0 && pg != 0) {
    ledPinR = (int)pr; ledPinG = (int)pg;
    Serial.printf("Loaded LED mapping from prefs: R=%d G=%d\n", ledPinR, ledPinG);
  }
  
  // Setup hardware
  setupDisplay();
  setupButtons();
  setupLEDs();
  setupI2S();
  setupUART();

  // Print hardware pin mappings for easier debug
  Serial.println("Pin mappings:");
  Serial.print(" TFT_MOSI: "); Serial.println(TFT_MOSI);
  Serial.print(" TFT_SCLK: "); Serial.println(TFT_SCLK);
  Serial.print(" TFT_CS:   "); Serial.println(TFT_CS);
  Serial.print(" TFT_DC:   "); Serial.println(TFT_DC);
  Serial.print(" TFT_RST:  "); Serial.println(TFT_RST);
  Serial.print(" BUTTON_VOICE: "); Serial.println(BUTTON_VOICE);
  Serial.print(" BUTTON_NEXT:  "); Serial.println(BUTTON_NEXT);
  Serial.print(" BUTTON_BACK:  "); Serial.println(BUTTON_BACK);
  
  // Display startup message
  displayStatus("Connecting to WiFi...", TFT_BLUE);
    setLED(false, true);  // use green for connecting
  
  // Connect to WiFi
  setupWiFi();

  // Read and print device MAC after WiFi is initialized
  deviceMAC = WiFi.macAddress();
  Serial.print("Device MAC: ");
  Serial.println(deviceMAC);

  // Report memory and PSRAM status for diagnostics
  Serial.print("Free heap: ");
  Serial.println(ESP.getFreeHeap());
#ifdef ESP32
  Serial.print("PSRAM found: ");
  Serial.println(psramFound() ? "yes" : "no");
#endif
  
  // Register device and get token
  if (!loadDeviceToken()) {
    displayStatus("Registering device...", TFT_YELLOW);
    setLED(true, true);  // yellow (red+green)
    registerDevice();
  }
  
  // Load trending news
  displayStatus("Loading news...", TFT_GREEN);
  setLED(false, true);  // Green LED
  fetchTrendingNews();
  
  // Display first article
  if (totalArticles > 0) {
    displayNewsArticle(0);
  } else {
    displayStatus("No news available", TFT_RED);
  }

  // Start a lightweight HTTP server to mirror display in a browser tab
  // Serve a simple server-side mirror page (no client-side JS) to avoid fetch/CORS issues
  webServer.on("/", HTTP_GET, []() {
    Serial.print("HTTP / request from "); Serial.println(webServer.client().remoteIP());
    String html = "<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>TruthPod Mirror</title>";
    html += "<style>body{font-family:Arial,Helvetica,sans-serif;background:#111;color:#eee;padding:12px} .card{background:#222;padding:12px;border-radius:8px;max-width:720px} h2{color:#9cf}</style></head><body>";
    html += "<div class=\"card\"><h2>TruthPod Mirror</h2>";
    html += "<div><strong>Status:</strong> " + String((totalArticles>0)?"ready":"no-news") + "</div>";
    if (totalArticles > 0 && currentArticleIndex < totalArticles) {
      html += "<h3>" + jsonEscape(newsArticles[currentArticleIndex].title) + "</h3>";
      html += "<div><strong>Source:</strong> " + jsonEscape(newsArticles[currentArticleIndex].source) + "</div>";
      html += "<div><strong>Confidence:</strong> " + String((int)(newsArticles[currentArticleIndex].confidence * 100)) + "%</div>";
    } else {
      html += "<div><em>No news available</em></div>";
    }
    html += "<hr/><div><strong>Display:</strong> " + String(tft.width()) + " x " + String(tft.height()) + "</div>";
    html += "<div><strong>LED mapping:</strong> R=" + String(ledPinR) + " G=" + String(ledPinG) + " (inverted=" + String(ledInverted?"yes":"no") + ")</div>";
    html += "</div></body></html>";
    webServer.sendHeader("Access-Control-Allow-Origin", "*");
    webServer.send(200, "text/html", html);
  });

  // Log unknown requests to help debug network/browser issues
  webServer.onNotFound([]() {
    Serial.print("HTTP request not found: ");
    Serial.print(webServer.uri());
    Serial.print(" from ");
    Serial.println(webServer.client().remoteIP());
    webServer.sendHeader("Access-Control-Allow-Origin", "*");
    webServer.send(404, "text/plain", "Not found");
  });

  webServer.on("/status.json", HTTP_GET, []() {
    // Build a compact JSON payload reflecting the current display
    String payload = "{";
    payload += "\"status\":\"" + String((totalArticles>0)?"ready":"no-news") + "\",";
    if (totalArticles > 0 && currentArticleIndex < totalArticles) {
      payload += "\"title\":\"" + jsonEscape(newsArticles[currentArticleIndex].title) + "\",";
      payload += "\"source\":\"" + jsonEscape(newsArticles[currentArticleIndex].source) + "\",";
      payload += "\"confidence\":" + String(newsArticles[currentArticleIndex].confidence, 2);
    } else {
      payload += "\"title\":\"-\",\"source\":\"-\",\"confidence\":0";
    }
    // Add some runtime diagnostic flags
    payload += ",\"tft_width\":" + String(tft.width());
    payload += ",\"tft_height\":" + String(tft.height());
    payload += ",\"led_inverted\":" + String(ledInverted ? 1 : 0);
    payload += ",\"led_r\":" + String(ledPinR);
    payload += ",\"led_g\":" + String(ledPinG);
    payload += "}";
    webServer.sendHeader("Access-Control-Allow-Origin", "*");
    webServer.send(200, "application/json", payload);
  });

  // Simple ping for network/debugging
  webServer.on("/ping", HTTP_GET, []() {
    Serial.print("HTTP /ping request from "); Serial.println(webServer.client().remoteIP());
    webServer.sendHeader("Access-Control-Allow-Origin", "*");
    webServer.send(200, "text/plain", "OK");
  });

  // Trigger a display test from browser (useful to force color fills on demand)
  webServer.on("/test_display", HTTP_GET, []() {
    Serial.print("HTTP /test_display request from "); Serial.println(webServer.client().remoteIP());
    // Run the same quick display sequence used at boot
    tft.fillScreen(TFT_RED);
    delay(200);
    tft.fillScreen(TFT_GREEN);
    delay(200);
  tft.fillScreen(TFT_BLUE);
    delay(200);
    drawStartupGraphics();
    webServer.sendHeader("Access-Control-Allow-Origin", "*");
    webServer.send(200, "text/plain", "display test run");
  });

  // Trigger LED polarity diagnostic from browser
  webServer.on("/led_test", HTTP_GET, []() {
    Serial.print("HTTP /led_test request from "); Serial.println(webServer.client().remoteIP());
    Serial.println("LED diagnostic (HIGH then LOW) via /led_test...");
  pinMode(ledPinR, OUTPUT);
  pinMode(ledPinG, OUTPUT);
  // HIGH pass
  digitalWrite(ledPinR, HIGH);
  digitalWrite(ledPinG, HIGH);
  delay(500);
  // LOW pass (common-anode case)
  digitalWrite(ledPinR, LOW);
  digitalWrite(ledPinG, LOW);
  delay(500);
  // Reset to off
  digitalWrite(ledPinR, LOW);
  digitalWrite(ledPinG, LOW);
    webServer.sendHeader("Access-Control-Allow-Origin", "*");
    webServer.send(200, "text/plain", "led test run");
  });

  // Allow setting LED inversion at runtime and persist the choice
  webServer.on("/led_set", HTTP_GET, []() {
    Serial.print("HTTP /led_set request from "); Serial.println(webServer.client().remoteIP());
    String inv = webServer.arg("invert"); // invert=1 or invert=0
    if (inv == "1") {
      ledInverted = true;
      preferences.putBool("led_inverted", true);
      Serial.println("LED inversion set: INVERTED (common-anode)");
      webServer.sendHeader("Access-Control-Allow-Origin", "*");
      webServer.send(200, "text/plain", "led_inverted=1");
      return;
    } else if (inv == "0") {
      ledInverted = false;
      preferences.putBool("led_inverted", false);
      Serial.println("LED inversion set: NORMAL (common-cathode)");
      webServer.sendHeader("Access-Control-Allow-Origin", "*");
      webServer.send(200, "text/plain", "led_inverted=0");
      return;
    }
    webServer.sendHeader("Access-Control-Allow-Origin", "*");
    webServer.send(400, "text/plain", "expected query: /led_set?invert=0|1");
  });

  // Remap LED pins at runtime: /led_map?r=2&g=21
  webServer.on("/led_map", HTTP_GET, []() {
    Serial.print("HTTP /led_map request from "); Serial.println(webServer.client().remoteIP());
    String rs = webServer.arg("r");
    String gs = webServer.arg("g");
    if (rs.length() == 0 || gs.length() == 0) {
      webServer.sendHeader("Access-Control-Allow-Origin", "*");
      webServer.send(400, "text/plain", "expected query: /led_map?r=<pin>&g=<pin>");
      return;
    }
    int r = rs.toInt();
    int g = gs.toInt();
    // Basic validation
    if (r < 0 || g < 0) {
      webServer.sendHeader("Access-Control-Allow-Origin", "*");
      webServer.send(400, "text/plain", "invalid pins");
      return;
    }
    ledPinR = r; ledPinG = g;
    // Persist mapping
    preferences.putUInt("led_r", ledPinR);
    preferences.putUInt("led_g", ledPinG);
    // Reconfigure pins immediately
    pinMode(ledPinR, OUTPUT); pinMode(ledPinG, OUTPUT);
    setLED(false,false);
    Serial.printf("LED mapping updated: R=%d G=%d\n", ledPinR, ledPinG);
    webServer.sendHeader("Access-Control-Allow-Origin", "*");
    webServer.send(200, "text/plain", "led_map_ok");
  });

  // Pulse a single LED color for faster on-site debugging: /led_pulse?color=red|green
  webServer.on("/led_pulse", HTTP_GET, []() {
    String col = webServer.arg("color");
    pinMode(ledPinR, OUTPUT); pinMode(ledPinG, OUTPUT);
    if (col == "red") {
      setLED(true, false);
      delay(400);
      setLED(false, false);
      webServer.sendHeader("Access-Control-Allow-Origin", "*");
      webServer.send(200, "text/plain", "pulsed red");
      return;
    } else if (col == "green") {
      setLED(false, true);
      delay(400);
      setLED(false, false);
      webServer.sendHeader("Access-Control-Allow-Origin", "*");
      webServer.send(200, "text/plain", "pulsed green");
      return;
    }
    webServer.sendHeader("Access-Control-Allow-Origin", "*");
    webServer.send(400, "text/plain", "expected query: /led_pulse?color=red|green");
  });

  // Lightweight LED calibration UI (safe raw literal; page reads /status.json to get mapping)
  webServer.on("/led_calibrate", HTTP_GET, []() {
    Serial.print("HTTP /led_calibrate request from "); Serial.println(webServer.client().remoteIP());
    static const char page[] PROGMEM = R"rawliteral(
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LED Calibration</title>
<style>body{font-family:Arial,Helvetica,sans-serif;background:#111;color:#eee;padding:12px} .card{background:#222;padding:12px;border-radius:8px;max-width:520px} button{margin:6px;padding:8px 12px;border-radius:6px;border:0;background:#0066cc;color:#fff} input,select{margin:6px;padding:6px;border-radius:6px;border:1px solid #444;background:#111;color:#fff}</style>
</head>
<body>
<div class="card">
<h2>LED Calibration</h2>
<div id="info">Loading...</div>
<div>
<button id="testBtn">Run LED Test</button>
<button id="redOn">Red On</button>
<button id="redOff">Red Off</button>
<button id="greenOn">Green On</button>
<button id="greenOff">Green Off</button>
</div>
<div style="margin-top:10px">
<label>Invert wiring: </label>
<select id="invertSel"><option value="0">Normal (common-cathode)</option><option value="1">Inverted (common-anode)</option></select>
<button id="applyInvert">Apply</button>
</div>
<div style="margin-top:10px">
<label>Remap pins:</label><br/>
R: <input id="pinR" size="4"/> G: <input id="pinG" size="4"/> <button id="applyMap">Apply Map</button>
</div>
<div id="msg" style="margin-top:10px;color:#9f9"></div>
</div>
<script>
async function json(path){try{let r=await fetch(path);if(r.ok) return r.json();}catch(e){}return null;}
async function init(){ let s = await json('/status.json'); if(s){ document.getElementById('info').textContent = 'Current mapping: R='+(s.led_r||'')+' G='+(s.led_g||'')+' | Inverted='+(s.led_inverted? 'yes':'no'); document.getElementById('pinR').value = s.led_r || ''; document.getElementById('pinG').value = s.led_g || ''; document.getElementById('invertSel').value = s.led_inverted? '1':'0'; } }
document.getElementById('testBtn').onclick = async function(){ document.getElementById('msg').textContent='Running test...'; await fetch('/led_test'); document.getElementById('msg').textContent='Test triggered';};
document.getElementById('redOn').onclick = async function(){ await fetch('/led_map?r='+document.getElementById('pinR').value+'&g='+document.getElementById('pinG').value); await fetch('/led_set?invert='+document.getElementById('invertSel').value); document.getElementById('msg').textContent='Red ON'; };
document.getElementById('redOff').onclick = async function(){ await fetch('/led_map?r='+document.getElementById('pinR').value+'&g='+document.getElementById('pinG').value); await fetch('/led_set?invert='+document.getElementById('invertSel').value); document.getElementById('msg').textContent='Red OFF'; };
document.getElementById('greenOn').onclick = async function(){ await fetch('/led_map?r='+document.getElementById('pinR').value+'&g='+document.getElementById('pinG').value); await fetch('/led_set?invert='+document.getElementById('invertSel').value); document.getElementById('msg').textContent='Green ON'; };
document.getElementById('greenOff').onclick = async function(){ await fetch('/led_map?r='+document.getElementById('pinR').value+'&g='+document.getElementById('pinG').value); await fetch('/led_set?invert='+document.getElementById('invertSel').value); document.getElementById('msg').textContent='Green OFF'; };
document.getElementById('applyInvert').onclick = async function(){ await fetch('/led_set?invert='+document.getElementById('invertSel').value); document.getElementById('msg').textContent='Invert set'; };
document.getElementById('applyMap').onclick = async function(){ let r=document.getElementById('pinR').value; let g=document.getElementById('pinG').value; await fetch('/led_map?r='+r+'&g='+g); document.getElementById('msg').textContent='Mapping saved R='+r+' G='+g; };
init();
</script>
</body>
</html>
)rawliteral";
    webServer.sendHeader("Access-Control-Allow-Origin", "*");
    webServer.send(200, "text/html", page);
  });

  // Trigger a playback / hardware test from browser
  webServer.on("/test_play", HTTP_GET, []() {
    Serial.print("HTTP /test_play request from "); Serial.println(webServer.client().remoteIP());
    webServer.sendHeader("Access-Control-Allow-Origin", "*");
    webServer.send(200, "text/plain", "playing");
    // Run the same hardware test routine used for test mode (blocking)
    runHardwareTest();
  });

  webServer.begin();
  Serial.println("Web server started: Open http://" + WiFi.localIP().toString() + "/ in a browser to mirror display");

  // Run quick diagnostics to help debug display/LED/touch issues
  delay(200);
  Serial.println("Running on-device diagnostics...");
  // Display test: fill colors and show text
  tft.fillScreen(TFT_RED);
  delay(300);
  tft.fillScreen(TFT_GREEN);
  delay(300);
  tft.fillScreen(TFT_BLUE);
  delay(300);
  drawStartupGraphics();

  // LED diagnostic: toggle both polarities to help detect common-anode vs cathode wiring
  Serial.println("LED diagnostic: toggling LEDs (HIGH then LOW)...");
  pinMode(ledPinR, OUTPUT);
  pinMode(ledPinG, OUTPUT);
  // Try lighting with HIGH
  digitalWrite(ledPinR, HIGH);
  digitalWrite(ledPinG, HIGH);
  delay(400);
  // Then try lighting with LOW (common-anode case)
  digitalWrite(ledPinR, LOW);
  digitalWrite(ledPinG, LOW);
  delay(400);
  // Reset to off
  digitalWrite(ledPinR, LOW);
  digitalWrite(ledPinG, LOW);

  Serial.println("Input diagnostic: printing button/touch states every 1s for 10s...");
  for (int i = 0; i < 10; ++i) {
    Serial.print("BTN voice(dig): "); Serial.print(digitalRead(BUTTON_VOICE));
    // If pin supports touchRead, include it
    #ifdef TOUCH_PAD_MAX
    // touchRead exists on ESP32; use cautiously
    int tval = touchRead(BUTTON_VOICE);
    Serial.print("  touch:"); Serial.print(tval);
    #endif
    Serial.print("  BTN next:"); Serial.print(digitalRead(BUTTON_NEXT));
    Serial.print("  BTN back:"); Serial.println(digitalRead(BUTTON_BACK));
    delay(1000);
  }
}

// ===== Main Loop =====
void loop() {
  // Poll web server to handle incoming HTTP requests (mirror page)
  webServer.handleClient();
  // Check WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    displayStatus("WiFi disconnected!", TFT_RED);
      setLED(true, false);  // Red LED
    setupWiFi();
    return;
  }
  
  // Handle button presses
  // Handle voice button (respect auto-detected active level)
  int voiceState = digitalRead(BUTTON_VOICE);
  int voicePressedState = btnVoiceActiveHigh ? HIGH : LOW;
  if (voiceState == voicePressedState) {
    delay(50);  // Debounce
    if (digitalRead(BUTTON_VOICE) == voicePressedState) {
      handleVoiceButton();
      while (digitalRead(BUTTON_VOICE) == voicePressedState) delay(10);
    }
  }
  
  int nextState = digitalRead(BUTTON_NEXT);
  int nextPressedState = btnNextActiveHigh ? HIGH : LOW;
  if (nextState == nextPressedState) {
    delay(50);
    if (digitalRead(BUTTON_NEXT) == nextPressedState) {
      handleNextButton();
      while (digitalRead(BUTTON_NEXT) == nextPressedState) delay(10);
    }
  }
  
  int backState = digitalRead(BUTTON_BACK);
  int backPressedState = btnBackActiveHigh ? HIGH : LOW;
  if (backState == backPressedState) {
    delay(50);
    if (digitalRead(BUTTON_BACK) == backPressedState) {
      handleBackButton();
      while (digitalRead(BUTTON_BACK) == backPressedState) delay(10);
    }
  }
  
  // Check for camera data
  handleCameraData();
  
  delay(100);
}

// ===== WiFi Setup =====
void setupWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWiFi connection failed!");
  displayStatus("WiFi Failed!", TFT_RED);
  setLED(true, false);
  }
}

// ===== Display Setup =====
void setupDisplay() {
  Serial.println("Initializing display...");
  // Try toggling reset line if present to give panel a clean boot
#if defined(TFT_RST) && (TFT_RST != -1)
  pinMode(TFT_RST, OUTPUT);
  digitalWrite(TFT_RST, LOW);
  delay(50);
  digitalWrite(TFT_RST, HIGH);
  delay(50);
#endif
  tft.init();
  tft.setRotation(1);  // Landscape
  Serial.print("Display init done. WidthxHeight: "); Serial.print(tft.width()); Serial.print(" x "); Serial.println(tft.height());
  // Turn on backlight if module BL pin is wired to an MCU GPIO
#if TFT_BL != -1
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH); // Full brightness; replace with PWM if desired
#endif
  // Show startup graphics/logo
  drawStartupGraphics();
}

// ===== Button Setup =====
void setupButtons() {
  // Auto-detect whether each input is active-high (touch module drives HIGH when touched)
  // or active-low (button to GND with pull-up). This helps support both touch modules
  // that drive their output HIGH on touch (e.g., TTP223 default) and simple buttons.
  // Helper: pins 34..39 are input-only ADC pins on ESP32 and do NOT support internal pull-ups
  auto supportsInternalPullup = [](int pin){ return !(pin >= 34 && pin <= 39); };

  // For pins that support internal pull-ups, enable INPUT_PULLUP to avoid floating
  // reads during boot. Those are assumed to be regular buttons wired to GND (active-low).
  // For input-only ADC pins (34..39) we cannot enable INTERNAL_PULLUP, so treat them
  // as potentially driven-by-module (e.g. touch sensor) and perform a short sample to
  // auto-detect whether they are active-high.

  // If using TTP223 touch modules they drive their OUT HIGH on touch.
  // Configure pins as plain INPUT (no internal pull-up) and assume active-high.
#ifdef USE_TOUCH_MODULES
  pinMode(BUTTON_VOICE, INPUT);
  pinMode(BUTTON_NEXT, INPUT);
  pinMode(BUTTON_BACK, INPUT);
#else
  if (supportsInternalPullup(BUTTON_VOICE)) pinMode(BUTTON_VOICE, INPUT_PULLUP);
  else pinMode(BUTTON_VOICE, INPUT);

  if (supportsInternalPullup(BUTTON_NEXT)) pinMode(BUTTON_NEXT, INPUT_PULLUP);
  else pinMode(BUTTON_NEXT, INPUT);

  if (supportsInternalPullup(BUTTON_BACK)) pinMode(BUTTON_BACK, INPUT_PULLUP);
  else pinMode(BUTTON_BACK, INPUT);
#endif

  delay(10);
  const int samples = 5;
  int vSum = 0, nSum = 0, bSum = 0;
  for (int i = 0; i < samples; ++i) {
    vSum += digitalRead(BUTTON_VOICE);
    nSum += digitalRead(BUTTON_NEXT);
    bSum += digitalRead(BUTTON_BACK);
    delay(5);
  }

  // Determine active polarity:
  // - If using touch modules (TTP223) we expect active-high outputs, so mark
  //   the button as active-high explicitly.
  // - Otherwise:
  //   - If a pin supports internal pull-up we assume a conventional button wired to GND
  //     (active-low), so default to activeHigh = false.
  //   - If a pin is input-only (no internal pull-up) we rely on the sampled value to
  //     detect modules that drive HIGH when active (active-high).
#ifdef USE_TOUCH_MODULES
  btnVoiceActiveHigh = true;
  btnNextActiveHigh  = true;
  btnBackActiveHigh  = true;
#else
  btnVoiceActiveHigh = supportsInternalPullup(BUTTON_VOICE) ? false : (vSum > samples/2);
  btnNextActiveHigh  = supportsInternalPullup(BUTTON_NEXT)  ? false : (nSum > samples/2);
  btnBackActiveHigh  = supportsInternalPullup(BUTTON_BACK)  ? false : (bSum > samples/2);
#endif

  // Re-configure pins: keep INPUT_PULLUP where supported for stable idle state.
  // For input-only pins (34..39), leave as INPUT and warn the user to add an
  // external pull-up resistor if they experience floating/unstable readings.
  if (!supportsInternalPullup(BUTTON_VOICE)) {
    Serial.print("Warning: BUTTON_VOICE (GPIO "); Serial.print(BUTTON_VOICE);
    Serial.println(") does not support internal pull-up. Please add an external pull-up resistor (10k) or move the button to a different GPIO.");
  }
  if (!supportsInternalPullup(BUTTON_NEXT)) {
    Serial.print("Warning: BUTTON_NEXT (GPIO "); Serial.print(BUTTON_NEXT);
    Serial.println(") does not support internal pull-up. Please add an external pull-up resistor (10k) or move the button to a different GPIO.");
  }
  if (!supportsInternalPullup(BUTTON_BACK)) {
    Serial.print("Warning: BUTTON_BACK (GPIO "); Serial.print(BUTTON_BACK);
    Serial.println(") does not support internal pull-up. Please add an external pull-up resistor (10k) or move the button to a different GPIO.");
  }

  Serial.print("Button active-high detection (voice,next,back): ");
  Serial.print(btnVoiceActiveHigh); Serial.print(","); Serial.print(btnNextActiveHigh); Serial.print(","); Serial.println(btnBackActiveHigh);
}

// ===== LED Setup =====
void setupLEDs() {
  pinMode(ledPinR, OUTPUT);
  pinMode(ledPinG, OUTPUT);
  setLED(false, false);
  // Boot-time LED verification: blink red then green once
  // Helps validate wiring on first power-up
  digitalWrite(ledPinR, HIGH);
  delay(300);
  digitalWrite(ledPinR, LOW);
  delay(150);
  digitalWrite(ledPinG, HIGH);
  delay(300);
  digitalWrite(ledPinG, LOW);
  delay(150);
}

void setLED(bool red, bool green) {
  if (ledInverted) {
    // Inverted wiring (common-anode)
    digitalWrite(ledPinR, red ? LOW : HIGH);
    digitalWrite(ledPinG, green ? LOW : HIGH);
  } else {
    // Normal wiring (common-cathode)
    digitalWrite(ledPinR, red ? HIGH : LOW);
    digitalWrite(ledPinG, green ? HIGH : LOW);
  }
}

void setLEDByConfidence(float confidence) {
  if (confidence >= 0.80) {
    setLED(false, true);  // Green - Verified
  } else if (confidence >= 0.50) {
    setLED(true, true);   // Yellow - Questionable
  } else {
    setLED(true, false);  // Red - Fake/Unverified
  }
}

// ===== I2S Setup =====
void setupI2S() {
  // Configure I2S for microphone (analog MAX4466 via internal ADC)
  // Use I2S ADC mode to capture from the internal ADC (MAX4466 -> ADC pin)
  i2s_config_t i2s_adc_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX | I2S_MODE_ADC_BUILT_IN),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 4,
    .dma_buf_len = 1024,
    .use_apll = true,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };

  i2s_driver_install(I2S_NUM_0, &i2s_adc_config, 0, NULL);
  // Configure which ADC channel to use (ADC unit 1, channel 6 -> GPIO34)
#ifdef ADC_UNIT_1
  i2s_set_adc_mode(ADC_UNIT_1, ADC1_CHANNEL_6);
#else
  i2s_set_adc_mode(ADC_UNIT_1, ADC1_CHANNEL_6);
#endif
  i2s_adc_enable(I2S_NUM_0);

  // Speaker: LM386 via built-in DAC (optional). If both analog mic (I2S ADC)
  // and DAC are attempted together, there is a known driver conflict; skip
  // enabling the DAC in that case.
#ifdef USE_LM386
#ifdef USE_ANALOG_MIC
  Serial.println("Warning: USE_ANALOG_MIC and USE_LM386 both enabled. Skipping DAC enable to avoid driver conflict.");
  dacAvailable = false;
#else
  dac_output_enable(DAC_CHANNEL_1); // GPIO25
  dacAvailable = true;
#endif
#endif
}

// ===== UART Setup =====
void setupUART() {
  Serial2.begin(115200, SERIAL_8N1, UART_RX, UART_TX);
  Serial.println("UART initialized for ESP32-CAM communication");
}

// ===== Device Registration =====
void registerDevice() {
  String payload = "{\"device_mac\":\"" + deviceMAC + "\"}";
  String response = "";
  
  if (makeAPICall("/api/iot/device/register", "POST", payload, response)) {
    // Parse JSON response
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, response);
    
    if (!error) {
      deviceToken = doc["api_token"].as<String>();
      saveDeviceToken(deviceToken);
      Serial.println("Device registered successfully!");
      displayStatus("Device registered!", TFT_GREEN);
    } else {
      Serial.println("Failed to parse registration response");
      displayStatus("Registration failed!", TFT_RED);
    }
  } else {
    Serial.println("Device registration failed");
    displayStatus("Registration failed!", TFT_RED);
  }
}

// Simple hardware test routine invoked when testMode is activated
void runHardwareTest() {
  Serial.println("=== RUNNING HARDWARE TEST ===");
  displayStatus("TEST MODE", TFT_YELLOW);
  // Color fills
  tft.fillScreen(TFT_RED); delay(300);
  tft.fillScreen(TFT_GREEN); delay(300);
  tft.fillScreen(TFT_BLUE); delay(300);
  drawStartupGraphics();

  // LED pattern
  Serial.println("LED pattern...");
  for (int i = 0; i < 3; ++i) {
    setLED(true, false); delay(200);
    setLED(true, true); delay(200);
    setLED(false, true); delay(200);
  }
  setLED(false, false);

  // Microphone: record a short buffer and report RMS level
  size_t wanted = SAMPLE_RATE / 4 * (BITS_PER_SAMPLE/8); // 250ms
  uint8_t* buf = (uint8_t*)malloc(wanted);
  if (!buf) { Serial.println("Mic test: alloc failed"); return; }
  size_t r = 0; size_t bytesRead = 0;
  unsigned long start = millis();
  while (r < wanted && (millis() - start) < 1000) {
    i2s_read(I2S_NUM_0, buf + r, wanted - r, &bytesRead, 100);
    r += bytesRead;
  }
  Serial.print("Mic test: recorded bytes = "); Serial.println(r);
  // Compute simple RMS (16-bit PCM assumed)
  long sum = 0; int samples = r / 2;
  for (int i = 0; i < samples; ++i) {
    int16_t s = ((int16_t*)buf)[i];
    sum += (long)s * (long)s;
  }
  free(buf);
  float rms = 0;
  if (samples > 0) rms = sqrt((float)sum / samples) / 32768.0;
  Serial.print("Mic RMS: "); Serial.println(rms);
  displayStatus(String("Mic RMS:") + String(rms, 3), TFT_CYAN);
  delay(800);

  // Speaker test: short square wave (LM386 DAC)
  Serial.println("Speaker test: playing square wave");
  if (!dacAvailable) {
    Serial.println("DAC not available: skipping speaker test");
  } else {
    int freq = 600;
    unsigned long period = 1000000UL / freq;
    for (int k = 0; k < 2000; ++k) {
      dacWrite(LM386_DAC_PIN, 200);
      delayMicroseconds(period / 2);
      dacWrite(LM386_DAC_PIN, 55);
      delayMicroseconds(period / 2);
    }
    dacWrite(LM386_DAC_PIN, 0);
  }

  displayStatus("TEST DONE", TFT_GREEN);
  Serial.println("=== HARDWARE TEST COMPLETE ===");
}

bool loadDeviceToken() {
  deviceToken = preferences.getString("token", "");
  if (deviceToken.length() > 0) {
    Serial.println("Loaded device token from storage");
    return true;
  }
  return false;
}

void saveDeviceToken(String token) {
  preferences.putString("token", token);
  Serial.println("Device token saved");
}

// ===== Display Functions =====
void displayStatus(String message, uint16_t color) {
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(color, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(10, 100);
  tft.println(message);
}

// Simple startup graphic/logo displayed during initialization.
// Uses basic LovyanGFX drawing primitives so it remains library-version
// agnostic and lightweight.
void drawStartupGraphics() {
  // Clear and background
  tft.fillScreen(TFT_BLACK);

  // Draw rounded banner
  uint16_t bannerColor = TFT_BLUE;
  tft.fillRect(0, 8, tft.width(), 64, bannerColor);

  // Draw circular logo on left
  int cx = 28;
  int cy = 40;
  int r = 22;
  tft.fillCircle(cx, cy, r, TFT_WHITE);
  tft.fillCircle(cx, cy, r - 6, TFT_BLUE);
  tft.fillCircle(cx, cy, r - 10, TFT_WHITE);

  // Draw device name
  tft.setTextSize(2);
  tft.setTextColor(TFT_WHITE, bannerColor);
  tft.setCursor(64, 30);
  tft.print("TruthPod");

  // Draw subtitle below banner
  tft.setTextSize(1);
  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.setCursor(10, 84);
  tft.print("A quick news verification assistant");

  // Small progress dots animation (3 steps)
  int px = tft.width() - 60;
  int py = 82;
  for (int i = 0; i < 3; i++) {
    tft.fillCircle(px + i * 12, py, 4, TFT_YELLOW);
    delay(150);
  }

  delay(400);
}

void displayNewsArticle(int index) {
  if (index < 0 || index >= totalArticles) return;
  
  NewsArticle article = newsArticles[index];
  
  // Clear screen
  tft.fillScreen(TFT_BLACK);
  
  // Set background color based on confidence
  uint16_t bgColor = TFT_BLACK;
  if (article.confidence >= 0.80) {
    bgColor = TFT_DARKGREEN;
  } else if (article.confidence >= 0.50) {
    bgColor = 0xFD20;  // Orange/Yellow
  } else {
    bgColor = TFT_MAROON;
  }
  
  // Draw header with confidence color
  tft.fillRect(0, 0, tft.width(), 40, bgColor);
  tft.setTextColor(TFT_WHITE, bgColor);
  tft.setTextSize(1);
  tft.setCursor(5, 5);
  tft.print("Source: ");
  tft.println(article.source);
  tft.setCursor(5, 20);
  tft.print("Confidence: ");
  tft.print((int)(article.confidence * 100));
  tft.println("%");
  
  // Display title
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(5, 50);
  
  // Word wrap title
  String title = article.title;
  int lineWidth = 0;
  int lineCount = 0;
  int maxLinePixels = tft.width() - 20; // leave margin
  for (int i = 0; i < title.length() && lineCount < 4; i++) {
    char c = title.charAt(i);
    tft.print(c);
    lineWidth += 12;  // Approximate character width
    if (lineWidth >= maxLinePixels || (c == ' ' && lineWidth >= (maxLinePixels - 50))) {
      tft.println();
      tft.setCursor(5, 50 + (++lineCount * 20));
      lineWidth = 0;
    }
  }
  
  // Display navigation hint
  tft.setTextSize(1);
  tft.setCursor(5, 220);
  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.print("Article ");
  tft.print(index + 1);
  tft.print(" of ");
  tft.println(totalArticles);
  tft.setCursor(5, 230);
  tft.println("Press VOICE to hear");
  
  // Set LED based on confidence
  setLEDByConfidence(article.confidence);
  
  currentArticleIndex = index;
}

// ===== Button Handlers =====
void handleVoiceButton() {
  Serial.println("Voice button pressed");
  
  // Check if we have a current article to read
  if (totalArticles > 0 && currentArticleIndex < totalArticles) {
    // Play audio for current article
  displayStatus("Playing audio...", TFT_BLUE);
  setLED(false, true);
    playNewsAudio(newsArticles[currentArticleIndex].id);
    displayNewsArticle(currentArticleIndex);
  } else {
    // Record voice query
  displayStatus("Recording...", TFT_RED);
  setLED(true, false);
    recordAndTranscribe();
  }
}

void handleNextButton() {
  Serial.println("Next button pressed");
  if (totalArticles > 0) {
    currentArticleIndex = (currentArticleIndex + 1) % totalArticles;
    displayNewsArticle(currentArticleIndex);
  }
}

void handleBackButton() {
  Serial.println("Back button pressed");
  if (totalArticles > 0) {
    currentArticleIndex = (currentArticleIndex - 1 + totalArticles) % totalArticles;
    displayNewsArticle(currentArticleIndex);
  }
}

// ===== Voice Recording and Transcription =====
void recordAndTranscribe() {
  // Allocate buffer for audio data with PSRAM-aware fallback and shrinking
  size_t desiredSize = RECORD_SIZE;
  uint8_t* audioBuffer = nullptr;
  Serial.print("Attempting audio buffer allocation, desired bytes: ");
  Serial.println(desiredSize);
  while (desiredSize >= 1024) {
    // Try PSRAM first if available
#ifdef ESP32
    if (psramFound()) {
      audioBuffer = (uint8_t*)ps_malloc(desiredSize);
      if (audioBuffer) {
        Serial.print("Allocated "); Serial.print(desiredSize); Serial.println(" bytes in PSRAM");
      }
    }
#endif
    if (!audioBuffer) {
      audioBuffer = (uint8_t*)malloc(desiredSize);
      if (audioBuffer) {
        Serial.print("Allocated "); Serial.print(desiredSize); Serial.println(" bytes in heap");
      }
    }
    if (audioBuffer) break;
    // halve the requested buffer and try again
    desiredSize /= 2;
    Serial.print("Allocation failed, trying smaller buffer: ");
    Serial.println(desiredSize);
  }
  if (!audioBuffer) {
    Serial.println("Failed to allocate audio buffer");
    displayStatus("Memory error!", TFT_RED);
    return;
  }
  
  // Record audio
  size_t bytesRead = 0;
  size_t totalBytesRead = 0;
  
  Serial.println("Recording audio...");
  unsigned long startTime = millis();
  
  // Read up to the allocated buffer size (desiredSize). Also respect RECORD_TIME timeout.
  while (totalBytesRead < desiredSize && (millis() - startTime) < (RECORD_TIME * 1000)) {
    size_t toRead = desiredSize - totalBytesRead;
    i2s_read(I2S_NUM_0, audioBuffer + totalBytesRead, toRead, &bytesRead, portMAX_DELAY);
    totalBytesRead += bytesRead;
  }
  
  Serial.print("Recorded ");
  Serial.print(totalBytesRead);
  Serial.println(" bytes");
  Serial.print("Free heap after record: ");
  Serial.println(ESP.getFreeHeap());
  
  // Prepare WAV container (16-bit PCM mono) and encode to base64
  // Prepare WAV header separately and stream-encode header+audio without
  // allocating a contiguous wav buffer (helps devices without PSRAM)
  int wavHeaderSize = 44;
  uint8_t wavHeader[44];
  // ChunkID "RIFF"
  wavHeader[0] = 'R'; wavHeader[1] = 'I'; wavHeader[2] = 'F'; wavHeader[3] = 'F';
  uint32_t subchunk2Size = totalBytesRead;
  uint32_t chunkSize = 36 + subchunk2Size;
  memcpy(wavHeader + 4, &chunkSize, 4);
  // Format "WAVE"
  wavHeader[8] = 'W'; wavHeader[9] = 'A'; wavHeader[10] = 'V'; wavHeader[11] = 'E';
  // Subchunk1ID "fmt "
  wavHeader[12] = 'f'; wavHeader[13] = 'm'; wavHeader[14] = 't'; wavHeader[15] = ' ';
  uint32_t subchunk1Size = 16;
  memcpy(wavHeader + 16, &subchunk1Size, 4);
  uint16_t audioFormat = 1;
  memcpy(wavHeader + 20, &audioFormat, 2);
  uint16_t numChannels = 1;
  memcpy(wavHeader + 22, &numChannels, 2);
  uint32_t sampleRate = SAMPLE_RATE;
  memcpy(wavHeader + 24, &sampleRate, 4);
  uint16_t bitsPerSample = 16;
  uint32_t byteRate = SAMPLE_RATE * numChannels * (bitsPerSample / 8);
  memcpy(wavHeader + 28, &byteRate, 4);
  uint16_t blockAlign = numChannels * (bitsPerSample / 8);
  memcpy(wavHeader + 32, &blockAlign, 2);
  memcpy(wavHeader + 34, &bitsPerSample, 2);
  wavHeader[36] = 'd'; wavHeader[37] = 'a'; wavHeader[38] = 't'; wavHeader[39] = 'a';
  memcpy(wavHeader + 40, &subchunk2Size, 4);

  // Encode header + audio without allocating a full wavBuf
  String base64Audio = base64_encode_two_parts(wavHeader, wavHeaderSize, audioBuffer, totalBytesRead);
  free(audioBuffer);
  
  // Send to backend for transcription
  displayStatus("Transcribing...", TFT_YELLOW);
  setLED(false, true);
  
  // Send as WAV container base64 to backend
  String payload = "{\"audio_base64\":\"" + base64Audio + "\",\"mime_type\":\"audio/wav\"}";
  String response = "";
  
  if (makeAPICall("/api/iot/voice/transcribe", "POST", payload, response)) {
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, response);
    
    if (!error) {
      String transcription = doc["transcription"].as<String>();
      Serial.print("Transcribed: ");
      Serial.println(transcription);
      String tlow = transcription;
      tlow.toLowerCase();
      if (tlow.indexOf("test mode") >= 0) {
        Serial.println("Activation phrase detected: entering test mode");
        testMode = true;
        // persist for convenience (optional)
        preferences.putBool("test_mode", true);
        runHardwareTest();
        return;
      }
      
      // Search for news based on transcription
      if (transcription.length() > 0) {
        fetchSearchNews(transcription);
        if (totalArticles > 0) {
          displayNewsArticle(0);
        } else {
          displayStatus("No results found", TFT_RED);
        }
      }
    } else {
      Serial.println("Failed to parse transcription response");
      displayStatus("Transcription failed", TFT_RED);
    }
  } else {
    Serial.println("Transcription request failed");
    // If server rejected the payload with 400, try an alternate payload shape some backends expect
    if (lastHttpResponseCode == 400) {
      Serial.println("Attempting alternate upload format (audio_data/wav)...");
      String altPayload = "{\"audio_data\":\"" + base64Audio + "\",\"format\":\"wav\",\"sample_rate\":" + String(SAMPLE_RATE) + "}";
      String altResponse = "";
      if (makeAPICall("/api/iot/voice/transcribe", "POST", altPayload, altResponse)) {
        StaticJsonDocument<512> doc2;
        DeserializationError err2 = deserializeJson(doc2, altResponse);
        if (!err2) {
          String transcription = doc2["transcription"].as<String>();
          Serial.print("Transcribed (alt): "); Serial.println(transcription);
          if (transcription.length() > 0) {
            fetchSearchNews(transcription);
            if (totalArticles > 0) {
              displayNewsArticle(0);
            } else {
              displayStatus("No results found", TFT_RED);
            }
          }
          return;
        } else {
          Serial.println("Failed to parse alternate transcription response");
          displayStatus("Transcription failed", TFT_RED);
        }
      } else {
        Serial.println("Alternate upload also failed");
        displayStatus("Transcription failed", TFT_RED);
      }
    } else {
      displayStatus("Connection error", TFT_RED);
    }
  }
}

// ===== Fetch Trending News =====
void fetchTrendingNews() {
  String response = "";
  
  // Backend trending endpoint: /api/iot/trending?region=in&limit=5
  // Note: Backend doesn't support category parameter, only region and limit
  if (makeAPICall("/api/iot/trending?region=in&limit=5", "GET", "", response)) {
    parseNewsResponse(response);
    // If backend returned zero articles, fall back to compiled demo data
    if (totalArticles == 0) {
      Serial.println("Backend returned 0 articles: using fallback news");
      // copy fallback into newsArticles
      totalArticles = min(10, fallbackCount);
      for (int i = 0; i < totalArticles; ++i) {
        newsArticles[i] = fallbackNews[i];
      }
      currentArticleIndex = 0;
      // persist fallback into preferences for later debugging
      StaticJsonDocument<1024> doc;
      JsonArray arr = doc.createNestedArray("data");
      for (int i = 0; i < totalArticles; ++i) {
        JsonObject o = arr.createNestedObject();
        o["news_id"] = newsArticles[i].id;
        o["headline"] = newsArticles[i].title;
        o["source"] = newsArticles[i].source;
        o["confidence"] = newsArticles[i].confidence;
      }
      String serialized; serializeJson(doc, serialized);
      preferences.putString("fallback_news", serialized);
      // attempt to upload fallback to backend for seeding (best-effort)
      String uploadResp;
      String uploadPayload = "{";
      uploadPayload += "\"data\":";
      uploadPayload += serialized;
      uploadPayload += "}";
      if (makeAPICall("/api/iot/news/import", "POST", uploadPayload, uploadResp)) {
        Serial.println("Fallback news uploaded to backend (if endpoint supported)");
      } else {
        Serial.println("Failed to upload fallback news to backend (ignored)");
      }
    }
  } else {
    Serial.println("Failed to fetch trending news: using fallback news");
    // copy fallback into newsArticles
    totalArticles = min(10, fallbackCount);
    for (int i = 0; i < totalArticles; ++i) {
      newsArticles[i] = fallbackNews[i];
    }
    currentArticleIndex = 0;
  }
}

// ===== Fetch Search News =====
void fetchSearchNews(String query) {
  // Backend search endpoint: /api/iot/search?query=<text>&limit=10
  String endpoint = "/api/iot/search?query=" + urlEncode(query) + "&limit=10";
  String response = "";
  
  if (makeAPICall(endpoint, "GET", "", response)) {
    parseNewsResponse(response);
  } else {
    Serial.println("Failed to fetch search news");
  }
}

void parseNewsResponse(String response) {
  StaticJsonDocument<4096> doc;
  DeserializationError error = deserializeJson(doc, response);
  
  if (error) {
    Serial.println("Failed to parse news response");
    totalArticles = 0;
    return;
  }
  
  // Backend returns {"data": [{"news_id": "...", "headline": "...", "source": "...", "confidence": 0.95, "url": "..."}]}
  JsonArray articles = doc["data"];
  totalArticles = min((int)articles.size(), 10);
  
  Serial.print("Parsed ");
  Serial.print(totalArticles);
  Serial.println(" articles");
  
  for (int i = 0; i < totalArticles; i++) {
    JsonObject article = articles[i];
    newsArticles[i].id = article["news_id"].as<String>();  // Changed from "id" to "news_id"
    newsArticles[i].title = article["headline"].as<String>();  // Changed from "title" to "headline"
    newsArticles[i].source = article["source"].as<String>();
    newsArticles[i].description = "";  // Backend doesn't return description in list
    newsArticles[i].confidence = article["confidence"] | 0.75;
    newsArticles[i].publishedAt = "";  // Backend doesn't return publishedAt in list
  }
}

// ===== Play News Audio =====
void playNewsAudio(String newsId) {
  String endpoint = "/api/iot/news/" + newsId + "/tts";
  String response = "";
  
  if (makeAPICall(endpoint, "GET", "", response)) {
    StaticJsonDocument<16384> doc;
    DeserializationError error = deserializeJson(doc, response);
    
    if (!error) {
      // Backend returns {"audio_base64": "...", "mime_type": "audio/mpeg"}
      String base64Audio = doc["audio_base64"].as<String>();  // Changed from "audio_data" to "audio_base64"
      String mimeType = doc["mime_type"] | "audio/mpeg";  // gTTS returns MP3 by default
      
      Serial.print("Received audio (");
      Serial.print(mimeType);
      Serial.print("): ");
      Serial.print(base64Audio.length());
      Serial.println(" chars");
      
      // Decode base64 audio
      int decodedLen = base64_dec_len(base64Audio.c_str(), base64Audio.length());
      uint8_t* audioData = (uint8_t*)malloc(decodedLen);
      
      if (audioData) {
        base64_decode((char*)audioData, base64Audio.c_str(), base64Audio.length());
        
        // Choose playback method: I2S (external amp) or DAC (LM386)
#ifdef USE_LM386
        if (!dacAvailable) {
          Serial.println("DAC not available (skipped) — cannot play LM386 audio when I2S ADC is enabled");
        } else {
          // Playing compressed audio (MP3) via DAC is not implemented here.
          Serial.println("LM386 playback of decoded audio not implemented — skipping");
        }
#else
        // Play audio through I2S speaker (MAX98357A)
        size_t bytesWritten = 0;
        i2s_write(I2S_NUM_1, audioData, decodedLen, &bytesWritten, portMAX_DELAY);
        Serial.println("Audio played (I2S)");
#endif
        
        free(audioData);
      } else {
        Serial.println("Failed to allocate audio buffer");
      }
    } else {
      Serial.println("Failed to parse TTS response");
    }
  } else {
    Serial.println("Failed to fetch TTS audio");
  }
}

// ===== Handle Camera Data =====
void handleCameraData() {
  if (Serial2.available() > 0) {
    String cameraData = Serial2.readStringUntil('\n');
    Serial.print("Camera data received: ");
    Serial.println(cameraData);
    
    // Parse camera data (format: "USER_ID:123")
    if (cameraData.startsWith("USER_ID:")) {
      String userId = cameraData.substring(8);
      Serial.print("Recognized user: ");
      Serial.println(userId);
      
      // Display welcome message
      tft.fillScreen(TFT_BLACK);
      tft.setTextColor(TFT_GREEN, TFT_BLACK);
      tft.setTextSize(2);
      tft.setCursor(50, 100);
      tft.print("Welcome User ");
      tft.println(userId);
      
  setLED(false, true);
      delay(2000);
      
      // Load personalized news if available
      // fetchTrendingNews();  // Could be personalized based on user preferences
      displayNewsArticle(currentArticleIndex);
    }
  }
}

// ===== API Helper Functions =====
bool makeAPICall(String endpoint, String method, String payload, String& response) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected");
    return false;
  }
  
  String url = String(API_BASE_URL) + endpoint;
  Serial.print("API Call: ");
  Serial.print(method);
  Serial.print(" ");
  Serial.println(url);
  // Use a secure client for HTTPS but allow insecure fallback (setInsecure)
  WiFiClientSecure *secureClient = nullptr;
  if (url.startsWith("https://")) {
    secureClient = new WiFiClientSecure();
    // WARNING: setInsecure() disables certificate verification. This is
    // acceptable for local/demo use but not recommended for production.
    secureClient->setInsecure();
    http.begin(*secureClient, url);
  } else {
    http.begin(url);
  }
  http.addHeader("Content-Type", "application/json");
  
  // Add authorization header if we have a token
  if (deviceToken.length() > 0) {
    http.addHeader("Authorization", "Bearer " + deviceToken);
  }
  
  int httpResponseCode;
  
  if (method == "POST") {
    httpResponseCode = http.POST(payload);
  } else if (method == "GET") {
    httpResponseCode = http.GET();
  } else {
    http.end();
    return false;
  }
  
  Serial.print("Response code: ");
  Serial.println(httpResponseCode);
  
  if (httpResponseCode > 0) {
    response = http.getString();
    http.end();
    // remember last HTTP code for callers that want to inspect
    lastHttpResponseCode = httpResponseCode;
    // Log non-2xx response body for debugging (print up to 1024 chars)
    if (!(httpResponseCode >= 200 && httpResponseCode < 300)) {
      Serial.print("API non-2xx response code: ");
      Serial.println(httpResponseCode);
      Serial.print("API non-2xx response body: ");
      if (response.length() > 1024) Serial.println(response.substring(0,1024)); else Serial.println(response);
    }
    // Treat any 2xx response as success (201 Created from register endpoint is valid)
    if (secureClient) {
      secureClient->stop();
      delete secureClient;
      secureClient = nullptr;
    }
    return (httpResponseCode >= 200 && httpResponseCode < 300);
  } else {
    Serial.print("HTTP Error: ");
    Serial.println(httpResponseCode);
    http.end();
    if (secureClient) {
      secureClient->stop();
      delete secureClient;
      secureClient = nullptr;
    }
    return false;
  }
}

String urlEncode(String str) {
  String encodedString = "";
  char c;
  for (int i = 0; i < str.length(); i++) {
    c = str.charAt(i);
    if (isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~') {
      encodedString += c;
    } else if (c == ' ') {
      encodedString += '+';
    } else {
      encodedString += '%';
      char hex[3];
      sprintf(hex, "%02X", c);
      encodedString += hex;
    }
  }
  return encodedString;
}

// Very small JSON string escaper for double-quotes, backslashes and control chars
String jsonEscape(const String &s) {
  String out;
  out.reserve(s.length() + 16);
  for (size_t i = 0; i < s.length(); ++i) {
    char c = s.charAt(i);
    switch (c) {
      case '\\': out += "\\\\"; break;
      case '"': out += "\\\""; break;
      case '\n': out += "\\n"; break;
      case '\r': out += "\\r"; break;
      case '\t': out += "\\t"; break;
      default:
        if ((unsigned char)c < 0x20) {
          char buf[7];
          sprintf(buf, "\\u%04x", (int)c);
          out += buf;
        } else {
          out += c;
        }
    }
  }
  return out;
}
