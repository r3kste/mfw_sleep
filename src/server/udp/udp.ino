#define CAMERA_MODEL_XIAO_ESP32S3
#include "WiFi.h"
#include "AsyncUDP.h"
#include "camera_pins.h"
#include "camera_wrap.h"


constexpr size_t MAX_PACKET_SIZE = 1024;  // Optimal for WiFi reliability
constexpr char SSID[] = "Adithya";
constexpr char PASSWORD[] = "Adithya3003";
constexpr int RELAY_PIN = 23;
constexpr int UDP_PORT = 6969;
constexpr unsigned long WIFI_TIMEOUT_MS = 10000;  // 10 seconds timeout

AsyncUDP udp;

void initializeCamera() {
    int cameraInitState = initCamera();
    Serial.printf("Camera initialization state: %d\n", cameraInitState);

    pinMode(LED_BUILTIN, OUTPUT);

    if (cameraInitState != 0) {
        digitalWrite(LED_BUILTIN, HIGH);
        Serial.println("Camera initialization failed!");
    } else {
        Serial.println("Camera initialized successfully.");
    }
}

void handleUdpPacket(AsyncUDPPacket& packet) {
    Serial.printf("UDP Packet Type: %s, From: %s:%d, To: %s:%d, Length: %d\n",
                  packet.isBroadcast() ? "Broadcast" : packet.isMulticast() ? "Multicast" : "Unicast",
                  packet.remoteIP().toString().c_str(), packet.remotePort(),
                  packet.localIP().toString().c_str(), packet.localPort(),
                  packet.length());

    String data = (const char*)packet.data();
    if (data.startsWith("ON")) {
        Serial.println("Turning on relay");
        digitalWrite(RELAY_PIN, LOW);
    } else if (data.startsWith("OFF")) {
        Serial.println("Turning off relay");
        digitalWrite(RELAY_PIN, HIGH);
    }

    packet.printf("Received %u bytes of data", packet.length());
}

bool setupUdpListener(int port) {
    if (udp.listen(port)) {
        Serial.printf("UDP Listening on IP: %s, Port: %d\n", WiFi.localIP().toString().c_str(), port);
        udp.onPacket([](AsyncUDPPacket packet) { handleUdpPacket(packet); });
        return true;
    } else {
        Serial.println("Failed to start UDP listener.");
        return false;
    }
}

bool connectToWiFi(const char* ssid, const char* password) {
    WiFi.disconnect(true);
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);

    unsigned long startAttemptTime = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - startAttemptTime < WIFI_TIMEOUT_MS) {
        delay(500);
        Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\nWiFi connected! IP Address: %s\n", WiFi.localIP().toString().c_str());
        return true;
    } else {
        Serial.println("\nWiFi connection failed!");
        return false;
    }
}

void sendCameraFrames() {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("Failed to capture frame.");
        delay(1000);
        return;
    }

    size_t remaining = fb->len;
    uint8_t* buffer = fb->buf;
    uint16_t packetNumber = 0;

    while (remaining > 0) {
        size_t chunkSize = min(MAX_PACKET_SIZE - 4, remaining);  // Reserve 4 bytes for header
        uint8_t packet[MAX_PACKET_SIZE];

        // Header format: [Total Packets (2B) | Current Packet (2B)]
        uint16_t totalPackets = (fb->len + MAX_PACKET_SIZE - 5) / (MAX_PACKET_SIZE - 4);
        packet[0] = totalPackets >> 8;
        packet[1] = totalPackets & 0xFF;
        packet[2] = packetNumber >> 8;
        packet[3] = packetNumber & 0xFF;

        memcpy(packet + 4, buffer, chunkSize);

        udp.broadcast(packet, chunkSize + 4);

        buffer += chunkSize;
        remaining -= chunkSize;
        packetNumber++;
        delay(10);  // Prevent WiFi buffer overflow
    }

    esp_camera_fb_return(fb);
    delay(10);  // ~10 FPS
}

void setup() {
    Serial.begin(115200);
    pinMode(RELAY_PIN, OUTPUT);
    digitalWrite(RELAY_PIN, HIGH);  // Ensure relay is off initially

    initializeCamera();

    if (!connectToWiFi(SSID, PASSWORD)) {
        Serial.println("Exiting setup due to WiFi failure.");
        return;
    }

    if (!setupUdpListener(UDP_PORT)) {
        Serial.println("Exiting setup due to UDP listener failure.");
        return;
    }
}

void loop() {
    Serial.printf("Free heap: %d bytes\n", ESP.getFreeHeap());
    sendCameraFrames();
}