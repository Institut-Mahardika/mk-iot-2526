CREATE DATABASE IF NOT EXISTS iot_scan
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_general_ci;

USE iot_scan; -- Sesuaikan dengan database yang ada.

CREATE TABLE IF NOT EXISTS ldr_readings (
  id           BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  device_id    VARCHAR(64) NOT NULL,       -- wajib ada device ID
  angle_deg    INT NOT NULL,               -- 0–180 derajat
  ldr_state    TINYINT(1) NOT NULL,        -- 1=gelap, 0=terang
  raw_value    INT NULL,                   -- opsional (kalau pakai analog AO)
  created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  INDEX idx_device_time (device_id, created_at),
  INDEX idx_created (created_at)
);

CREATE TABLE IF NOT EXISTS alert_logs (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  reading_id      BIGINT UNSIGNED NOT NULL,
  device_id       VARCHAR(64) NOT NULL,
  angle_deg       INT NOT NULL,
  ldr_state       TINYINT(1) NOT NULL,
  raw_value       INT NULL,
  alert_type      VARCHAR(32) NOT NULL,      -- RED_HOLD, YELLOW_BLINK, DARK_LONG
  sent_to_telegram TINYINT(1) NOT NULL DEFAULT 0,
  sent_at         TIMESTAMP NULL DEFAULT NULL,
  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  INDEX idx_alert_time (created_at),
  INDEX idx_alert_device (device_id, created_at),

  CONSTRAINT fk_alert_reading
    FOREIGN KEY (reading_id)
    REFERENCES ldr_readings(id)
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS settings (
  id            TINYINT PRIMARY KEY DEFAULT 1,
  yellow_logic  VARCHAR(32) NOT NULL DEFAULT 'gelap_singkat',
  red_hold_ms   INT NOT NULL DEFAULT 1500,
  servo_mode    VARCHAR(16) NOT NULL DEFAULT 'auto',   -- auto/manual
  servo_target  INT NOT NULL DEFAULT 90,               -- sudut jika manual
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                   ON UPDATE CURRENT_TIMESTAMP
);
INSERT IGNORE INTO settings (id) VALUES (1);

CREATE TABLE IF NOT EXISTS devices (
  device_id   VARCHAR(64) PRIMARY KEY,
  name        VARCHAR(128),
  location    VARCHAR(128),
  created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT IGNORE INTO devices(device_id, name, location)
VALUES
('esp32-013', 'Scan Bot 1', 'Lab IoT Mahardika');