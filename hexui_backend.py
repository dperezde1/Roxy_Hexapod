#!/usr/bin/env python3
"""
hexui_backend.py
────────────────
Main controller bridge between the HexUI frontend (over MQTT) and the
physical Hexapod python gait engines.

Dependencies:
    pip install paho-mqtt adafruit-circuitpython-servokit pyserial

Features:
    - Listens to 'hexapod/command/controller' telemetry over MQTT
    - Routes Gamepad Axes (ly) to Gait Forward/Backward
    - Routes Gamepad Axes (lx) to Strafing Left/Right (Crab Walk via IK/Hooks)
    - Routes Gamepad Axes (rx) to Turning
    - Routes Gamepad Buttons (e.g., 'Y'/'X') to switch Gait Mode
"""

import sys
import os
import json
import time
import signal
import math
import threading
import paho.mqtt.client as mqtt

# ── Import our core hardware and gait classes ──
# Because we refactored into 'hexapod_core' and 'gaits' folders, 
# add them to Python's sys path to resolve imports.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, "hexapod_core"))
sys.path.append(os.path.join(BASE_DIR, "gaits"))

from servo_control import ServoController
from tripod_walk import TripodGait
from ripple_walk import RippleGait
from stair_climb import StairClimbSequence

# ── MQTT Broker Config ──
BROKER_HOST = "localhost"   # Pi typically runs Mosquitto locally
BROKER_PORT = 1883          # Default raw TCP port (HexUI uses WS on 9001)
TOPIC_TELEMETRY = "hexapod/command/controller"
TOPIC_IMU = "hexapod/telemetry/imu"
TOPIC_FEET = "hexapod/telemetry/feet"
TOPIC_STATE = "hexapod/telemetry/state"

def quat_to_euler(w, x, y, z):
    # Roll (x-axis rotation)
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.degrees(math.atan2(sinr_cosp, cosr_cosp))

    # Pitch (y-axis rotation)
    sinp = 2 * (w * y - z * x)
    if abs(sinp) >= 1:
        pitch = math.degrees(math.copysign(math.pi / 2, sinp))
    else:
        pitch = math.degrees(math.asin(sinp))

    # Yaw (z-axis rotation)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.degrees(math.atan2(siny_cosp, cosy_cosp))

    return pitch, roll, yaw

