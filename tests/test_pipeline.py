from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest
import yaml
from PIL import Image

from platform_book.build import build
from platform_book.errors import ManifestError, ValidationError
from platform_book.guid import unity_guid
from platform_book.inputs import discover_images
from platform_book.manifest import load_manifest
from platform_book.release import stage_drafts
from platform_book.verify import verify_package
from platform_book.ziputil import deterministic_zip


def manifest_data(source: Path, output: Path) -> dict:
    return {
        "id": "net.example.platform-magazine.vol16",
        "title": "Platform Vol.16",
        "author": "Platform Editors",
        "source": {
            "path": str(source), "type": "images", "cover": "cover.png",
            "page_order": "affinity_spreads",
        },
        "output": {
            "directory": str(output), "version": "1.0.0", "max_dimension": 512,
            "latest_version": "16.0.0",
            "jpeg_quality": 80, "warning_size_mb": 20, "hard_size_mb": 40,
            "latest_id": "net.example.platform-magazine.latest",
        },
        "rights": {"redistribution_approved": True, "statement": "Approved by publisher"},
    }


def write_manifest(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "book.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def sample_images(path: Path) -> list[Path]:
    path.mkdir()
    for name, size, color in [
        ("cover.png", (1200, 600), "white"),
        ("page10.png", (900, 600), "blue"),
        ("page2.jpg", (300, 700), "green"),
        ("page3.jpg", (300, 700), "yellow"),
        ("page1.png", (1200, 800), "red"),
    ]:
        Image.new("RGB", size, color).save(path / name)
    return discover_images(path)


def test_natural_image_order(tmp_path: Path) -> None:
    images = sample_images(tmp_path / "pages")
    assert [p.name for p in images] == [
        "cover.png", "page1.png", "page2.jpg", "page3.jpg", "page10.png"
    ]


def test_guid_is_deterministic_32_hex() -> None:
    first = unity_guid("net.example.book", "Runtime/pages/page_001.jpg")
    assert first == unity_guid("net.example.book", "Runtime/pages/page_001.jpg")
    assert len(first) == 32
    int(first, 16)
    assert first != unity_guid("net.example.other", "Runtime/pages/page_001.jpg")


def test_rights_rejection(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    data = manifest_data(pages, tmp_path / "out")
    data["rights"]["redistribution_approved"] = False
    with pytest.raises(ManifestError, match="redistribution"):
        load_manifest(write_manifest(tmp_path, data))


def test_image_source_requires_explicit_cover(tmp_path: Path) -> None:
    source = tmp_path / "pages"
    sample_images(source)
    data = manifest_data(source, tmp_path / "out")
    del data["source"]["cover"]
    with pytest.raises(ManifestError, match="source.cover"):
        load_manifest(write_manifest(tmp_path, data))


def test_build_rejects_odd_udon_content_page_count(tmp_path: Path) -> None:
    source = tmp_path / "pages"
    sample_images(source)
    (source / "page3.jpg").unlink()
    with pytest.raises(ValidationError, match="even number of content pages"):
        build(write_manifest(tmp_path, manifest_data(source, tmp_path / "out")))


def test_output_must_not_contain_source_or_manifest(tmp_path: Path) -> None:
    output = tmp_path / "out"
    source = output / "source"
    source.mkdir(parents=True)
    data = manifest_data(source, output)
    with pytest.raises(ManifestError, match="must not contain"):
        load_manifest(write_manifest(tmp_path, data))


def test_target_name_is_strict_unity_asset_basename(tmp_path: Path) -> None:
    source = tmp_path / "pages"
    sample_images(source)
    data = manifest_data(source, tmp_path / "out")
    data["output"]["target_name"] = "../../../outside"
    with pytest.raises(ManifestError, match="target_name"):
        load_manifest(write_manifest(tmp_path, data))


def test_deterministic_zip_has_package_json_at_root(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    (package / "package.json").write_text("{}\n")
    (package / "z.txt").write_text("z")
    (package / "a.txt").write_text("a")
    one, two = tmp_path / "one.zip", tmp_path / "two.zip"
    deterministic_zip(package, one)
    deterministic_zip(package, two)
    assert hashlib.sha256(one.read_bytes()).digest() == hashlib.sha256(two.read_bytes()).digest()
    with zipfile.ZipFile(one) as archive:
        assert archive.namelist() == ["a.txt", "package.json", "z.txt"]
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())
        assert all(info.create_system == 3 and info.external_attr == 0o100644 << 16 for info in archive.infolist())


def test_build_images_produces_self_contained_active_packages_and_artifacts(tmp_path: Path) -> None:
    source = tmp_path / "source"
    ordered = sample_images(source)
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in ordered}
    output = tmp_path / "dist"
    result = build(write_manifest(tmp_path, manifest_data(source, output)))

    assert result.volume.package_dir.is_dir()
    assert result.latest.package_dir.is_dir()
    for product in (result.volume, result.latest):
        package = json.loads((product.package_dir / "package.json").read_text())
        assert package["name"] == product.package_id
        assert (product.package_dir / "Runtime/cover.jpg").is_file()
        assert (product.package_dir / "Runtime/pages/page_001.jpg").is_file()
        prefab = next((product.package_dir / "Runtime").glob("*.prefab")).read_text()
        assert "m_IsActive: 1" in prefab
        assert "  pageTextures:\n" in prefab
        assert prefab.count("- {fileID: 2800000, guid:") == 4
        assert "Platform Vol.16" in prefab
        assert "Platform Editors" in prefab
        material = next((product.package_dir / "Runtime/materials").glob("*.mat")).read_text()
        cover_guid = unity_guid(product.package_id, "Runtime/cover.jpg")
        assert cover_guid in material
        assert package["vpmDependencies"]["net.ts7m.udon-magazine"] == "0.2.0"
        assert (product.package_dir / "LICENSE").is_file()
        verify_package(product.package_dir, product.zip_path)

    volume_package = json.loads((result.volume.package_dir / "package.json").read_text())
    latest_package = json.loads((result.latest.package_dir / "package.json").read_text())
    assert volume_package["version"] == "1.0.0"
    assert "/vol16-v1.0.0/" in volume_package["url"]
    assert latest_package["version"] == "16.0.0"
    assert "/latest-v16.0.0/" in latest_package["url"]

    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in ordered} == before
    assert result.resolved_manifest.is_file()
    assert result.hashes.is_file()
    assert result.validation_report.is_file()
    assert result.contact_sheet.is_file()
    assert "self-contained" in (output / "README-latest.md").read_text()


