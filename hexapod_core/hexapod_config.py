"""
hexapod_config.py
─────────────────
All hardware constants, calibration data, and tuneable gait
parameters for the hexapod tripod walk.
"""

import math

# ═════════════════════════════════════════════════════════════
#  SERVO CALIBRATION
# ═════════════════════════════════════════════════════════════
# logical_min / logical_max : range the user (or gait code) commands
# offset   : added after optional reverse; shifts physical zero
# reverse  : if True → angle = 180 - angle BEFORE offset

SERVO_CONFIG = {
    # ── Leg 1 (Front-Right) ────────────────────────────────
    1: {
        "YAW":  {"logical_min": 0, "logical_max": 180, "offset": -5,  "reverse": False},
        "HIP":  {"logical_min": 0, "logical_max": 135, "offset":  15, "reverse": False},
        "KNEE": {"logical_min": 0, "logical_max": 180, "offset":  0,  "reverse": True},
    },
    # ── Leg 2 (Mid-Right) ─────────────────────────────────
    2: {
        "YAW":  {"logical_min": 0, "logical_max": 180, "offset":  5,  "reverse": False},
        "HIP":  {"logical_min": 0, "logical_max": 135, "offset":  5,  "reverse": False},
        "KNEE": {"logical_min": 0, "logical_max": 180, "offset": -15, "reverse": False},
    },
    # ── Leg 3 (Back-Right) ────────────────────────────────
    3: {
        "YAW":  {"logical_min": 0, "logical_max": 180, "offset":  0,  "reverse": False},
        "HIP":  {"logical_min": 0, "logical_max": 135, "offset":  0,  "reverse": False},
        "KNEE": {"logical_min": 0, "logical_max": 180, "offset": -20, "reverse": False},
    },
    # ── Leg 4 (Back-Left) ─────────────────────────────────
    4: {
        "YAW":  {"logical_min": 0, "logical_max": 180, "offset":  5,  "reverse": False},
        "HIP":  {"logical_min": 0, "logical_max": 135, "offset":  5,  "reverse": False},
        "KNEE": {"logical_min": 0, "logical_max": 180, "offset": -15, "reverse": False},
    },
    # ── Leg 5 (Mid-Left) ──────────────────────────────────
    5: {
        "YAW":  {"logical_min": 0, "logical_max": 180, "offset":  5,  "reverse": False},
        "HIP":  {"logical_min": 0, "logical_max": 135, "offset":  0,  "reverse": False},
        "KNEE": {"logical_min": 0, "logical_max": 180, "offset":  0,  "reverse": False},
    },
    # ── Leg 6 (Front-Left) ────────────────────────────────
    6: {
        "YAW":  {"logical_min": 0, "logical_max": 180, "offset":  0,  "reverse": False},
        "HIP":  {"logical_min": 0, "logical_max": 135, "offset":  0,  "reverse": False},
        "KNEE": {"logical_min": 0, "logical_max": 180, "offset":  0,  "reverse": False},
    },
}

# ═════════════════════════════════════════════════════════════
#  CHANNEL / PIN MAPPING
# ═════════════════════════════════════════════════════════════
# ("kit", ch)      → PCA9685 ServoKit channel
# ("arduino", pin) → Arduino Nano digital pin via USB serial

LEG_CHANNELS = {
    1: {
        "YAW":  ("kit",     15),
        "HIP":  ("arduino",  5),
        "KNEE": ("arduino",  6),
    },
    2: {"YAW": ("kit",  0), "HIP": ("kit",  1), "KNEE": ("kit",  2)},
    3: {"YAW": ("kit",  3), "HIP": ("kit",  4), "KNEE": ("kit",  5)},
    4: {"YAW": ("kit",  6), "HIP": ("kit",  7), "KNEE": ("kit",  8)},
    5: {"YAW": ("kit",  9), "HIP": ("kit", 10), "KNEE": ("kit", 11)},
    6: {"YAW": ("kit", 12), "HIP": ("kit", 13), "KNEE": ("kit", 14)},
}

# ═════════════════════════════════════════════════════════════
#  NEUTRAL STANDING ANGLES  (logical degrees)
# ═════════════════════════════════════════════════════════════
# Yaw perpendicular to side wall, hip horizontal, tibia 90° down

NEUTRAL_ANGLES = {
    1: {"YAW":  90, "HIP": 110, "KNEE": 60},
    2: {"YAW":  90, "HIP": 110, "KNEE": 60},
    3: {"YAW":  90, "HIP": 110, "KNEE": 60},
    4: {"YAW":  90, "HIP": 110, "KNEE": 60},
    5: {"YAW":  90, "HIP": 110, "KNEE": 60},
    6: {"YAW":  90, "HIP": 110, "KNEE": 60},
}

