/**
 * TruthPod ESP32-CAM Firmware
 * Face Recognition Module for TruthPod
 * 
 * Features:
 * - Camera initialization (OV2640)
 * - Face capture on button press
 * - Face enrollment and recognition via backend API
 * - UART communication with main ESP32 board
 * - LED status indicators
 * 
 * Hardware:
 * - ESP32-CAM (AI-Thinker)
 * - OV2640 Camera
 * - Push button for capture
 * - Built-in LED for status
 * 
 * Communication Protocol with Main Board:
 * - Send: "USER_ID:123\n" when face recognized
 * - Send: "NO_FACE\n" when no face detected
 * - Send: "ENROLL_OK:456\n" when enrollment successful
 */

#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <base64.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

// ===== Configuration =====
// Set to 0 while using Serial Monitor over GPIO 1/3 to avoid pin conflicts
#define ENABLE_MAINBOARD_UART 0
// WiFi Credentials (same as main board)
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Backend API Configuration
const char* API_BASE_URL = "https://your-backend.onrender.com";
// const char* API_BASE_URL = "http://192.168.1.100:8000";  // Or use local IP for testing

// Device Configuration
String deviceMAC = "";
String deviceToken = "";  // Will be shared from main board via UART or get own token
Preferences preferencesCam;

// ===== Pin Definitions (ESP32-CAM AI-Thinker) =====
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

// Button and LED
#define BUTTON_PIN        13  // Flash button on ESP32-CAM
#define LED_PIN            4  // Built-in LED (flash LED)
#define STATUS_LED        33  // GPIO 33 for external status LED (optional)

// UART pins for communication with main board
#define UART_TX            1  // TX (to main board RX)
#define UART_RX            3  // RX (from main board TX)

// ===== Global Variables =====
HTTPClient http;
bool cameraInitialized = false;
bool enrollMode = false;  // Toggle between recognize and enroll modes

// ===== Function Prototypes =====
void setupWiFi();
void setupCamera();
void setupButton();
void setupLED();
void setupUART();
void registerDevice();
bool loadDeviceToken();
void saveDeviceToken(String token);
void captureAndRecognize();
void captureAndEnroll();
camera_fb_t* captureImage();
void sendToMainBoard(String message);
bool makeAPICall(String endpoint, String method, String payload, String& response);
void blinkLED(int times, int delayMs);

// ===== Setup =====
void setup() {
  // Disable brownout detector to prevent resets on power fluctuations
  // Note: Only do this if you have stable 5V power
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  delay(2000);  // Give time for serial to stabilize
  
  Serial.println();
  Serial.println("=== TruthPod ESP32-CAM Starting ===");
  Serial.println("Setup: Phase 1 - Hardware Init");
  
  // Setup hardware
  setupButton();
  Serial.println("Setup: Button OK");
  
  setupLED();
  Serial.println("Setup: LED OK");
  
  #if ENABLE_MAINBOARD_UART
  setupUART();
  Serial.println("Setup: UART OK");
  #endif
  
  // Prepare WiFi and preferences
  WiFi.mode(WIFI_STA);
  preferencesCam.begin("truthpod_cam", false);

  // Get device MAC address (after WiFi mode set)
  deviceMAC = WiFi.macAddress();
  Serial.print("Camera MAC: ");
  Serial.println(deviceMAC);
  
  Serial.println("Setup: Phase 2 - Camera Init");
  setupCamera();
  Serial.println("Setup: Camera OK");
  
  // Connect to WiFi
  Serial.println("Setup: Phase 3 - WiFi Connect");
  blinkLED(3, 200);  // Indicate starting
  setupWiFi();

  // Obtain device token (either from storage or via registration)
  Serial.println("Setup: Phase 4 - Device Registration");
  if (!loadDeviceToken()) {
    Serial.println("Token: Not found in storage, registering device...");
    registerDevice();
  } else {
    Serial.println("Token: Loaded from storage");
  }
  
  // Verify we have a valid token
  if (deviceToken.length() > 0) {
    Serial.print("Token: Active (length=");
    Serial.print(deviceToken.length());
    Serial.println(")");
  } else {
    Serial.println("Token: WARNING - No token available! API calls will fail with 401/403.");
    Serial.println("Token: Check network connection or backend availability.");
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    blinkLED(2, 500);  // Indicate WiFi connected
  } else {
    blinkLED(5, 100);  // Indicate WiFi failed
  }
  
  Serial.println("ESP32-CAM ready!");
  Serial.println("Press button to capture and recognize face");
}

