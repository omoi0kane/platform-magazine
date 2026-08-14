from __future__ import annotations

import json
from pathlib import Path

import pytest

from platform_book.listing import (
    filter_listing,
    group_slug_for_package,
    write_group_listings,
)


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


@pytest.mark.parametrize(
    ("package_id", "expected"),
    [
        ("net.omoi0kane.platform-magazine.latest", "latest"),
        ("net.omoi0kane.platform-magazine.vol01", "vol01-05"),
        ("net.omoi0kane.platform-magazine.vol05", "vol01-05"),
        ("net.omoi0kane.platform-magazine.vol06", "vol06-10"),
        ("net.omoi0kane.platform-magazine.vol10", "vol06-10"),
        ("net.omoi0kane.platform-magazine.vol11", "vol11-15"),
        ("net.omoi0kane.platform-magazine.vol15", "vol11-15"),
        ("net.omoi0kane.platform-magazine.vol16", "vol16-20"),
        ("net.omoi0kane.platform-magazine.vol20", "vol16-20"),
        ("net.omoi0kane.platform-magazine.special2025", "special"),
    ],
)
def test_group_slug_for_package(package_id: str, expected: str) -> None:
    assert group_slug_for_package(package_id) == expected


@pytest.mark.parametrize(
    "package_id",
    [
        "net.omoi0kane.platform-magazine",
        "net.omoi0kane.platform-magazine.vol21",
        "net.omoi0kane.platform-magazine.vol1",
        "net.example.unknown",
    ],
)
def test_group_slug_rejects_unknown_or_out_of_range_package(package_id: str) -> None:
    with pytest.raises(ValueError):
        group_slug_for_package(package_id)


def test_write_group_listings_partitions_each_package_once(tmp_path: Path) -> None:
    source = tmp_path / "index.json"
    package_ids = [
        "net.omoi0kane.platform-magazine.latest",
        *(f"net.omoi0kane.platform-magazine.vol{number:02d}" for number in range(1, 21)),
        "net.omoi0kane.platform-magazine.special2023",
        "net.omoi0kane.platform-magazine.special2024",
    ]
    source.write_text(
        json.dumps(
            {
                "name": "All packages",
                "id": "net.example.all",
                "url": "https://example.com/index.json",
                "packages": {package_id: {"versions": {"1.0.0": {}}} for package_id in package_ids},
            }
        ),
        encoding="utf-8",
    )

    written = write_group_listings(source, tmp_path / "listings", "https://example.com/")

    assert set(written) == {"latest", "vol01-05", "vol06-10", "vol11-15", "vol16-20", "special"}
    grouped_ids: list[str] = []
    expected_sizes = {
        "latest": 1,
        "vol01-05": 5,
        "vol06-10": 5,
        "vol11-15": 5,
        "vol16-20": 5,
        "special": 2,
    }
    listing_ids: set[str] = set()
    for slug, path in written.items():
        result = json.loads(path.read_text(encoding="utf-8"))
        assert result["url"] == f"https://example.com/listings/{slug}.json"
        assert len(result["packages"]) == expected_sizes[slug]
        grouped_ids.extend(result["packages"])
        listing_ids.add(result["id"])
    assert len(listing_ids) == 6
    assert sorted(grouped_ids) == sorted(package_ids)
    assert len(grouped_ids) == len(set(grouped_ids))
