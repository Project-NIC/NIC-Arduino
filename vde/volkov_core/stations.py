"""
Host glue: give the opaque station bytes a meaning for Volkov.

The MLA log carries only a 1-byte **station index**. The real station lives in the
prefix station table as a 42-byte record per station: an 8-byte opaque identity
(which MLA leaves uninterpreted on purpose) + a 2-byte signed-metres elevation +
a 32-byte human-readable name (UTF-8, NUL-padded, all-zero = none).
Volkov's convention — matching MLA's ``dl_ident`` identity helper — reads the
identity as ``region(2) + number(2) + kind(2) + reserved(2)``, all u16 LE. This
tiny module is the only place that convention lives; the backend just asks it
for a label.
"""

from __future__ import annotations

import os
import struct
import sys

_MLA_TOOLS = os.path.join(os.path.dirname(__file__), "..",
                          "third_party", "nic_mla", "tools")
_p = os.path.abspath(_MLA_TOOLS)
if _p not in sys.path:
    sys.path.insert(0, _p)

from mla_schema import mla_read_stations, mla_split_station  # noqa: E402


class VdeStationMap:
    """Resolve a 1-byte station index to its real (region, number) + elevation."""

    def __init__(self, records: list[bytes] | None):
        self._records = records  # list of 42-byte records, or None if no table

    @classmethod
    def from_prefix(cls, prefix: bytes) -> "VdeStationMap":
        try:
            return cls(mla_read_stations(prefix))
        except Exception:
            return cls(None)

    @property
    def present(self) -> bool:
        return bool(self._records)

    @property
    def records(self) -> list[bytes]:
        """The raw 42-byte station records (empty list if no table)."""
        return list(self._records or [])

    def resolve(self, index: int) -> tuple[int, int] | None:
        """(region, number) for a log index (1..n); None if absent/out of range.

        Reads the 8-byte identity as dl_ident (region/number/kind/reserved).
        """
        if not self._records or not (1 <= index <= len(self._records)):
            return None
        identity, _elev, _name = mla_split_station(self._records[index - 1])
        region, number, _kind, _reserved = struct.unpack("<HHHH", identity)
        return region, number

    def elevation(self, index: int) -> int | None:
        """Signed-metres elevation for a log index (None if absent/unset)."""
        if not self._records or not (1 <= index <= len(self._records)):
            return None
        return mla_split_station(self._records[index - 1])[1]

    def name(self, index: int) -> str:
        """Human-readable station name for a log index ("" if absent/unset)."""
        if not self._records or not (1 <= index <= len(self._records)):
            return ""
        return mla_split_station(self._records[index - 1])[2]

    def label(self, index: int) -> str:
        """Human label for a station index: 'region/number', else '#index'."""
        rn = self.resolve(index)
        return f"{rn[0]}/{rn[1]}" if rn else f"#{index}"
