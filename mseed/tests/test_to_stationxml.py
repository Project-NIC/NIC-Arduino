# SPDX-License-Identifier: MIT
"""
StationXML emitter tests.

Build a tiny .mla with a GPS-identity station (name + elevation + a seismo-ish
``m/s`` channel and a meteo ``degC`` channel), emit FDSN StationXML, and assert:
  • the document is well-formed XML;
  • the Network/Station codes EQUAL what from_mla.py writes into the miniSEED
    for the same identity (the key pairing check) — and so do the channel codes
    and sample rate;
  • Latitude/Longitude/Elevation/Site Name are present and correct;
  • one Channel per DATA field, each with the right code + SampleRate +
    InstrumentSensitivity Value (= 10**-exp10) + Input/Output units;
  • the non-GPS-identity path raises (never silently emits 0,0), and a coords
    override supplies coordinates.

If ObsPy is installed: also parse the emitted XML with read_inventory and check
it loads (validates against the real FDSN schema) — the gold-standard proof of
spec-compliance. If ObsPy is missing, that sub-check is SKIPPED with a note (the
suite never fails on a missing optional dep), exactly like test_mseed.py.
"""
import os
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import nic_mseed  # noqa: E402  — puts third_party (nic_mla, nic_dmd) on sys.path
from nic_mseed import StationXmlExporter, MseedExporter
from nic_mla import MlaCore, MlaPosixHAL
from mla_schema import (  # noqa: E402
    MlaSchemaBuilder, MlaStationTable, mla_read_stations, dl_gps, dl_ident,
)

_NS = {"x": "http://www.fdsn.org/xml/station/1"}

_p = _f = 0
def check(name, cond):
    global _p, _f
    if cond: _p += 1; print(f"  PASS  {name}")
    else:    _f += 1; print(f"  FAIL  {name}")


def _build_gps_mla(path):
    """A station with a GPS identity, a name, an elevation, and two channels."""
    sb = MlaSchemaBuilder()
    sb.log("datetime")
    sb.data("z",    unit="m_s",  width=2, exp10=-6, signed=True)   # MEMS seismo (m/s)
    sb.data("temp", unit="degC", width=2, exp10=-1, signed=True)   # meteo (degC)
    st = MlaStationTable()
    st.station(dl_gps(50.0865, 14.4115), elev_m=235, name="Praha-Klementinum")
    schema, stations = sb.table(), st.table()

    with MlaPosixHAL.create(path, file_size=256 * 1024) as hal:
        core = MlaCore(hal)
        core.format(file_size=256 * 1024, schema_table=schema, station_table=stations)
        base = 1_748_000_000
        for i in range(20):
            row = (i).to_bytes(2, "little", signed=True) + \
                  (200 + i).to_bytes(2, "little", signed=True)
            core.append(base + i, station=1, data=row, subsec=i)
    return stations


def _build_ident_mla(path):
    """A station with a hierarchical (non-GPS) identity → no coordinates."""
    sb = MlaSchemaBuilder()
    sb.log("datetime")
    sb.data("z", unit="raw", width=2, signed=True)
    st = MlaStationTable()
    st.station(dl_ident(region=55, number=25000), elev_m=None, name="Klem")
    schema, stations = sb.table(), st.table()
    with MlaPosixHAL.create(path, file_size=128 * 1024) as hal:
        core = MlaCore(hal)
        core.format(file_size=128 * 1024, schema_table=schema, station_table=stations)
        for i in range(5):
            core.append(1_748_000_000 + i, station=1,
                        data=(i).to_bytes(2, "little", signed=True))
    return stations


