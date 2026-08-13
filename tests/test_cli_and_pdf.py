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


def test_pdf_affinity_order_builds_cover_atlas_and_orders_only_interior(tmp_path: Path) -> None:
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
    assert Image.open(pages[0]).size == (200, 120)
    cover_left_pixel = Image.open(pages[0]).getpixel((50, 60))
    cover_right_pixel = Image.open(pages[0]).getpixel((150, 60))
    cover_left = cover_left_pixel[0] if isinstance(cover_left_pixel, tuple) else cover_left_pixel
    cover_right = cover_right_pixel[0] if isinstance(cover_right_pixel, tuple) else cover_right_pixel
    assert isinstance(cover_left, (int, float)) and isinstance(cover_right, (int, float))
    assert abs(cover_left - round(gray_levels[0] * 255)) <= 3
    assert abs(cover_right - round(gray_levels[5] * 255)) <= 3
    observed = []
    for page in pages[1:]:
        pixel = Image.open(page).getpixel((50, 60))
        observed.append(pixel[0] if isinstance(pixel, tuple) else pixel)
    expected = [round(gray_levels[index] * 255) for index in (2, 1, 4, 3)]
    assert len(pages) == 5
    assert all(abs(actual - wanted) <= 3 for actual, wanted in zip(observed, expected, strict=True))


def test_pdf_affinity_spread_pages_splits_each_wide_interior_right_then_left(tmp_path: Path) -> None:
    pdf = tmp_path / "book.pdf"
    doc = pymupdf.open()
    front = doc.new_page(width=100, height=120)
    front.draw_rect(front.rect, color=(0.1, 0.1, 0.1), fill=(0.1, 0.1, 0.1))
    spread = doc.new_page(width=200, height=120)
    spread.draw_rect(pymupdf.Rect(0, 0, 100, 120), color=(0.25, 0.25, 0.25), fill=(0.25, 0.25, 0.25))
    spread.draw_rect(pymupdf.Rect(100, 0, 200, 120), color=(0.75, 0.75, 0.75), fill=(0.75, 0.75, 0.75))
    back = doc.new_page(width=100, height=120)
    back.draw_rect(back.rect, color=(0.9, 0.9, 0.9), fill=(0.9, 0.9, 0.9))
    doc.save(pdf)

    pages = prepare(
        pdf, tmp_path / "prepared", max_dimension=120, quality=95,
        page_order="affinity_spread_pages", back_cover=True,
    )

    assert len(pages) == 3
    assert Image.open(pages[0]).size == (200, 120)
    assert Image.open(pages[1]).size == (100, 120)
    assert Image.open(pages[2]).size == (100, 120)
    right_pixel = Image.open(pages[1]).getpixel((50, 60))
    left_pixel = Image.open(pages[2]).getpixel((50, 60))
    right = right_pixel[0] if isinstance(right_pixel, tuple) else right_pixel
    left = left_pixel[0] if isinstance(left_pixel, tuple) else left_pixel
    assert isinstance(right, (int, float)) and isinstance(left, (int, float))
    assert abs(right - round(0.75 * 255)) <= 3
    assert abs(left - round(0.25 * 255)) <= 3


def test_pdf_affinity_spread_pages_rejects_single_page_interior(tmp_path: Path) -> None:
    pdf = tmp_path / "book.pdf"
    doc = pymupdf.open()
    for _ in range(3):
        doc.new_page(width=100, height=120)
    doc.save(pdf)
    with pytest.raises(InputError, match="wide spread"):
        prepare(
            pdf, tmp_path / "prepared", page_order="affinity_spread_pages", back_cover=True,
        )


def test_pdf_affinity_spread_pages_assigns_odd_center_column_once(tmp_path: Path) -> None:
    pdf = tmp_path / "book.pdf"
    doc = pymupdf.open()
    doc.new_page(width=100, height=120)
    doc.new_page(width=201, height=120)
    doc.new_page(width=100, height=120)
    doc.save(pdf)
    pages = prepare(
        pdf, tmp_path / "prepared", max_dimension=120, quality=95,
        page_order="affinity_spread_pages", back_cover=True,
    )
    right_size = Image.open(pages[1]).size
    left_size = Image.open(pages[2]).size
    assert sorted((right_size[0], left_size[0])) == [100, 101]
    assert right_size[0] + left_size[0] == 201


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
