/*
  HexapodFirmware.ino
  ───────────────────
  Advanced Hexapod control node using the MPU6050 Hardware DMP.
  
  Features:
    1. "SERVO <pin> <angle>\n" lazy-loading actuation via Python.
    2. Digital Motion Processor (DMP) computes Quaternions (w,x,y,z) on-silicon
       to prevent Euler gimbal-lock on the Raspberry Pi LQR IK solver.
    3. Hardware Interrupt on D2 signals DMP Data Ready to save CPU.
    4. 6 Digital Input Pullups for foot contact switches.
    5. Streams telemetry down the USB serial pipe at 20Hz.
*/

#include <Servo.h>
#include "I2Cdev.h"
#include "MPU6050_6Axis_MotionApps20.h"

// If you are using standard Wire library (Arduino Uno/Nano):
#if I2CDEV_IMPLEMENTATION == I2CDEV_ARDUINO_WIRE
    #include "Wire.h"
#endif

// ═════════════════════════════════════════════════════════════
//  CONFIGURATION (EDIT THESE PINS IF NEEDED)
// ═════════════════════════════════════════════════════════════

// 1. MPU6050 Settings
MPU6050 mpu;
#define INTERRUPT_PIN 2  // MUST connect MPU6050 'INT' to Nano Digital Pin 2

// DMP Status Variables
bool dmpReady = false;  
uint8_t mpuIntStatus;   
uint8_t devStatus;      
uint16_t packetSize;    
uint16_t fifoCount;     
uint8_t fifoBuffer[64]; 
Quaternion q;           // [w, x, y, z]

// 2. Foot Switch Digital Pins (Assuming normally open, connected to GND)
// Servos are on 5 and 6 via Python commands. D2 is used for IMU interrupt.
#define PIN_BTN_1 7
#define PIN_BTN_2 8
#define PIN_BTN_3 9
#define PIN_BTN_4 10
#define PIN_BTN_5 11
#define PIN_BTN_6 12

// 3. Telemetry Send Rate (e.g. 50ms = 20Hz update to Python)
const unsigned long TELEM_INTERVAL = 50;

// ═════════════════════════════════════════════════════════════
//  STATE VARIABLES & ISR
// ═════════════════════════════════════════════════════════════

// Servo tracking
Servo servos[13]; 
bool servoAttached[13];

// Serial comms
#define BUFFER_SIZE 32
char inputBuffer[BUFFER_SIZE];
uint8_t bufIndex = 0;

unsigned long lastTelemTime = 0;

// Interrupt Service Routine (ISR)
volatile bool mpuInterrupt = false;
void dmpDataReady() {
    mpuInterrupt = true;
}

// ═════════════════════════════════════════════════════════════
//  SETUP
// ═════════════════════════════════════════════════════════════

void setup() {
  // Join I2C bus
  #if I2CDEV_IMPLEMENTATION == I2CDEV_ARDUINO_WIRE
      Wire.begin();
      Wire.setClock(400000); // 400kHz I2C clock
  #elif I2CDEV_IMPLEMENTATION == I2CDEV_BUILTIN_FASTWIRE
      Fastwire::setup(400, true);
  #endif

  Serial.begin(115200);
  while (!Serial);

  // Debug LED
  pinMode(13, OUTPUT);
  digitalWrite(13, LOW);

  // Initialize Foot Switches
  pinMode(PIN_BTN_1, INPUT_PULLUP);
  pinMode(PIN_BTN_2, INPUT_PULLUP);
  pinMode(PIN_BTN_3, INPUT_PULLUP);
  pinMode(PIN_BTN_4, INPUT_PULLUP);
  pinMode(PIN_BTN_5, INPUT_PULLUP);
  pinMode(PIN_BTN_6, INPUT_PULLUP);

  for(int i=0; i<13; i++) {
    servoAttached[i] = false;
  }

  // Initialize MPU6050 & DMP
  Serial.println("Initializing MPU6050...");
  mpu.initialize();
  pinMode(INTERRUPT_PIN, INPUT);

  if (!mpu.testConnection()) {
      Serial.println("ERR: MPU6050 connection failed");
      // Don't halt, we still want servo control to work
  }

  Serial.println("Initializing DMP...");
  devStatus = mpu.dmpInitialize();

  // Supply your own gyro offsets here if you have them, scaled for min sensitivity
  mpu.setXGyroOffset(220);
  mpu.setYGyroOffset(76);
  mpu.setZGyroOffset(-85);
  mpu.setZAccelOffset(1788); 

  // Make sure it worked (returns 0 if so)
  if (devStatus == 0) {
      mpu.setDMPEnabled(true);
      attachInterrupt(digitalPinToInterrupt(INTERRUPT_PIN), dmpDataReady, RISING);
      mpuIntStatus = mpu.getIntStatus();
      dmpReady = true;
      packetSize = mpu.dmpGetFIFOPacketSize();
      Serial.println("DMP Ready! Waiting for first interrupt...");
  } else {
      Serial.print("DMP Initialization failed (code ");
      Serial.print(devStatus);
      Serial.println(")");
  }

  Serial.println("HEXAPOD QUATERNION FIRMWARE v3.0 ACTIVE");
}

