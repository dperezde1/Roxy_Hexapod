# 🦀 Roxy Hexapod - Advanced Teleoperation & Telemetry System

The **Roxy Hexapod** is a 6-legged robot project featuring advanced teleoperation, live telemetry, and multiple gait engines. This repository contains the complete software stack, including the hardware firmware, Python backend, and a modern React-based user interface.

## 🚀 Key Features

*   **🎮 Xbox Controller Teleoperation**: Full 6-axis control with walking, turning, and crab-walking (strafing) support.
*   **📊 Live Telemetry**: Real-time visualization of IMU (Pitch, Roll, Yaw), foot contact sensors, and gait status via MQTT.
*   **🤖 Multiple Gait Engines**: Supports stable **Tripod** and **Ripple** walking gaits, as well as specialized stair climbing sequences.
*   **🎥 Integrated Camera HUD**: Live video feed with simulated human detection overlays.
*   **📐 Precise Kinematics**: Optimized joint-angle calculations for stable, ground-hugging movement.

---

## 📂 Project Structure

```text
├── gaits/               # Reusable gait logic (Tripod, Ripple, Stair Climb)
├── hexapod_core/        # Hardware drivers, pin maps, and central configuration
├── HexUI/               # React (Vite/TypeScript) web application for teleop
├── HexapodFirmware/     # Arduino code for servo/IMU/switch management
├── miniTests/           # Automated scripts to test gaits without a controller
├── hexui_backend.py     # Main Python MQTT <-> Hardware bridge
└── .gitignore           # Project-wide Git exclusion rules
```

## 🛠 Preparation and Setup

### 1. Arduino Firmware
Flash the code in `HexapodFirmware/` to your onboard Arduino. This manages the MPU6050 IMU and foot switches.

### 2. Python Backend
The backend requires Python 3.x and the `paho-mqtt` library.
```bash
# Ensure an MQTT broker (like Mosquitto) is running on port 1883
python hexui_backend.py
```

### 3. Frontend Dashboard
The UI is a React application built with Vite.
```bash
cd HexUI
npm install
npm run dev
# Open http://localhost:5173 to start teleoperation!
```

## 🎮 Controller Mappings
- **Left Stick (X/Y)**: Move Forward/Backward and Strafe Left/Right.
- **Right Stick (X)**: Turn Left/Right in place.
- **Y Button**: Toggle Gait Mode (Tripod vs. Ripple).
- **A Button**: Execute Stair Climbing sequence.

---

## 🔬 Testing
If you want to test the robot's gaits autonomously without using the web interface or a controller:
```bash
python miniTests/test_all_gaits.py
```

## 🌐 GitHub Integration
The project is hosted and synchronized with GitHub at: [Roxy_Hexapod](https://github.com/dperezde1/Roxy_Hexapod.git)
