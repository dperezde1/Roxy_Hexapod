#!/usr/bin/env python3
"""
main.py
───────
Command-line entry point for the hexapod controller.

Usage
─────
  python3 main.py                           # 5 forward walk cycles
  python3 main.py walk --cycles 10          # 10 forward cycles
  python3 main.py walk --direction backward # walk backward
  python3 main.py walk --speed slow         # slower gait
  python3 main.py pushup                    # push up then back down
  python3 main.py pushup --hold 5           # push up, hold 5 sec
  python3 main.py turn --direction right    # turn right 3 cycles
  python3 main.py turn --direction left -c 5  # turn left 5 cycles
  python3 main.py stand                     # just stand

Press Ctrl-C at any time to stop and return to neutral stance.
"""

import argparse
import signal
import sys
import time

from servo_control import ServoController
from tripod_walk  import TripodGait


# ─────────────────────────────────────────────
#  Speed presets for walking
# ─────────────────────────────────────────────
SPEED_PRESETS = {
    "slow": {
        "interpolation_steps": 30,
        "step_delay":          0.04,
        "stride_angle":       10,
        "hip_lift":           20,
        "lift_height":        15,
    },
    "normal": {},
    "fast": {
        "interpolation_steps": 12,
        "step_delay":          0.01,
        "stride_angle":       18,
        "hip_lift":           30,
        "lift_height":        25,
    },
}


def build_parser():
    parser = argparse.ArgumentParser(
        description="Hexapod Controller — walk, push-up, turn",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Press Ctrl-C at any time to safely stop and stand.",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress per-step logging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # ── walk ──
    walk_p = subparsers.add_parser("walk", help="Tripod walk forward/backward")
    walk_p.add_argument("--cycles", "-c", type=int, default=5)
    walk_p.add_argument("--direction", "-d", choices=["forward", "backward"], default="forward")
    walk_p.add_argument("--speed", "-s", choices=["slow", "normal", "fast"], default="normal")
    walk_p.add_argument("--stride", type=float, default=None, help="Override stride angle (degrees)")
    walk_p.add_argument("--lift", type=float, default=None, help="Override knee bend (degrees)")
    walk_p.add_argument("--hip-lift", type=float, default=None, help="Override hip lift (degrees)")

    # ── pushup ──
    pushup_p = subparsers.add_parser("pushup", help="Push-up to tall stance and back")
    pushup_p.add_argument("--hold", type=float, default=2.0,
                          help="Seconds to hold the tall pose (default: 2)")
    pushup_p.add_argument("--stay", action="store_true",
                          help="Stay in push-up pose (don't come back down)")

    # ── turn ──
    turn_p = subparsers.add_parser("turn", help="Turn in place")
    turn_p.add_argument("--direction", "-d", choices=["left", "right"], required=True)
    turn_p.add_argument("--cycles", "-c", type=int, default=3)

    # ── stand ──
    subparsers.add_parser("stand", help="Just stand in neutral position")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Default to 'walk' if no subcommand given
    if args.command is None:
        args.command = "walk"
        args.cycles = 5
        args.direction = "forward"
        args.speed = "normal"
        args.stride = None
        args.lift = None
        args.hip_lift = None

    verbose = not args.quiet

    # ── Init hardware ──
    print("=" * 55)
    print("  Hexapod Controller")
    print("=" * 55)

    ctrl = ServoController(verbose=verbose)

    # Build walk overrides
    walk_overrides = {}
    if args.command == "walk":
        walk_overrides = dict(SPEED_PRESETS.get(args.speed, {}))
        if args.stride is not None:
            walk_overrides["stride_angle"] = args.stride
        if args.lift is not None:
            walk_overrides["lift_height"] = args.lift
        if args.hip_lift is not None:
            walk_overrides["hip_lift"] = args.hip_lift

    gait = TripodGait(ctrl, params=walk_overrides if walk_overrides else None,
                      verbose=verbose)

    # ── Ctrl-C handler ──
    def signal_handler(sig, frame):
        print("\n[INTERRUPT] Stopping …")
        gait.stop()
        ctrl.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Always start by standing
        ctrl.stand()

        if args.command == "stand":
            print("[STAND] Robot is standing. Press Ctrl-C to release.")
            signal.pause()

        elif args.command == "walk":
            if args.direction == "forward":
                gait.walk_forward(num_cycles=args.cycles)
            else:
                gait.walk_backward(num_cycles=args.cycles)
            ctrl.stand()
            print("[DONE] Walk complete.")

        elif args.command == "pushup":
            gait.push_up()
            if args.stay:
                print("[PUSH-UP] Holding tall pose. Press Ctrl-C to release.")
                signal.pause()
            else:
                print(f"[PUSH-UP] Holding for {args.hold}s …")
                time.sleep(args.hold)
                gait.push_down()
                print("[DONE] Push-up complete.")

        elif args.command == "turn":
            if args.direction == "right":
                gait.turn_right(num_cycles=args.cycles)
            else:
                gait.turn_left(num_cycles=args.cycles)
            ctrl.stand()
            print("[DONE] Turn complete.")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("[SAFE] Attempting to return to stand …")
        try:
            ctrl.stand()
        except Exception:
            pass
        raise

    finally:
        ctrl.shutdown()


if __name__ == "__main__":
    main()
