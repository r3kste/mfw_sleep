// uncomment the below comments if using a H bridge motor

// int En = 25;
// int A = 12;
// int B = 13;
int stop = 5;
// int speed = 0;

#include "WiFi.h"
#include "AsyncUDP.h"

constexpr char SSID[] = "Factorio";
constexpr char PASSWORD[] = "Factorio";
constexpr int UDP_PORT = 5005;
constexpr unsigned long WIFI_TIMEOUT_MS = 10000;  // 10 seconds timeout
constexpr unsigned long ACK_TIMEOUT_MS = 1000;     // 500ms timeout for acknowledgment

AsyncUDP udp;
IPAddress clientIP;
bool clientConnected = false;
volatile bool ackReceived = false;  // Shared flag to track acknowledgment

void handleUdpPacket(AsyncUDPPacket& packet) {
    String data = (const char*)packet.data();

    if (data.startsWith("GUY_ALIVE")) {
      notSleep();
    } else if (data.startsWith("GUY_DEAD")) {
      Sleep();
    }
    else{
      Serial.println("something wrong");
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

void setup() {
    Serial.begin(115200);
    pinMode(stop, OUTPUT);
    digitalWrite(stop, LOW);
    // pinMode(En, OUTPUT);
    // pinMode(A, OUTPUT);
    // pinMode(B, OUTPUT);
    // digitalWrite(A,LOW);
    // digitalWrite(B,LOW); 

    if (!connectToWiFi(SSID, PASSWORD)) {
        Serial.println("Exiting setup due to WiFi failure.");
        return;
    }

    if (!setupUdpListener(UDP_PORT)) {
        Serial.println("Exiting setup due to UDP listener failure.");
        return;
    }
}

void notSleep() {
  // digitalWrite(A ,HIGH);
  // digitalWrite(B ,LOW);
  digitalWrite(stop ,LOW);
  Serial.println("not sleeping");

  // for (int i = 0; i<256 ; i++){
  //   analogWrite(En,i);
  //   delay(20);
  //   speed = i;
  // }
  
}

void Sleep() {
  // digitalWrite(A ,HIGH);
  // digitalWrite(B ,LOW);  
  digitalWrite(stop ,HIGH);
  Serial.println("sleeping");
  // for (int i = speed; i >= 0 ; --i){
  //   analogWrite(En,i);
  //   delay(20);
  //   speed = i;
  // }
}

void loop(){
   // test code
  // Sleep();
  // delay(2000);
  // notSleep();
  // delay(2000);
}
