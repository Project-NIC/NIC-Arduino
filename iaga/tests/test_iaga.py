# SPDX-License-Identifier: MIT
"""The pure IAGA-2002 writer: header shape, line widths, value round-trip."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from nic_iaga import write_iaga2002, parse_iaga2002, NOT_OBSERVED
from nic_iaga.iaga import _MANDATORY

_p = _f = 0
def check(name, cond):
    global _p, _f
    if cond: _p += 1; print(f"  PASS  {name}")
    else:    _f += 1; print(f"  FAIL  {name}")


T0 = 1752624000  # 2025-07-16 00:00:00 UTC-ish epoch (exact date irrelevant)
ROWS = [
    (T0 + 0,   21563.25, -1234.56, 43210.00, 48000.12),
    (T0 + 60,  21563.00, -1234.00, 43209.75, 48000.00),
    (T0 + 120.5, -99.25,     0.00,    99.99),            # 3 components, sub-second
]

text = write_iaga2002(ROWS, iaga_code="nic1", station_name="Praha-Libus",
                      latitude=50.007, longitude=14.446, elevation_m=304,
                      sampling="60 seconds", interval_type="1-minute",
                      comments=["community variometer — NIC-Gauss (RM3100)"])

lines = text.splitlines()
hdr = [l for l in lines if l.endswith("|")]
data = [l for l in lines if not l.endswith("|")]

check("all header records are exactly 70 chars", all(len(l) == 70 for l in hdr))
check("12 mandatory keywords present",
      all(any(l[1:24].rstrip() == k for l in hdr) for k in _MANDATORY))
check("comment record kept", any(l.lstrip().startswith("# community") for l in hdr))
check("column header carries the code",
      any("NIC1X" in l and "NIC1F" in l for l in hdr))
check("one data line per row", len(data) == len(ROWS))
check("data lines are 67 chars", all(len(l) == 67 for l in data))

headers, rows = parse_iaga2002(text)
check("Data Type is variation", headers["Data Type"] == "variation")
check("IAGA CODE upper-cased", headers["IAGA CODE"] == "NIC1")
check("longitude folded to 0-360", abs(float(headers["Geodetic Longitude"]) - 14.446) < 1e-6)
check("values round-trip", abs(rows[0][1] - 21563.25) < 0.005
      and abs(rows[1][3] - 43209.75) < 0.005)
check("missing F -> NOT_OBSERVED", rows[2][4] == NOT_OBSERVED)
check("sub-second kept as milliseconds", abs(rows[2][0] - (T0 + 120.5)) < 0.001)

print(f"\n{_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
