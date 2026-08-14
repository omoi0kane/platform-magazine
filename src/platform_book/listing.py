"""VPM listing maintenance and grouping helpers."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ListingGroup:
    slug: str
    name: str
    listing_id: str


LISTING_GROUPS = (
    ListingGroup("latest", "Platform Magazine — 最新号", "net.omoi0kane.platform-magazine.listing.latest"),
    ListingGroup("vol01-05", "Platform Magazine — Vol.1–5", "net.omoi0kane.platform-magazine.listing.vol01-05"),
    ListingGroup("vol06-10", "Platform Magazine — Vol.6–10", "net.omoi0kane.platform-magazine.listing.vol06-10"),
    ListingGroup("vol11-15", "Platform Magazine — Vol.11–15", "net.omoi0kane.platform-magazine.listing.vol11-15"),
    ListingGroup("vol16-20", "Platform Magazine — Vol.16–20", "net.omoi0kane.platform-magazine.listing.vol16-20"),
    ListingGroup("special", "Platform Magazine — 特別号", "net.omoi0kane.platform-magazine.listing.special"),
)
_GROUP_BY_SLUG = {group.slug: group for group in LISTING_GROUPS}
_VOLUME_ID = re.compile(r"^net\.omoi0kane\.platform-magazine\.vol(\d{2})$")
_SPECIAL_ID = re.compile(r"^net\.omoi0kane\.platform-magazine\.special\d{4}$")


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


def group_slug_for_package(package_id: str) -> str:
    """Return the one public listing group for a current Platform package ID."""
    if package_id == "net.omoi0kane.platform-magazine.latest":
        return "latest"
    if _SPECIAL_ID.fullmatch(package_id):
        return "special"

    match = _VOLUME_ID.fullmatch(package_id)
    if match is None:
        raise ValueError(f"package ID does not belong to a public listing group: {package_id}")

    volume = int(match.group(1))
    for lower, upper, slug in (
        (1, 5, "vol01-05"),
        (6, 10, "vol06-10"),
        (11, 15, "vol11-15"),
        (16, 20, "vol16-20"),
    ):
        if lower <= volume <= upper:
            return slug
    raise ValueError(f"volume is outside the supported Vol.1–20 range: {package_id}")


def write_group_listings(source: Path, output_directory: Path, base_url: str) -> dict[str, Path]:
    """Split a curated all-package listing into six non-overlapping public listings."""
    data = json.loads(source.read_text(encoding="utf-8"))
    packages = data.get("packages")
    if not isinstance(packages, dict) or not packages:
        raise TypeError("VPM listing must contain a non-empty packages object")

    grouped: dict[str, dict[str, object]] = {group.slug: {} for group in LISTING_GROUPS}
    for package_id, package in packages.items():
        grouped[group_slug_for_package(package_id)][package_id] = package

    if sum(len(items) for items in grouped.values()) != len(packages):
        raise ValueError("grouped listing coverage does not match the source listing")

    output_directory.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    normalized_base = base_url.rstrip("/")
    for slug, items in grouped.items():
        group = _GROUP_BY_SLUG[slug]
        result = copy.deepcopy(data)
        result["name"] = group.name
        result["id"] = group.listing_id
        result["url"] = f"{normalized_base}/listings/{slug}.json"
        result["packages"] = items
        destination = output_directory / f"{slug}.json"
        destination.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written[slug] = destination
    return written