def test_broken_prefab_page_guid_is_detected(tmp_path: Path) -> None:
    source = tmp_path / "source"
    sample_images(source)
    result = build(write_manifest(tmp_path, manifest_data(source, tmp_path / "dist")))
    prefab_path = next((result.volume.package_dir / "Runtime").glob("*.prefab"))
    text = prefab_path.read_text()
    valid = unity_guid(result.volume.package_id, "Runtime/pages/page_001.jpg")
    prefab_path.write_text(text.replace(valid, "f" * 32, 1))
    with pytest.raises(ValidationError, match="does not resolve"):
        verify_package(result.volume.package_dir)


def test_affinity_spread_order_excludes_cover_from_page_textures(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    for name, color in [
        ("cover.png", "white"), ("page2.png", "red"), ("page3.png", "green"),
        ("page4.png", "blue"), ("page5.png", "yellow"),
    ]:
        Image.new("RGB", (120, 180), color).save(source / name)
    result = build(write_manifest(tmp_path, manifest_data(source, tmp_path / "dist")))
    prefab = next((result.volume.package_dir / "Runtime").glob("*.prefab")).read_text()
    refs = [
        unity_guid(result.volume.package_id, f"Runtime/pages/page_{index:03d}.jpg")
        for index in range(1, 5)
    ]
    assert all(ref in prefab for ref in refs)
    assert unity_guid(result.volume.package_id, "Runtime/cover.jpg") not in prefab.split("pageTextures:", 1)[1].split("doublePageCount:", 1)[0]
    # The resolved manifest preserves the source sequence used to produce generated pages.
    resolved = yaml.safe_load(result.resolved_manifest.read_text())
    assert resolved["resolved"]["source_page_order"] == ["page3.png", "page2.png", "page5.png", "page4.png"]


def test_existing_unmanaged_output_directory_is_never_deleted(tmp_path: Path) -> None:
    source = tmp_path / "source"
    sample_images(source)
    output = tmp_path / "dist"
    output.mkdir()
    sentinel = output / "do-not-delete.txt"
    sentinel.write_text("important")
    with pytest.raises(ValidationError, match="not managed"):
        build(write_manifest(tmp_path, manifest_data(source, output)))
    assert sentinel.read_text() == "important"


def test_release_staging_defaults_to_side_effect_free_plan(tmp_path: Path) -> None:
    source = tmp_path / "source"
    sample_images(source)
    manifest = write_manifest(tmp_path, manifest_data(source, tmp_path / "dist"))
    build(manifest)
    volume, latest = stage_drafts(manifest, "deadbeef", execute=False)
    assert volume.tag == "vol16-v1.0.0"
    assert latest.tag == "latest-v16.0.0"
    assert len(volume.sha256) == 64


def test_stage_release_rejects_stale_zip(tmp_path: Path) -> None:
    source = tmp_path / "source"
    sample_images(source)
    manifest_path = tmp_path / "book.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest_data(source, tmp_path / "dist"), sort_keys=False))
    result = build(manifest_path)
    with zipfile.ZipFile(result.volume.zip_path, "w") as archive:
        archive.writestr("package.json", "{}")
    with pytest.raises(ValidationError, match="ZIP file list does not match"):
        stage_drafts(manifest_path, target="deadbeef", execute=False)
