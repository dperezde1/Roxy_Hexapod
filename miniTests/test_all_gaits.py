#!/usr/bin/env python3
"""
test_all_gaits.py
─────────────────
Sequentially exercises all available gaits and movements of the hexapod
without requiring the MQTT broker or Gamepad controller.

Tests:
1. Tripod (Forward, Backward, Turn, Strafe, Push-up)
2. Ripple (Forward)
3. Stair Climb (Sequence)
"""

import sys
import os
import time

# Correctly resolve paths relative to the miniTests folder
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(SCRIPT_DIR, "..", "hexapod_core"))
sys.path.append(os.path.join(SCRIPT_DIR, "..", "gaits"))

from servo_control import ServoController
from tripod_walk import TripodGait
from ripple_walk import RippleGait
from stair_climb import StairClimbSequence

def run_tests():
    print("==================================================")
    print("   HEXAPOD AUTOMATED GAIT TEST SUITE")
    print("==================================================")
    
    print("\n[SETUP] Initializing Hardware Controller...")
    # Verbose=True prints the joint math and servo states visibly to the console
    ctrl = ServoController(verbose=True)
    
    try:
        ctrl.stand()
        print("\n[SETUP] Standing Neutral. Waiting 2 seconds...")
        time.sleep(2.0)
        
        # ── 1. Tripod Gait Tests ──
        print("\n" + "="*40)
        print(" TEST SUITE 1: TRIPOD GAIT")
        print("="*40)
        tripod = TripodGait(ctrl, verbose=True)
        
        print("\n>>> Testing: Walk Forward (3 cycles)")
        tripod.walk_forward(num_cycles=3)
        time.sleep(1)

        print("\n>>> Testing: Walk Backward (3 cycles)")
        tripod.walk_backward(num_cycles=3)
        time.sleep(1)

        print("\n>>> Testing: Turn Right (2 cycles)")
        tripod.turn_right(num_cycles=2)
        time.sleep(1)

        print("\n>>> Testing: Turn Left (2 cycles)")
        tripod.turn_left(num_cycles=2)
        time.sleep(1)

        print("\n>>> Testing: Strafe Right (Crab Walk) (2 cycles)")
        tripod.strafe_right(num_cycles=2)
        time.sleep(1)

        print("\n>>> Testing: Strafe Left (Crab Walk) (2 cycles)")
        tripod.strafe_left(num_cycles=2)
        time.sleep(1)

        print("\n>>> Testing: Push-up Stance Transition")
        tripod.push_up()
        time.sleep(2)
        tripod.push_down()
        time.sleep(1)
        
        tripod.stop()
        
        # ── 2. Ripple Gait Tests ──
        print("\n" + "="*40)
        print(" TEST SUITE 2: RIPPLE GAIT")
        print("="*40)
        ripple = RippleGait(ctrl, verbose=True)
        
        print("\n>>> Testing: Ripple Walk Forward (2 cycles)")
        if hasattr(ripple, 'walk_forward'):
            ripple.walk_forward(num_cycles=2)
        else:
            print("Ripple walk_forward not found.")
        time.sleep(1)
        
        ripple.stop()

        # ── 3. Stair Climb Tests ──
        print("\n" + "="*40)
        print(" TEST SUITE 3: STAIR CLIMB SEQUENCE")
        print("="*40)
        climber = StairClimbSequence(ctrl, verbose=True)
        
        print("\n>>> Testing: Stair Climb (100mm)")
        if hasattr(climber, 'execute_climb'):
            climber.execute_climb(100)
        else:
            print("execute_climb not found.")
        time.sleep(1)

        print("\n==================================================")
        print("   ALL TESTS COMPLETED SUCCESSFULLY")
        print("==================================================")
        
    except KeyboardInterrupt:
        print("\n[ABORT] Test suite interrupted by user.")
    except Exception as e:
        print(f"\n[ERROR] An exception occurred during testing: {e}")
    finally:
        print("\n[SHUTDOWN] Returning to neutral and closing hardware links...")
        ctrl.shutdown()

if __name__ == "__main__":
    run_tests()
