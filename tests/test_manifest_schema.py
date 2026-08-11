from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from platform_book.errors import ManifestError
from platform_book.manifest import load_manifest


def test_manifest_requires_declared_domain_fields(tmp_path: Path) -> None:
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.safe_dump({"id": "net.example.book"}))
    with pytest.raises(ManifestError, match="missing required field"):
        load_manifest(path)


def test_manifest_rejects_unsupported_source_type(tmp_path: Path) -> None:
    data = {
        "id": "net.example.book", "title": "Book", "author": "A",
        "source": {"path": "x", "type": "docx"},
        "output": {"directory": "out", "version": "1.0.0", "latest_version": "16.0.0"},
        "rights": {"redistribution_approved": True, "statement": "ok"},
    }
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(ManifestError, match="source.type"):
        load_manifest(path)


def test_committed_example_matches_json_schema() -> None:
    root = Path(__file__).resolve().parents[1]
    schema = yaml.safe_load((root / "schemas/book-manifest.schema.yaml").read_text())
    example = yaml.safe_load((root / "examples/book.yaml").read_text())
    Draft202012Validator.check_schema(schema)
    assert list(Draft202012Validator(schema).iter_errors(example)) == []
