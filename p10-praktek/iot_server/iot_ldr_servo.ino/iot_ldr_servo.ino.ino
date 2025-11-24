#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>

Servo myServo;

// ===== WiFi Config =====
const char* SSID = "AN132";
const char* PASS = "000999888";

// ===== API Endpoint =====
// PRIMARY → Cloud (VPS)
const char* API_PRIMARY = "http://iot.mahardika.ac.id/api/ldr/insert";

// FALLBACK → Lokal (jika cloud gagal)
const char* API_LOCAL   = "http://172.20.10.9:5100/api/ldr/insert";

// Device ID
const char* DEVICE_ID = "esp32-013";

// ===== Pin Mapping =====
#define SERVO_PIN   15
#define LDR_DO      14
#define LED_R       25
#define LED_Y       26
#define LED_G       27
#define BUZZER_PIN  12

// ===== Motion / Logic =====
const int STEP_DEG = 10;
const int STEP_DELAY_MS = 300;
const unsigned long DARK_SUSTAIN_MS = 1500;
const unsigned long BLINK_Y_MS = 300;
const unsigned long Y_BEEP_PERIOD = 600;
const unsigned long Y_BEEP_ON_MS = 150;

unsigned long darkSinceMs = 0;
bool isDarkPrev = false;

// ========================= UTIL =========================
void setLights(bool r, bool y, bool g) {
  digitalWrite(LED_R, r);
  digitalWrite(LED_Y, y);
  digitalWrite(LED_G, g);
}
void buzzerOn() { digitalWrite(BUZZER_PIN, HIGH); }
void buzzerOff() { digitalWrite(BUZZER_PIN, LOW); }

// ================= Light + Buzzer Logic ==================
void handleLightAndBuzzer(bool isDark) {
  unsigned long now = millis();

  if (isDark && !isDarkPrev) darkSinceMs = now;
  isDarkPrev = isDark;

  if (!isDark) {
    setLights(0,0,1); 
    buzzerOff();
    return;
  }

  unsigned long dur = now - darkSinceMs;

  if (dur >= DARK_SUSTAIN_MS) {
    setLights(1,0,0); 
    buzzerOn();
  } else {
    bool blink = ((now / BLINK_Y_MS) % 2) == 0;
    setLights(0, blink, 0);

    bool beep = (now % Y_BEEP_PERIOD) < Y_BEEP_ON_MS;
    if (beep) buzzerOn(); else buzzerOff();
  }
}

// =============== POST to server (Cloud + fallback) ===============
bool postTo(const char* url, const String& json) {
  HTTPClient http;
  http.setTimeout(3000);
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  int code = http.POST(json);
  http.end();
  return (code >= 200 && code < 300);
}

bool postReading(int angleDeg, bool isDark) {
  if (WiFi.status() != WL_CONNECTED) return false;

  String json = 
    String("{\"device_id\":\"") + DEVICE_ID + "\","
    "\"angle_deg\":" + angleDeg + ","
    "\"ldr_state\":" + (isDark ? "1" : "0") +
    "}";

  // Try cloud first
  if (postTo(API_PRIMARY, json)) {
    Serial.println("POST → CLOUD OK");
    return true;
  }

  // Fallback to local
  if (postTo(API_LOCAL, json)) {
    Serial.println("POST → LOCAL OK (CLOUD DOWN)");
    return true;
  }

  Serial.println("POST FAIL → BOTH ENDPOINTS");
  return false;
}

// ================== Sampling ====================
void sampleAtAngle(int angle) {
  myServo.write(angle);
  delay(STEP_DELAY_MS);

  bool isDark = (digitalRead(LDR_DO) == HIGH);
  Serial.printf("Sudut %3d° | %s\n", angle, isDark ? "GELAP" : "TERANG");

  handleLightAndBuzzer(isDark);
  postReading(angle, isDark);
}

void scanAndSample() {
  for (int a=0;a<=180;a+=STEP_DEG) sampleAtAngle(a);
  for (int a=180;a>=0;a-=STEP_DEG) sampleAtAngle(a);
}

// ================== WiFi Auto-Reconnect ====================
void ensureWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.print("Reconnecting WiFi");
  WiFi.disconnect(true);
  WiFi.begin(SSID, PASS);

  int r=0;
  while (WiFi.status()!=WL_CONNECTED && r<20){
    Serial.print(".");
    delay(500);
    r++;
  }
  Serial.println();
}

// ================== Setup ====================
void setup() {
  Serial.begin(115200);

  pinMode(LDR_DO, INPUT);
  pinMode(LED_R, OUTPUT);
  pinMode(LED_Y, OUTPUT);
  pinMode(LED_G, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  
  buzzerOff();
  setLights(0,0,1);

  myServo.attach(SERVO_PIN);

  WiFi.begin(SSID, PASS);
  Serial.print("Connecting WiFi");
  int ct = 0;
  while (WiFi.status()!=WL_CONNECTED && ct<40) {
    Serial.print(".");
    delay(500);
    ct++;
  }
  Serial.println();
  if (WiFi.status()==WL_CONNECTED)
    Serial.println("WiFi Connected ✔");
  else
    Serial.println("WiFi FAILED (offline mode)");
}

// ================== Loop ====================
void loop() {
  ensureWiFi();
  scanAndSample();
  delay(200);
}