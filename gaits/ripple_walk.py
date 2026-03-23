"""
ripple_walk.py
──────────────
Continuous wave (ripple) gait engine for a 6-legged hexapod.

Supports:
  • Ripple walk (forward / backward)
  • Stand (return to neutral pose)

Ripple gait overview
────────────────────
The ripple gait is a continuous wave moving from the rear to the front
of the body. Contralateral legs (opposite side, same segment) are 180°
out of phase. Adjacent ipsilateral legs (same side, consecutive segments)
are 90° out of phase (or spaced evenly by 1/6th of a cycle).

This results in a stable 4-on-the-ground, 2-in-the-air sequence:
Phase 0: L3 lifts, R2 lifts
Phase 1: L2 lifts, R1 lifts
Phase 2: L1 lifts, R3 lifts

We use a continuous time variable `t` from 0.0 to 1.0.
Each leg has a phase offset.
  Phase 0.0 to 0.16 (1/6th): Leg swings forward (lifts, sweeps, lowers)
  Phase 0.16 to 1.0 (5/6th): Leg stays on ground, sweeps backward
"""

import time
import copy
import math

from hexapod_config import (
    NEUTRAL_ANGLES,
    RIGHT_LEGS,
    LEFT_LEGS,
    GAIT_PARAMS,
    SERVO_CONFIG,
)


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation from a to b by factor t ∈ [0, 1]."""
    return a + (b - a) * t


def _smooth_step(t: float) -> float:
    """
    Smoothstep easing — zero velocity at start and end.
    Maps t ∈ [0, 1] → [0, 1] with smooth acceleration.
    """
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _clamp_joint(leg: int, joint: str, angle: float) -> float:
    """Clamp an angle to the servo's logical limits."""
    cfg = SERVO_CONFIG[leg][joint]
    return max(cfg["logical_min"], min(cfg["logical_max"], angle))


