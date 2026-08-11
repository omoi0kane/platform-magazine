from __future__ import annotations

import hashlib


def unity_guid(package_id: str, relative_path: str) -> str:
    """Return a stable Unity-compatible 32-hex GUID for an owned asset."""
    normalized_path = relative_path.replace("\\", "/").lstrip("/")
    canonical = f"{package_id}\0{normalized_path}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]