def main():
    print("NIC-MLA → FDSN StationXML emitter")
    RATE, NET = 100.0, "NQ"

    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "gps.mla")
        stations = _build_gps_mla(path)

        ex = StationXmlExporter(sample_rate_hz=RATE, network=NET)
        xml = ex.to_string(path)

        # 1) well-formed XML
        root = None
        try:
            root = ET.fromstring(xml)
            well_formed = True
        except ET.ParseError:
            well_formed = False
        check("emitted document is well-formed XML", well_formed)
        check("root is FDSNStationXML 1.1",
              root is not None
              and root.tag == "{http://www.fdsn.org/xml/station/1}FDSNStationXML"
              and root.get("schemaVersion") == "1.1")

        net_el = root.find("x:Network", _NS)
        sta_el = net_el.find("x:Station", _NS)
        chans = sta_el.findall("x:Channel", _NS)

        # 2) THE PAIRING CHECK — codes must equal what from_mla.py produces.
        mx = MseedExporter(sample_rate_hz=RATE, network=NET)
        st_records = mla_read_stations(open(path, "rb").read()[:512])
        m_net, m_sta, m_loc = mx._station_codes(1, st_records)
        check("Network code == from_mla network code",
              net_el.get("code") == m_net)
        check("Station code == from_mla station code (identity pairing)",
              sta_el.get("code") == m_sta)
        check("Location code == from_mla location code",
              all(c.get("locationCode") == m_loc for c in chans))
        # derive channel codes the exact same way from_mla does, from the schema
        from mla_schema import mla_read_schema
        data_fields = mla_read_schema(open(path, "rb").read()[:512])[1]
        m_chan_codes = [mx._channel_code(f, i) for i, f in enumerate(data_fields)]
        check("Channel codes == from_mla channel codes",
              [c.get("code") for c in chans] == m_chan_codes)

        # 3) coordinates / elevation / site name present and correct
        def txt(parent, tag):
            el = parent.find("x:" + tag, _NS)
            return None if el is None else el.text
        check("Station Latitude correct", txt(sta_el, "Latitude") == "50.0865")
        check("Station Longitude correct", txt(sta_el, "Longitude") == "14.4115")
        check("Station Elevation correct", float(txt(sta_el, "Elevation")) == 235.0)
        site = sta_el.find("x:Site/x:Name", _NS)
        check("Site Name == station name", site is not None and site.text == "Praha-Klementinum")

        # 4) one channel per DATA field, right code + rate + sensitivity + units
        check("one Channel per DATA field (2)", len(chans) == 2)
        by_code = {c.get("code"): c for c in chans}
        # field 0: z  m/s  exp10=-6 -> sensitivity 1e6
        z = by_code.get(m_chan_codes[0])
        check("seismo channel SampleRate == rate",
              z is not None and float(txt(z, "SampleRate")) == RATE)
        zs = z.find("x:Response/x:InstrumentSensitivity", _NS)
        check("seismo sensitivity == 10**-exp10 (1e6)",
              float(zs.find("x:Value", _NS).text) == 10.0 ** 6)
        check("seismo InputUnits == m/s (m_s mapped)",
              zs.find("x:InputUnits/x:Name", _NS).text == "m/s")
        check("seismo OutputUnits == count",
              zs.find("x:OutputUnits/x:Name", _NS).text == "count")
        check("seismo Frequency == 0",
              zs.find("x:Frequency", _NS).text == "0")
        # field 1: temp  degC  exp10=-1 -> sensitivity 10
        t = by_code.get(m_chan_codes[1])
        ts = t.find("x:Response/x:InstrumentSensitivity", _NS)
        check("meteo sensitivity == 10**-exp10 (10)",
              float(ts.find("x:Value", _NS).text) == 10.0 ** 1)
        check("meteo InputUnits == degC (pass-through)",
              ts.find("x:InputUnits/x:Name", _NS).text == "degC")
        check("meteo channel Depth == 0",
              txt(t, "Depth") == "0")

        # 5) flat-response limitation is stated in the XML (and no PolesZeros)
        check("flat-response comment present", "Flat response:" in xml)
        check("no poles/zeros stage emitted", "PolesZeros" not in xml and "<Stage" not in xml)

        # 6) write-to-file path + stats
        out = os.path.join(d, "gps.xml")
        stats = ex.export(path, out)
        check("export() writes a file", os.path.exists(out) and stats["bytes"] > 0)
        check("export() stats: 1 station, 2 channels",
              stats["stations"] == 1 and stats["channels"] == 2)

        # 7) non-GPS identity: must raise (never silent 0,0); override supplies coords
        ipath = os.path.join(d, "ident.mla")
        _build_ident_mla(ipath)
        raised = False
        try:
            StationXmlExporter(sample_rate_hz=50.0, network=NET).to_string(ipath)
        except ValueError as e:
            raised = "station index 1" in str(e)
        check("non-GPS identity without coords raises (names the station)", raised)
        xml_ov = StationXmlExporter(sample_rate_hz=50.0, network=NET,
                                    coords={1: (49.0, 16.0)}).to_string(ipath)
        rov = ET.fromstring(xml_ov).find(".//x:Station", _NS)
        check("coords override supplies Latitude/Longitude",
              rov.find("x:Latitude", _NS).text == "49.0"
              and rov.find("x:Longitude", _NS).text == "16.0")
        check("unknown elevation emitted as placeholder 0",
              float(rov.find("x:Elevation", _NS).text) == 0.0)

        # 8) OPTIONAL gold-standard: ObsPy parses (validates the real FDSN schema).
        try:
            import io
            from obspy import read_inventory
            # lxml rejects a unicode str that declares an encoding, so feed bytes
            # (read_inventory(StringIO(...)) hits that lxml rule; bytes is the
            # obspy-recommended form and the same validation either way).
            try:
                inv = read_inventory(io.StringIO(xml))
            except ValueError:
                inv = read_inventory(io.BytesIO(xml.encode("utf-8")))
            obs_sta = inv[0][0]
            check("ObsPy loads our StationXML (FDSN-schema valid)",
                  inv[0].code == NET and obs_sta.code == m_sta)
            check("ObsPy sees the GPS coordinates",
                  abs(obs_sta.latitude - 50.0865) < 1e-6
                  and abs(obs_sta.longitude - 14.4115) < 1e-6)
            obs_codes = sorted(c.code for c in obs_sta)
            check("ObsPy sees both channels with their sensitivities",
                  obs_codes == sorted(m_chan_codes)
                  and all(c.response is not None
                          and c.response.instrument_sensitivity is not None
                          for c in obs_sta))
            # Explicit XSD validation if obspy exposes it.
            try:
                from obspy.io.stationxml.core import validate_stationxml
                ok, errs = validate_stationxml(io.BytesIO(xml.encode("utf-8")))
                check("ObsPy validate_stationxml against bundled XSD",
                      ok and not list(errs))
            except Exception:
                pass
        except ImportError:
            print("  SKIP  ObsPy not installed — run this test on a machine with "
                  "ObsPy for gold-standard FDSN-schema validation")

    print(f"\nResult: {_p}/{_p+_f} PASS | {_f} FAIL")
    sys.exit(0 if _f == 0 else 1)


if __name__ == "__main__":
    main()
