"""LocalBackend — the host filesystem (the brief's primary storage path)."""

from __future__ import annotations

import os
import shutil
from datetime import datetime

from .backend import Backend, BackendError, Entry

MLA_EXTS = (".mla",)


class LocalBackend(Backend):
    """Browse a directory on the host OS filesystem."""

    def __init__(self, path: str):
        self.path = os.path.abspath(path)

    @property
    def location(self) -> str:
        return self.path

    # ── browsing ────────────────────────────────────────────────────────────
    def list(self) -> list[Entry]:
        dirs: list[Entry] = []
        files: list[Entry] = []
        try:
            with os.scandir(self.path) as it:
                for e in it:
                    try:
                        st = e.stat()
                        mtime = st.st_mtime
                        size = st.st_size
                        is_dir = e.is_dir()
                    except OSError:
                        mtime, size, is_dir = None, 0, False
                    if is_dir:
                        dirs.append(Entry(e.name, True, 0, mtime, "dir"))
                    else:
                        is_mla = e.name.lower().endswith(MLA_EXTS)
                        files.append(Entry(
                            e.name, is_mla, size, mtime,
                            "mla" if is_mla else "file",
                        ))
        except OSError as exc:
            raise BackendError(f"Cannot read directory: {exc}") from exc

        dirs.sort(key=lambda x: x.name.lower())
        files.sort(key=lambda x: x.name.lower())
        out: list[Entry] = []
        if os.path.dirname(self.path) != self.path:
            out.append(Entry("..", True, 0, None, "updir"))
        return out + dirs + files

    def enter(self, entry: Entry) -> "Backend | None":
        if not entry.is_container:
            return None
        if entry.name == "..":
            parent = os.path.dirname(self.path)
            return LocalBackend(parent) if parent != self.path else None
        target = os.path.join(self.path, entry.name)
        if entry.kind == "mla":
            from .mla import MlaBackend  # local import avoids a cycle
            return MlaBackend(target, parent=self)
        return LocalBackend(target)

    # ── reading ─────────────────────────────────────────────────────────────
    def read(self, entry: Entry) -> bytes:
        # an .mla is "enterable" but still a real file on disk → copyable/readable
        if entry.is_container and entry.kind != "mla":
            raise BackendError("Not a file")
        try:
            with open(os.path.join(self.path, entry.name), "rb") as f:
                return f.read()
        except OSError as exc:
            raise BackendError(f"Cannot read file: {exc}") from exc

    def info(self, entry: Entry) -> list[tuple[str, str]]:
        full = os.path.join(self.path, entry.name)
        rows = [("Name", entry.name), ("Path", full)]
        try:
            st = os.stat(full)
            rows.append(("Kind", "Directory" if entry.is_container and entry.kind != "mla"
                         else ("MLA container" if entry.kind == "mla" else "File")))
            if not (entry.is_container and entry.kind == "dir"):
                rows.append(("Size", f"{st.st_size} B"))
            rows.append(("Modified", datetime.fromtimestamp(st.st_mtime)
                         .strftime("%Y-%m-%d %H:%M:%S")))
            rows.append(("Mode", oct(st.st_mode & 0o777)))
        except OSError as exc:
            rows.append(("Error", str(exc)))
        return rows

    # ── mutating ────────────────────────────────────────────────────────────
    def mkdir(self, name: str) -> None:
        try:
            os.mkdir(os.path.join(self.path, name))
        except OSError as exc:
            raise BackendError(f"mkdir failed: {exc}") from exc

    def delete(self, entry: Entry) -> None:
        if entry.name == "..":
            raise BackendError("Cannot delete '..'")
        target = os.path.join(self.path, entry.name)
        try:
            if entry.is_container and entry.kind == "dir":
                shutil.rmtree(target)
            else:
                os.remove(target)
        except OSError as exc:
            raise BackendError(f"delete failed: {exc}") from exc

    def rename(self, entry: Entry, new_name: str) -> None:
        if entry.name == "..":
            raise BackendError("Cannot rename '..'")
        src = os.path.join(self.path, entry.name)
        dst = os.path.join(self.path, new_name)
        try:
            os.rename(src, dst)
        except OSError as exc:
            raise BackendError(f"rename failed: {exc}") from exc

    def put_file(self, name: str, data: bytes) -> None:
        try:
            with open(os.path.join(self.path, name), "wb") as f:
                f.write(data)
        except OSError as exc:
            raise BackendError(f"copy failed: {exc}") from exc

    def exists(self, name: str) -> bool:
        return os.path.exists(os.path.join(self.path, name))
