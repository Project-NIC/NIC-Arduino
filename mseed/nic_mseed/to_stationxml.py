# SPDX-License-Identifier: MIT
"""
to_stationxml.py — the metadata sidecar: NIC-MLA → FDSN StationXML 1.1.

``from_mla.py`` writes the miniSEED DATA records (raw integer counts). FDSN
tools (ObsPy / SeisComp) also need the **metadata** that pairs with those
records — station identity, coordinates, sample rate, and the count→physical
sensitivity. That metadata is **StationXML**, and this module emits it.

The MLA prefix already carries everything needed:
  • the 8-byte STATION identity            → the SEED network/station/location
    codes (the SAME derivation ``from_mla.py`` uses — see the pairing note);
  • a GPS identity (``dl_gps``)            → station/channel Latitude/Longitude;
  • the i16 elevation field                → <Elevation> (metres);
  • the 32-byte station name               → <Site><Name>;
  • each DATA field's SCHEMA descriptor    → one <Channel> (code + units + the
    count→physical scale ``exp10``).

THE PAIRING CONTRACT (why this reuses ``from_mla.py``)
------------------------------------------------------
FDSN tools match metadata to data by the Network/Station/Location/Channel
(NSLC) codes AND the channel sample rate. If StationXML and miniSEED disagree
on any of these, the metadata silently fails to attach. To make that
impossible, this emitter does NOT re-derive any of those — it drives the very
same ``MseedExporter`` that ``from_mla.py`` uses, and reads the codes and the
rate straight back out of it (``_station_codes`` / ``_channel_code`` /
``rate``). Same input + same code path ⇒ identical NSLC + rate, by
construction. Build the exporter once and hand it to both halves.

HONEST LIMITATIONS (read before trusting the output)
----------------------------------------------------
  • FLAT RESPONSE. Each channel carries only an <InstrumentSensitivity> (a
    single overall gain = counts per physical unit, at frequency 0) — there is
    NO poles/zeros / stage cascade. MLA does not carry a frequency response, so
    one cannot be emitted. This is exact for flat meteo sensors (temperature,
    pressure, …) and a first-order (DC-gain-only) approximation for the MEMS
    seismo channels: it lets a tool read counts and apply the scalar gain, but
    it does NOT support true instrument deconvolution. An XML comment on every
    channel says so.
  • COORDINATES NEED A GPS IDENTITY. StationXML requires Latitude/Longitude on
    every Station and Channel. They come from ``dl_gps_decode`` when the
    identity is the GPS form. The hierarchical ``dl_ident`` form (region /
    number / kind) carries NO coordinates — for such files you MUST pass a
    ``coords`` override per station, otherwise this raises (it never silently
    emits 0,0).
  • UNKNOWN ELEVATION. The i16 elevation sentinel 0x8000 means "unknown". Since
    StationXML requires an <Elevation>, an unknown elevation is emitted as
    ``<Elevation>0</Elevation>`` (a placeholder, NOT a measured 0 m); a real
    elevation is carried through verbatim.

Pure host code, no external packages (ObsPy is an optional test-only check). A
sibling of the CSV/SQLite exporters and of ``from_mla.py``; it never touches
the on-disk MLA format and reads MLA only through the vendored ``nic_mla``.
"""
from __future__ import annotations

import datetime as _dt
import struct
from xml.sax.saxutils import escape as _xml_escape

from nic_mla import MlaCore, MlaPosixHAL
from mla_schema import (
    mla_read_schema,
    mla_read_stations,
    mla_split_station,
    dl_gps_decode,
)

from .from_mla import MseedExporter

_FDSN_NS = "http://www.fdsn.org/xml/station/1"
_SCHEMA_VERSION = "1.1"

# ── MLA UNIT vocabulary → StationXML unit names ─────────────────────────────
#  The MlaField.unit keys (from mla_schema.UNITS) are SI-ish tokens; StationXML
#  wants conventional unit strings. Map the ones that differ; everything else
#  passes through unchanged (degC, Pa, hPa, V, A, W, count, lux, mm, ppm, …).
_UNIT_NAME = {
    "m_s": "m/s",      # velocity (MEMS seismo)
    "m_s2": "m/s**2",  # acceleration (ADXL355 / ICM seismo) — FDSN unit string
    "pct": "%",        # percent
    "unix_s": "s",     # Unix seconds → seconds
    "raw": "count",    # untyped/dimensionless → counts
    "id": "count",     # identifier → counts (dimensionless)
}


