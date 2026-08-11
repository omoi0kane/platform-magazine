from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Never

from .errors import ValidationError

_GUID = re.compile(r"^[0-9a-f]{32}$")
_PAGE_REF = re.compile(r"^  - \{fileID: 2800000, guid: ([0-9a-f]{32}), type: 3\}$", re.MULTILINE)


@dataclass(frozen=True)
class Verification:
    package_id: str
    page_count: int
    size_bytes: int
    warnings: tuple[str, ...]


def _fail(message: str) -> Never:
    raise ValidationError(message)


def verify_package(package_dir: Path | str, zip_path: Path | str | None = None) -> Verification:
    root = Path(package_dir)
    package_file = root / "package.json"
    try:
        package = json.loads(package_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"invalid or missing package.json: {exc}")
    package_id, version = package.get("name"), package.get("version")
    if (
        not isinstance(package_id, str) or not package_id or
        not isinstance(version, str) or re.fullmatch(r"\d+\.\d+\.\d+", version) is None
    ):
        _fail("package identity/version is missing")
    if root.name != package_id:
        _fail(f"package identity {package_id!r} does not match directory {root.name!r}")

    pages_dir = root / "Runtime/pages"
    pages = sorted(pages_dir.glob("page_*.jpg"))
    expected = [f"page_{index:03d}.jpg" for index in range(1, len(pages) + 1)]
    if not pages or [p.name for p in pages] != expected:
        _fail("page continuity failed; expected page_001.jpg through the final page")
    forbidden = [p for p in root.rglob("*") if p.is_file() and p.suffix.casefold() in {".pdf", ".png", ".jpeg"}]
    if forbidden:
        _fail(f"original/source file type found in package: {forbidden[0].relative_to(root)}")

    guid_to_asset: dict[str, Path] = {}
    assets = [p for p in root.rglob("*") if p.is_file() and not p.name.endswith(".meta")]
    for asset in assets:
        meta = asset.with_name(asset.name + ".meta")
        if not meta.is_file():
            _fail(f"asset is missing .meta: {asset.relative_to(root)}")
        match = re.search(r"^guid: ([0-9a-f]{32})$", meta.read_text(encoding="utf-8"), re.MULTILINE)
        if not match or not _GUID.fullmatch(match.group(1)):
            _fail(f"invalid GUID in {meta.relative_to(root)}")
        guid = match.group(1)
        if guid in guid_to_asset:
            _fail(f"duplicate GUID in metas: {guid}")
        guid_to_asset[guid] = asset

    meta_guids: list[str] = []
    for meta in root.rglob("*.meta"):
        match = re.search(r"^guid: ([0-9a-f]{32})$", meta.read_text(encoding="utf-8"), re.MULTILINE)
        if not match:
            _fail(f"meta file has no valid GUID: {meta.relative_to(root)}")
        meta_guids.append(match.group(1))
    if len(meta_guids) != len(set(meta_guids)):
        _fail("unique GUID check failed")
    for directory in (root / "Runtime", pages_dir, root / "Runtime/materials"):
        if not directory.with_name(directory.name + ".meta").is_file():
            _fail(f"Unity folder is missing .meta: {directory.relative_to(root)}")

    prefabs = list((root / "Runtime").glob("*.prefab"))
    if len(prefabs) != 1:
        _fail("exactly one generated prefab is required")
    prefab = prefabs[0].read_text(encoding="utf-8")
    root_name = package.get("platformBook", {}).get("targetName")
    root_block = re.search(
        rf"GameObject:\n(?:(?!--- !u!).)*?  m_Name: {re.escape(str(root_name))}\n(?:(?!--- !u!).)*?  m_IsActive: (\d)",
        prefab, re.DOTALL,
    )
    if not root_block or root_block.group(1) != "1":
        _fail("generated prefab root is not active")
    page_guids = _PAGE_REF.findall(prefab)
    if len(page_guids) != len(pages):
        _fail(f"prefab page GUID count {len(page_guids)} does not match page count {len(pages)}")
    page_asset_guids = {
        guid for guid, asset in guid_to_asset.items()
        if asset.parent == pages_dir and asset.suffix.casefold() == ".jpg"
    }
    expected_page_guids = []
    for page in pages:
        match = re.search(
            r"^guid: ([0-9a-f]{32})$",
            page.with_name(page.name + ".meta").read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        expected_page_guids.append(match.group(1) if match else "")
    if page_guids != expected_page_guids:
        unknown = next((guid for guid in page_guids if guid not in page_asset_guids), None)
        if unknown:
            _fail(f"prefab page GUID does not resolve to a generated page: {unknown}")
        _fail("prefab page GUID order does not match generated page order")

    material = next((root / "Runtime/materials").glob("*.mat"), None)
    if material is None:
        _fail("generated cover material is missing")
    cover = root / "Runtime/cover.jpg"
    if not cover.is_file():
        _fail("generated cover image is missing")
    cover_meta = cover.with_name(cover.name + ".meta").read_text(encoding="utf-8")
    cover_guid_match = re.search(r"^guid: ([0-9a-f]{32})$", cover_meta, re.MULTILINE)
    if cover_guid_match is None or cover_guid_match.group(1) not in material.read_text(encoding="utf-8"):
        _fail("generated material does not reference the cover image")
    if not (root / "LICENSE").is_file():
        _fail("generated package is missing LICENSE")

    if zip_path is not None:
        zip_path = Path(zip_path)
        try:
            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
                if len(names) != len(set(names)):
                    _fail("ZIP contains duplicate entries")
                for name in names:
                    path = PurePosixPath(name)
                    if path.is_absolute() or ".." in path.parts or "\\" in name:
                        _fail(f"ZIP contains an unsafe entry path: {name}")
                if "package.json" not in names or any(name.startswith(f"{package_id}/") for name in names):
                    _fail("ZIP layout must place package.json at ZIP root")
                if names != sorted(names):
                    _fail("ZIP entries are not deterministically ordered")
                expected_names = sorted(
                    path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
                )
                if names != expected_names:
                    _fail("ZIP file list does not match the generated package")
                for name in expected_names:
                    info = archive.getinfo(name)
                    if info.date_time != (1980, 1, 1, 0, 0, 0):
                        _fail(f"ZIP timestamp is not deterministic: {name}")
                    if info.create_system != 3 or info.external_attr != 0o100644 << 16:
                        _fail(f"ZIP permission metadata is not deterministic: {name}")
                    if archive.read(name) != (root / name).read_bytes():
                        _fail(f"ZIP content does not match the generated package: {name}")
        except (OSError, zipfile.BadZipFile) as exc:
            _fail(f"invalid package ZIP: {exc}")
        size = zip_path.stat().st_size
    else:
        size = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())

    config = package.get("platformBook", {})
    warning_bytes = float(config.get("warningSizeMb", 100)) * 1024 * 1024
    hard_bytes = float(config.get("hardSizeMb", 200)) * 1024 * 1024
    if size > hard_bytes:
        _fail(f"package size {size} exceeds hard threshold {int(hard_bytes)} bytes")
    warnings = (f"package size {size} exceeds warning threshold {int(warning_bytes)} bytes",) if size > warning_bytes else ()
    return Verification(package_id, len(pages), size, warnings)
