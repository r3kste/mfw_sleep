#define CAMERA_MODEL_XIAO_ESP32S3
#include "WiFi.h"
#include "AsyncUDP.h"
#include "camera_pins.h"
#include "camera_wrap.h"

constexpr size_t MAX_PACKET_SIZE = 1024; // Optimal for WiFi reliability
constexpr char SSID[] = "Factorio";
constexpr char PASSWORD[] = "Factorio";
constexpr int RELAY_PIN = 23;
constexpr int UDP_PORT = 6969;
constexpr int APP_PORT = 5005;
constexpr unsigned long WIFI_TIMEOUT_MS = 10000; // 10 seconds timeout
constexpr unsigned long ACK_TIMEOUT_MS = 1000;   // 500ms timeout for acknowledgment
int LED_PIN = D2;
int IR_pin = D0;

AsyncUDP udp;
AsyncUDP app;
IPAddress clientIP;
bool clientConnected = false;
bool cameraEnabled = true;

int IR_read()
{
    int value = digitalRead(IR_pin);
    return value;
}

void initializeCamera()
{
    int cameraInitState = initCamera();
    Serial.printf("Camera initialization state: %d\n", cameraInitState);

    pinMode(LED_BUILTIN, OUTPUT);

    if (cameraInitState != 0)
    {
        digitalWrite(LED_BUILTIN, HIGH);
        Serial.println("Camera initialization failed!");
    }
    else
    {
        Serial.println("Camera initialized successfully.");
    }
}

volatile bool ackReceived = false; // Shared flag to track acknowledgment

void handleUdpPacket(AsyncUDPPacket &packet)
{
    String data = (const char *)packet.data();

    if (data.startsWith("HELLO"))
    {
        clientIP = packet.remoteIP();
        clientConnected = true;
        Serial.printf("Client connected: %s\n", clientIP.toString().c_str());
        constexpr char ackMessage[] = "ACK";
        udp.writeTo((const uint8_t *)ackMessage, strlen(ackMessage), clientIP, UDP_PORT);
    }
    else if (data.startsWith("ACK"))
    {
        ackReceived = true; // Set the acknowledgment flag
    }
    else if (data.startsWith("LED_"))
    {
        // Extract brightness value from the command
        int brightness = data.substring(4).toInt();
        brightness = constrain(brightness, 0, 255);
        analogWrite(LED_PIN, brightness);
        Serial.printf("LED brightness set to: %d\n", brightness);
    }
}

void handleAppPacket(AsyncUDPPacket &packet)
{
    String data = (const char *)packet.data();

    if (data.startsWith("CAM_ON"))
    {
        cameraEnabled = true;
        Serial.println("Camera turned ON.");
    }
    else if (data.startsWith("CAM_OFF"))
    {
        cameraEnabled = false;
        Serial.println("Camera turned OFF.");
    }
    else if (data.startsWith("LED_"))
    {
        // Extract brightness value from the command
        int brightness = data.substring(4).toInt();
        brightness = constrain(brightness, 0, 255);
        analogWrite(LED_PIN, brightness);
        Serial.printf("LED brightness set to: %d\n", brightness);
    }
}

void broadcastCameraPresence()
{
    while (!clientConnected)
    {
        const char *message = "I_AM_THE_CAMERA";
        if (udp.broadcastTo((uint8_t *)message, strlen(message), UDP_PORT))
        {
            Serial.println("Broadcast message sent: I_AM_THE_CAMERA");
        }
        else
        {
            Serial.println("Failed to send broadcast message.");
        }
        delay(1000);
    }
}

bool setupAppListener(int port)
{
    if (app.listen(port))
    {
        Serial.printf("App Listening on IP: %s, Port: %d\n", WiFi.localIP().toString().c_str(), port);
        app.onPacket([](AsyncUDPPacket packet)
                     { handleAppPacket(packet); });
        return true;
    }
    else
    {
        Serial.println("Failed to start App listener.");
        return false;
    }
}

bool setupUdpListener(int port)
{
    if (udp.listen(port))
    {
        Serial.printf("UDP Listening on IP: %s, Port: %d\n", WiFi.localIP().toString().c_str(), port);
        udp.onPacket([](AsyncUDPPacket packet)
                     { handleUdpPacket(packet); });
        return true;
    }
    else
    {
        Serial.println("Failed to start UDP listener.");
        return false;
    }
}

bool connectToWiFi(const char *ssid, const char *password)
{
    WiFi.disconnect(true);
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);

    unsigned long startAttemptTime = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - startAttemptTime < WIFI_TIMEOUT_MS)
    {
        delay(500);
        Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED)
    {
        Serial.printf("\nWiFi connected! IP Address: %s\n", WiFi.localIP().toString().c_str());
        return true;
    }
    else
    {
        Serial.println("\nWiFi connection failed!");
        return false;
    }
}

bool sendPacketWithAck(const uint8_t *packet, size_t length)
{
    unsigned long startTime = millis();
    ackReceived = false; // Reset the acknowledgment flag

    while (!ackReceived && millis() - startTime < 1000)
    { // 1 second timeout for the entire process
        udp.writeTo(packet, length, clientIP, UDP_PORT);
        delay(10); // Small delay to prevent flooding
    }

    if (!ackReceived)
    {
        Serial.println("Failed to send packet within 1 second. Receiver deemed disconnected.");
        clientConnected = false; // Mark the receiver as disconnected
    }

    return ackReceived;
}

void sendCameraFrames()
{
    if (!clientConnected)
    {
        Serial.println("No client connected. Skipping frame transmission.");
        delay(1000);
        return;
    }

    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb)
    {
        Serial.println("Failed to capture frame.");
        delay(1000);
        return;
    }

    uint16_t totalPackets = (fb->len + MAX_PACKET_SIZE - 6) / (MAX_PACKET_SIZE - 5); // Reserve 5 bytes for header
    size_t remaining = fb->len;
    uint8_t *buffer = fb->buf;
    uint16_t packetNumber = 0;

    while (remaining > 0)
    {
        size_t chunkSize = min(MAX_PACKET_SIZE - 5, remaining); // Reserve 5 bytes for header
        uint8_t packet[MAX_PACKET_SIZE];
        uint8_t ir_status = IR_read(); // Read the IR sensor status

        // Header format: [Total Packets (2B) | Current Packet (2B) | IR Status (1B)]
        packet[0] = totalPackets >> 8;
        packet[1] = totalPackets & 0xFF;
        packet[2] = packetNumber >> 8;
        packet[3] = packetNumber & 0xFF;
        packet[4] = ir_status; // Add IR sensor status to the header

        memcpy(packet + 5, buffer, chunkSize); // Copy image data after the header

        if (!sendPacketWithAck(packet, chunkSize + 5))
        {
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

void setup()
{
    Serial.begin(115200);
    pinMode(LED_PIN, OUTPUT);
    pinMode(RELAY_PIN, OUTPUT);
    digitalWrite(RELAY_PIN, HIGH);

    initializeCamera();

    if (!connectToWiFi(SSID, PASSWORD))
    {
        Serial.println("Exiting setup due to WiFi failure.");
        return;
    }

    if (!setupAppListener(APP_PORT))
    {
        Serial.println("Exiting setup due to App listener failure.");
        return;
    }

    if (!setupUdpListener(UDP_PORT))
    {
        Serial.println("Exiting setup due to UDP listener failure.");
        return;
    }
}

void loop()
{
    if (!clientConnected)
    {
        broadcastCameraPresence();
    }
    else
    {
        if (cameraEnabled)
        {
            sendCameraFrames();
        }
    }
}