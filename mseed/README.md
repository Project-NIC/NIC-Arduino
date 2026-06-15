# NIC-MSEED

**A standalone NIC data library — turn a NIC-MLA log into miniSEED (Steim-1 / Steim-2).**

---

[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](https://opensource.org/licenses/MIT)

---

```
   .mla  ──▶  [NIC-DMD decode if compressed]  ──▶  per-channel int counts  ──▶  miniSEED
```

> **What this is.** One of the standalone NIC data libraries (alongside NIC-MLA,
> NIC-DMD, NIC-KSF). A NIC node logs its samples into a NIC-MLA container; **miniSEED**
> is the lingua franca of seismology, dropping straight into **ObsPy, SeisComp, SWARM**
> and the FDSN toolchain. NIC-MSEED is the bridge — it reads a `.mla`, decompresses
> NIC-DMD blobs, pulls the raw integer counts out per SCHEMA channel, and writes
> standard miniSEED records. Whoever has a seismic MLA log (e.g. from **NIC-Quake** /
> **NIC-Station**) and needs SEED uses it — **a worked library, not a framework.** (For
> ad-hoc CSV / SQLite inspection of any MLA log, use NIC-GLUE-OUT; miniSEED is the
> seismo path.)

## Two implementations

- **Python** (`nic_mseed/`) — the reference: pure Python 3.10+, no external packages.
- **C** (`c/`) — the same Steim-1/2 codec + miniSEED writer in portable C, for
  on-device / embedded export. Both are host-tested and round-trip against each other's
  vectors.

## Two layers

- **`steim` / `mseed`** — a container-agnostic core: integers → Steim-1/2 frames
  → miniSEED records, and back (a minimal reader for round-trip tests). No deps.
- **`from_mla`** — the converter that wires **NIC-MLA + NIC-DMD** to that core:
  per-station DMD replay, schema-driven channel split, SEED code mapping.

## Quick start

```python
from nic_mseed import MseedExporter, STEIM2

stats = MseedExporter(
    sample_rate_hz=100.0,        # device ODR — miniSEED needs the rate; MLA doesn't store it
    network="NQ",                # SEED network code
    version=STEIM2,              # or STEIM1
    channel_map={"z": "HHZ", "n": "HHN", "e": "HHE"},   # SCHEMA field → SEED channel
).export("quake.mla", "quake.mseed")
print(stats)   # {channels, samples, records, bytes, out}
```

```bash
python3 examples/mla_to_mseed.py            # builds a sample .mla, converts, prints stats
python3 tests/test_steim.py                 # Steim-1/2 codec round-trip
python3 tests/test_mseed.py                 # miniSEED writer (+ ObsPy gold-standard if installed)
python3 tests/test_from_mla.py              # end-to-end MLA(+DMD) → miniSEED round-trip
python3 tests/test_to_stationxml.py         # StationXML metadata (+ ObsPy schema check if installed)
```

## How MLA maps to miniSEED

| miniSEED needs | comes from |
|---|---|
| start time (BTIME) | MLA `timestamp` (u32 s) + `subsec` (u16) of the first record |
| sample rate | **you supply it** (`sample_rate_hz` = device ODR); `subsec` only pins the sub-second phase |
| integer counts | MLA payload split per SCHEMA field (raw, or NIC-DMD-decompressed) — *raw* counts, not the scaled physical value (calibration belongs in StationXML) |
| network/station/location | the MLA STATION table (or `station_map`) |
| channel code | the SCHEMA field name (or `channel_map`) |

Each `(station, field)` becomes one miniSEED channel. The converter assumes an
evenly-sampled, contiguous series per channel (true for synchronised acquisition,
e.g. **NIC-Quake**); gap-splitting is left to a later pass.

## StationXML metadata sidecar

miniSEED carries the *data*; FDSN tools also need the *metadata* — station
identity, coordinates, sample rate, and the count→physical sensitivity. That is
**StationXML**, and `nic_mseed/to_stationxml.py` emits it (FDSN StationXML 1.1):

```python
from nic_mseed import StationXmlExporter

StationXmlExporter(
    sample_rate_hz=100.0,        # MUST match the rate used for the miniSEED export
    network="NQ",                # same constructor args as MseedExporter
).export("quake.mla", "quake.xml")
```

It **pairs with the miniSEED**: the Network/Station/Location/Channel (NSLC) codes
and the sample rate are taken from the *same* `MseedExporter` `from_mla.py` uses,
so ObsPy / SeisComp attach the metadata to the data by construction. The MLA
prefix supplies the rest: the GPS identity (`dl_gps`) → Latitude/Longitude, the
i16 field → Elevation, the 32-byte name → `<Site><Name>`, and each DATA field's
`exp10` → an `<InstrumentSensitivity>` (overall gain = counts per physical unit =
`10**-exp10`) with the field's unit (`m_s`→`m/s`, `degC`, `Pa`, …) as input and
`count` as output.

Two honest limitations (also stated in the module and in the XML):

- **Flat response.** Each channel carries only an `<InstrumentSensitivity>` (a
  scalar DC gain) — no poles/zeros / stage cascade, because MLA does not carry a
  frequency response. Exact for flat meteo sensors; a first-order approximation
  for the MEMS seismo channels. It is **not** sufficient for true instrument
  deconvolution.
- **Coordinates need a GPS identity.** Latitude/Longitude come from a `dl_gps`
  identity. A hierarchical `dl_ident` identity carries no coordinates — pass a
  `coords={index: (lat, lon)}` override, or the emitter raises (it never silently
  writes 0,0). An unknown elevation (the 0x8000 sentinel) is written as a
  placeholder `0`.

```bash
python3 -m nic_mseed.to_stationxml quake.mla quake.xml --rate 100 --network NQ
python3 tests/test_to_stationxml.py         # emitter + pairing (+ ObsPy schema check if installed)
```

## Validation

The codec and writer round-trip through this package's own minimal reader. The
miniSEED test additionally validates against **ObsPy** when it is installed — run
`python3 tests/test_mseed.py` on a machine with ObsPy for gold-standard proof of
spec-compliance.

## Layout

```
nic_mseed/          Python: steim (codec) + mseed (writer) + from_mla (converter) + to_stationxml (metadata)
c/                  C: portable Steim-1/2 codec + miniSEED writer (+ tests, CMake)
examples/           runnable MLA → miniSEED demo
tests/              codec round-trip, writer, end-to-end converter, and StationXML tests
third_party/        vendored NIC-MLA + NIC-DMD (see VENDORED.md)
```

The Python reference is pure Python 3.10+, no external packages (ObsPy is an optional
*test-only* check). The C build is host-testable with CMake:

```bash
cmake -S c -B c/build && cmake --build c/build && ctest --test-dir c/build --output-on-failure
```

## License

MIT License — Copyright (c) 2026 NIC — Native Intellect Community

---

## Acknowledgements

To my brother for advice during the development of this project.
For technical assistance with code optimisation, to AI assistants Claude (Anthropic) and Gemini (Google).

★ Viva La Resistánce ★
