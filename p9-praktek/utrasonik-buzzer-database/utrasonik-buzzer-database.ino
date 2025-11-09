#include <WiFi.h>
#include <HTTPClient.h>
#include <math.h>   // untuk fabsf

#define TRIG_PIN     13
#define ECHO_PIN     12   // WAJIB lewat divider 2k:1k atau level shifter
#define BUZZER_PIN   14

// WiFi
const char* ssid     = "PUSDATIN";
const char* password = "@Mahardika+";

// API Flask
const char* serverUrl = "http://192.168.100.174:5000/ultrasonic/insert";

// Fisika & aturan kirim
const float SPEED_OF_SOUND_CM_PER_US = 0.0343f / 2.0f;  // cm/us (pulang-pergi)
const float THRESHOLD_CM = 15.0f;

const float  DELTA_CM          = 1.0f;     // kirim bila berubah ≥ 1 cm
const unsigned long sendCooldownMs = 2000; // anti-spam (2 s)

// State kirim
unsigned long lastSentMs       = 0;
bool          lastAlarm        = false;
float         lastSentDistance = -1000.0f; // sentinel

float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(4);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000UL); // timeout 30ms (~5m)
  if (duration == 0) return -1.0f; // no echo / out of range
  return duration * SPEED_OF_SOUND_CM_PER_US;
}

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  WiFi.begin(ssid, password);
  Serial.print("WiFi connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(600);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected.");
}

void loop() {
  float d = readDistanceCm();

  if (d < 0) {
    Serial.println("No echo / out of range");
    digitalWrite(BUZZER_PIN, LOW);
    delay(200);
    return;
  }

  Serial.printf("Distance: %.2f cm\n", d);
  bool alarm = (d <= THRESHOLD_CM);

  // indikator buzzer
  digitalWrite(BUZZER_PIN, alarm ? HIGH : LOW);

  // logika Opsi B: kirim jika alarm berubah ATAU (jarak berubah signifikan & cooldown lewat)
  unsigned long now = millis();
  bool cooldownOver  = (now - lastSentMs) >= sendCooldownMs;
  bool firstSend     = (lastSentDistance < -999.0f);
  bool changedEnough = firstSend || (fabsf(d - lastSentDistance) >= DELTA_CM);

  if ((alarm != lastAlarm) || (changedEnough && cooldownOver)) {
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(serverUrl);
      http.setTimeout(3000); // ms
      http.addHeader("Content-Type", "application/json");

      String payload = String("{\"distance_cm\":") + String(d, 2) +
                       ",\"threshold_cm\":" + String(THRESHOLD_CM, 1) +
                       ",\"triggered\":" + (alarm ? "true" : "false") +
                       ",\"device_id\":\"esp32-001\"}";

      int code = http.POST(payload);
      Serial.printf("POST %d\n", code);
      http.end();

      lastSentMs       = now;
      lastSentDistance = d;
      lastAlarm        = alarm;
    } else {
      Serial.println("WiFi lost");
    }
  }

  delay(200); // ~5 Hz
}