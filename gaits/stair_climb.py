"""
stair_climb.py
──────────────
Discrete phase routine for climbing a 200mm vertical stair step.

Unlike cyclic walking gaits, climbing a massive obstacle requires
specific, sequential shifting of the center of gravity and extreme
joint extensions.
"""

import time
import copy
from hexapod_core.hexapod_config import NEUTRAL_ANGLES, SERVO_CONFIG

def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def _smooth_step(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

def _clamp_joint(leg: int, joint: str, angle: float) -> float:
    cfg = SERVO_CONFIG[leg][joint]
    return max(cfg["logical_min"], min(cfg["logical_max"], angle))

class StairClimbSequence:
    def __init__(self, servo_controller, verbose=True):
        self.ctrl = servo_controller
        self.verbose = verbose
        self.current_stance = copy.deepcopy(NEUTRAL_ANGLES)
        self.steps = 50
        self.delay = 0.03
        
    def _execute_transition(self, target_pose, steps=None, delay=None):
        """Smoothly moves all 18 servos from current_stance to target_pose."""
        steps = steps or self.steps
        delay = delay or self.delay
        
        start_pose = copy.deepcopy(self.current_stance)
        
        for i in range(steps + 1):
            t = _smooth_step(i / steps)
            pose = {}
            for leg in range(1, 7):
                if leg in target_pose:
                    pose[leg] = {
                        "YAW":  _clamp_joint(leg, "YAW",  _lerp(start_pose[leg]["YAW"],  target_pose[leg]["YAW"],  t)),
                        "HIP":  _clamp_joint(leg, "HIP",  _lerp(start_pose[leg]["YAW"],  target_pose[leg]["HIP"],  t)),
                        "KNEE": _clamp_joint(leg, "KNEE", _lerp(start_pose[leg]["YAW"],  target_pose[leg]["KNEE"], t)),
                    }
                else:
                    pose[leg] = dict(start_pose[leg])
                    
            self.ctrl.set_all_legs(pose, verbose_override=False)
            time.sleep(delay)
            
        # Update current stance
        for leg, angles in target_pose.items():
            self.current_stance[leg] = dict(angles)

    def execute_climb(self, step_height_mm=200):
        """
        Executes a 3-phase lurch to climb a 200mm step.
        """
        if self.verbose:
            print(f"\n[STAIR CLIMB] Initiating 200mm step climb sequence...")
            
        # ── Phase 1: Front Lurch ──
        # Lift front legs extremely high, reach forward, and plant on step.
        if self.verbose: print("  Phase 1: Planting Front Legs High")
        target_1 = copy.deepcopy(self.current_stance)
        
        # NOTE: To reach 200mm high, the hip must go near 0 (flat outwards) and 
        # the knee must extend significantly. (Values are estimations requiring tuning)
        front_legs = [1, 4]  # Right Front, Left Front
        for leg in front_legs:
            target_1[leg]["HIP"] = 15    # Lift hip nearly flat to clear step
            target_1[leg]["KNEE"] = 130  # Extend knee to plant far forward
            # Sweep yaw slightly outward to widen stance on step
            target_1[leg]["YAW"] = 60 if leg == 1 else 120 

        self._execute_transition(target_1)
        time.sleep(1.0)
        
        # ── Phase 2: Heave / CG Shift ──
        # Pull the front legs back to drag body up/forward.
        # Push with rear legs (raise hips) to elevate the back.
        if self.verbose: print("  Phase 2: Heave Center of Gravity Forward")
        target_2 = copy.deepcopy(self.current_stance)
        
        # Front legs pull back
        for leg in front_legs:
            # Hip pushes down (increases angle) to lift body up
            target_2[leg]["HIP"] = 60 
            target_2[leg]["KNEE"] = 90
            target_2[leg]["YAW"] = 90
            
        # Middle legs [2, 5] and Rear legs [3, 6] push UP to elevate body
        back_legs = [2, 5, 3, 6]
        for leg in back_legs:
            # Hips down (pushes legs into ground -> raises body)
            target_2[leg]["HIP"] = 125 
            # Knees extend backwards to propel body forward
            target_2[leg]["KNEE"] = 40

        self._execute_transition(target_2, steps=80, delay=0.04) # Slower, heavy heave
        time.sleep(1.0)
        
        # ── Phase 3: Rear Recovery ──
        # With CG safely on the upper step, lift the rear legs onto the step.
        if self.verbose: print("  Phase 3: Recovering Rear Legs")
        target_3 = copy.deepcopy(NEUTRAL_ANGLES) 
        # Target is back to neutral, but now the whole robot is 200mm higher.
        
        self._execute_transition(target_3)
        
        if self.verbose:
            print("[STAIR CLIMB] Sequence Complete.\n")

    def stop(self):
        self.ctrl.stand()
        self.current_stance = copy.deepcopy(NEUTRAL_ANGLES)