# ═════════════════════════════════════════════════════════════
#  LEG GEOMETRY  (millimetres)
# ═════════════════════════════════════════════════════════════

COXA_LENGTH  = 46    # yaw axis → hip axis
FEMUR_LENGTH = 167   # hip axis → knee axis
TIBIA_LENGTH = 167   # knee axis → foot tip
BODY_TO_YAW  = 43    # centre of body wall → yaw axis mount

# ═════════════════════════════════════════════════════════════
#  BODY GEOMETRY  (millimetres)
# ═════════════════════════════════════════════════════════════
# Octagonal base — front/back walls 114.2 mm,
# angled walls 100 mm, side walls 118.6 mm.
# Front/back legs angled 25° inward from the middle legs.

BODY_FRONT_WALL  = 114.2
BODY_ANGLED_WALL = 100.0
BODY_SIDE_WALL   = 118.6

# ═════════════════════════════════════════════════════════════
#  TRIPOD GROUPS
# ═════════════════════════════════════════════════════════════

TRIPOD_A = [1, 3, 5]   # front-right, back-right, mid-left
TRIPOD_B = [2, 4, 6]   # mid-right,   back-left,  front-left

# ═════════════════════════════════════════════════════════════
#  RIGHT vs LEFT SIDE  (for mirroring motion)
# ═════════════════════════════════════════════════════════════

RIGHT_LEGS = [1, 2, 3]
LEFT_LEGS  = [4, 5, 6]

# ═════════════════════════════════════════════════════════════
#  GAIT PARAMETERS  (tuneable)
# ═════════════════════════════════════════════════════════════

GAIT_PARAMS = {
    # How many degrees the yaw sweeps ± from neutral per step
    "stride_angle":     15,     # degrees (total swing = 2 × this)

    # How much the hip raises during swing (subtracted from neutral hip)
    "hip_lift":         35,     # degrees — lifts leg off the ground

    # How much the knee bends during swing (added to neutral knee angle)
    "lift_height":      20,     # degrees — tucks tibia up

    # Number of interpolation sub-steps per half-cycle (phase)
    "interpolation_steps": 30,

    # Seconds between each interpolation sub-step
    "step_delay":       0.02,   # 20 ms → one phase ≈ 0.4 s

    # Pause (seconds) after each full cycle — set 0 for continuous
    "cycle_pause":      0.0,
}

# ═════════════════════════════════════════════════════════════
#  ARDUINO SERIAL
# ═════════════════════════════════════════════════════════════

ARDUINO_BAUD = 115200

# ═════════════════════════════════════════════════════════════
#  PUSH-UP STANCE  (taller, narrower standing pose)
# ═════════════════════════════════════════════════════════════
# Hip goes lower (more vertical leg → body rises)
# Knee extends (straighter tibia → narrower footprint)
# Adjust these to find the best tall/narrow pose for your bot.

PUSHUP_ANGLES = {
    1: {"YAW":  90, "HIP": 125, "KNEE": 20},
    2: {"YAW":  90, "HIP": 125, "KNEE": 20},
    3: {"YAW":  90, "HIP": 125, "KNEE": 20},
    4: {"YAW":  90, "HIP": 125, "KNEE": 20},
    5: {"YAW":  90, "HIP": 125, "KNEE": 20},
    6: {"YAW":  90, "HIP": 125, "KNEE": 20},
}

# Number of interpolation steps for the push-up transition
PUSHUP_STEPS = 25
PUSHUP_DELAY = 0.03   # seconds between steps

# ═════════════════════════════════════════════════════════════
#  TURNING PARAMETERS
# ═════════════════════════════════════════════════════════════

TURN_PARAMS = {
    # How far yaw sweeps for turning (degrees)
    "turn_angle":       15,

    # Hip lift during swing phase of turn
    "hip_lift":         25,

    # Knee bend during swing phase of turn
    "knee_bend":        20,

    # Interpolation sub-steps per phase
    "interpolation_steps": 20,

    # Delay between sub-steps
    "step_delay":       0.02,
}

# ═════════════════════════════════════════════════════════════
#  STRAFING PARAMETERS
# ═════════════════════════════════════════════════════════════

STRAFE_PARAMS = {
    # How much the knee extends/tucks to push the body sideways
    "knee_shift":       30,

    # Hip lift during swing phase of strafe
    "hip_lift":         25,

    # Knee bend during swing phase
    "knee_bend":        20,

    # Interpolation sub-steps per phase
    "interpolation_steps": 20,

    # Delay between sub-steps
    "step_delay":       0.02,
}
