# SPDX-License-Identifier: MIT
"""
iaga.py — the container-agnostic IAGA-2002 writer.

IAGA-2002 is the exchange format of ground geomagnetism (INTERMAGNET's own,
and what **SuperMAG** ingests from its ~600 variometers). One file = one
station, one cadence: 12 mandatory 70-char header records, optional comment
records, one column-header record, then one 70-char-max data line per sample.

    physical values in nT, %10.2f  ·  missing = 99999.00  ·  not-observed = 88888.00

NIC's Gauss is a *variometer* (it reports field deviation, not absolutes), so
files written here declare ``Data Type: variation`` — exactly the class of data
SuperMAG takes; the absolute baseline stays the observatories' job (the
variometer doctrine, nic-station ``gauss/README.md``).

This module is pure formatting: it takes rows of ``(unix_seconds, x, y, z[, f])``
floats already in nT and writes text. Reading MLA and applying calibration is
``from_mla``'s job — same two-layer split as NIC-MSEED.
"""
from __future__ import annotations

import time as _time

MISSING = 99999.00       # value gap (sensor should have reported, didn't)
NOT_OBSERVED = 88888.00  # element not recorded at all (e.g. no F channel)

_MANDATORY = ("Format", "Source of Data", "Station Name", "IAGA CODE",
              "Geodetic Latitude", "Geodetic Longitude", "Elevation",
              "Reported", "Sensor Orientation", "Digital Sampling",
              "Data Interval Type", "Data Type")


def _hdr(keyword: str, value: str) -> str:
    """One 70-char header record: ' ' + keyword(23) + value(45) + '|'."""
    line = f" {keyword:<23.23}{value:<45.45}|"
    assert len(line) == 70
    return line


def write_iaga2002(rows, *, iaga_code: str, station_name: str = "",
                   source: str = "NIC - Native Intellect Community",
                   latitude: float = 0.0, longitude: float = 0.0,
                   elevation_m: float = 0.0, reported: str = "XYZF",
                   orientation: str = "XYZ", sampling: str = "",
                   interval_type: str = "", data_type: str = "variation",
                   comments=()) -> str:
    """Format rows as one IAGA-2002 file body (a ``str``).

    rows        — iterable of (unix_s, x, y, z) or (unix_s, x, y, z, f); values
                  in nT (floats). Use MISSING / NOT_OBSERVED for gaps. unix_s
                  may be float (sub-second cadence keeps its milliseconds).
    iaga_code   — the station's 3–4 char code (community stations pick one and
                  register it with the aggregator, the Raspberry-Shake way).
    reported    — element letters for the 4 data columns, e.g. "XYZF".
    longitude   — degrees east 0–360 per the spec (negatives are converted).
    """
    code = iaga_code.upper()[:4]
    lon = longitude % 360.0
    out = [
        _hdr("Format", "IAGA-2002"),
        _hdr("Source of Data", source),
        _hdr("Station Name", station_name or code),
        _hdr("IAGA CODE", code),
        _hdr("Geodetic Latitude", f"{latitude:.3f}"),
        _hdr("Geodetic Longitude", f"{lon:.3f}"),
        _hdr("Elevation", f"{elevation_m:.0f}"),
        _hdr("Reported", reported[:4]),
        _hdr("Sensor Orientation", orientation),
        _hdr("Digital Sampling", sampling),
        _hdr("Data Interval Type", interval_type),
        _hdr("Data Type", data_type),
    ]
    for c in comments:
        out.append(f" # {c:<66.66}|")

    # column header: 27-char prefix aligns with the data lines' DATE/TIME/DOY,
    # then the four 10-char right-justified CODE+element labels; padded to 70.
    cols = "".join(f"{code + e:>10.10}" for e in reported[:4].upper())
    out.append(f"{'DATE       TIME         DOY' + cols:<69.69}|")

    for row in rows:
        t, vals = float(row[0]), list(row[1:4])
        vals.append(float(row[4]) if len(row) > 4 else NOT_OBSERVED)
        tm = _time.gmtime(int(t))
        ms = int(round((t - int(t)) * 1000))
        out.append("%04d-%02d-%02d %02d:%02d:%02d.%03d %03d%s" % (
            tm.tm_year, tm.tm_mon, tm.tm_mday, tm.tm_hour, tm.tm_min,
            tm.tm_sec, ms, tm.tm_yday,
            "".join("%10.2f" % float(v) for v in vals)))
    return "\n".join(out) + "\n"


def parse_iaga2002(text: str):
    """Minimal reader for round-trip tests: returns (headers, rows).

    headers — {keyword: value} from the 12+ header records (comments skipped);
    rows    — [(unix_s, v1, v2, v3, v4), ...] floats as written.
    """
    import calendar
    headers, rows = {}, []
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.endswith("|"):
            body = line[:-1]
            if body.lstrip().startswith("#"):
                continue
            if body.startswith("DATE"):
                continue
            kw, val = body[1:24].rstrip(), body[24:].strip()
            if kw:
                headers[kw] = val
            continue
        d, tstr, _doy = line[0:10], line[11:23], line[24:27]
        y, mo, dd = int(d[0:4]), int(d[5:7]), int(d[8:10])
        hh, mm = int(tstr[0:2]), int(tstr[3:5])
        ss = float(tstr[6:])
        unix = calendar.timegm((y, mo, dd, hh, mm, 0, 0, 0, 0)) + ss
        vals = [float(line[27 + i * 10: 37 + i * 10]) for i in range(4)]
        rows.append((unix, *vals))
    return headers, rows


__all__ = ["write_iaga2002", "parse_iaga2002", "MISSING", "NOT_OBSERVED",
           "_MANDATORY"]
