"""
Command-line interface for Event Tracker.

Version 0.1 development goal:
Allow quick exercise logging from the terminal before building the PWA.
"""

import argparse

from log_event import list_events, log_exercise_event


def build_parser() -> argparse.ArgumentParser:
    """Create and configure the command-line argument parser."""

    parser = argparse.ArgumentParser(
        description="Log an exercise event."
    )

    parser.add_argument(
        "exercise_type",
        help="Type of exercise, such as walk, run, weights, bike, or pushups.",
    )

    parser.add_argument(
        "amount",
        type=float,
        help="Numeric amount, such as 1, 2.5, 30, or 45.",
    )

    parser.add_argument(
        "unit",
        help="Unit for amount, such as mile, miles, minute, minutes, rep, or reps.",
    )

    parser.add_argument(
        "note",
        nargs="?",
        default=None,
        help="Optional note.",
    )

    return parser


def main() -> None:
    """Run the command-line logger."""

    parser = build_parser()
    args = parser.parse_args()

    event_id = log_exercise_event(
        exercise_type=args.exercise_type,
        amount=args.amount,
        unit=args.unit,
        note=args.note,
    )

    print(f"Logged exercise event #{event_id}: {args.exercise_type} {args.amount:g} {args.unit}")

    if args.note:
        print(f"Note: {args.note}")

    print("\nRecent events:")
    for event in list_events()[:5]:
        print(event)


if __name__ == "__main__":
    main()