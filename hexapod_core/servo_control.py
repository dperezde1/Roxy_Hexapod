"""
servo_control.py
────────────────
Hardware abstraction layer for the hexapod's 18 servos.

Routing
  Legs 2-6 (all joints) + Leg 1 YAW  →  PCA9685 via Adafruit ServoKit
  Leg 1 HIP / KNEE                    →  Arduino Nano via USB serial

The calibration transform is applied identically to the user's
existing single-servo control script:
  1. Clamp logical angle to [logical_min, logical_max]
  2. Reverse if needed  (180 - angle)
  3. Add offset
  4. Safety clamp to [0, 180]
"""

import time
import serial
import threading
import serial.tools.list_ports
from adafruit_servokit import ServoKit

from hexapod_config import (
    SERVO_CONFIG,
    LEG_CHANNELS,
    NEUTRAL_ANGLES,
    ARDUINO_BAUD,
)


# ─────────────────────────────────────────────
#  Calibration transform
# ─────────────────────────────────────────────

def logical_to_physical(logical_angle: float, config: dict) -> int:
    """
    Convert a logical (user / gait) angle to the physical angle
    sent to the servo hardware.
    """
    a = max(config["logical_min"], min(config["logical_max"], logical_angle))

    if config["reverse"]:
        a = 180.0 - a

    a += config["offset"]

    return int(round(max(0.0, min(180.0, a))))


# ─────────────────────────────────────────────
#  Arduino helper
# ─────────────────────────────────────────────

def _find_arduino_port():
    """Auto-detect the Arduino Nano serial port."""
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = (p.description or "").lower()
        if any(tag in desc for tag in ("arduino", "ch340", "ftdi", "usb serial")):
            return p.device
    for p in ports:
        dev = p.device or ""
        if "usb" in dev.lower() or "acm" in dev.lower() or "ttyUSB" in dev:
            return p.device
    return None


# ─────────────────────────────────────────────
#  ServoController
# ─────────────────────────────────────────────

class ServoController:
    """
    Unified interface for all 18 hexapod servos.

    Usage
    -----
        ctrl = ServoController()
        ctrl.stand()                  # neutral pose
        ctrl.set_servo(1, "YAW", 75) # single servo
        ctrl.set_leg(2, 90, 60, 80)  # whole leg
        ctrl.set_all_legs(positions)  # all legs at once
        ctrl.shutdown()
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        
        # ── Telemetry State ──
        self.imu_quaternion = (1.0, 0.0, 0.0, 0.0)
        self.foot_contacts = [0, 0, 0, 0, 0, 0]
        self._arduino_running = False
        self._arduino_thread = None

        # ── PCA9685 ──
        self.kit = ServoKit(channels=16)
        if self.verbose:
            print("[INIT] PCA9685 ServoKit ready (16 channels)")

        # ── Arduino Nano ──
        port = _find_arduino_port()
        if port:
            self.arduino = serial.Serial(port, ARDUINO_BAUD, timeout=1)
            time.sleep(2)                       # wait for Nano reset
            self.arduino.reset_input_buffer()
            if self.verbose:
                print(f"[INIT] Arduino Nano on {port} @ {ARDUINO_BAUD} baud")
                
            # Start background telemetry listener
            self._arduino_running = True
            self._arduino_thread = threading.Thread(target=self._arduino_listen_loop, daemon=True)
            self._arduino_thread.start()
        else:
            self.arduino = None
            print("[WARNING] Arduino not found — Leg 1 HIP/KNEE will not work.")

    # ── low-level ────────────────────────────

    def _arduino_listen_loop(self):
        """Background thread parsing 20Hz telemetry and consuming Servo ACKs."""
        while self._arduino_running and self.arduino and self.arduino.is_open:
            try:
                line = self.arduino.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                    
                if line.startswith("TELEM"):
                    parts = line.split(" ")
                    if len(parts) >= 3:
                        q_part = parts[1]
                        b_part = parts[2]
                        
                        if q_part.startswith("Q:"):
                            q_vals = q_part[2:].split(",")
                            if len(q_vals) == 4:
                                try:
                                    self.imu_quaternion = (
                                        float(q_vals[0]), float(q_vals[1]),
                                        float(q_vals[2]), float(q_vals[3])
                                    )
                                except ValueError:
                                    pass
                                    
                        if b_part.startswith("B:"):
                            b_vals = b_part[2:].split(",")
                            if len(b_vals) == 6:
                                # Arduino already inverts with !digitalRead():
                                # 1 = pressed (ground contact), 0 = not pressed (air)
                                try:
                                    self.foot_contacts = [int(v) for v in b_vals]
                                except ValueError:
                                    pass
                                    
                elif line.startswith("OK"):
                    pass # Silently consume servo ACKs so they don't spam terminal
                elif self.verbose:
                    print(f"  [Arduino] {line}")
            except Exception:
                pass

    def _arduino_set(self, pin: int, angle: int):
        """Send a SERVO command to the Arduino Nano."""
        if self.arduino is None:
            if self.verbose:
                print(f"  [Arduino SKIP] D{pin}={angle}° (no connection)")
            return
        cmd = f"SERVO {pin} {angle}\n"
        self.arduino.write(cmd.encode("utf-8"))
        # Do not call readline() here! The listener thread handles ACKs asynchronously.

    # ── public API ───────────────────────────

    def set_servo(self, leg: int, joint: str, logical_angle: float):
        """Move one servo to a logical angle (calibration applied)."""
        config       = SERVO_CONFIG[leg][joint]
        driver, addr = LEG_CHANNELS[leg][joint]
        physical     = logical_to_physical(logical_angle, config)

        if driver == "kit":
            self.kit.servo[addr].angle = physical
        elif driver == "arduino":
            self._arduino_set(addr, physical)

        if self.verbose:
            tag = f"ch{addr:02d}" if driver == "kit" else f"D{addr}"
            print(f"  Leg {leg} {joint:4s} → {driver:7s} {tag} | "
                  f"logical {logical_angle:6.1f}° → physical {physical}°")

    def set_leg(self, leg: int, yaw: float, hip: float, knee: float):
        """Set all three joints of one leg at once."""
        self.set_servo(leg, "YAW",  yaw)
        self.set_servo(leg, "HIP",  hip)
        self.set_servo(leg, "KNEE", knee)

    def set_all_legs(self, positions: dict, verbose_override: bool = None):
        """
        Set every servo from a positions dict.

        Parameters
        ----------
        positions : dict
            {leg_number: {"YAW": angle, "HIP": angle, "KNEE": angle}, ...}
        """
        prev_verbose = self.verbose
        if verbose_override is not None:
            self.verbose = verbose_override

        for leg in sorted(positions.keys()):
            p = positions[leg]
            self.set_leg(leg, p["YAW"], p["HIP"], p["KNEE"])

        self.verbose = prev_verbose

    def stand(self):
        """Move all legs to the neutral standing position."""
        if self.verbose:
            print("\n[STAND] Moving to neutral position …")
        self.set_all_legs(NEUTRAL_ANGLES)
        if self.verbose:
            print("[STAND] Done.\n")

    def shutdown(self):
        """Return to neutral and close connections."""
        if self.verbose:
            print("\n[SHUTDOWN] Returning to stand …")
        self.stand()
        
        self._arduino_running = False
        time.sleep(0.1)
        
        if self.arduino:
            self.arduino.close()
            if self.verbose:
                print("[SHUTDOWN] Arduino serial closed.")
        if self.verbose:
            print("[SHUTDOWN] Complete.\n")
