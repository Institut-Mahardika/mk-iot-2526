CREATE DATABASE IF NOT EXISTS iot_scan
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE iot_scan;

-- pembacaan LDR + sudut servo
CREATE TABLE IF NOT EXISTS ldr_readings (
  id           BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  device_id    VARCHAR(64) NOT NULL DEFAULT 'esp32-001',
  angle_deg    INT NOT NULL,
  ldr_state    TINYINT(1) NOT NULL,        -- 1 = gelap, 0 = terang
  raw_value    INT NULL,                    -- opsional kalau pakai AO di masa depan
  created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX (device_id), INDEX (created_at)
);

-- konfigurasi ambang & arah putaran yang bisa diubah dari web
CREATE TABLE IF NOT EXISTS settings (
  id            TINYINT PRIMARY KEY DEFAULT 1,
  yellow_logic  VARCHAR(16) NOT NULL DEFAULT 'gelap_singkat',
  red_hold_ms   INT NOT NULL DEFAULT 1500,     -- durasi gelap bertahan → MERAH
  servo_mode    VARCHAR(16) NOT NULL DEFAULT 'auto',  -- auto|manual
  servo_target  INT NOT NULL DEFAULT 90,       -- jika manual, target derajat
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

INSERT IGNORE INTO settings (id) VALUES (1);