// ═════════════════════════════════════════════════════════════
//  MAIN LOOP
// ═════════════════════════════════════════════════════════════

void loop() {
  // 1. Process Incoming Serial Commands from Python
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (bufIndex > 0) {
        inputBuffer[bufIndex] = '\0';
        parseAndExecute(inputBuffer);
        bufIndex = 0;
      }
    } else {
      if (bufIndex < BUFFER_SIZE - 1) {
        inputBuffer[bufIndex++] = c;
      } else {
        Serial.println("ERR buffer_overflow");
        bufIndex = 0;
      }
    }
  }

  // 2. Poll the DMP if ready
  if (dmpReady && mpuInterrupt) {
      // Reset interrupt flag and get INT_STATUS byte
      mpuInterrupt = false;
      mpuIntStatus = mpu.getIntStatus();

      fifoCount = mpu.getFIFOCount();

      // Check for overflow
      if ((mpuIntStatus & _BV(MPU6050_INTERRUPT_FIFO_OFLOW_BIT)) || fifoCount >= 1024) {
          mpu.resetFIFO();
          fifoCount = mpu.getFIFOCount();
          Serial.println("ERR FIFO_OVERFLOW");
      } 
      // Check for DMP data ready interrupt
      else if (mpuIntStatus & _BV(MPU6050_INTERRUPT_DMP_INT_BIT)) {
          // Wait for correct available data length
          while (fifoCount < packetSize) fifoCount = mpu.getFIFOCount();

          // Read a packet from FIFO
          mpu.getFIFOBytes(fifoBuffer, packetSize);
          fifoCount -= packetSize; // track remaining bytes

          // Extract Quaternions!
          mpu.dmpGetQuaternion(&q, fifoBuffer);
      }
  }

  // 3. Transmit periodic Telemetry (Quaternions + Buttons)
  unsigned long currentMillis = millis();
  if (currentMillis - lastTelemTime >= TELEM_INTERVAL) {
    lastTelemTime = currentMillis;
    sendTelemetry();
  }
}

// ═════════════════════════════════════════════════════════════
//  FUNCTIONS
// ═════════════════════════════════════════════════════════════

bool parseAndExecute(char* line) {
  char* token;

  token = strtok(line, " \t\r\n");
  if (token == NULL || strcmp(token, "SERVO") != 0) {
    return false; // ignore non-servo commands silently
  }

  token = strtok(NULL, " \t\r\n");
  if (token == NULL) return false;
  int pin = atoi(token);

  token = strtok(NULL, " \t\r\n");
  if (token == NULL) return false;
  int angle = atoi(token);

  if (pin > 0 && pin < 13) {
    // Lazy Attachment 
    if (!servoAttached[pin]) {
      servos[pin].write(angle);
      servos[pin].attach(pin);
      servoAttached[pin] = true;
    } else {
      servos[pin].write(angle);
    }
    
    // Exact acknowledgment requested by user
    Serial.print("OK ");
    Serial.print(pin);
    Serial.print(" ");
    Serial.println(angle);

    // Visual debug blink
    digitalWrite(13, HIGH);
    delay(3);
    digitalWrite(13, LOW);
  }
  return true;
}

void sendTelemetry() {
  // Read Foot Switches 
  int b1 = !digitalRead(PIN_BTN_1);
  int b2 = !digitalRead(PIN_BTN_2);
  int b3 = !digitalRead(PIN_BTN_3);
  int b4 = !digitalRead(PIN_BTN_4);
  int b5 = !digitalRead(PIN_BTN_5);
  int b6 = !digitalRead(PIN_BTN_6);

  // Send formatted telemetry to USB
  // Format: TELEM Q:w,x,y,z B:1,0,0,0,1,1
  // We multiply quaternions by 1000 and send as integers to save serial bandwidth, 
  // or just send as floats. Floats with 4 decimal places are safer.
  Serial.print("TELEM Q:");
  Serial.print(q.w, 4); Serial.print(",");
  Serial.print(q.x, 4); Serial.print(",");
  Serial.print(q.y, 4); Serial.print(",");
  Serial.print(q.z, 4); 
  Serial.print(" B:");
  Serial.print(b1); Serial.print(",");
  Serial.print(b2); Serial.print(",");
  Serial.print(b3); Serial.print(",");
  Serial.print(b4); Serial.print(",");
  Serial.print(b5); Serial.print(",");
  Serial.println(b6);
}
