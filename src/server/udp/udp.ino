#define CAMERA_MODEL_XIAO_ESP32S3
#include "WiFi.h"
#include "AsyncUDP.h"
#include "camera_pins.h"
#include "camera_wrap.h"

constexpr size_t MAX_PACKET_SIZE = 1024;  // Optimal for WiFi reliability
constexpr char SSID[] = "Omayawa";
constexpr char PASSWORD[] = "MFWS2025";
constexpr int RELAY_PIN = 23;
constexpr int UDP_PORT = 6969;
constexpr unsigned long WIFI_TIMEOUT_MS = 10000;  // 10 seconds timeout
constexpr unsigned long ACK_TIMEOUT_MS = 1000;     // 500ms timeout for acknowledgment
int LED_PIN = D1;

AsyncUDP udp;
IPAddress clientIP;
bool clientConnected = false;

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

volatile bool ackReceived = false;  // Shared flag to track acknowledgment

void handleUdpPacket(AsyncUDPPacket& packet) {
    String data = (const char*)packet.data();

    if (data.startsWith("HELLO")) {
        clientIP = packet.remoteIP();
        clientConnected = true;
        Serial.printf("Client connected: %s\n", clientIP.toString().c_str());
        // send ACK to client
        udp.writeTo("ACK", strlen(ackMessage), clientIP, UDP_PORT);
    } else if (data.startsWith("ACK")) {
        ackReceived = true;  // Set the acknowledgment flag
    } else if (data.startsWith("LED_")) {
        // Extract brightness value from the command
        int brightness = data.substring(4).toInt();
        brightness = constrain(brightness, 0, 255);  // Ensure brightness is within 0-255
        analogWrite(LED_PIN, brightness);  // Set LED brightness
        Serial.printf("LED brightness set to: %d\n", brightness);
    }
}

void broadcastCameraPresence() {
    const char* message = "I_AM_THE_CAMERA";
    if (udp.broadcastTo(message, UDP_PORT)) {
        Serial.println("Broadcast message sent: I_AM_THE_CAMERA");
    } else {
        Serial.println("Failed to send broadcast message.");
    }
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

bool sendPacketWithAck(const uint8_t* packet, size_t length) {
    unsigned long startTime = millis();
    ackReceived = false;  // Reset the acknowledgment flag

    while (!ackReceived && millis() - startTime < 1000) {  // 1 second timeout for the entire process
        udp.writeTo(packet, length, clientIP, UDP_PORT);
        delay(10);  // Small delay to prevent flooding
    }

    if (!ackReceived) {
        Serial.println("Failed to send packet within 1 second. Receiver deemed disconnected.");
        clientConnected = false;  // Mark the receiver as disconnected
    }

    return ackReceived;
}

void sendCameraFrames() {
    if (!clientConnected) {
        Serial.println("No client connected. Skipping frame transmission.");
        delay(1000);
        return;
    }

    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("Failed to capture frame.");
        delay(1000);
        return;
    }

    uint16_t totalPackets = (fb->len + MAX_PACKET_SIZE - 5) / (MAX_PACKET_SIZE - 4);
    size_t remaining = fb->len;
    uint8_t* buffer = fb->buf;
    uint16_t packetNumber = 0;

    while (remaining > 0) {
        size_t chunkSize = min(MAX_PACKET_SIZE - 4, remaining);  // Reserve 4 bytes for header
        uint8_t packet[MAX_PACKET_SIZE];

        // Header format: [Total Packets (2B) | Current Packet (2B)]
        packet[0] = totalPackets >> 8;
        packet[1] = totalPackets & 0xFF;
        packet[2] = packetNumber >> 8;
        packet[3] = packetNumber & 0xFF;

        memcpy(packet + 4, buffer, chunkSize);

        if (!sendPacketWithAck(packet, chunkSize + 4)) {
            Serial.printf("Failed to send packet %d. Dropping frame.\n", packetNumber);
            break;
        }

        buffer += chunkSize;
        remaining -= chunkSize;
        packetNumber++;
    }

    esp_camera_fb_return(fb);
    delay(20);
}

void setup() {
    Serial.begin(115200);
    pinMode(LED_PIN, OUTPUT);
    pinMode(RELAY_PIN, OUTPUT);
    digitalWrite(RELAY_PIN, HIGH);

    initializeCamera();

    if (!connectToWiFi(SSID, PASSWORD)) {
        Serial.println("Exiting setup due to WiFi failure.");
        return;
    }

    if (!setupUdpListener(UDP_PORT)) {
        Serial.println("Exiting setup due to UDP listener failure.");
        return;
    }

    broadcastCameraPresence();
}

void loop() {
    sendCameraFrames();
}