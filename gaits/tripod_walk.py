"""
tripod_walk.py
──────────────
Angle-based gait engine for a 6-legged hexapod.

Supports:
  • Tripod walk (forward / backward)
  • Push-up (transition to taller/narrower stance)
  • Turning (left / right in place)

Tripod gait overview
────────────────────
Two groups of three legs alternate between SWING (in the air,
moving forward) and STANCE (on the ground, pushing backward):

  Group A  =  legs {1, 3, 5}   (front-right, back-right, mid-left)
  Group B  =  legs {2, 4, 6}   (mid-right,   back-left,  front-left)

One full gait cycle has two phases:
  Phase 1 :  A swings,  B pushes
  Phase 2 :  B swings,  A pushes

The yaw sweep is ± stride_angle relative to each leg's neutral
yaw.  On right-side legs (1, 2, 3) "forward" means a LOWER yaw
angle; on left-side legs (4, 5, 6) "forward" means a HIGHER yaw
angle.  This is because the servos are mirrored.
"""

import time
import copy

from hexapod_config import (
    NEUTRAL_ANGLES,
    TRIPOD_A,
    TRIPOD_B,
    RIGHT_LEGS,
    LEFT_LEGS,
    GAIT_PARAMS,
    SERVO_CONFIG,
    PUSHUP_ANGLES,
    PUSHUP_STEPS,
    PUSHUP_DELAY,
    TURN_PARAMS,
    STRAFE_PARAMS,
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


class TripodGait:
    """
    Tripod gait controller.

    Parameters
    ----------
    servo_controller : ServoController
        Instance from servo_control.py
    params : dict, optional
        Override any key in GAIT_PARAMS
    verbose : bool
        Print phase / step info to console
    """

    def __init__(self, servo_controller, params: dict = None, verbose: bool = True):
        self.ctrl    = servo_controller
        self.verbose = verbose

        # merge user overrides into defaults
        self.params = dict(GAIT_PARAMS)
        if params:
            self.params.update(params)

        # snapshot of neutral for reference
        self.neutral = copy.deepcopy(NEUTRAL_ANGLES)

        # tracks current stance (normal vs push-up)
        self.current_stance = copy.deepcopy(NEUTRAL_ANGLES)

        # running flag (can be cleared by another thread / signal)
        self._running = False

    # ──────────────────────────────────────────
    #  Yaw direction helpers
    # ──────────────────────────────────────────

    def _forward_yaw(self, leg: int, magnitude: float) -> float:
        """
        Return the yaw angle that is `magnitude` degrees FORWARD
        of the leg's neutral yaw.
        """
        neutral_yaw = self.neutral[leg]["YAW"]
        if leg in RIGHT_LEGS:
            return _clamp_joint(leg, "YAW", neutral_yaw - magnitude)
        else:
            return _clamp_joint(leg, "YAW", neutral_yaw + magnitude)

    def _backward_yaw(self, leg: int, magnitude: float) -> float:
        """Opposite of _forward_yaw."""
        neutral_yaw = self.neutral[leg]["YAW"]
        if leg in RIGHT_LEGS:
            return _clamp_joint(leg, "YAW", neutral_yaw + magnitude)
        else:
            return _clamp_joint(leg, "YAW", neutral_yaw - magnitude)

    # ──────────────────────────────────────────
    #  Build target poses for walk phases
    # ──────────────────────────────────────────

    def _phase_start_pose(self, swing_legs, stance_legs, direction=1):
        """Starting pose: swing legs at back yaw, stance at front yaw."""
        stride = self.params["stride_angle"]
        pose = {}
        for leg in swing_legs:
            yaw = self._backward_yaw(leg, stride) if direction == 1 else self._forward_yaw(leg, stride)
            pose[leg] = {"YAW": yaw, "HIP": self.neutral[leg]["HIP"], "KNEE": self.neutral[leg]["KNEE"]}
        for leg in stance_legs:
            yaw = self._forward_yaw(leg, stride) if direction == 1 else self._backward_yaw(leg, stride)
            pose[leg] = {"YAW": yaw, "HIP": self.neutral[leg]["HIP"], "KNEE": self.neutral[leg]["KNEE"]}
        return pose

    def _phase_end_pose(self, swing_legs, stance_legs, direction=1):
        """End pose: swing legs at front, stance at back."""
        stride = self.params["stride_angle"]
        pose = {}
        for leg in swing_legs:
            yaw = self._forward_yaw(leg, stride) if direction == 1 else self._backward_yaw(leg, stride)
            pose[leg] = {"YAW": yaw, "HIP": self.neutral[leg]["HIP"], "KNEE": self.neutral[leg]["KNEE"]}
        for leg in stance_legs:
            yaw = self._backward_yaw(leg, stride) if direction == 1 else self._forward_yaw(leg, stride)
            pose[leg] = {"YAW": yaw, "HIP": self.neutral[leg]["HIP"], "KNEE": self.neutral[leg]["KNEE"]}
        return pose

    # ──────────────────────────────────────────
    #  Execute one walk phase with interpolation
    # ──────────────────────────────────────────

    def _execute_phase(self, swing_legs, stance_legs, direction=1):
        """
        Smoothly interpolate through one walk phase.

        Swing legs: trapezoidal hip+knee profile (lift → hold → lower)
        Stance legs: sweep yaw backward on the ground.
        """
        steps     = self.params["interpolation_steps"]
        delay     = self.params["step_delay"]
        hip_lift  = self.params["hip_lift"]
        knee_bend = self.params["lift_height"]

        start = self._phase_start_pose(swing_legs, stance_legs, direction)
        end   = self._phase_end_pose(swing_legs, stance_legs, direction)

        for i in range(steps + 1):
            if not self._running:
                return

            t = i / steps
            t_smooth = _smooth_step(t)
            pose = {}

            # ── Swing legs (in the air) ──
            for leg in swing_legs:
                yaw = _lerp(start[leg]["YAW"], end[leg]["YAW"], t_smooth)
                neutral_hip  = self.neutral[leg]["HIP"]
                neutral_knee = self.neutral[leg]["KNEE"]

                if t <= 0.25:
                    lift_t = _smooth_step(t / 0.25)
                    hip  = _lerp(neutral_hip,  neutral_hip - hip_lift,   lift_t)
                    knee = _lerp(neutral_knee, neutral_knee + knee_bend, lift_t)
                elif t <= 0.75:
                    hip  = neutral_hip  - hip_lift
                    knee = neutral_knee + knee_bend
                else:
                    lower_t = _smooth_step((t - 0.75) / 0.25)
                    hip  = _lerp(neutral_hip - hip_lift,   neutral_hip,  lower_t)
                    knee = _lerp(neutral_knee + knee_bend, neutral_knee, lower_t)

                pose[leg] = {
                    "YAW": yaw,
                    "HIP": _clamp_joint(leg, "HIP", hip),
                    "KNEE": _clamp_joint(leg, "KNEE", knee),
                }

            # ── Stance legs (on the ground) ──
            for leg in stance_legs:
                yaw = _lerp(start[leg]["YAW"], end[leg]["YAW"], t_smooth)
                pose[leg] = {
                    "YAW":  yaw,
                    "HIP":  self.neutral[leg]["HIP"],
                    "KNEE": self.neutral[leg]["KNEE"],
                }

            self.ctrl.set_all_legs(pose, verbose_override=False)
            if delay > 0:
                time.sleep(delay)

    # ══════════════════════════════════════════
    #  PUBLIC: Walking
    # ══════════════════════════════════════════

    def walk_forward(self, num_cycles: int = 5):
        """Execute num_cycles of forward tripod walk."""
        self._running = True
        if self.verbose:
            print(f"\n[WALK] Forward × {num_cycles} cycles  "
                  f"(stride={self.params['stride_angle']}°, "
                  f"hip_lift={self.params['hip_lift']}°, "
                  f"lift={self.params['lift_height']}°, "
                  f"steps={self.params['interpolation_steps']}, "
                  f"delay={self.params['step_delay']}s)")

        for cycle in range(num_cycles):
            if not self._running:
                break
            if self.verbose:
                print(f"  Cycle {cycle + 1}/{num_cycles}")
            self._execute_phase(TRIPOD_A, TRIPOD_B, direction=1)
            self._execute_phase(TRIPOD_B, TRIPOD_A, direction=1)
            if self.params["cycle_pause"] > 0:
                time.sleep(self.params["cycle_pause"])

        if self.verbose:
            print("[WALK] Done.\n")

    def walk_backward(self, num_cycles: int = 5):
        """Execute num_cycles of backward tripod walk."""
        self._running = True
        if self.verbose:
            print(f"\n[WALK] Backward × {num_cycles} cycles")

        for cycle in range(num_cycles):
            if not self._running:
                break
            if self.verbose:
                print(f"  Cycle {cycle + 1}/{num_cycles}")
            self._execute_phase(TRIPOD_A, TRIPOD_B, direction=-1)
            self._execute_phase(TRIPOD_B, TRIPOD_A, direction=-1)
            if self.params["cycle_pause"] > 0:
                time.sleep(self.params["cycle_pause"])

        if self.verbose:
            print("[WALK] Done.\n")

    def stop(self):
        """Stop the gait loop and return to neutral stance."""
        self._running = False
        if self.verbose:
            print("[STOP] Finishing current step and returning to stand …")
        self.ctrl.stand()
        self.current_stance = copy.deepcopy(NEUTRAL_ANGLES)

    # ══════════════════════════════════════════
    #  PUBLIC: Push-Up (stance transition)
    # ══════════════════════════════════════════

    def _transition_group(self, legs, other_legs, target, steps, delay):
        """
        Lift one tripod group, transition their joints to target
        angles, then lower them — while the other group holds still.

        Three sub-phases:
          1. Lift legs off the ground
          2. Move joints to target while in the air
          3. Lower legs to plant at new pose
        """
        hip_lift  = self.params.get("hip_lift", 25)
        knee_bend = self.params.get("lift_height", 20)

        current = {leg: dict(self.current_stance[leg]) for leg in legs}

        lift_steps  = max(1, steps // 4)
        move_steps  = max(1, steps // 2)
        lower_steps = max(1, steps // 4)

        # ── Phase 1: LIFT off the ground ──
        for i in range(lift_steps + 1):
            t = _smooth_step(i / lift_steps)
            pose = {}
            for leg in legs:
                hip  = _lerp(current[leg]["HIP"],  current[leg]["HIP"] - hip_lift, t)
                knee = _lerp(current[leg]["KNEE"], current[leg]["KNEE"] + knee_bend, t)
                pose[leg] = {
                    "YAW":  current[leg]["YAW"],
                    "HIP":  _clamp_joint(leg, "HIP",  hip),
                    "KNEE": _clamp_joint(leg, "KNEE", knee),
                }
            for leg in other_legs:
                pose[leg] = dict(self.current_stance[leg])
            self.ctrl.set_all_legs(pose, verbose_override=False)
            time.sleep(delay)

        lifted_hip  = {leg: _clamp_joint(leg, "HIP",  current[leg]["HIP"] - hip_lift) for leg in legs}
        lifted_knee = {leg: _clamp_joint(leg, "KNEE", current[leg]["KNEE"] + knee_bend) for leg in legs}

        # ── Phase 2: MOVE joints to target while in the air ──
        for i in range(move_steps + 1):
            t = _smooth_step(i / move_steps)
            pose = {}
            for leg in legs:
                yaw = _lerp(current[leg]["YAW"], target[leg]["YAW"], t)
                target_hip_up  = _clamp_joint(leg, "HIP",  target[leg]["HIP"] - hip_lift)
                target_knee_up = _clamp_joint(leg, "KNEE", target[leg]["KNEE"] + knee_bend)
                hip  = _lerp(lifted_hip[leg],  target_hip_up,  t)
                knee = _lerp(lifted_knee[leg], target_knee_up, t)
                pose[leg] = {
                    "YAW":  _clamp_joint(leg, "YAW", yaw),
                    "HIP":  _clamp_joint(leg, "HIP",  hip),
                    "KNEE": _clamp_joint(leg, "KNEE", knee),
                }
            for leg in other_legs:
                pose[leg] = dict(self.current_stance[leg])
            self.ctrl.set_all_legs(pose, verbose_override=False)
            time.sleep(delay)

        # ── Phase 3: LOWER legs to plant at target ──
        for i in range(lower_steps + 1):
            t = _smooth_step(i / lower_steps)
            pose = {}
            for leg in legs:
                target_hip_up  = _clamp_joint(leg, "HIP",  target[leg]["HIP"] - hip_lift)
                target_knee_up = _clamp_joint(leg, "KNEE", target[leg]["KNEE"] + knee_bend)
                hip  = _lerp(target_hip_up,  target[leg]["HIP"],  t)
                knee = _lerp(target_knee_up, target[leg]["KNEE"], t)
                pose[leg] = {
                    "YAW":  target[leg]["YAW"],
                    "HIP":  _clamp_joint(leg, "HIP",  hip),
                    "KNEE": _clamp_joint(leg, "KNEE", knee),
                }
            for leg in other_legs:
                pose[leg] = dict(self.current_stance[leg])
            self.ctrl.set_all_legs(pose, verbose_override=False)
            time.sleep(delay)

        # Update tracked stance
        for leg in legs:
            self.current_stance[leg] = dict(target[leg])

    def push_up(self):
        """
        Transition from current stance to the taller/narrower
        push-up pose using a ripple sequence (pairs) for high stability.
        """
        if self.verbose:
            print("\n[PUSH-UP] Rising to tall stance (Ripple Style) …")

        target = copy.deepcopy(PUSHUP_ANGLES)
        pairs = [[1, 4], [2, 5], [3, 6]]
        all_legs = {1, 2, 3, 4, 5, 6}
        
        for pair in pairs:
            other_legs = list(all_legs - set(pair))
            self._transition_group(pair, other_legs, target, PUSHUP_STEPS, PUSHUP_DELAY)

        if self.verbose:
            print("[PUSH-UP] Done — standing tall.\n")

    def push_down(self):
        """
        Transition from push-up pose back to normal neutral
        stance using a ripple sequence (pairs).
        """
        if self.verbose:
            print("\n[PUSH-DOWN] Lowering to normal stance (Ripple Style) …")

        target = copy.deepcopy(NEUTRAL_ANGLES)
        pairs = [[1, 4], [2, 5], [3, 6]]
        all_legs = {1, 2, 3, 4, 5, 6}
        
        for pair in pairs:
            other_legs = list(all_legs - set(pair))
            self._transition_group(pair, other_legs, target, PUSHUP_STEPS, PUSHUP_DELAY)

        if self.verbose:
            print("[PUSH-DOWN] Done — normal stance.\n")

    # ══════════════════════════════════════════
    #  PUBLIC: Turning
    # ══════════════════════════════════════════

    def _turn_phase(self, swing_legs, stance_legs, turn_direction):
        """
        One turning phase.  turn_direction: +1 = right, -1 = left.

        Stance legs (on ground) sweep yaw to PUSH the body.
        Swing legs (in air) sweep yaw the OPPOSITE way to
        REPOSITION for the next push — so the two phases
        accumulate rotation instead of canceling out.
        """
        tp = TURN_PARAMS
        steps     = tp["interpolation_steps"]
        delay     = tp["step_delay"]
        hip_lift  = tp["hip_lift"]
        knee_bend = tp["knee_bend"]
        angle     = tp["turn_angle"]

        # Stance legs: sweep in the "push" direction
        # Swing legs:  sweep in the opposite direction (reposition)
        stance_start = {}
        stance_end   = {}
        swing_start  = {}
        swing_end    = {}

        for leg in stance_legs:
            neutral_yaw = self.neutral[leg]["YAW"]
            if turn_direction == 1:  # right turn
                stance_start[leg] = _clamp_joint(leg, "YAW", neutral_yaw - angle)
                stance_end[leg]   = _clamp_joint(leg, "YAW", neutral_yaw + angle)
            else:  # left turn
                stance_start[leg] = _clamp_joint(leg, "YAW", neutral_yaw + angle)
                stance_end[leg]   = _clamp_joint(leg, "YAW", neutral_yaw - angle)

        for leg in swing_legs:
            neutral_yaw = self.neutral[leg]["YAW"]
            # Swing goes the OPPOSITE way (repositioning)
            if turn_direction == 1:  # right turn
                swing_start[leg] = _clamp_joint(leg, "YAW", neutral_yaw + angle)
                swing_end[leg]   = _clamp_joint(leg, "YAW", neutral_yaw - angle)
            else:  # left turn
                swing_start[leg] = _clamp_joint(leg, "YAW", neutral_yaw - angle)
                swing_end[leg]   = _clamp_joint(leg, "YAW", neutral_yaw + angle)

        for i in range(steps + 1):
            if not self._running:
                return

            t = i / steps
            t_smooth = _smooth_step(t)
            pose = {}

            # Swing legs: lift + rotate OPPOSITE + lower
            for leg in swing_legs:
                yaw = _lerp(swing_start[leg], swing_end[leg], t_smooth)
                neutral_hip  = self.neutral[leg]["HIP"]
                neutral_knee = self.neutral[leg]["KNEE"]

                if t <= 0.25:
                    lift_t = _smooth_step(t / 0.25)
                    hip  = _lerp(neutral_hip,  neutral_hip - hip_lift,   lift_t)
                    knee = _lerp(neutral_knee, neutral_knee + knee_bend, lift_t)
                elif t <= 0.75:
                    hip  = neutral_hip  - hip_lift
                    knee = neutral_knee + knee_bend
                else:
                    lower_t = _smooth_step((t - 0.75) / 0.25)
                    hip  = _lerp(neutral_hip - hip_lift,   neutral_hip,  lower_t)
                    knee = _lerp(neutral_knee + knee_bend, neutral_knee, lower_t)

                pose[leg] = {
                    "YAW":  yaw,
                    "HIP":  _clamp_joint(leg, "HIP",  hip),
                    "KNEE": _clamp_joint(leg, "KNEE", knee),
                }

            # Stance legs: rotate on the ground (PUSH direction)
            for leg in stance_legs:
                yaw = _lerp(stance_start[leg], stance_end[leg], t_smooth)
                pose[leg] = {
                    "YAW":  yaw,
                    "HIP":  self.neutral[leg]["HIP"],
                    "KNEE": self.neutral[leg]["KNEE"],
                }

            self.ctrl.set_all_legs(pose, verbose_override=False)
            if delay > 0:
                time.sleep(delay)

    def turn_right(self, num_cycles: int = 3):
        """Turn clockwise for num_cycles."""
        self._running = True
        if self.verbose:
            print(f"\n[TURN] Right × {num_cycles} cycles  "
                  f"(angle={TURN_PARAMS['turn_angle']}°)")

        for cycle in range(num_cycles):
            if not self._running:
                break
            if self.verbose:
                print(f"  Cycle {cycle + 1}/{num_cycles}")
            self._turn_phase(TRIPOD_A, TRIPOD_B, turn_direction=1)
            self._turn_phase(TRIPOD_B, TRIPOD_A, turn_direction=1)

        if self.verbose:
            print("[TURN] Done.\n")

    def turn_left(self, num_cycles: int = 3):
        """Turn counter-clockwise for num_cycles."""
        self._running = True
        if self.verbose:
            print(f"\n[TURN] Left × {num_cycles} cycles  "
                  f"(angle={TURN_PARAMS['turn_angle']}°)")

        for cycle in range(num_cycles):
            if not self._running:
                break
            if self.verbose:
                print(f"  Cycle {cycle + 1}/{num_cycles}")
            self._turn_phase(TRIPOD_A, TRIPOD_B, turn_direction=-1)
            self._turn_phase(TRIPOD_B, TRIPOD_A, turn_direction=-1)

        if self.verbose:
            print("[TURN] Done.\n")

    # ══════════════════════════════════════════
    #  PUBLIC: Strafing (Crab Walk)
    # ══════════════════════════════════════════

    def _strafe_phase(self, swing_legs, stance_legs, strafe_direction):
        """
        One strafing phase. strafe_direction: +1 = right, -1 = left.
        
        Purely stretches and tucks the knee joints while holding yaw neutral.
        For strafing RIGHT (+1), right legs PULL (tuck knee), left legs PUSH (extend knee).
        """
        sp = STRAFE_PARAMS
        steps     = sp["interpolation_steps"]
        delay     = sp["step_delay"]
        hip_lift  = sp["hip_lift"]
        knee_bend = sp["knee_bend"]
        shift     = sp["knee_shift"]

        stance_start = {}
        stance_end   = {}
        swing_start  = {}
        swing_end    = {}

        for leg in stance_legs:
            neutral_knee = self.neutral[leg]["KNEE"]
            is_right_leg = leg in RIGHT_LEGS
            reach_out = neutral_knee - shift
            tuck_in   = neutral_knee + shift
            
            # Stance legs push body in the strafe_direction
            if strafe_direction == 1: # Right
                stance_start[leg] = reach_out if is_right_leg else tuck_in
                stance_end[leg]   = tuck_in if is_right_leg else reach_out
            else: # Left
                stance_start[leg] = tuck_in if is_right_leg else reach_out
                stance_end[leg]   = reach_out if is_right_leg else tuck_in

        for leg in swing_legs:
            neutral_knee = self.neutral[leg]["KNEE"]
            is_right_leg = leg in RIGHT_LEGS
            reach_out = neutral_knee - shift
            tuck_in   = neutral_knee + shift
            
            # Swing legs do the opposite to reset for next phase
            if strafe_direction == 1:
                swing_start[leg] = tuck_in if is_right_leg else reach_out
                swing_end[leg]   = reach_out if is_right_leg else tuck_in
            else:
                swing_start[leg] = reach_out if is_right_leg else tuck_in
                swing_end[leg]   = tuck_in if is_right_leg else reach_out

        for i in range(steps + 1):
            if not self._running:
                return

            t = i / steps
            t_smooth = _smooth_step(t)
            pose = {}

            # Swing legs: lift + shift knee + lower
            for leg in swing_legs:
                base_knee = _lerp(swing_start[leg], swing_end[leg], t_smooth)
                neutral_hip  = self.neutral[leg]["HIP"]
                
                if t <= 0.25:
                    lift_t = _smooth_step(t / 0.25)
                    hip  = _lerp(neutral_hip,  neutral_hip - hip_lift, lift_t)
                    knee = _lerp(base_knee, base_knee + knee_bend, lift_t)
                elif t <= 0.75:
                    hip  = neutral_hip  - hip_lift
                    knee = base_knee + knee_bend
                else:
                    lower_t = _smooth_step((t - 0.75) / 0.25)
                    hip  = _lerp(neutral_hip - hip_lift, neutral_hip, lower_t)
                    knee = _lerp(base_knee + knee_bend, base_knee, lower_t)

                pose[leg] = {
                    "YAW":  self.neutral[leg]["YAW"],
                    "HIP":  _clamp_joint(leg, "HIP",  hip),
                    "KNEE": _clamp_joint(leg, "KNEE", knee),
                }

            # Stance legs: push/pull body sideways
            for leg in stance_legs:
                knee = _lerp(stance_start[leg], stance_end[leg], t_smooth)
                pose[leg] = {
                    "YAW":  self.neutral[leg]["YAW"],
                    "HIP":  self.neutral[leg]["HIP"],
                    "KNEE": _clamp_joint(leg, "KNEE", knee),
                }

            self.ctrl.set_all_legs(pose, verbose_override=False)
            if delay > 0:
                time.sleep(delay)

    def strafe_right(self, num_cycles: int = 3):
        """Strafe right for num_cycles."""
        self._running = True
        if self.verbose:
            print(f"\n[STRAFE] Right × {num_cycles} cycles")

        for cycle in range(num_cycles):
            if not self._running:
                break
            if self.verbose:
                print(f"  Cycle {cycle + 1}/{num_cycles}")
            self._strafe_phase(TRIPOD_A, TRIPOD_B, strafe_direction=1)
            self._strafe_phase(TRIPOD_B, TRIPOD_A, strafe_direction=1)

        if self.verbose:
            print("[STRAFE] Done.\n")

    def strafe_left(self, num_cycles: int = 3):
        """Strafe left for num_cycles."""
        self._running = True
        if self.verbose:
            print(f"\n[STRAFE] Left × {num_cycles} cycles")

        for cycle in range(num_cycles):
            if not self._running:
                break
            if self.verbose:
                print(f"  Cycle {cycle + 1}/{num_cycles}")
            self._strafe_phase(TRIPOD_A, TRIPOD_B, strafe_direction=-1)
            self._strafe_phase(TRIPOD_B, TRIPOD_A, strafe_direction=-1)

        if self.verbose:
            print("[STRAFE] Done.\n")
