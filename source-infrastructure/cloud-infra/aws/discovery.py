"""
Cloud infrastructure discovery entry point.

Usage:
    python discovery.py --mode fixture    # Normalize local fixture JSONs (Phase 1)
    python discovery.py --mode live       # Query live AWS via boto3 (Phase 3)
"""

import argparse
import sys
from pathlib import Path

# Ensure cloud-infra package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aws.config import FIXTURE_DIR, INVENTORY_DIR
from normalize import normalize


def run_fixture_mode() -> None:
    """Load fixture JSONs and produce normalized inventory."""
    print(f"[NETRA] Running in FIXTURE mode")
    print(f"  Fixtures:  {FIXTURE_DIR}")
    print(f"  Output:    {INVENTORY_DIR}")
    print()

    assets, connections = normalize(FIXTURE_DIR, INVENTORY_DIR)

    print()
    print(f"[NETRA] Discovery complete.")
    print(f"  {len(assets)} assets → inventory/assets.json")
    print(f"  {len(connections)} connections → inventory/connections.json")


def run_live_mode() -> None:
    """Query live AWS infrastructure via boto3. (Phase 3 — not yet implemented)"""
    raise NotImplementedError(
        "Live AWS discovery is not yet implemented. "
        "This will be built in Phase 3 using boto3 describe_* calls. "
        "Use --mode fixture for now."
    )


def main():
    parser = argparse.ArgumentParser(
        description="NETRA Cloud Infrastructure Discovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python discovery.py --mode fixture   # Use local JSON fixtures\n"
            "  python discovery.py --mode live       # Query live AWS (Phase 3)\n"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["fixture", "live"],
        default="fixture",
        help="Discovery mode: 'fixture' (default) or 'live'.",
    )
    args = parser.parse_args()

    if args.mode == "fixture":
        run_fixture_mode()
    elif args.mode == "live":
        run_live_mode()


if __name__ == "__main__":
    main()
