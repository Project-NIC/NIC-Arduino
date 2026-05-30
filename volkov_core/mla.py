"""
MlaBackend — browse the records inside an NIC-MLA container as if they were files.

This is the Matroshka / Volkov Commander idea: pressing Enter on an .mla file
"steps inside" it, and each logged record shows up as an item in the panel. The
log carries the metadata (time, station, channel, type); the data block carries
only the payload — so the panel is built from the log alone, and the payload is
read lazily on view.

The whole container is read into RAM on open (the documented host model: "load
the log into RAM, then filter"), so the file handle is closed immediately and
there is no open-file lifecycle to manage.
"""

from __future__ import annotations

import os
import struct
import sys
from datetime import datetime

from .backend import Backend, BackendError, Entry, Unsupported

# Make the vendored MLA reference importable.
_MLA_DIR = os.path.join(os.path.dirname(__file__), "..", "third_party", "nic_mla")
if _MLA_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(_MLA_DIR))

try:
    from nic_mla import MlaCore, MlaPosixHAL  # noqa: E402
except Exception as exc:  # pragma: no cover - only if vendoring is broken
    raise BackendError(f"NIC-MLA library not available: {exc}") from exc

# rec_type decoding (high nibble = class, low nibble = encoding)
_ENC = {0x0: "raw", 0x1: "delta", 0x2: "keyframe", 0x3: "text"}
_CLS = {0x00: "measure", 0x10: "event", 0x20: "config", 0xF0: "checkpoint"}


def rec_type_name(rt: int) -> str:
    cls = _CLS.get(rt & 0xF0, f"cls{rt >> 4:X}")
    enc = _ENC.get(rt & 0x0F, f"enc{rt & 0xF:X}")
    return f"{cls}/{enc}"


class MlaBackend(Backend):
    """Read-only-ish view of an .mla container's records."""

    def __init__(self, path: str, parent: Backend):
        self.path = os.path.abspath(path)
        self._parent = parent
        self._records: list[tuple] = []  # [(MlaLog, bytes)]
        self._summary: dict = {}
        self._load()

    def _load(self) -> None:
        try:
            with MlaPosixHAL(self.path) as hal:
                core = MlaCore(hal)
                core.mount()
                self._records = list(core)  # host model: read it all into RAM
                self._summary = self._summarize(core, self._records)
        except Exception as exc:
            raise BackendError(f"Cannot open MLA: {exc}") from exc

    @staticmethod
    def _summarize(core, records) -> dict:
        stations = sorted({r.station for r, _ in records})
        times = [r.timestamp for r, _ in records]
        return {
            "count": len(records),
            "stations": stations,
            "time_from": min(times) if times else None,
            "time_to": max(times) if times else None,
        }

    @property
    def location(self) -> str:
        # e.g. ".../weather.mla/" — the trailing marker hints we're "inside"
        return self.path

    @property
    def label(self) -> str:
        return os.path.basename(self.path)

    # ── browsing ────────────────────────────────────────────────────────────
    def list(self) -> list[Entry]:
        out = [Entry("..", True, 0, None, "updir")]
        for i, (rec, _data) in enumerate(self._records):
            name = "%05d  st%-3d ch%-3d %s" % (
                rec.seq, rec.station, rec.channel, rec_type_name(rec.rec_type),
            )
            stamp = datetime.fromtimestamp(rec.timestamp).strftime("%Y%m%d_%H%M%S")
            export = "rec%05d_%s_st%d_ch%d.bin" % (
                rec.seq, stamp, rec.station, rec.channel,
            )
            out.append(Entry(
                name=name, is_container=False, size=rec.length,
                mtime=rec.timestamp, kind="record",
                meta={"idx": i, "export_name": export},
            ))
        return out

    def enter(self, entry: Entry) -> "Backend | None":
        if entry.name == "..":
            return self._parent  # back out to the directory holding the .mla
        return None  # records are leaves

    # ── reading ─────────────────────────────────────────────────────────────
    def read(self, entry: Entry) -> bytes:
        idx = entry.meta.get("idx")
        if idx is None or not (0 <= idx < len(self._records)):
            raise BackendError("No such record")
        return self._records[idx][1]

    def info(self, entry: Entry) -> list[tuple[str, str]]:
        if entry.name == "..":
            return self._container_info()
        idx = entry.meta.get("idx")
        rec, data = self._records[idx]
        ts = datetime.fromtimestamp(rec.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        rows = [
            ("Record (seq)", str(rec.seq)),
            ("Time", f"{ts}  (unix {rec.timestamp})"),
            ("Station", str(rec.station)),
            ("Channel", str(rec.channel)),
            ("Type", f"0x{rec.rec_type:02X}  {rec_type_name(rec.rec_type)}"),
            ("Length", f"{rec.length} B"),
        ]
        if rec.kf_back:
            rows.append(("Keyframe back", str(rec.kf_back)))
        # convenience decodes for tiny payloads
        if len(data) == 4:
            rows.append(("As float32", f"{struct.unpack('<f', data)[0]:.4f}"))
            rows.append(("As int32", str(struct.unpack('<i', data)[0])))
        return rows

    def _container_info(self) -> list[tuple[str, str]]:
        s = self._summary
        rows = [
            ("MLA file", self.path),
            ("Size", f"{os.path.getsize(self.path)} B"),
            ("Records", str(s.get("count", 0))),
        ]
        stations = s.get("stations") or []
        if stations:
            rows.append(("Stations", ", ".join(map(str, stations))))
        if s.get("time_from") is not None:
            fr = datetime.fromtimestamp(s["time_from"]).strftime("%Y-%m-%d %H:%M")
            to = datetime.fromtimestamp(s["time_to"]).strftime("%Y-%m-%d %H:%M")
            rows.append(("Time range", f"{fr} … {to}"))
        return rows

    # ── mutating — intentionally limited inside MLA ───────────────────────────
    # By design the MLA container is append-only and crash-safe: the GUI does not
    # edit records in place (that would break CRCs / the two-pointer layout). You
    # can always copy a record OUT (F5) and work on the copy. See design notes.
    _RO = "MLA is append-only by design — copy a record out (F5) to work on it."

    def mkdir(self, name: str) -> None:
        raise Unsupported(self._RO)

    def delete(self, entry: Entry) -> None:
        raise Unsupported(self._RO)

    def rename(self, entry: Entry, new_name: str) -> None:
        raise Unsupported(self._RO)

    def put_file(self, name: str, data: bytes) -> None:
        raise Unsupported(self._RO)