// ===== Main Loop =====
void loop() {
  // Check WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected! Reconnecting...");
    setupWiFi();
    return;
  }
  
  // Check button press
  if (digitalRead(BUTTON_PIN) == LOW) {
    delay(50);  // Debounce
    if (digitalRead(BUTTON_PIN) == LOW) {
      Serial.println("Button pressed!");
      
      // Check for long press (hold for 3 seconds to enroll)
      unsigned long pressStart = millis();
      while (digitalRead(BUTTON_PIN) == LOW && (millis() - pressStart) < 3000) {
        delay(10);
      }
      
      unsigned long pressDuration = millis() - pressStart;
      
      if (pressDuration >= 3000) {
        // Long press - Enroll mode
        Serial.println("Long press detected - Enroll mode");
        digitalWrite(LED_PIN, HIGH);
        delay(500);
        digitalWrite(LED_PIN, LOW);
        delay(200);
        digitalWrite(LED_PIN, HIGH);
        delay(500);
        digitalWrite(LED_PIN, LOW);
        captureAndEnroll();
      } else {
        // Short press - Recognize mode
        Serial.println("Short press detected - Recognize mode");
        digitalWrite(LED_PIN, HIGH);
        captureAndRecognize();
        digitalWrite(LED_PIN, LOW);
      }
      
      // Wait for button release
      while (digitalRead(BUTTON_PIN) == LOW) delay(10);
    }
  }
  
  // Check for commands from main board via UART
  if (Serial2.available() > 0) {
    String command = Serial2.readStringUntil('\n');
    Serial.print("Received command: ");
    Serial.println(command);
    
    if (command == "CAPTURE") {
      captureAndRecognize();
    } else if (command == "ENROLL") {
      captureAndEnroll();
    } else if (command.startsWith("TOKEN:")) {
      // Receive device token from main board
      deviceToken = command.substring(6);
      Serial.println("Device token received from main board");
    }
  }
  
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
  }
}

// ===== Camera Setup =====
void setupCamera() {
  Serial.println("Camera: Configuring...");
  
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
  config.grab_mode = CAMERA_GRAB_LATEST;  // Add this to prevent buffer issues
  
  Serial.println("Camera: Checking PSRAM...");
  // Init with high specs for face detection
  if (psramFound()) {
    Serial.println("Camera: PSRAM found, using high quality");
    config.frame_size = FRAMESIZE_QVGA;  // 320x240
    config.jpeg_quality = 10;
    config.fb_count = 2;
    config.fb_location = CAMERA_FB_IN_PSRAM;
  } else {
    Serial.println("Camera: WARNING - No PSRAM! Using minimal config");
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }
  
  Serial.println("Camera: Initializing...");
  // Initialize camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init FAILED with error 0x%x\n", err);
    cameraInitialized = false;
    // Don't return - let setup continue
    Serial.println("Camera: Continuing without camera...");
    return;
  }
  
  Serial.println("Camera: Init SUCCESS!");
  cameraInitialized = true;
  
  // Adjust camera settings
  sensor_t* s = esp_camera_sensor_get();
  if (s != NULL) {
    s->set_brightness(s, 0);     // -2 to 2
    s->set_contrast(s, 0);       // -2 to 2
    s->set_saturation(s, 0);     // -2 to 2
    s->set_special_effect(s, 0); // 0 to 6 (0 - No Effect)
    s->set_whitebal(s, 1);       // 0 = disable , 1 = enable
    s->set_awb_gain(s, 1);       // 0 = disable , 1 = enable
    s->set_wb_mode(s, 0);        // 0 to 4
    s->set_exposure_ctrl(s, 1);  // 0 = disable , 1 = enable
    s->set_aec2(s, 0);           // 0 = disable , 1 = enable
    s->set_gain_ctrl(s, 1);      // 0 = disable , 1 = enable
    s->set_agc_gain(s, 0);       // 0 to 30
    s->set_gainceiling(s, (gainceiling_t)0);  // 0 to 6
    s->set_bpc(s, 0);            // 0 = disable , 1 = enable
    s->set_wpc(s, 1);            // 0 = disable , 1 = enable
    s->set_raw_gma(s, 1);        // 0 = disable , 1 = enable
    s->set_lenc(s, 1);           // 0 = disable , 1 = enable
    s->set_hmirror(s, 0);        // 0 = disable , 1 = enable
    s->set_vflip(s, 0);          // 0 = disable , 1 = enable
    s->set_dcw(s, 1);            // 0 = disable , 1 = enable
  }
}

