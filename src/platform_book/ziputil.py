from __future__ import annotations

import zipfile
from pathlib import Path

_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def deterministic_zip(source: Path, destination: Path) -> Path:
    if not (source / "package.json").is_file():
        raise ValueError(f"package.json must exist at package root: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        files = [p for p in source.rglob("*") if p.is_file()]
        for path in sorted(files, key=lambda item: item.relative_to(source).as_posix()):
            relative = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(relative, _ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return destination
