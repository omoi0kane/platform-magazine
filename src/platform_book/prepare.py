from __future__ import annotations

import shutil
from pathlib import Path

import pymupdf
from PIL import Image, ImageOps

from .errors import InputError
from .inputs import order_book_images

_PREPARED_MARKER = ".platform-book-prepared"


def pdf_source_page_order(page_count: int, page_order: str, back_cover: bool) -> list[int]:
    """Return zero-based PDF pages in Udon order, with the front cover first."""
    if page_count < 1:
        raise InputError("PDF has no pages")
    body = list(range(1, page_count - (1 if back_cover else 0)))
    if page_order == "affinity_spreads":
        if len(body) % 2:
            raise InputError("affinity_spreads requires an even number of interior PDF pages")
        body = [page for index in range(0, len(body), 2) for page in body[index:index + 2][::-1]]
    elif page_order != "natural":
        raise InputError("PDF sources support natural or affinity_spreads page order")
    return [0, *body]


def _save_jpeg(image: Image.Image, destination: Path, max_dimension: int, quality: int) -> None:
    image = ImageOps.exif_transpose(image).convert("RGB")
    if max(image.size) > max_dimension:
        image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
    image.save(
        destination, "JPEG", quality=quality, optimize=False, progressive=False,
        subsampling=2, dpi=(72, 72), exif=b"",
    )


def prepare(
    source: Path | str,
    destination: Path | str,
    max_dimension: int = 2048,
    quality: int = 85,
    source_type: str = "auto",
    cover: str | None = None,
    page_order: str = "natural",
    explicit_pages: tuple[str, ...] = (),
    back_cover: bool = False,
) -> list[Path]:
    """Render/copy normalized pages without ever writing to the original source."""
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if max_dimension < 64 or not 1 <= quality <= 100:
        raise InputError("max_dimension must be >=64 and quality must be 1..100")
    is_pdf = source.is_file() and source.suffix.casefold() == ".pdf"
    is_images = source.is_dir()
    if source_type == "pdf" and not is_pdf:
        raise InputError(f"source.type is pdf but path is not a PDF: {source}")
    if source_type == "images" and not is_images:
        raise InputError(f"source.type is images but path is not a directory: {source}")
    if source_type not in {"auto", "pdf", "images"}:
        raise InputError(f"unsupported source type: {source_type}")
    if is_pdf and page_order == "explicit":
        raise InputError("PDF sources support natural or affinity_spreads page order")
    if is_images and cover is None:
        raise InputError("source.cover is required for an image directory")
    if destination == source or source in destination.parents:
        raise InputError("prepared output must not be inside the source")
    if destination in source.parents:
        raise InputError("prepared output must not contain the source")
    if destination == Path(destination.anchor) or destination == Path.home().resolve():
        raise InputError("prepared output must not be a filesystem root or home directory")
    if destination.exists():
        existing = list(destination.iterdir()) if destination.is_dir() else []
        marker = destination / _PREPARED_MARKER
        if not destination.is_dir() or (existing and not marker.is_file()):
            raise InputError(f"prepared output directory is not managed by platform-book: {destination}")
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    (destination / _PREPARED_MARKER).write_text("platform-book prepared pages\n", encoding="utf-8")

    try:
        if is_pdf:
            document = pymupdf.open(source)
            try:
                if document.page_count == 0:
                    raise InputError(f"PDF has no pages: {source}")
                source_pages = pdf_source_page_order(document.page_count, page_order, back_cover)
                for index, source_index in enumerate(source_pages, 1):
                    page = document[source_index]
                    longest = max(page.rect.width, page.rect.height)
                    scale = max_dimension / longest if longest else 1.0
                    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False, colorspace=pymupdf.csRGB)
                    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                    _save_jpeg(image, destination / f"page_{index:03d}.jpg", max_dimension, quality)
            finally:
                document.close()
        elif is_images:
            for index, page in enumerate(order_book_images(source, cover, page_order, explicit_pages), 1):
                with Image.open(page) as image:
                    _save_jpeg(image, destination / f"page_{index:03d}.jpg", max_dimension, quality)
        else:
            raise InputError(f"source must be a PDF or image directory: {source}")
    except (OSError, pymupdf.FileDataError) as exc:
        raise InputError(f"cannot prepare source {source}: {exc}") from exc
    return sorted(destination.glob("page_*.jpg"))
