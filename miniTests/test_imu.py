#!/usr/bin/env python3
"""
test_imu.py
───────────
A simple diagnostic script to test the Arduino Nano telemetry stream
without needing the Arduino IDE Serial Monitor.

Run this on the Raspberry Pi:
  python3 test_imu.py
"""

import sys
import os
import time
import serial

# Add hexapod_core to path to easily grab our auto-port-finder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, "hexapod_core"))

from servo_control import _find_arduino_port, ARDUINO_BAUD

def main():
    print("=" * 50)
    print("  Arduino IMU & Button Telemetry Tester")
    print("=" * 50)

    port = _find_arduino_port()
    if not port:
        print("[ERROR] Could not auto-detect the Arduino Nano.")
        print("Please check the USB connection to the Pi.")
        sys.exit(1)

    print(f"\n[INIT] Found Arduino on {port} at {ARDUINO_BAUD} baud.")
    
    try:
        arduino = serial.Serial(port, ARDUINO_BAUD, timeout=1)
        # Wait a moment for the Arduino to reset on connection
        time.sleep(2)
        arduino.reset_input_buffer()
        print("[INIT] Serial port opened. Waiting for data...\n")
        
        while True:
            # Read a full line from the Arduino
            line = arduino.readline().decode('utf-8', errors='ignore').strip()
            
            if line:
                # If it's a telemetry packet, maybe highlight it
                if line.startswith("TELEM"):
                    print(f"--> {line}")
                else:
                    # Echo boot messages or errors
                    print(f"    {line}")
                    
    except KeyboardInterrupt:
        print("\n[STOP] User interrupted test.")
    except Exception as e:
        print(f"\n[ERROR] {e}")
    finally:
        if 'arduino' in locals() and arduino.is_open:
            arduino.close()
            print("[STOP] Serial port closed.")

if __name__ == "__main__":
    main()