def _unit_name(unit: str) -> str:
    """StationXML <Name> for an MLA UNIT-vocabulary token."""
    return _UNIT_NAME.get(unit, unit)


def _iso_utc(when: _dt.datetime | None = None) -> str:
    """UTC ISO-8601 with a trailing Z (StationXML's datetime form)."""
    if when is None:
        when = _dt.datetime.now(_dt.timezone.utc)
    elif when.tzinfo is not None:
        when = when.astimezone(_dt.timezone.utc)
    return when.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"


def _is_gps_identity(identity: bytes) -> bool:
    """Heuristic: does this 8-byte identity look like a ``dl_gps`` lat/lon?

    GPS packs 2× i32 (degrees × 1e7), so |lat| ≤ 90 and |lon| ≤ 180 after
    decode. The hierarchical ``dl_ident`` form is 4× u16; its low 16 bits being
    the region make a tiny lat plausible, but the high halves (kind/reserved)
    almost never land inside ±90/±180 simultaneously — and we additionally
    reject the all-zero identity, which both forms share. Callers who want to be
    certain pass an explicit ``coords`` override (which skips this guess).
    """
    if len(identity) != 8 or identity == b"\x00" * 8:
        return False
    try:
        lat, lon = dl_gps_decode(identity)
    except struct.error:
        return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def _num(x: float) -> str:
    """A StationXML numeric value as a plain decimal (no scientific notation).

    StationXML's double type accepts ``1e-06``, but a plain decimal reads better
    and is unambiguous across the whole exp10 range. Starts from repr()'s
    SHORTEST round-tripping form and just shifts the decimal point (pure string
    work — no re-quantisation, so no ``…999`` artefacts), then trims.
    """
    r = repr(float(x))
    if "e" not in r and "E" not in r:
        return r
    sign = ""
    if r[0] in "+-":
        sign, r = ("" if r[0] == "+" else r[0]), r[1:]
    mant, exp = r.lower().split("e")
    exp = int(exp)
    intp, _, frac = mant.partition(".")
    digits = intp + frac
    point = len(intp) + exp                      # position of the decimal point
    if point <= 0:
        s = "0." + "0" * (-point) + digits
    elif point >= len(digits):
        s = digits + "0" * (point - len(digits))
    else:
        s = digits[:point] + "." + digits[point:]
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return sign + (s or "0")