class RippleGait:
    """
    Continuous Ripple gait controller.

    Parameters
    ----------
    servo_controller : ServoController
        Instance from servo_control.py
    params : dict, optional
        Override any key in GAIT_PARAMS
    verbose : bool
        Print phase info to console
    """

    def __init__(self, servo_controller, params: dict = None, verbose: bool = True):
        self.ctrl    = servo_controller
        self.verbose = verbose

        # Merge user overrides into defaults
        self.params = dict(GAIT_PARAMS)
        if params:
            self.params.update(params)

        self.neutral = copy.deepcopy(NEUTRAL_ANGLES)
        self._running = False

        # ── Leg phase offsets (0.0 to 1.0) ──
        # Adjacent legs differ by 1/6 = ~0.166
        # Opposite legs differ by 1/2 = 0.5
        # We start the wave from the back (3) moving to front (1)
        # R3=0, R2=1/6, R1=2/6
        # L3=3/6, L2=4/6, L1=5/6
        self.leg_offsets = {
            3: 0.0,             # Right Back
            2: 1.0 / 6.0,       # Right Mid
            1: 2.0 / 6.0,       # Right Front
            6: 3.0 / 6.0,       # Left Back  (opposite R3 + 0.5)
            5: 4.0 / 6.0,       # Left Mid   (opposite R2 + 0.5)
            4: 5.0 / 6.0,       # Left Front (opposite R1 + 0.5)
        }

        # The fraction of the cycle a single leg spends in the air
        self.duty_cycle = 1.0 / 6.0

    # ──────────────────────────────────────────
    #  Trajectory Generator
    # ──────────────────────────────────────────

    def _get_leg_pose(self, leg: int, global_t: float, direction: int) -> dict:
        """
        Calculate the required angles for a single leg at a given global time.
        
        direction: +1 for forward walk, -1 for backward walk
        """
        stride    = self.params["stride_angle"]
        hip_lift  = self.params["hip_lift"]
        lift      = self.params["lift_height"]
        
        # Local phase for this leg: shift global time by leg's offset
        # Result is 0.0 to 1.0 where 0.0 is the start of its swing phase
        local_t = (global_t - self.leg_offsets[leg]) % 1.0
        
        # We define YAW relative to neutral
        # Forward YAW mapping:
        # Right legs: forward = lower yaw (-offset)
        # Left legs:  forward = higher yaw (+offset)
        # By default, a "forward" swing moves the leg forward.
        def yaw_angle(offset):
            neutral_yaw = self.neutral[leg]["YAW"]
            if leg in RIGHT_LEGS:
                return neutral_yaw - offset
            else:
                return neutral_yaw + offset

        neutral_hip  = self.neutral[leg]["HIP"]
        neutral_knee = self.neutral[leg]["KNEE"]
        
        # ──  Phase 1: SWING (Leg in air)  ──
        if local_t <= self.duty_cycle:
            # Map 0 -> duty_cycle to normalized 0.0 -> 1.0
            st = local_t / self.duty_cycle
            st_smooth = _smooth_step(st)
            
            # Yaw sweeps from BACK to FRONT
            # IF direction is -1 (walking backward), swing goes FRONT to BACK
            start_yaw = yaw_angle(-stride) if direction == 1 else yaw_angle(stride)
            end_yaw   = yaw_angle(stride)  if direction == 1 else yaw_angle(-stride)
            yaw = _lerp(start_yaw, end_yaw, st_smooth)
            
            # Trapezoidal Hip/Knee lift
            # 0-25% lift up
            # 25-75% hold high
            # 75-100% lower
            if st <= 0.25:
                lt = _smooth_step(st / 0.25)
                hip  = _lerp(neutral_hip,  neutral_hip - hip_lift, lt)
                knee = _lerp(neutral_knee, neutral_knee + lift,    lt)
            elif st <= 0.75:
                hip  = neutral_hip - hip_lift
                knee = neutral_knee + lift
            else:
                lt = _smooth_step((st - 0.75) / 0.25)
                hip  = _lerp(neutral_hip - hip_lift, neutral_hip,  lt)
                knee = _lerp(neutral_knee + lift,    neutral_knee, lt)
                
        # ──  Phase 2: STANCE (Leg on ground)  ──
        else:
            # Map duty_cycle -> 1.0 to normalized 0.0 -> 1.0
            stance_fraction = 1.0 - self.duty_cycle
            st = (local_t - self.duty_cycle) / stance_fraction
            
            # Yaw sweeps from FRONT to BACK
            start_yaw = yaw_angle(stride)  if direction == 1 else yaw_angle(-stride)
            end_yaw   = yaw_angle(-stride) if direction == 1 else yaw_angle(stride)
            
            # Linear push for constant body speed
            yaw = _lerp(start_yaw, end_yaw, st)
            
            # Keep hip/knee planted at neutral
            hip  = neutral_hip
            knee = neutral_knee

        return {
            "YAW":  _clamp_joint(leg, "YAW",  yaw),
            "HIP":  _clamp_joint(leg, "HIP",  hip),
            "KNEE": _clamp_joint(leg, "KNEE", knee)
        }

    # ──────────────────────────────────────────
    #  Execution Loop
    # ──────────────────────────────────────────

    def _execute_cycles(self, num_cycles: int, direction: int = 1):
        """
        Run the ripple gait loop by incrementing global time `t`.
        """
        # We need more resolution than tripod because the cycle is continuous
        # and there are 6 defined sub-phases. 
        # Using 60 steps per cycle means 10 steps per leg's swing phase.
        steps_per_cycle = max(60, self.params["interpolation_steps"] * 2)
        delay = self.params["step_delay"]
        
        for cycle in range(num_cycles):
            if not self._running:
                break
                
            if self.verbose:
                print(f"  Cycle {cycle + 1}/{num_cycles}")
                
            for step in range(steps_per_cycle):
                if not self._running:
                    return
                    
                global_t = step / steps_per_cycle
                
                pose = {}
                for leg in range(1, 7):
                    pose[leg] = self._get_leg_pose(leg, global_t, direction)
                    
                self.ctrl.set_all_legs(pose, verbose_override=False)
                
                if delay > 0:
                    time.sleep(delay)
                    
            if self.params["cycle_pause"] > 0:
                time.sleep(self.params["cycle_pause"])

    # ──────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────

    def walk_forward(self, num_cycles: int = 5):
        self._running = True
        if self.verbose:
            print(f"\n[RIPPLE] Forward × {num_cycles} cycles")
        self._execute_cycles(num_cycles, direction=1)
        if self.verbose:
            print("[RIPPLE] Done.\n")

    def walk_backward(self, num_cycles: int = 5):
        self._running = True
        if self.verbose:
            print(f"\n[RIPPLE] Backward × {num_cycles} cycles")
        self._execute_cycles(num_cycles, direction=-1)
        if self.verbose:
            print("[RIPPLE] Done.\n")

    def stop(self):
        self._running = False
        if self.verbose:
            print("[STOP] Returning to stand …")
        self.ctrl.stand()
