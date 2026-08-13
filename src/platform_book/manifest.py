from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .errors import ManifestError

_ID = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)+$")
_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
_TARGET_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*$")


@dataclass(frozen=True)
class Manifest:
    id: str
    title: str
    author: str
    source_path: Path
    source_type: str
    source_cover: str | None
    source_back_cover: bool
    page_order: str
    explicit_pages: tuple[str, ...]
    output_directory: Path
    version: str
    latest_version: str
    latest_id: str
    target_name: str
    max_dimension: int
    jpeg_quality: int
    warning_size_mb: float
    hard_size_mb: float
    rights_statement: str
    raw: dict[str, Any]
    manifest_path: Path


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ManifestError(f"field '{field}' must be a mapping")
    return value


def _required(data: dict[str, Any], field: str) -> Any:
    if field not in data:
        raise ManifestError(f"missing required field: {field}")
    return data[field]


def _reject_unknown(data: dict[str, Any], allowed: set[str], section: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ManifestError(f"unknown field in {section}: {unknown[0]}")


def load_manifest(path: Path | str) -> Manifest:
    path = Path(path).resolve()
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ManifestError(f"cannot read manifest {path}: {exc}") from exc
    data = _mapping(loaded, "manifest")
    _reject_unknown(data, {"id", "title", "author", "source", "output", "rights"}, "manifest")
    for field in ("id", "title", "author", "source", "output", "rights"):
        _required(data, field)

    package_id = data["id"]
    if not isinstance(package_id, str) or not _ID.fullmatch(package_id):
        raise ManifestError("id must be a reverse-domain-style lowercase package ID")
    for field in ("title", "author"):
        if not isinstance(data[field], str) or not data[field].strip():
            raise ManifestError(f"field '{field}' must be a non-empty string")

    source = _mapping(data["source"], "source")
    output = _mapping(data["output"], "output")
    rights = _mapping(data["rights"], "rights")
    _reject_unknown(source, {"path", "type", "cover", "back_cover", "page_order", "pages"}, "source")
    _reject_unknown(
        output,
        {"directory", "version", "latest_version", "latest_id", "target_name", "max_dimension", "jpeg_quality",
         "warning_size_mb", "hard_size_mb"},
        "output",
    )
    _reject_unknown(rights, {"redistribution_approved", "statement"}, "rights")
    for section, values, fields in (
        ("source", source, ("path",)),
        ("output", output, ("directory", "version", "latest_version")),
        ("rights", rights, ("redistribution_approved", "statement")),
    ):
        for field in fields:
            if field not in values:
                raise ManifestError(f"missing required field: {section}.{field}")
    if rights["redistribution_approved"] is not True:
        raise ManifestError("rights.redistribution_approved must be true before building")
    if not isinstance(rights["statement"], str) or not rights["statement"].strip():
        raise ManifestError("rights.statement must be a non-empty string")

    source_type = source.get("type", "auto")
    if source_type not in {"auto", "pdf", "images"}:
        raise ManifestError("source.type must be one of: auto, pdf, images")
    source_cover = source.get("cover")
    if source_cover is not None and (not isinstance(source_cover, str) or not source_cover.strip()):
        raise ManifestError("source.cover must be a non-empty relative filename")
    if source_cover is not None and (Path(source_cover).is_absolute() or ".." in Path(source_cover).parts):
        raise ManifestError("source.cover must stay inside the source directory")
    source_back_cover = source.get("back_cover", False)
    if not isinstance(source_back_cover, bool):
        raise ManifestError("source.back_cover must be true or false")
    page_order = source.get("page_order", "natural")
    if page_order not in {"natural", "affinity_spreads", "affinity_spread_pages", "explicit"}:
        raise ManifestError(
            "source.page_order must be one of: natural, affinity_spreads, affinity_spread_pages, explicit"
        )
    raw_pages = source.get("pages", [])
    if not isinstance(raw_pages, list) or any(not isinstance(item, str) or not item for item in raw_pages):
        raise ManifestError("source.pages must be a list of filenames")
    if page_order == "explicit" and not raw_pages:
        raise ManifestError("source.pages is required when source.page_order is explicit")
    if page_order != "explicit" and raw_pages:
        raise ManifestError("source.pages is only allowed when source.page_order is explicit")
    version = output["version"]
    if not isinstance(version, str) or not _VERSION.fullmatch(version):
        raise ManifestError("output.version must use semantic x.y.z form")
    latest_version = output["latest_version"]
    if not isinstance(latest_version, str) or not _VERSION.fullmatch(latest_version):
        raise ManifestError("output.latest_version must use semantic x.y.z form")
    if not isinstance(source["path"], str) or not source["path"].strip():
        raise ManifestError("source.path must be a non-empty string")
    if not isinstance(output["directory"], str) or not output["directory"].strip():
        raise ManifestError("output.directory must be a non-empty string")

    def integer(name: str, default: int, minimum: int, maximum: int | None = None) -> int:
        value = output.get(name, default)
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum or (maximum and value > maximum):
            raise ManifestError(f"output.{name} is outside the allowed range")
        return value

    warning = float(output.get("warning_size_mb", 100.0))
    hard = float(output.get("hard_size_mb", 200.0))
    if warning < 0 or hard <= 0 or warning > hard:
        raise ManifestError("size thresholds must satisfy 0 <= warning_size_mb <= hard_size_mb")

    base = path.parent
    source_path = Path(source["path"])
    output_path = Path(output["directory"])
    source_path = source_path if source_path.is_absolute() else (base / source_path).resolve()
    output_path = output_path if output_path.is_absolute() else (base / output_path).resolve()
    if source_path == output_path or source_path in output_path.parents:
        raise ManifestError("output.directory must not be the source or inside the source")
    if output_path in source_path.parents:
        raise ManifestError("output.directory must not contain the source")
    if output_path == Path(output_path.anchor) or output_path == Path.home().resolve() or output_path in path.parents:
        raise ManifestError("output.directory is an unsafe root, home, or manifest ancestor")

    actual_images = source_path.is_dir()
    actual_pdf = source_path.is_file() and source_path.suffix.casefold() == ".pdf"
    if (source_type == "images" or (source_type == "auto" and actual_images)) and source_cover is None:
        raise ManifestError("source.cover is required for an image directory")
    if (source_type == "pdf" or (source_type == "auto" and actual_pdf)) and page_order == "explicit":
        raise ManifestError("PDF sources support natural or affinity_spreads page order")
    if (source_type == "images" or (source_type == "auto" and actual_images)) and source_back_cover:
        raise ManifestError("source.back_cover is currently supported only for PDF sources")

    latest_id = output.get("latest_id", package_id.rsplit(".", 1)[0] + ".latest")
    if not isinstance(latest_id, str) or not _ID.fullmatch(latest_id) or latest_id == package_id:
        raise ManifestError("output.latest_id must be a distinct valid package ID")
    target_name = output.get("target_name", package_id.rsplit(".", 1)[-1].replace("-", "_"))
    if (
        not isinstance(target_name, str) or not _TARGET_NAME.fullmatch(target_name)
        or target_name in {".", ".."}
    ):
        raise ManifestError("output.target_name must be a safe Unity asset basename")

    return Manifest(
        id=package_id, title=data["title"].strip(), author=data["author"].strip(),
        source_path=source_path, source_type=source_type, source_cover=source_cover,
        source_back_cover=source_back_cover,
        page_order=page_order, explicit_pages=tuple(raw_pages), output_directory=output_path,
        version=version, latest_version=latest_version, latest_id=latest_id, target_name=target_name.strip(),
        max_dimension=integer("max_dimension", 2048, 64),
        jpeg_quality=integer("jpeg_quality", 85, 1, 100),
        warning_size_mb=warning, hard_size_mb=hard,
        rights_statement=rights["statement"].strip(), raw=data, manifest_path=path,
    )
