from __future__ import annotations

import json
from pathlib import Path

import pytest

from platform_book.listing import filter_listing


def test_filter_listing_removes_only_explicit_package_ids(tmp_path: Path) -> None:
    listing = tmp_path / "index.json"
    listing.write_text(
        json.dumps(
            {
                "name": "Platform Magazine Listing",
                "packages": {
                    "net.omoi0kane.platform-magazine": {"versions": {"0.0.8": {}}},
                    "net.omoi0kane.platform-magazine.latest": {"versions": {"17.0.0": {}}},
                    "net.omoi0kane.platform-magazine.vol17": {"versions": {"1.0.0": {}}},
                },
            }
        ),
        encoding="utf-8",
    )

    removed = filter_listing(
        listing,
        {"net.omoi0kane.platform-magazine"},
        public_description="Public description",
    )
    result = json.loads(listing.read_text(encoding="utf-8"))

    assert removed == ["net.omoi0kane.platform-magazine"]
    assert set(result["packages"]) == {
        "net.omoi0kane.platform-magazine.latest",
        "net.omoi0kane.platform-magazine.vol17",
    }
    assert all(
        manifest["description"] == "Public description"
        for package in result["packages"].values()
        for manifest in package["versions"].values()
    )


def test_filter_listing_fails_without_packages_object(tmp_path: Path) -> None:
    listing = tmp_path / "index.json"
    listing.write_text("{}", encoding="utf-8")

    with pytest.raises(TypeError, match="packages object"):
        filter_listing(listing, {"net.omoi0kane.platform-magazine"})