class HexUIBackend:
    def __init__(self, verbose=True):
        self.verbose = verbose
        
        # 1. Initialize Hardware Abstraction
        print("[INIT] Connecting to Hardware (PCA9685/Nano) ...")
        self.ctrl = ServoController(verbose=False)
        self.ctrl.stand()
        print("[INIT] Hardware Ready - Standing Neutral.")

        # 2. Initialize Gait Engines
        self.gaits = {
            "TRIPOD": TripodGait(self.ctrl, verbose=False),
            "RIPPLE": RippleGait(self.ctrl, verbose=False),
        }
        self.active_gait_name = "RIPPLE"
        self.active_gait = self.gaits[self.active_gait_name]
        
        # Stair Climbing Sequence
        self.stair_climb = StairClimbSequence(self.ctrl, verbose=True)

        # 3. Telemetry State Management
        # The frontend blasts 20Hz telemetry. We must avoid 
        # starting a 'walk' cycle if one is already running.
        self.last_update_ts = 0
        self.deadzone = 0.2
        self.is_walking = False

        # Button Debouncing
        self.last_buttons = {0: False, 1: False, 2: False, 3: False}
        
    def start_mqtt(self):
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
        try:
            print(f"[MQTT] Connecting to Broker at {BROKER_HOST}:{BROKER_PORT}...")
            self.client.connect(BROKER_HOST, BROKER_PORT, 60)
            # Starts the MQTT thread in the background
            self.client.loop_start()
            print("[MQTT] Connected and Listening in Background.")
        except ConnectionRefusedError:
            print(f"[ERROR] Could not connect to MQTT broker at {BROKER_HOST}:{BROKER_PORT}.")
            print("Ensure 'mosquitto' is installed and running on the Pi.")
            sys.exit(1)

        # ── Start Telemetry Publisher Thread ──
        self.telem_running = True
        self.telem_thread = threading.Thread(target=self._telemetry_loop, daemon=True)
        self.telem_thread.start()

    def _telemetry_loop(self):
        """Publishes IMU, Foot Contacts, and State at ~10Hz."""
        while self.telem_running:
            if hasattr(self, 'client') and self.client.is_connected():
                # 1. IMU
                w, x, y, z = self.ctrl.imu_quaternion
                pitch, roll, yaw = quat_to_euler(w, x, y, z)
                imu_msg = json.dumps({
                    "pitch": pitch,
                    "roll": roll,
                    "yaw": yaw,
                    "accelX": 0.0,
                    "accelY": 0.0,
                    "accelZ": 0.0
                })
                self.client.publish(TOPIC_IMU, imu_msg, qos=0)

                # 2. Foot Contacts
                feet_msg = json.dumps({
                    "contacts": self.ctrl.foot_contacts
                })
                self.client.publish(TOPIC_FEET, feet_msg, qos=0)

                # 3. State
                state_msg = json.dumps({
                    "active_gait": self.active_gait_name
                })
                self.client.publish(TOPIC_STATE, state_msg, qos=0)
            
            time.sleep(0.1)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[MQTT] Subscribed to '{TOPIC_TELEMETRY}'")
            client.subscribe(TOPIC_TELEMETRY)
        else:
            print(f"[MQTT Error] Connection failed with code {rc}")

    def _on_message(self, client, userdata, msg):
        """
        Callback fired at ~20Hz from the React Frontend gamepad polling.
        Expected JSON Payload: 
        {"axes": {"lx":0, "ly":0.8, "rx":0, "ry":0}, "buttons": {"0":false, "3":true}, "timestamp":...}
        """
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            
            axes = payload.get("axes", {})
            buttons = payload.get("buttons", {})

            # ── 1. Check Buttons for Gait Switching (Debounce) ──
            # Button 3 (Y) toggles the general gait between Tripod/Ripple.
            is_y_pressed = buttons.get("3", False)
            was_y_pressed = self.last_buttons.get(3, False)
            
            if is_y_pressed and not was_y_pressed:
                print("[MODE] Gait switching disabled, locked to RIPPLE")
                # self._toggle_gait()
                
            self.last_buttons[3] = is_y_pressed
            
            # Button 0 (A) triggers Stair Climb
            is_a_pressed = buttons.get("0", False)
            was_a_pressed = self.last_buttons.get(0, False)
            
            if is_a_pressed and not was_a_pressed and not self.is_walking:
                self.is_walking = True
                self.stair_climb.execute_climb(200) # Climb 200mm
                self.is_walking = False
                
            self.last_buttons[0] = is_a_pressed

            # ── 2. Handle Joystick Commands ──
            # We don't want to block the MQTT callback thread for long walking methods.
            # In a true continuous system, we map the input vectors to the phase generator.
            # For our discrete phase algorithms, we trigger 1 cycle at a time if the stick is held.
            
            ly = axes.get("ly", 0.0)
            lx = axes.get("lx", 0.0)
            rx = axes.get("rx", 0.0)

            # Prevent concurrent overlapping walk requests
            if not self.is_walking:
                self.is_walking = True
                
                # Forward / Backward (LY Axis) -> Use Active Gait
                if ly < -self.deadzone:
                    self._dispatch_command('walk_forward', force_tripod=False)
                elif ly > self.deadzone:
                    self._dispatch_command('walk_backward', force_tripod=False)
                
                # Turning (RX Axis) -> Uses Active Gait (Ripple)
                elif rx > self.deadzone:
                    self._dispatch_command('turn_right', force_tripod=False)
                elif rx < -self.deadzone:
                    self._dispatch_command('turn_left', force_tripod=False)
                    
                # Strafing (LX Axis) -> Uses Active Gait (Ripple)
                elif lx > self.deadzone:
                    self._dispatch_command('strafe_right', force_tripod=False)
                elif lx < -self.deadzone:
                    self._dispatch_command('strafe_left', force_tripod=False)
                    
                else:
                    # No stick input -> implicitly stand still using active gait
                    self.active_gait.stop()
                    pass
                
                self.is_walking = False

        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"[HexUI Error] {e}")

    def _toggle_gait(self):
        if self.active_gait_name == "TRIPOD":
            self.active_gait_name = "RIPPLE"
            self.active_gait = self.gaits["RIPPLE"]
        else:
            self.active_gait_name = "TRIPOD"
            self.active_gait = self.gaits["TRIPOD"]
            
        print(f"\n[MODE] Switched active gait to: {self.active_gait_name}")
        self.ctrl.stand()

    def _dispatch_command(self, cmd_name, force_tripod=False):
        """Helper to invoke gait methods safely 1 cycle at a time."""
        gait = self.gaits["TRIPOD"] if force_tripod else self.active_gait
        if hasattr(gait, cmd_name):
            func = getattr(gait, cmd_name)
            func(num_cycles=1)  # Execute 1 discrete chunk
        else:
            print(f"[HexUI] Selected Gait does not support '{cmd_name}' yet.")
            time.sleep(0.5) # small backoff to prevent log spam

    def shutdown(self):
        print("\n[HexUI] Shutting down...")
        self.telem_running = False
        if hasattr(self, 'telem_thread'):
            self.telem_thread.join(timeout=1.0)
            
        if hasattr(self, 'client'):
            self.client.loop_stop()
            self.client.disconnect()
        if hasattr(self, 'ctrl'):
            self.active_gait.stop()
            self.ctrl.shutdown()

if __name__ == "__main__":
    controller = HexUIBackend()
    controller.start_mqtt()
    
    def signal_handler(sig, frame):
        controller.shutdown()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    
    print("\nHexUI Backend Bridge is running. Press Ctrl-C to quit.")
    # Block main thread forever while MQTT runs in background
    signal.pause()
