"""Remove explicitly obsolete package IDs from a generated VPM listing."""

from __future__ import annotations

import argparse
from pathlib import Path

from platform_book.listing import filter_listing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("listing", type=Path)
    parser.add_argument("--exclude", action="append", required=True)
    parser.add_argument("--public-description")
    args = parser.parse_args()

    removed = filter_listing(
        args.listing,
        set(args.exclude),
        public_description=args.public_description,
    )
    print(f"Removed obsolete package IDs: {', '.join(removed) if removed else '(none found)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
