from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .errors import ValidationError
from .manifest import load_manifest
from .verify import verify_package


@dataclass(frozen=True)
class DraftRelease:
    package_id: str
    tag: str
    title: str
    zip_path: Path
    package_json: Path
    sha256: str


def release_plan(manifest_path: Path | str) -> tuple[DraftRelease, DraftRelease]:
    manifest = load_manifest(manifest_path)
    products = (
        (manifest.id, manifest.id.rsplit(".", 1)[-1], manifest.version, manifest.title),
        (manifest.latest_id, "latest", manifest.latest_version, f"{manifest.title} (Latest)"),
    )
    drafts: list[DraftRelease] = []
    for package_id, tag_prefix, version, title in products:
        package_dir = manifest.output_directory / "packages" / package_id
        zip_path = manifest.output_directory / "zips" / f"{package_id}-{version}.zip"
        verify_package(package_dir, zip_path)
        package_json = package_dir / "package.json"
        drafts.append(
            DraftRelease(
                package_id=package_id,
                tag=f"{tag_prefix}-v{version}",
                title=f"{title} v{version}",
                zip_path=zip_path,
                package_json=package_json,
                sha256=hashlib.sha256(zip_path.read_bytes()).hexdigest(),
            )
        )
    return drafts[0], drafts[1]


def stage_drafts(manifest_path: Path | str, target: str, execute: bool = False) -> tuple[DraftRelease, DraftRelease]:
    if not target or any(character.isspace() for character in target):
        raise ValidationError("a non-empty git target commit/ref is required")
    drafts = release_plan(manifest_path)
    if not execute:
        return drafts
    try:
        subprocess.run(["gh", "auth", "status"], check=True, capture_output=True, text=True)
        for draft in drafts:
            existing = subprocess.run(
                ["gh", "release", "view", draft.tag], check=False, capture_output=True, text=True,
            )
            if existing.returncode == 0:
                raise ValidationError(f"release tag already exists: {draft.tag}")
            body = (
                f"Package: `{draft.package_id}`\n\n"
                f"ZIP SHA-256: `{draft.sha256}`\n\n"
                "Draft only. Publish after the Unity/VCC release gate and explicit user approval."
            )
            subprocess.run(
                [
                    "gh", "release", "create", draft.tag, str(draft.zip_path), str(draft.package_json),
                    "--draft", "--target", target, "--title", draft.title, "--notes", body,
                ],
                check=True,
            )
    except FileNotFoundError as exc:
        raise ValidationError("GitHub CLI (gh) is not installed") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        raise ValidationError(f"GitHub draft release staging failed: {detail}") from exc
    return drafts
