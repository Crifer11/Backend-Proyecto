#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>

// ==== CONFIGURA TU RED WIFI ====
const char* ssid = "NOMBRE DE TU INTERNET";       
const char* password = "TU CONTRASEÑA";  

// ==== CONFIGURA EL SERVIDOR FLASK ====
String serverName = "http://192.168.1.71:5000/upload_facial";


// ==== PINES DE LA CAMARA (AI THINKER) ====
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

// ==== PIN LED FLASH ====
#define LED_FLASH 4

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(false);
  Serial.println("\n===== INICIANDO ESP32-CAM =====");

  // ==== Conexión WiFi ====
  WiFi.begin(ssid, password);
  Serial.print("Conectando a WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ Conectado a WiFi!");
  Serial.print("📡 IP local: ");
  Serial.println(WiFi.localIP());

  // ==== Configuración de la cámara ====
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

  if(psramFound()){
      config.frame_size = FRAMESIZE_VGA;  // 640x480
      config.jpeg_quality = 10;           
      config.fb_count = 1;
  } else {
      config.frame_size = FRAMESIZE_QVGA; // 320x240
      config.jpeg_quality = 10;
      config.fb_count = 1;
  }

  Serial.println("Iniciando cámara...");
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("❌ Error iniciando cámara: 0x%x\n", err);
    return;
  }
  Serial.println("✅ Cámara iniciada correctamente!");

  // ==== Configuración del flash ====
  pinMode(LED_FLASH, OUTPUT);
  digitalWrite(LED_FLASH, LOW);

  // ==== DESCARTAR FRAMES FANTASMA INICIALES ====
  for (int i = 0; i < 3; i++) {
    camera_fb_t * fb = esp_camera_fb_get();
    if(fb) esp_camera_fb_return(fb);
  }
  Serial.println("Frames iniciales descartados para evitar foto atrasada.");

  Serial.println("👉 Escribe '1' en la consola para capturar una foto.");
}

void capturarYEnviarFoto() {
  Serial.println("📸 Capturando foto...");

  // ==== DESCARTAR UN FRAME EXTRA ANTES DE LA CAPTURA REAL ====
  camera_fb_t *old = esp_camera_fb_get();
  if (old) esp_camera_fb_return(old);

  // ==== CAPTURA REAL ====
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("❌ Error: no se pudo capturar la foto");
    return;
  }
  Serial.printf("✅ Foto capturada! Tamaño: %d bytes\n", fb->len);

  if (WiFi.status() == WL_CONNECTED) {
    WiFiClient client;
    HTTPClient http;

    http.begin(client, serverName);
    http.addHeader("Content-Type", "image/jpeg");

    int httpResponseCode = http.POST(fb->buf, fb->len);
    
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("📥 Respuesta del servidor: " + response);
    } else {
      Serial.printf("❌ Error al enviar la imagen. Código: %d\n", httpResponseCode);
    }

    http.end();
  } else {
    Serial.println("❌ WiFi no conectado");
  }

  esp_camera_fb_return(fb);
}

void loop() {
  if (Serial.available() > 0) {
    char comando = Serial.read();
    if (comando == '1') {
      Serial.println("📸 Comando recibido → Tomando foto...");

      // Flash encendido momentáneo
      digitalWrite(LED_FLASH, HIGH);
      delay(1000);

      capturarYEnviarFoto();

      // Apagar flash
      delay(300);
      digitalWrite(LED_FLASH, LOW);
    }
  }
}
