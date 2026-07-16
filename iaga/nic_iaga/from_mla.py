# SPDX-License-Identifier: MIT
"""
from_mla.py — the converter that connects NIC-MLA (+ NIC-DMD) to IAGA-2002.

Same two-layer split as NIC-MSEED: ``iaga`` is the pure format writer; this
module reads a ``.mla`` container (decompressing NIC-DMD blobs when a record's
``compressed`` bit is set), picks the magnetometer SCHEMA fields, applies the
schema calibration — ``physical = (raw + offset) * 10**exp10`` — so the output
is **nT, not counts** (unlike miniSEED, where counts stay raw and calibration
lives in StationXML), and writes one IAGA-2002 text per station.

One MLA record = one sample row (the Gauss slow-poll cadence: each record
carries one X/Y/Z[/F] reading with its own timestamp).
"""
from __future__ import annotations

from nic_mla import MlaCore, MlaPosixHAL
from mla_schema import mla_read_schema, mla_read_stations, mla_split_station
from nic_dmd import DmdDecoder

from .iaga import write_iaga2002, NOT_OBSERVED

_X_NAMES = ("x", "bx", "mag_x", "magx")
_Y_NAMES = ("y", "by", "mag_y", "magy")
_Z_NAMES = ("z", "bz", "mag_z", "magz")
_F_NAMES = ("f", "bf", "mag_f", "total")


def _find(fields, names, override):
    if override is not None:
        for i, f in enumerate(fields):
            if f.name == override:
                return i
        raise ValueError(f"field {override!r} not in SCHEMA")
    for i, f in enumerate(fields):
        if f.name.lower() in names:
            return i
    return None


class IagaExporter:
    """Convert a NIC-MLA container to IAGA-2002 (one text file per station).

    subsec_unit — same options as NIC-MSEED ("ms" default here: the Gauss
                  housekeeping stream stamps milliseconds, not sample index).
    x/y/z/f     — SCHEMA field names when auto-detect shouldn't guess.
    stations    — {mla_station_index: dict of write_iaga2002 kwargs}
                  (iaga_code, latitude, longitude, elevation_m, ...); a station
                  missing here gets code f"N{index:02d}" and zero coordinates.
    """

    def __init__(self, *, subsec_unit="ms", x=None, y=None, z=None, f=None,
                 stations: dict | None = None, **iaga_kw):
        self.subsec_unit = subsec_unit
        self.names = (x, y, z, f)
        self.stations = dict(stations or {})
        self.iaga_kw = dict(iaga_kw)

    def _subsec(self, subsec: int) -> float:
        u = self.subsec_unit
        if callable(u):
            return float(u(subsec))
        return {"ms": subsec / 1000.0, "tick": subsec / 65536.0}[u]

    def export(self, mla_path: str, out_path: str) -> dict:
        """Write one file per station: ``out_path`` for the first, then
        ``out_path`` with ``_s<index>`` appended before the extension. Returns
        stats: {station_index: {"rows": n, "out": path}}."""
        with MlaPosixHAL(mla_path) as hal:
            core = MlaCore(hal)
            core.mount()
            fields = mla_read_schema(core._prefix.to_bytes())[1]
            if not fields:
                raise ValueError("MLA file has no SCHEMA — cannot map components")
            st_table = mla_read_stations(core._prefix.to_bytes())
            pkt_len = sum(f.width for f in fields)

            ix = _find(fields, _X_NAMES, self.names[0])
            iy = _find(fields, _Y_NAMES, self.names[1])
            iz = _find(fields, _Z_NAMES, self.names[2])
            iff = _find(fields, _F_NAMES, self.names[3])
            if ix is None or iy is None or iz is None:
                raise ValueError("no X/Y/Z magnetometer fields found in SCHEMA "
                                 "(pass x=/y=/z= field names)")

            decoders, rows = {}, {}
            for rec, payload in core:                        # oldest first
                st = rec.station
                if rec.compressed:
                    dec = decoders.get(st) or decoders.setdefault(st, DmdDecoder(pkt_len))
                    row = dec.decompress(payload)
                else:
                    row = payload
                if len(row) != pkt_len:
                    continue                                 # not a schema row
                vals, pos = [], 0
                for fld in fields:
                    v = int.from_bytes(row[pos:pos + fld.width], "little",
                                       signed=fld.signed)
                    pos += fld.width
                    vals.append((v + fld.offset) * (10.0 ** fld.exp10))
                t = rec.timestamp + self._subsec(rec.subsec)
                sample = (t, vals[ix], vals[iy], vals[iz],
                          vals[iff] if iff is not None else NOT_OBSERVED)
                rows.setdefault(st, []).append(sample)

        stats = {}
        for n, st in enumerate(sorted(rows)):
            kw = dict(self.iaga_kw)
            kw.setdefault("reported", "XYZF")
            meta = self.stations.get(st, {})
            kw.update(meta)
            kw.setdefault("iaga_code", f"N{st:02d}")
            if "station_name" not in kw and st_table and 1 <= st <= len(st_table):
                kw["station_name"] = mla_split_station(st_table[st - 1])[2]
            path = out_path if n == 0 else _suffixed(out_path, st)
            with open(path, "w", newline="\n") as fh:
                fh.write(write_iaga2002(rows[st], **kw))
            stats[st] = {"rows": len(rows[st]), "out": path}
        return stats


def _suffixed(path: str, idx: int) -> str:
    dot = path.rfind(".")
    return (path + f"_s{idx}") if dot < 0 else f"{path[:dot]}_s{idx}{path[dot:]}"


def export_mla_to_iaga(mla_path: str, out_path: str, **kw) -> dict:
    """Convenience wrapper: one-shot MLA → IAGA-2002 conversion."""
    return IagaExporter(**kw).export(mla_path, out_path)
