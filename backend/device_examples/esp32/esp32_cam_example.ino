/*
  TruthPod ESP32-CAM example (Arduino)

  - Initializes the AI-Thinker ESP32-CAM module
  - Connects to WiFi
  - Registers device and stores api_token in Preferences
  - Captures a JPEG image, base64-encodes it, and POSTs to /api/iot/face/recognize
  - Shows how to enroll a face by POSTing to /api/iot/face/enroll

  Notes:
  - Requires the ESP32 board support and the "ESP32" core (AI-Thinker config)
  - Install libraries: WiFi, HTTPClient, Preferences, esp_camera
  - Configure CAMERA_MODEL_AI_THINKER pins below for AI-Thinker board
*/

#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <Update.h>

// --- Configure your WiFi + backend ---
const char* ssid = "YOUR_WIFI_SSID";
const char* pass = "YOUR_WIFI_PASSWORD";
const char* base_url = "http://192.168.1.100:8000"; // backend

Preferences prefs;

// --- AI-Thinker camera pins ---
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

String base64_encode(const uint8_t *data, size_t input_length) {
  static const char encoding_table[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  String encoded = "";
  encoded.reserve((input_length + 2) / 3 * 4);

  for (size_t i = 0; i < input_length; i += 3) {
    uint32_t octet_a = i < input_length ? data[i] : 0;
    uint32_t octet_b = (i + 1) < input_length ? data[i + 1] : 0;
    uint32_t octet_c = (i + 2) < input_length ? data[i + 2] : 0;

    uint32_t triple = (octet_a << 16) + (octet_b << 8) + octet_c;

    encoded += encoding_table[(triple >> 18) & 0x3F];
    encoded += encoding_table[(triple >> 12) & 0x3F];
    encoded += (i + 1) < input_length ? encoding_table[(triple >> 6) & 0x3F] : '=';
    encoded += (i + 2) < input_length ? encoding_table[triple & 0x3F] : '=';
  }
  return encoded;
}

void init_camera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_QVGA; // 320x240 to keep payload small
  config.jpeg_quality = 10; // 0-63 lower means higher quality (and larger size)
  config.fb_count = 1;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    while (true) { delay(1000); }
  }
}

String register_device(const char* mac) {
  HTTPClient http;
  String url = String(base_url) + "/api/iot/device/register";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  String body = String("{\"device_mac\":\"") + mac + String("\",\"device_name\":\"ESP32-CAM\",\"device_type\":\"ESP32-CAM\"}");
  int code = http.POST(body);
  String resp = "";
  if (code == 201 || code == 200) {
    resp = http.getString();
  }
  http.end();
  return resp;
}

void save_token(const String& token) {
  prefs.begin("truthpod", false);
  prefs.putString("api_token", token);
  prefs.end();
}

String load_token() {
  prefs.begin("truthpod", true);
  String t = prefs.getString("api_token", "");
  prefs.end();
  return t;
}

String post_face_recognize(const String& token, const String& image_b64) {
  HTTPClient http;
  String url = String(base_url) + "/api/iot/face/recognize";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", "Bearer " + token);
  String body = String("{\"image_base64\":\"") + image_b64 + String("\"}");
  int code = http.POST(body);
  String resp = "";
  if (code == 200) resp = http.getString();
  http.end();
  return resp;
}

String post_face_enroll(const String& token, const String& image_b64, const String& user_name) {
  HTTPClient http;
  String url = String(base_url) + "/api/iot/face/enroll";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", "Bearer " + token);
  String body = String("{\"user_name\":\"") + user_name + String("\",\"image_base64\":\"") + image_b64 + String("\"}");
  int code = http.POST(body);
  String resp = "";
  if (code == 200 || code == 201) resp = http.getString();
  http.end();
  return resp;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print('.');
  }
  Serial.println("\nConnected");

  init_camera();

  // Register device if token not present
  String token = load_token();
  if (token.length() == 0) {
    String mac = WiFi.macAddress();
    Serial.println("Registering device with MAC: " + mac);
    String resp = register_device(mac.c_str());
    Serial.println("Register response: " + resp);
    int i = resp.indexOf("api_token");
    if (i >= 0) {
      int q = resp.indexOf('"', i + 11);
      int q2 = resp.indexOf('"', q + 1);
      String tokenVal = resp.substring(q + 1, q2);
      save_token(tokenVal);
      token = tokenVal;
      Serial.println("Saved token");
    }
  }

  // Capture and recognize a face
  if (token.length() > 0) {
    camera_fb_t * fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Camera capture failed");
    } else {
      Serial.printf("Captured %u bytes\n", fb->len);
      // base64 encode
      String b64 = base64_encode(fb->buf, fb->len);
      // keep payload size in mind; you can also shrink image before encoding by setting frame_size lower
      Serial.println("Posting to /api/iot/face/recognize (payload size: " + String(b64.length()) + ")");
      String res = post_face_recognize(token, b64);
      Serial.println("Recognize response: " + res);

      // Example enroll call (uncomment to enroll):
      // String enrollRes = post_face_enroll(token, b64, "TestUser");
      // Serial.println("Enroll response: " + enrollRes);

      esp_camera_fb_return(fb);
    }
  }

  // Check for OTA and apply if available
  delay(2000);
  Serial.println("Checking for OTA firmware...");
  // firmware_latest is public; no auth required for this endpoint
  HTTPClient http;
  String latestUrl = String(base_url) + "/api/iot/firmware/latest?device_type=ESP32";
  http.begin(latestUrl);
  int code = http.GET();
  if (code == 200) {
    String res = http.getString();
    Serial.println("Firmware latest response: " + res);
    if (res.indexOf("\"available\": true") >= 0) {
      int i = res.indexOf("\"url\":");
      if (i >= 0) {
        int q1 = res.indexOf('"', i + 6);
        int q2 = res.indexOf('"', q1 + 1);
        String fwUrl = res.substring(q1 + 1, q2);
        Serial.println("Found firmware URL: " + fwUrl);
        // perform OTA
        String fullUrl = String(base_url) + fwUrl;
        Serial.println("Downloading firmware: " + fullUrl);
        HTTPClient http2;
        http2.begin(fullUrl);
        int code2 = http2.GET();
        if (code2 == 200) {
          int contentLength = http2.getSize();
          WiFiClient * stream = http2.getStreamPtr();
          if (contentLength > 0) {
            Serial.println("Starting OTA, size=" + String(contentLength));
            if (!Update.begin(contentLength)) {
              Serial.println("Not enough space for OTA");
            } else {
              size_t written = Update.writeStream(*stream);
              if (written == (size_t)contentLength) {
                Serial.println("Written : " + String(written) + " bytes");
              } else {
                Serial.println("Written only " + String(written) + " of " + String(contentLength));
              }
              if (Update.end()) {
                if (Update.isFinished()) {
                  Serial.println("OTA success — rebooting...");
                  delay(1000);
                  ESP.restart();
                } else {
                  Serial.println("OTA not finished.");
                }
              } else {
                Serial.printf("OTA error #%d\n", Update.getError());
              }
            }
          } else {
            Serial.println("Content-Length not provided or zero");
          }
        } else {
          Serial.println("Failed to download firmware, code=" + String(code2));
        }
        http2.end();
      }
    }
  } else {
    Serial.println("Firmware latest check failed, code=" + String(code));
  }
  http.end();
}

void loop() {
  // Optionally send heartbeat periodically
  delay(60000);
}
