/*
  TruthPod ESP32 example (Arduino)

  - Connects to WiFi
  - Registers device and stores api_token in NVS (Preferences)
  - Fetches trending news using the token
  - Placeholders for face capture/enroll/recognize (requires camera + base64 library)

  Notes:
  - Install Arduino board "esp32" and addLibraries: WiFi, HTTPClient, Preferences
  - For image capture use the ESP32-CAM libraries; for base64 encoding use a base64 utility.
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <Preferences.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* pass = "YOUR_WIFI_PASSWORD";
const char* base_url = "http://192.168.1.100:8000"; // set to your backend

Preferences prefs;

String register_device(const char* mac) {
  HTTPClient http;
  String url = String(base_url) + "/api/iot/device/register";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  String body = String("{\"device_mac\":\"") + mac + String("\",\"device_name\":\"ESP32-Dev\",\"device_type\":\"ESP32\"}");
  int code = http.POST(body);
  String resp = "";
  if (code == 201 || code == 200) {
    resp = http.getString();
  }
  http.end();
  return resp;
}

String get_trending(const String& token, int limit=5) {
  HTTPClient http;
  String url = String(base_url) + "/api/iot/trending?limit=" + String(limit);
  http.begin(url);
  http.addHeader("Authorization", "Bearer " + token);
  int code = http.GET();
  String resp = "";
  if (code == 200) resp = http.getString();
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

void setup() {
  Serial.begin(115200);
  delay(1000);
  WiFi.begin(ssid, pass);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print('.');
  }
  Serial.println("\nConnected");

  // Try load token
  String token = load_token();
  if (token.length() == 0) {
    // Register using MAC address
    String mac = WiFi.macAddress();
    Serial.println("Registering device with MAC: " + mac);
    String resp = register_device(mac.c_str());
    Serial.println("Register response: " + resp);
    // Simple parsing to extract api_token (quick, not robust)
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

  if (token.length() > 0) {
    Serial.println("Fetching trending news...");
    String trending = get_trending(token, 3);
    Serial.println(trending);
  } else {
    Serial.println("No token available; registration may have failed.");
  }
}

void loop() {
  // Placeholder: main device loop
  delay(10000);
}

// Face enroll/recognize hints (not implemented here):
// - Capture JPEG from camera, resize to 320x240
// - Base64-encode the JPEG bytes
// - POST JSON { "user_name": "Alice", "image_base64": "..." } to /api/iot/face/enroll
// - POST JSON { "image_base64": "..." } to /api/iot/face/recognize