// ===== Button Setup =====
void setupButton() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
}

// ===== LED Setup =====
void setupLED() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  #ifdef STATUS_LED
  pinMode(STATUS_LED, OUTPUT);
  digitalWrite(STATUS_LED, LOW);
  #endif
}

void blinkLED(int times, int delayMs) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(delayMs);
    digitalWrite(LED_PIN, LOW);
    delay(delayMs);
  }
}

// ===== UART Setup =====
void setupUART() {
  // Use Serial2 for communication with main board
  Serial2.begin(115200, SERIAL_8N1, UART_RX, UART_TX);
  Serial.println("UART initialized for main board communication");
}

void sendToMainBoard(String message) {
  Serial2.println(message);
  Serial.print("Sent to main board: ");
  Serial.println(message);
}

// ===== Capture Image =====
camera_fb_t* captureImage() {
  if (!cameraInitialized) {
    Serial.println("Camera not initialized!");
    return NULL;
  }
  
  Serial.println("Capturing image...");
  
  // Flash LED during capture
  digitalWrite(LED_PIN, HIGH);
  
  camera_fb_t* fb = esp_camera_fb_get();
  
  digitalWrite(LED_PIN, LOW);
  
  if (!fb) {
    Serial.println("Camera capture failed");
    return NULL;
  }
  
  Serial.printf("Image captured: %d bytes, %dx%d\n", fb->len, fb->width, fb->height);
  return fb;
}

// ===== Capture and Recognize =====
void captureAndRecognize() {
  Serial.println("=== Face Recognition Mode ===");
  
  camera_fb_t* fb = captureImage();
  if (!fb) {
    sendToMainBoard("NO_FACE");
    return;
  }
  
  // Encode image to base64
  String base64Image = base64::encode(fb->buf, fb->len);
  esp_camera_fb_return(fb);
  
  // Send to backend for recognition
  // Backend expects: {"image_base64": "..."}
  String payload = "{\"image_base64\":\"" + base64Image + "\"}";
  String response = "";
  
  Serial.println("Sending to backend for recognition...");
  
  if (makeAPICall("/api/iot/face/recognize", "POST", payload, response)) {
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, response);
    
    if (!error) {
      // Backend returns: {"user_id": 123 or null, "user_name": "...", "confidence": 0.95}
      // user_id is null when user_name is "UNKNOWN"
      int userId = doc["user_id"] | 0;
      String userName = doc["user_name"] | "Unknown";
      float confidence = doc["confidence"] | 0.0;
      
      if (userId > 0 && userName != "UNKNOWN") {
        Serial.printf("Face recognized: User ID %d, Name: %s, Confidence: %.2f\n", 
                      userId, userName.c_str(), confidence);
        
        // Send to main board
        sendToMainBoard("USER_ID:" + String(userId));
        
        // Blink LED twice for success
        blinkLED(2, 200);
      } else {
        Serial.println("No matching face found");
        sendToMainBoard("NO_FACE");
        
        // Blink LED once for no match
        blinkLED(1, 500);
      }
    } else {
      Serial.println("Failed to parse recognition response");
      sendToMainBoard("ERROR");
    }
  } else {
    Serial.println("Recognition request failed");
    sendToMainBoard("ERROR");
  }
}

