from __future__ import annotations

import subprocess
from pathlib import Path

import pymupdf
import pytest
import yaml
from PIL import Image

from platform_book.cli import main
from platform_book.errors import InputError
from platform_book.prepare import prepare


def test_prepare_pdf_renders_pages_without_modifying_source(tmp_path: Path) -> None:
    pdf = tmp_path / "book.pdf"
    doc = pymupdf.open()
    for text in ("one", "two"):
        page = doc.new_page(width=300, height=400)
        page.insert_text((40, 40), text)
    doc.save(pdf)
    before = pdf.read_bytes()
    target = tmp_path / "prepared"
    pages = prepare(pdf, target, max_dimension=200, quality=75)
    assert [p.name for p in pages] == ["page_001.jpg", "page_002.jpg"]
    assert Image.open(pages[0]).size == (150, 200)
    assert pdf.read_bytes() == before


def test_prepare_pdf_renders_up_to_requested_resolution(tmp_path: Path) -> None:
    pdf = tmp_path / "book.pdf"
    doc = pymupdf.open()
    doc.new_page(width=300, height=400)
    doc.save(pdf)
    pages = prepare(pdf, tmp_path / "prepared", max_dimension=1200, quality=80)
    assert Image.open(pages[0]).size == (900, 1200)


def test_prepare_never_deletes_unmanaged_destination(tmp_path: Path) -> None:
    pdf = tmp_path / "book.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(pdf)
    destination = tmp_path / "existing"
    destination.mkdir()
    sentinel = destination / "important.txt"
    sentinel.write_text("keep")
    with pytest.raises(InputError, match="not managed"):
        prepare(pdf, destination)
    assert sentinel.read_text() == "keep"


def test_prepare_rejects_destination_that_contains_source(tmp_path: Path) -> None:
    destination = tmp_path / "managed"
    source = destination / "book.pdf"
    destination.mkdir()
    doc = pymupdf.open()
    doc.new_page()
    doc.save(source)
    (destination / ".platform-book-prepared").write_text("platform-book prepared pages\n")
    with pytest.raises(InputError, match="must not contain"):
        prepare(source, destination)
    assert source.is_file()


def test_pdf_affinity_order_includes_back_cover_and_adds_blank_filler(tmp_path: Path) -> None:
    pdf = tmp_path / "book.pdf"
    doc = pymupdf.open()
    gray_levels = [0.08, 0.20, 0.32, 0.44, 0.56, 0.68]
    for gray in gray_levels:
        page = doc.new_page(width=100, height=120)
        page.draw_rect(page.rect, color=(gray, gray, gray), fill=(gray, gray, gray))
    doc.save(pdf)
    pages = prepare(
        pdf, tmp_path / "prepared", max_dimension=120, quality=95,
        page_order="affinity_spreads", back_cover=True,
    )
    observed = []
    for page in pages:
        pixel = Image.open(page).getpixel((50, 60))
        observed.append(pixel[0] if isinstance(pixel, tuple) else pixel)
    expected = [round(gray_levels[index] * 255) for index in (0, 2, 1, 4, 3, 5)] + [255]
    assert len(observed) == 7
    assert all(abs(actual - wanted) <= 3 for actual, wanted in zip(observed, expected, strict=True))


def test_cli_reports_manifest_errors_cleanly(tmp_path: Path) -> None:
    manifest = tmp_path / "bad.yaml"
    manifest.write_text(yaml.safe_dump({"id": "x"}))
    result = subprocess.run(
        ["uv", "run", "platform-book", "build", str(manifest)], check=False, text=True, capture_output=True
    )
    assert result.returncode == 2
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_prepare_then_build_uses_separate_review_directory(tmp_path: Path) -> None:
    pdf = tmp_path / "book.pdf"
    doc = pymupdf.open()
    doc.new_page(width=300, height=400)
    doc.new_page(width=300, height=400)
    doc.new_page(width=300, height=400)
    doc.save(pdf)
    output = tmp_path / "dist"
    manifest = tmp_path / "book.yaml"
    manifest.write_text(yaml.safe_dump({
        "id": "net.example.book.vol1", "title": "Book", "author": "Author",
        "source": {"path": str(pdf), "type": "pdf", "page_order": "natural"},
        "output": {
            "directory": str(output), "version": "1.0.0", "latest_version": "1.0.0",
            "latest_id": "net.example.book.latest", "target_name": "Book_vol1",
        },
        "rights": {"redistribution_approved": True, "statement": "test fixture"},
    }), encoding="utf-8")

    assert main(["prepare", str(manifest)]) == 0
    assert (tmp_path / "dist-prepared-pages" / "page_001.jpg").is_file()
    assert not output.exists()
    assert main(["build", str(manifest)]) == 0
    assert (output / "zips" / "net.example.book.vol1-1.0.0.zip").is_file()
