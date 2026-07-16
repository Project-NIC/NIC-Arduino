# SPDX-License-Identifier: MIT
"""
End-to-end: build a .mla with magnetometer rows (raw AND NIC-DMD-compressed
stations), convert to IAGA-2002, parse it back, and confirm the calibrated nT
values survive — proving the NIC-MLA + NIC-DMD + calibration bridge works.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import nic_iaga  # noqa: E402  — puts third_party (nic_mla, nic_dmd) on sys.path
from nic_iaga import export_mla_to_iaga, parse_iaga2002, NOT_OBSERVED
from nic_mla import MlaCore, MlaPosixHAL
from mla_schema import MlaSchemaBuilder, MlaStationTable, dl_ident
from nic_dmd import DmdEncoder

_p = _f = 0
def check(name, cond):
    global _p, _f
    if cond: _p += 1; print(f"  PASS  {name}")
    else:    _f += 1; print(f"  FAIL  {name}")

WIDTH = 6   # three int16 components: x, y, z


def _schema_stations():
    sb = MlaSchemaBuilder()
    sb.log("datetime")
    # RM3100-style: raw counts, exp10=-2 + offset -> nT with 0.01 nT LSB
    sb.data("mag_x", unit="raw", width=2, signed=True, exp10=-2, offset=100)
    sb.data("mag_y", unit="raw", width=2, signed=True, exp10=-2)
    sb.data("mag_z", unit="raw", width=2, signed=True, exp10=-2)
    st = MlaStationTable()
    st.station(dl_ident(region=55, number=25000), elev_m=235, name="Praha-Klementinum")  # 1 raw
    st.station(dl_ident(region=55, number=25001), elev_m=240, name="Libuš")              # 2 dmd
    return sb.table(), st.table()


def _pack(x, y, z):
    return (x.to_bytes(2, "little", signed=True)
            + y.to_bytes(2, "little", signed=True)
            + z.to_bytes(2, "little", signed=True))


T0 = 1752624000
RAW = [(1000, -2000, 30000), (1010, -1990, 29990), (1005, -2005, 30005)]


def _build(path):
    schema, stations = _schema_stations()
    hal = MlaPosixHAL.create(path, file_size=256 * 1024)
    with hal:
        core = MlaCore(hal)
        core.format(file_size=256 * 1024, schema_table=schema, station_table=stations)
        enc = DmdEncoder(WIDTH)
        since_kf = 0
        for i, (x, y, z) in enumerate(RAW):
            row = _pack(x, y, z)
            core.append(T0 + 60 * i, station=1, data=row, subsec=250)
            blob = enc.compress(row)
            since_kf = 0 if (blob[0] & 0x07) == 0 else since_kf + 1
            core.append(T0 + 60 * i, station=2, data=blob, subsec=250,
                        compressed=True, kf_back=since_kf)


with tempfile.TemporaryDirectory() as td:
    mla = os.path.join(td, "gauss.mla")
    out = os.path.join(td, "gauss.iaga2002")
    _build(mla)

    stats = export_mla_to_iaga(
        mla, out, subsec_unit="ms",
        stations={1: dict(iaga_code="NIC1", latitude=50.086, longitude=14.416,
                          elevation_m=235),
                  2: dict(iaga_code="NIC2", latitude=50.0,  longitude=14.45,
                          elevation_m=240)},
        sampling="60 seconds", interval_type="1-minute")

    check("two stations exported", len(stats) == 2 and stats[1]["rows"] == 3
          and stats[2]["rows"] == 3)

    hdr1, rows1 = parse_iaga2002(open(stats[1]["out"]).read())
    hdr2, rows2 = parse_iaga2002(open(stats[2]["out"]).read())

    check("station 1 code + name from tables",
          hdr1["IAGA CODE"] == "NIC1" and hdr1["Station Name"] == "Praha-Klementinum")
    # calibration: (raw + offset) * 10^exp10 ; x has offset 100 -> (1000+100)*0.01
    check("calibration applied (offset + exp10)",
          abs(rows1[0][1] - 11.00) < 0.005 and abs(rows1[0][2] - (-20.00)) < 0.005
          and abs(rows1[0][3] - 300.00) < 0.005)
    check("no F channel -> NOT_OBSERVED", all(r[4] == NOT_OBSERVED for r in rows1))
    check("subsec ms carried", abs(rows1[0][0] - (T0 + 0.25)) < 0.001)
    check("DMD-compressed station decodes to the same values",
          all(abs(a[i] - b[i]) < 0.005 for a, b in zip(rows1, rows2)
              for i in (1, 2, 3)))
    check("variation data type declared", hdr2["Data Type"] == "variation")

print(f"\n{_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
