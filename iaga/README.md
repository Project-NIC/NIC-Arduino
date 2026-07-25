# NIC-IAGA

**A standalone NIC data library — turn a NIC-MLA magnetometer log into IAGA-2002.**

---

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](https://opensource.org/licenses/MIT)

---

```
   .mla  ──▶  [NIC-DMD decode if compressed]  ──▶  calibrated nT per component  ──▶  IAGA-2002
```

> **What this is.** One of the standalone NIC data libraries (alongside NIC-MLA,
> NIC-DMD, NIC-MSEED). **IAGA-2002** is the exchange format of ground geomagnetism —
> INTERMAGNET's own, and what **[SuperMAG](https://supermag.jhuapl.edu/)** ingests from
> its ~600 variometers worldwide. NIC-Gauss is a variometer (it reports field
> *deviation*, not absolutes), so its data goes out declared `Data Type: variation` —
> exactly the class SuperMAG takes; the absolute baseline stays the observatories' job
> (the variometer doctrine). NIC-IAGA is the bridge —
> it reads a `.mla`, decompresses NIC-DMD blobs, applies the SCHEMA calibration
> (`physical = (raw + offset) · 10^exp10` → **nT, not counts**) and writes standard
> IAGA-2002 text, one file per station. **A worked library, not a framework.**

> **Where calibration lives — the one deliberate difference from NIC-MSEED.**
> miniSEED carries raw counts and leaves calibration to StationXML metadata; IAGA-2002
> carries **physical nT**, so this exporter applies the SCHEMA calibration on the way
> out. Both read the same archive — the archive itself stays raw (derive-from-raw).

## Two layers

- **`iaga`** — a container-agnostic core: rows of `(unix_s, x, y, z[, f])` nT floats →
  IAGA-2002 text (12 mandatory 70-char header records, comments, column header,
  67-char data lines; missing = `99999.00`, not-observed = `88888.00`), plus a minimal
  reader for round-trip tests.
- **`from_mla`** — the converter that wires **NIC-MLA + NIC-DMD** to that core:
  per-station DMD replay, X/Y/Z(/F) field auto-detect (or named), calibration, station
  metadata from the MLA STATION table.

## Quick start

```python
from nic_iaga import export_mla_to_iaga

export_mla_to_iaga(
    "gauss.mla", "gauss.iaga2002",
    stations={1: dict(iaga_code="NIC1", latitude=50.086, longitude=14.416,
                      elevation_m=235)},
    sampling="60 seconds", interval_type="1-minute")
```

## Tests

```sh
python3 tests/test_iaga.py       # the pure writer: header shape, widths, round-trip
python3 tests/test_from_mla.py   # end-to-end: MLA (+DMD) → IAGA-2002 → parse-back
```

The vendored dependencies (`nic_mla`, `nic_dmd`) live under `third_party/`, the same
way NIC-MSEED, NIC-GLUE-IN and NIC-VDE vendor them.

## License

MIT — Copyright (c) 2026 NIC — Native Intellect Community
