"""VPM listing maintenance helpers."""

from __future__ import annotations

import json
from pathlib import Path


def filter_listing(
    path: Path,
    excluded_ids: set[str],
    *,
    public_description: str | None = None,
) -> list[str]:
    """Remove excluded IDs, optionally normalize descriptions, and rewrite a listing."""
    data = json.loads(path.read_text(encoding="utf-8"))
    packages = data.get("packages")
    if not isinstance(packages, dict):
        raise TypeError("VPM listing must contain a packages object")

    removed = sorted(package_id for package_id in excluded_ids if package_id in packages)
    for package_id in removed:
        del packages[package_id]

    overlap = set(packages) & excluded_ids
    if overlap:
        raise ValueError(f"excluded packages remain in listing: {sorted(overlap)}")

    if public_description is not None:
        for package in packages.values():
            versions = package.get("versions", {})
            if not isinstance(versions, dict):
                raise TypeError("VPM package entry must contain a versions object")
            for manifest in versions.values():
                manifest["description"] = public_description

    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return removed