class StationXmlExporter:
    """Emit FDSN StationXML 1.1 for the stations/channels of a NIC-MLA file.

    The NSLC codes and the channel sample rate are taken from the SAME
    ``MseedExporter`` configuration ``from_mla.py`` uses, so the emitted
    metadata pairs with the miniSEED byte-for-byte on the identifiers. Pass the
    same constructor arguments you pass ``MseedExporter`` (``sample_rate_hz``,
    ``network``, ``location``, ``channel_map``, ``station_map``, …); they are
    forwarded verbatim.

    Extra StationXML-only arguments:
      source        — <Source> text (default "NIC").
      module        — <Module> text (default "NIC-MSEED to_stationxml").
      coords        — {mla_station_index: (lat_deg, lon_deg[, elev_m])} override,
                      required for stations whose identity is NOT a GPS identity
                      (hierarchical ``dl_ident`` form carries no coordinates).
                      A 3rd element overrides the elevation too.
      start_date    — channel/station startDate (ISO-8601 str or datetime);
                      default: derived from each station's first record time, or
                      ``created`` when no record time is available.
      created       — <Created>/<CreationDate> timestamp (default: now, UTC).
    """

    def __init__(self, *, sample_rate_hz: float,
                 source: str = "NIC",
                 module: str = "NIC-MSEED to_stationxml",
                 coords: dict | None = None,
                 start_date=None,
                 created: _dt.datetime | None = None,
                 **mseed_kw):
        # Reuse from_mla.py's mapper unchanged → identical NSLC + rate.
        self._ex = MseedExporter(sample_rate_hz=sample_rate_hz, **mseed_kw)
        self.source = source
        self.module = module
        self.coords = dict(coords or {})
        self.start_date = start_date
        self.created = created

    # ── coordinate / elevation resolution ───────────────────────────────────
    def _station_coords(self, idx: int, identity: bytes,
                        elev_field: int | None) -> tuple[float, float, float]:
        """Return (lat, lon, elev_m) for one station, or raise a clear error.

        Priority: an explicit ``coords`` override, else a GPS identity decode.
        The elevation is the station's i16 field (override's 3rd element wins);
        an unknown/0x8000 elevation becomes 0.0 (a placeholder — StationXML
        requires the element).
        """
        elev = 0.0 if elev_field is None else float(elev_field)
        if idx in self.coords:
            c = self.coords[idx]
            if len(c) >= 3 and c[2] is not None:
                return float(c[0]), float(c[1]), float(c[2])
            return float(c[0]), float(c[1]), elev
        if _is_gps_identity(identity):
            lat, lon = dl_gps_decode(identity)
            return lat, lon, elev
        raise ValueError(
            f"station index {idx}: identity is not a GPS identity and has no "
            f"coordinates — StationXML requires Latitude/Longitude. Pass a "
            f"coords override, e.g. coords={{{idx}: (lat_deg, lon_deg)}}"
            f"{' or (lat, lon, elev_m)' if elev_field is None else ''}."
        )

    # ── XML building blocks ──────────────────────────────────────────────────
    @staticmethod
    def _el(tag: str, text, *, indent: int, **attrs) -> str:
        pad = "  " * indent
        a = "".join(f' {k}="{_xml_escape(str(v), {chr(34): "&quot;"})}"'
                    for k, v in attrs.items() if v is not None)
        if text is None:
            return f"{pad}<{tag}{a}/>"
        return f"{pad}<{tag}{a}>{_xml_escape(str(text))}</{tag}>"

    def _channel_xml(self, field, fi: int, *, loc: str,
                     lat: float, lon: float, elev: float,
                     start: str, created: str) -> list[str]:
        cha = self._ex._channel_code(field, fi)          # SAME code as miniSEED
        rate = self._ex.rate                             # SAME rate as miniSEED
        # Overall gain = counts per physical unit = inverse of the field's
        # scale (physical = (raw + offset) * mantissa * 10**exp10; the additive
        # offset is ignored for the sensitivity value, as documented). The mantissa
        # (MLA v2, D50) lets the gain be the REAL sensitivity (e.g. the ADXL355's
        # 26104 counts/(m/s²)), not just a power of ten. mantissa 0 ≡ 1.
        _mant = getattr(field, "mantissa", 1) or 1
        sensitivity = 1.0 / (_mant * 10.0 ** field.exp10)
        in_unit = _unit_name(field.unit)
        E = self._el
        out = [f'    <Channel code="{cha}" locationCode="{loc}" '
               f'startDate="{start}">']
        out += [
            E("Latitude", _num(lat), indent=3),
            E("Longitude", _num(lon), indent=3),
            E("Elevation", _num(elev), indent=3),
            E("Depth", "0", indent=3),
            E("SampleRate", _num(rate), indent=3),
            "      <!-- Flat response: InstrumentSensitivity only (overall "
            "count->physical gain at DC). MLA carries no poles/zeros, so no "
            "stage cascade is emitted: exact for flat meteo sensors, a "
            "first-order (DC-gain) approximation for MEMS seismo channels. "
            "Not suitable for true instrument deconvolution. -->",
            "      <Response>",
            "        <InstrumentSensitivity>",
            E("Value", _num(sensitivity), indent=5),
            E("Frequency", "0", indent=5),
            "          <InputUnits>",
            E("Name", in_unit, indent=6),
            "          </InputUnits>",
            "          <OutputUnits>",
            E("Name", "count", indent=6),
            "          </OutputUnits>",
            "        </InstrumentSensitivity>",
            "      </Response>",
            "    </Channel>",
        ]
        return out

    def _station_xml(self, idx: int, stations, data_fields,
                     *, created: str) -> list[str]:
        record = stations[idx - 1]
        identity, elev_field, name = mla_split_station(record)
        # Same derivation from_mla.py uses (it indexes stations[idx-1]) → the
        # Station/Location codes match the miniSEED byte-for-byte.
        _net, sta, loc = self._ex._station_codes(idx, stations)
        lat, lon, elev = self._station_coords(idx, identity, elev_field)
        start = self._station_start(idx, created)
        site = name or sta
        E = self._el
        out = [f'  <Station code="{sta}" startDate="{start}">']
        out += [
            E("Latitude", _num(lat), indent=2),
            E("Longitude", _num(lon), indent=2),
            E("Elevation", _num(elev), indent=2),
            "    <Site>",
            E("Name", site, indent=3),
            "    </Site>",
            E("CreationDate", created, indent=2),
        ]
        for fi, field in enumerate(data_fields):
            out += self._channel_xml(field, fi, loc=loc, lat=lat, lon=lon,
                                     elev=elev, start=start, created=created)
        out.append("  </Station>")
        return out

    # ── start-date resolution ────────────────────────────────────────────────
    def _station_start(self, idx: int, created: str) -> str:
        if self.start_date is not None:
            return self.start_date if isinstance(self.start_date, str) \
                else _iso_utc(self.start_date)
        t = self._first_ts.get(idx)
        if t is not None:
            return _iso_utc(_dt.datetime.fromtimestamp(t, _dt.timezone.utc))
        return created

    # ── main ────────────────────────────────────────────────────────────────
    def to_string(self, mla_path: str) -> str:
        """Read ``mla_path`` and return the StationXML document as a string."""
        with MlaPosixHAL(mla_path) as hal:
            core = MlaCore(hal)
            core.mount()
            prefix = core._prefix.to_bytes()
            data_fields = mla_read_schema(prefix)[1]
            if not data_fields:
                raise ValueError("MLA file has no SCHEMA — cannot map channels")
            stations = mla_read_stations(prefix)
            if not stations:
                raise ValueError("MLA file has no STATION table — cannot emit "
                                 "StationXML (no station identity/coordinates)")
            # Earliest record timestamp per station, for startDate defaults.
            self._first_ts: dict[int, int] = {}
            for rec, _payload in core:                  # oldest first
                self._first_ts.setdefault(rec.station, rec.timestamp)

        created = _iso_utc(self.created)
        net = self._ex.network

        body: list[str] = []
        for i in range(1, len(stations) + 1):
            body += self._station_xml(i, stations, data_fields, created=created)

        head = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<FDSNStationXML xmlns="{_FDSN_NS}" '
            f'schemaVersion="{_SCHEMA_VERSION}">',
            f"  <Source>{_xml_escape(self.source)}</Source>",
            f"  <Module>{_xml_escape(self.module)}</Module>",
            f"  <Created>{created}</Created>",
            f'  <Network code="{_xml_escape(net)}">',
        ]
        tail = ["  </Network>", "</FDSNStationXML>", ""]
        return "\n".join(head + body + tail)

    def export(self, mla_path: str, out_path: str) -> dict:
        """Read ``mla_path``, write StationXML to ``out_path``. Returns stats."""
        xml = self.to_string(mla_path)
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(xml)
        # Count stations/channels for the stats dict (cheap re-parse-free count).
        n_sta = xml.count("<Station ")
        n_cha = xml.count("<Channel ")
        return {"stations": n_sta, "channels": n_cha,
                "bytes": len(xml.encode("utf-8")), "out": out_path}


