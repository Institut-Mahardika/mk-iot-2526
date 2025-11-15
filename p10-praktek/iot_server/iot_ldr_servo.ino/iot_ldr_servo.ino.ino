#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>

Servo myServo;

// --- WiFi ---
const char* SSID     = "AN13 📱";
const char* PASS     = "";

// --- API ---
const char* DEVICE_ID  = "esp32-001";
const char* API_URL    = "http://172.20.10.2:5100/api/ldr/insert"; // ganti jika IP berubah

// --- Pin mapping ---
#define SERVO_PIN   15
#define LDR_DO      14     // LDR modul (digital output)
#define LED_R       25     // Traffic light
#define LED_Y       26
#define LED_G       27
#define BUZZER_PIN  12     // buzzer aktif HIGH

// --- Parameter gerak & logika ---
const int STEP_DEG       = 10;
const int STEP_DELAY_MS  = 300;
const unsigned long DARK_SUSTAIN_MS = 1500; // gelap lama -> MERAH
const unsigned long BLINK_Y_MS      = 300;  // kedip kuning
const unsigned long Y_BEEP_PERIOD   = 600;  // pola beep kuning
const unsigned long Y_BEEP_ON_MS    = 150;  // durasi ON beep kuning

// --- State ---
unsigned long darkSinceMs = 0;
bool isDarkPrev = false;

// ---------------- Utils ----------------
void setLights(bool r, bool y, bool g){
  digitalWrite(LED_R, r ? HIGH : LOW);
  digitalWrite(LED_Y, y ? HIGH : LOW);
  digitalWrite(LED_G, g ? HIGH : LOW);
}
void buzzerOn(){  digitalWrite(BUZZER_PIN, HIGH); }
void buzzerOff(){ digitalWrite(BUZZER_PIN, LOW);  }

void handleLightAndBuzzer(bool isDark){
  unsigned long now = millis();

  if (isDark && !isDarkPrev) darkSinceMs = now;
  isDarkPrev = isDark;

  if (!isDark){
    setLights(false,false,true);   // HIJAU
    buzzerOff();
    return;
  }

  unsigned long darkDur = now - darkSinceMs;
  if (darkDur >= DARK_SUSTAIN_MS){
    // MERAH: gelap berkelanjutan
    setLights(true,false,false);
    buzzerOn();                   // bunyi kontinu
  }else{
    // KUNING: gelap sesaat
    bool blink = ((now / BLINK_Y_MS) % 2) == 0;
    setLights(false, blink, false);

    // pola beep: ON sebentar setiap period
    bool beep = (now % Y_BEEP_PERIOD) < Y_BEEP_ON_MS;
    if (beep) buzzerOn(); else buzzerOff();
  }
}

bool postReading(int angleDeg, bool isDark, int rawValue /*optional: -1 jika tak ada*/){
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  http.begin(API_URL);
  http.addHeader("Content-Type", "application/json");

  // NOTE: LDR digital banyak yang HIGH=gelap, LOW=terang → sesuaikan jika kebalik
  String payload = String("{\"device_id\":\"") + DEVICE_ID + "\""
                 + ",\"angle_deg\":" + String(angleDeg)
                 + ",\"ldr_state\":" + (isDark ? "1" : "0");
  if (rawValue >= 0) {
    payload += String(",\"raw_value\":") + String(rawValue);
  }
  payload += "}";

  int code = http.POST(payload);
  bool ok = (code >= 200 && code < 300);
  Serial.printf("POST %s => HTTP %d\n", ok ? "OK" : "FAIL", code);
  http.end();
  return ok;
}

void sampleAtAngle(int angle){
  myServo.write(angle);
  delay(STEP_DELAY_MS);

  // Jika modul LDR kamu kebalik, ganti ke (digitalRead(LDR_DO) == LOW)
  bool isDark = (digitalRead(LDR_DO) == HIGH);
  Serial.printf("Sudut: %3d° | %s\n", angle, isDark ? "🌑 GELAP" : "☀️ TERANG");

  handleLightAndBuzzer(isDark);

  // Kirim ke server (tanpa raw_value → pakai -1)
  postReading(angle, isDark, -1);
}

void scanAndSample(){
  // 0 -> 180
  for (int angle = 0; angle <= 180; angle += STEP_DEG) {
    sampleAtAngle(angle);
  }
  // 180 -> 0
  for (int angle = 180; angle >= 0; angle -= STEP_DEG) {
    sampleAtAngle(angle);
  }
}

// ---------------- Setup & Loop ----------------
void setup() {
  Serial.begin(115200);

  pinMode(LDR_DO, INPUT);
  pinMode(LED_R, OUTPUT);
  pinMode(LED_Y, OUTPUT);
  pinMode(LED_G, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  buzzerOff();
  setLights(false,false,true); // start: hijau

  myServo.attach(SERVO_PIN);

  // WiFi connect
  Serial.printf("WiFi connecting to %s", SSID);
  WiFi.begin(SSID, PASS);
  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries < 40) { // ~20 detik
    delay(500);
    Serial.print(".");
    tries++;
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED){
    Serial.printf("WiFi connected. IP: %s\n", WiFi.localIP().toString().c_str());
  }else{
    Serial.println("WiFi FAILED, lanjut offline (POST akan di-skip).");
  }
}

void loop() {
  scanAndSample();
  delay(200);
}