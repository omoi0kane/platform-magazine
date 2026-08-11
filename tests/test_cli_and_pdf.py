from __future__ import annotations

import subprocess
from pathlib import Path

import pymupdf
import pytest
import yaml
from PIL import Image

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


def test_pdf_rejects_non_natural_page_order(tmp_path: Path) -> None:
    pdf = tmp_path / "book.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(pdf)
    with pytest.raises(InputError, match="PDF.*natural"):
        prepare(pdf, tmp_path / "prepared", page_order="affinity_spreads")


def test_cli_reports_manifest_errors_cleanly(tmp_path: Path) -> None:
    manifest = tmp_path / "bad.yaml"
    manifest.write_text(yaml.safe_dump({"id": "x"}))
    result = subprocess.run(
        ["uv", "run", "platform-book", "build", str(manifest)], check=False, text=True, capture_output=True
    )
    assert result.returncode == 2
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr
