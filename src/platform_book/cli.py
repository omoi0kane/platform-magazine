from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .build import build
from .errors import PlatformBookError
from .manifest import load_manifest
from .prepare import prepare
from .release import stage_drafts
from .verify import verify_package


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="platform-book", description="Build deterministic Platform Magazine VPM packages")
    commands = root.add_subparsers(dest="command", required=True)
    prepare_command = commands.add_parser("prepare", help="normalize manifest source pages for review")
    prepare_command.add_argument("manifest", type=Path)
    prepare_command.add_argument("--destination", type=Path, help="override prepared-page directory")
    build_command = commands.add_parser("build", help="build volume/latest packages and review artifacts")
    build_command.add_argument("manifest", type=Path)
    verify_command = commands.add_parser("verify", help="validate a generated package and optional ZIP")
    verify_command.add_argument("package", type=Path)
    verify_command.add_argument("--zip", dest="zip_path", type=Path)
    release_command = commands.add_parser("stage-release", help="validate and optionally create two GitHub draft releases")
    release_command.add_argument("manifest", type=Path)
    release_command.add_argument("--target", required=True, help="git commit/ref for draft tags")
    release_command.add_argument("--execute", action="store_true", help="create drafts; omitted means dry-run")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "prepare":
            manifest = load_manifest(args.manifest)
            destination = args.destination or manifest.output_directory.with_name(
                f"{manifest.output_directory.name}-prepared-pages"
            )
            pages = prepare(
                manifest.source_path, destination, manifest.max_dimension,
                manifest.jpeg_quality, manifest.source_type, manifest.source_cover,
                manifest.page_order, manifest.explicit_pages,
                manifest.source_back_cover,
            )
            print(f"prepared {len(pages)} pages in {destination}")
        elif args.command == "build":
            result = build(args.manifest)
            print(f"built volume: {result.volume.zip_path}")
            print(f"built latest: {result.latest.zip_path}")
            print(f"validation: {result.validation_report}")
        elif args.command == "verify":
            result = verify_package(args.package, args.zip_path)
            print(f"verified {result.package_id}: {result.page_count} pages, {result.size_bytes} bytes")
            for warning in result.warnings:
                print(f"warning: {warning}", file=sys.stderr)
        else:
            drafts = stage_drafts(args.manifest, args.target, args.execute)
            for draft in drafts:
                action = "staged" if args.execute else "planned"
                print(f"{action} draft {draft.tag}: {draft.zip_path} sha256={draft.sha256}")
        return 0
    except PlatformBookError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
