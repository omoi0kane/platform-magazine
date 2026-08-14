"""Generate the six public Platform Magazine VPM listings."""

from __future__ import annotations

import argparse
from pathlib import Path

from platform_book.listing import write_group_listings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()

    written = write_group_listings(args.source, args.output_directory, args.base_url)
    for slug, path in written.items():
        print(f"{slug}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
