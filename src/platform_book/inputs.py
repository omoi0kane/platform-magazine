from __future__ import annotations

import re
from pathlib import Path

from .errors import InputError

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


def natural_key(path: Path) -> tuple[object, ...]:
    return tuple(int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", path.name))


def discover_images(directory: Path) -> list[Path]:
    if not directory.is_dir():
        raise InputError(f"image source directory does not exist: {directory}")
    images = sorted(
        (p for p in directory.iterdir() if p.is_file() and p.suffix.casefold() in _IMAGE_SUFFIXES),
        key=natural_key,
    )
    if not images:
        raise InputError(f"no PNG/JPEG images found in: {directory}")
    return images


def order_book_images(
    directory: Path, cover: str | None, page_order: str, explicit_pages: tuple[str, ...] = (),
) -> list[Path]:
    """Return cover first, followed by content pages in Udon Magazine display order."""
    images = discover_images(directory)
    by_name = {path.name: path for path in images}
    if cover is None:
        cover_path = images[0]
    else:
        try:
            cover_path = by_name[cover]
        except KeyError as exc:
            raise InputError(f"declared cover image does not exist: {cover}") from exc
    body = [path for path in images if path != cover_path]
    if page_order == "explicit":
        if len(set(explicit_pages)) != len(explicit_pages):
            raise InputError("source.pages contains duplicate filenames")
        missing = [name for name in explicit_pages if name not in by_name or by_name[name] == cover_path]
        if missing:
            raise InputError(f"explicit page does not exist or is the cover: {missing[0]}")
        unlisted = {path.name for path in body} - set(explicit_pages)
        if unlisted:
            raise InputError(f"source.pages does not list every content image: {min(unlisted)}")
        body = [by_name[name] for name in explicit_pages]
    elif page_order == "affinity_spreads":
        body = [page for index in range(0, len(body), 2) for page in body[index:index + 2][::-1]]
    elif page_order != "natural":
        raise InputError(f"unsupported page ordering: {page_order}")
    return [cover_path, *body]
