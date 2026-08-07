"""Local content-addressed storage adapter."""
from __future__ import annotations

import hashlib
import mimetypes
import shutil
import uuid
from pathlib import Path

from app.node.domain import Source


class LocalSourceStore:
    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def persist(self, filename: str, source: Path) -> Source:
        digest = hashlib.sha256()
        with source.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        sha256 = digest.hexdigest()
        suffix = Path(filename).suffix.lower()
        target = self.root / f"{sha256}{suffix}"
        if not target.exists():
            shutil.copy2(source, target)
        return Source(
            id=str(uuid.uuid4()), filename=Path(filename).name,
            media_type=mimetypes.guess_type(filename)[0] or "application/octet-stream",
            sha256=sha256, size_bytes=target.stat().st_size, stored_path=str(target),
        )