def export_mla_to_stationxml(mla_path: str, out_path: str, *,
                             sample_rate_hz: float, **kw) -> dict:
    """Convenience wrapper: one-shot MLA → StationXML conversion."""
    return StationXmlExporter(sample_rate_hz=sample_rate_hz, **kw).export(
        mla_path, out_path)


# ── CLI ─────────────────────────────────────────────────────────────────────
def _main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        prog="to_stationxml",
        description="Emit FDSN StationXML 1.1 metadata for a NIC-MLA file "
                    "(pairs with the miniSEED from from_mla.py via matching "
                    "NSLC codes + sample rate).")
    ap.add_argument("mla", help="input .mla file")
    ap.add_argument("out", help="output .xml file (StationXML)")
    ap.add_argument("--rate", type=float, required=True,
                    help="sample rate in Hz (device ODR; MUST match the rate "
                         "used for the miniSEED export)")
    ap.add_argument("--network", default="XX", help="SEED network code (<=2 ch)")
    ap.add_argument("--location", default="", help="SEED location code (<=2 ch)")
    ap.add_argument("--source", default="NIC", help="<Source> text")
    args = ap.parse_args(argv)

    stats = export_mla_to_stationxml(
        args.mla, args.out, sample_rate_hz=args.rate,
        network=args.network, location=args.location, source=args.source)
    print(f"[stationxml] {stats['out']}  ({stats['bytes']} B, "
          f"{stats['stations']} stations, {stats['channels']} channels)")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(_main(sys.argv[1:]))