// ===== Capture and Enroll =====
void captureAndEnroll() {
  Serial.println("=== Face Enrollment Mode ===");
  Serial.println("Enter user name in Serial Monitor:");
  
  // Wait for user name from Serial (or could receive from main board via UART)
  unsigned long timeout = millis() + 10000;  // 10 second timeout
  String userName = "";
  
  while (userName.length() == 0 && millis() < timeout) {
    if (Serial.available() > 0) {
      userName = Serial.readStringUntil('\n');
      userName.trim();
    }
    
    // Check if name received from main board via UART
    if (Serial2.available() > 0) {
      String command = Serial2.readStringUntil('\n');
      if (command.startsWith("ENROLL_NAME:")) {
        userName = command.substring(12);
        userName.trim();
      }
    }
    
    delay(100);
  }
  
  if (userName.length() == 0) {
    Serial.println("Enrollment cancelled - no name provided");
    sendToMainBoard("ENROLL_CANCELLED");
    return;
  }
  
  Serial.print("Enrolling user: ");
  Serial.println(userName);
  
  camera_fb_t* fb = captureImage();
  if (!fb) {
    sendToMainBoard("ENROLL_FAILED");
    return;
  }
  
  // Encode image to base64
  String base64Image = base64::encode(fb->buf, fb->len);
  esp_camera_fb_return(fb);
  
  // Send to backend for enrollment
  // Backend expects: {"user_name": "...", "image_base64": "..."}
  String payload = "{\"user_name\":\"" + userName + "\",\"image_base64\":\"" + base64Image + "\"}";
  String response = "";
  
  Serial.println("Sending to backend for enrollment...");
  
  if (makeAPICall("/api/iot/face/enroll", "POST", payload, response)) {
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, response);
    
    if (!error) {
      // Backend returns: {"user_id": 123, "user_name": "...", "face_image_url": "..."}
      int userId = doc["user_id"] | 0;
      String returnedName = doc["user_name"] | "";
      String imageUrl = doc["face_image_url"] | "";
      
      Serial.printf("Enrollment successful: User ID %d, Name: %s\n", userId, returnedName.c_str());
      if (imageUrl.length() > 0) {
        Serial.printf("Image URL: %s\n", imageUrl.c_str());
      }
      
      // Send to main board
      sendToMainBoard("ENROLL_OK:" + String(userId));
      
      // Blink LED three times for success
      blinkLED(3, 300);
    } else {
      Serial.println("Failed to parse enrollment response");
      sendToMainBoard("ENROLL_FAILED");
    }
  } else {
    Serial.println("Enrollment request failed");
    sendToMainBoard("ENROLL_FAILED");
  }
}

// ===== API Helper Function =====
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
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  // Add authorization header if we have a token
  if (deviceToken.length() > 0) {
    http.addHeader("Authorization", "Bearer " + deviceToken);
    Serial.println("API: Added Authorization header");
  } else {
    Serial.println("API: WARNING - No token available, request may be rejected");
  }
  
  // Set timeout for large image uploads
  http.setTimeout(15000);  // 15 seconds
  
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
    
    // Log error responses for debugging
    if (httpResponseCode == 401 || httpResponseCode == 403) {
      Serial.println("API: Authentication/Authorization failed");
      Serial.print("API: Response body: ");
      Serial.println(response);
      
      // Try re-registering if token was rejected
      if (endpoint != "/api/iot/device/register") {
        Serial.println("API: Token may be invalid, clearing and will re-register on next boot");
        preferencesCam.remove("token");
        deviceToken = "";
      }
    }
    
    http.end();
    return (httpResponseCode == 200);
  } else {
    Serial.print("HTTP Error: ");
    Serial.println(httpResponseCode);
    http.end();
    return false;
  }
}

// ===== Device Registration & Token Storage =====
void registerDevice() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Token: WiFi not connected; cannot register");
    return;
  }

  String payload = String("{\"device_mac\":\"") + deviceMAC + "\"}";
  String response = "";

  if (makeAPICall("/api/iot/device/register", "POST", payload, response)) {
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, response);
    if (!error) {
      String token = doc["api_token"].as<String>();
      if (token.length() > 0) {
        deviceToken = token;
        saveDeviceToken(token);
        Serial.println("Token: Registration successful and saved");
      } else {
        Serial.println("Token: Registration response missing token");
      }
    } else {
      Serial.println("Token: Failed to parse registration response");
    }
  } else {
    Serial.println("Token: Device registration failed");
  }
}

bool loadDeviceToken() {
  deviceToken = preferencesCam.getString("token", "");
  return deviceToken.length() > 0;
}

void saveDeviceToken(String token) {
  preferencesCam.putString("token", token);
}
