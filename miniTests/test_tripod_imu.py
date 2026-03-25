#!/usr/bin/env python3
"""
test_tripod_imu.py
──────────────────
Tests the basic Tripod Gait engine while rapidly printing out
the asynchronous IMU and Foot Contact telemetry coming from
the Arduino background thread.
"""

import sys
import os
import time

# Add core and gaits to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, "..", "hexapod_core"))
sys.path.append(os.path.join(BASE_DIR, "..", "gaits"))

from servo_control import ServoController
from tripod_walk import TripodGait

def test_walk_with_telemetry():
    print("Initializing Hexapod Controller...")
    # Initialize the unified controller
    ctrl = ServoController(verbose=False)
    
    # Initialize the gait engine
    gait = TripodGait(ctrl, verbose=False)

    print("\n" + "="*50)
    print("Starting Tripod Walk + Telemetry Stream")
    print("="*50)

    try:
        # Move to standing position first
        ctrl.stand()
        time.sleep(1.0)
        
        print("Walking Forward...")
        
        # We will manually command half-cycles or just run a tight loop
        # But wait - walk_forward() blocks until the cycle is complete.
        # So instead of relying on the blocking walk_forward(), we will 
        # kick off the walk_forward(...) and then just print telemetry before 
        # and after, OR we can just modify the walk parameters slightly or 
        # wrap it in a thread to print telemetry continuously while it walks.

        # The easiest approach is to spin up a quick printer thread!
        running = True
        
        import threading
        def print_telemetry():
            while running:
                q = ctrl.imu_quaternion
                b = ctrl.foot_contacts
                sys.stdout.write(f"\r[Telemetry] Quat:({q[0]:5.2f}, {q[1]:5.2f}, {q[2]:5.2f}, {q[3]:5.2f})  Btns:{b}")
                sys.stdout.flush()
                time.sleep(0.05)

        telemetry_thread = threading.Thread(target=print_telemetry, daemon=True)
        telemetry_thread.start()

        # Execute 5 cycles of walking
        gait.walk_forward(num_cycles=5)
        
        # Stop printing thread
        running = False
        print("\n\nWalk complete. Shutting down...")
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user!")
        running = False
    finally:
        ctrl.shutdown()

if __name__ == "__main__":
    test_walk_with_telemetry()
