/**
 * TruthPod ESP32 Main Board Firmware
 * Cloud-first IoT News Verification Device
 * 
 * Features:
 * - WiFi connection and device registration
 * - Voice capture via I2S microphone
 * - News API calls (trending/search)
 * - TTS audio playback via I2S speaker
 * - TFT display with color-coded confidence scores
 * - RGB LED indicators (Green/Yellow/Red)
 * - Button handlers (Voice, Next, Back)
 * - UART communication with ESP32-CAM
 * - Stateless cloud-first design
 * 
 * Hardware:
 * - ESP32 DevKit (38-pin)
 * - ILI9341 TFT Display (SPI)
 * - I2S Microphone (INMP441)
 * - I2S Speaker/Amplifier (MAX98357A)
 * - 3x Push Buttons
 * - RGB LED or 3 separate LEDs
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <TFT_eSPI.h>
#include <driver/i2s.h>
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
const char* API_BASE_URL = "https://your-backend.onrender.com";  // Change to your deployed backend URL
// const char* API_BASE_URL = "http://192.168.1.100:8000";  // Or use local IP for testing

// Device Configuration
String deviceMAC = "";
String deviceToken = "";

// ===== Pin Definitions =====
// I2S Microphone (INMP441)
#define I2S_MIC_SERIAL_CLOCK 26
#define I2S_MIC_LEFT_RIGHT_CLOCK 25
#define I2S_MIC_SERIAL_DATA 33

// I2S Speaker (MAX98357A)
#define I2S_SPEAKER_SERIAL_CLOCK 14
#define I2S_SPEAKER_LEFT_RIGHT_CLOCK 27
#define I2S_SPEAKER_SERIAL_DATA 12

// Buttons
#define BUTTON_VOICE 34
#define BUTTON_NEXT 35
#define BUTTON_BACK 32

// RGB LED (or use 3 separate pins)
#define LED_RED 16
#define LED_GREEN 17
#define LED_BLUE 18

// UART for ESP32-CAM communication
#define UART_RX 19
#define UART_TX 23

// ===== Display Configuration =====
TFT_eSPI tft = TFT_eSPI();

// ===== Global State =====
Preferences preferences;
HTTPClient http;

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

bool isRecording = false;
bool isPlayingAudio = false;

// ===== I2S Configuration =====
const int SAMPLE_RATE = 16000;
const int BITS_PER_SAMPLE = 16;
const int RECORD_TIME = 5;  // seconds
const int RECORD_SIZE = SAMPLE_RATE * RECORD_TIME * (BITS_PER_SAMPLE / 8);

// ===== Function Prototypes =====
void setupWiFi();
void setupDisplay();
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
void setLED(bool red, bool green, bool blue);
void handleVoiceButton();
void handleNextButton();
void handleBackButton();
void recordAndTranscribe();
void fetchTrendingNews();
void fetchSearchNews(String query);
void playNewsAudio(String newsId);
void handleCameraData();
bool makeAPICall(String endpoint, String method, String payload, String& response);

// ===== Setup =====
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("=== TruthPod Starting ===");
  
  // Get device MAC address
  deviceMAC = WiFi.macAddress();
  Serial.print("Device MAC: ");
  Serial.println(deviceMAC);
  
  // Initialize preferences storage
  preferences.begin("truthpod", false);
  
  // Setup hardware
  setupDisplay();
  setupButtons();
  setupLEDs();
  setupI2S();
  setupUART();
  
  // Display startup message
  displayStatus("Connecting to WiFi...", TFT_BLUE);
  setLED(false, false, true);  // Blue LED
  
  // Connect to WiFi
  setupWiFi();
  
  // Register device and get token
  if (!loadDeviceToken()) {
    displayStatus("Registering device...", TFT_YELLOW);
    setLED(false, true, true);  // Cyan LED
    registerDevice();
  }
  
  // Load trending news
  displayStatus("Loading news...", TFT_GREEN);
  setLED(false, true, false);  // Green LED
  fetchTrendingNews();
  
  // Display first article
  if (totalArticles > 0) {
    displayNewsArticle(0);
  } else {
    displayStatus("No news available", TFT_RED);
  }
}

// ===== Main Loop =====
void loop() {
  // Check WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    displayStatus("WiFi disconnected!", TFT_RED);
    setLED(true, false, false);  // Red LED
    setupWiFi();
    return;
  }
  
  // Handle button presses
  if (digitalRead(BUTTON_VOICE) == LOW) {
    delay(50);  // Debounce
    if (digitalRead(BUTTON_VOICE) == LOW) {
      handleVoiceButton();
      while (digitalRead(BUTTON_VOICE) == LOW) delay(10);
    }
  }
  
  if (digitalRead(BUTTON_NEXT) == LOW) {
    delay(50);
    if (digitalRead(BUTTON_NEXT) == LOW) {
      handleNextButton();
      while (digitalRead(BUTTON_NEXT) == LOW) delay(10);
    }
  }
  
  if (digitalRead(BUTTON_BACK) == LOW) {
    delay(50);
    if (digitalRead(BUTTON_BACK) == LOW) {
      handleBackButton();
      while (digitalRead(BUTTON_BACK) == LOW) delay(10);
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
    setLED(true, false, false);
  }
}

// ===== Display Setup =====
void setupDisplay() {
  tft.init();
  tft.setRotation(1);  // Landscape
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(0, 0);
  tft.println("TruthPod");
  tft.setTextSize(1);
  tft.println("Initializing...");
}

// ===== Button Setup =====
void setupButtons() {
  pinMode(BUTTON_VOICE, INPUT_PULLUP);
  pinMode(BUTTON_NEXT, INPUT_PULLUP);
  pinMode(BUTTON_BACK, INPUT_PULLUP);
}

// ===== LED Setup =====
void setupLEDs() {
  pinMode(LED_RED, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_BLUE, OUTPUT);
  setLED(false, false, false);
}

void setLED(bool red, bool green, bool blue) {
  digitalWrite(LED_RED, red ? HIGH : LOW);
  digitalWrite(LED_GREEN, green ? HIGH : LOW);
  digitalWrite(LED_BLUE, blue ? HIGH : LOW);
}

void setLEDByConfidence(float confidence) {
  if (confidence >= 0.80) {
    setLED(false, true, false);  // Green - Verified
  } else if (confidence >= 0.50) {
    setLED(true, true, false);   // Yellow - Questionable
  } else {
    setLED(true, false, false);  // Red - Fake/Unverified
  }
}

// ===== I2S Setup =====
void setupI2S() {
  // Configure I2S for microphone (input)
  i2s_config_t i2s_mic_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 4,
    .dma_buf_len = 1024,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };
  
  i2s_pin_config_t mic_pin_config = {
    .bck_io_num = I2S_MIC_SERIAL_CLOCK,
    .ws_io_num = I2S_MIC_LEFT_RIGHT_CLOCK,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = I2S_MIC_SERIAL_DATA
  };
  
  i2s_driver_install(I2S_NUM_0, &i2s_mic_config, 0, NULL);
  i2s_set_pin(I2S_NUM_0, &mic_pin_config);
  
  // Configure I2S for speaker (output)
  i2s_config_t i2s_speaker_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 4,
    .dma_buf_len = 1024,
    .use_apll = false,
    .tx_desc_auto_clear = true,
    .fixed_mclk = 0
  };
  
  i2s_pin_config_t speaker_pin_config = {
    .bck_io_num = I2S_SPEAKER_SERIAL_CLOCK,
    .ws_io_num = I2S_SPEAKER_LEFT_RIGHT_CLOCK,
    .data_out_num = I2S_SPEAKER_SERIAL_DATA,
    .data_in_num = I2S_PIN_NO_CHANGE
  };
  
  i2s_driver_install(I2S_NUM_1, &i2s_speaker_config, 0, NULL);
  i2s_set_pin(I2S_NUM_1, &speaker_pin_config);
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
  tft.fillRect(0, 0, 320, 40, bgColor);
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
  for (int i = 0; i < title.length() && lineCount < 4; i++) {
    char c = title.charAt(i);
    tft.print(c);
    lineWidth += 12;  // Approximate character width
    if (lineWidth >= 300 || c == ' ' && lineWidth >= 250) {
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
    setLED(false, false, true);
    playNewsAudio(newsArticles[currentArticleIndex].id);
    displayNewsArticle(currentArticleIndex);
  } else {
    // Record voice query
    displayStatus("Recording...", TFT_RED);
    setLED(true, false, false);
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
  // Allocate buffer for audio data
  uint8_t* audioBuffer = (uint8_t*)malloc(RECORD_SIZE);
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
  
  while (totalBytesRead < RECORD_SIZE && (millis() - startTime) < (RECORD_TIME * 1000)) {
    i2s_read(I2S_NUM_0, audioBuffer + totalBytesRead, RECORD_SIZE - totalBytesRead, &bytesRead, portMAX_DELAY);
    totalBytesRead += bytesRead;
  }
  
  Serial.print("Recorded ");
  Serial.print(totalBytesRead);
  Serial.println(" bytes");
  
  // Encode audio to base64
  String base64Audio = base64_encode(audioBuffer, totalBytesRead);
  free(audioBuffer);
  
  // Send to backend for transcription
  displayStatus("Transcribing...", TFT_YELLOW);
  setLED(false, true, true);
  
  String payload = "{\"audio_data\":\"" + base64Audio + "\",\"format\":\"pcm16\",\"sample_rate\":" + String(SAMPLE_RATE) + "}";
  String response = "";
  
  if (makeAPICall("/api/iot/voice/transcribe", "POST", payload, response)) {
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, response);
    
    if (!error) {
      String transcription = doc["transcription"].as<String>();
      Serial.print("Transcribed: ");
      Serial.println(transcription);
      
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
    displayStatus("Connection error", TFT_RED);
  }
}

// ===== Fetch Trending News =====
void fetchTrendingNews() {
  String response = "";
  
  // Backend trending endpoint: /api/iot/trending?region=in&limit=5
  // Note: Backend doesn't support category parameter, only region and limit
  if (makeAPICall("/api/iot/trending?region=in&limit=5", "GET", "", response)) {
    parseNewsResponse(response);
  } else {
    Serial.println("Failed to fetch trending news");
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
        
        // Play audio through I2S speaker
        size_t bytesWritten = 0;
        i2s_write(I2S_NUM_1, audioData, decodedLen, &bytesWritten, portMAX_DELAY);
        
        free(audioData);
        Serial.println("Audio played");
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
      
      setLED(false, true, false);
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
  
  http.begin(url);
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
    return (httpResponseCode == 200);
  } else {
    Serial.print("HTTP Error: ");
    Serial.println(httpResponseCode);
    http.end();
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
