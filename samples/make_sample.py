#!/usr/bin/env python3
"""
Generate a sample NIC-MLA file for developing the Volkov Data GUI.

Simulates a small weather-station datalogger: a few stations in a ~5 km LoRa
range, each reporting several channels (temperature / humidity / pressure) over
a span of time. Payloads are raw little-endian values; metadata (time, station,
channel, type) lives in the log — exactly the normalization the format is built
around.

Usage:  python3 samples/make_sample.py [out.mla]
"""
from __future__ import annotations

import math
import os
import struct
import sys

# import the vendored MLA reference
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "third_party", "nic_mla"))
from nic_mla import MlaCore, MlaPosixHAL, ENC_RAW, CLASS_MEASURE, CLASS_EVENT  # noqa: E402

# rec_type = high nibble (class) | low nibble (encoding)
RT_MEASURE = CLASS_MEASURE | ENC_RAW
RT_EVENT = CLASS_EVENT | ENC_RAW

# channels: id -> (name, unit, base value, swing)
CHANNELS = {
    1: ("temperature", "°C", 12.0, 8.0),
    2: ("humidity", "%", 65.0, 20.0),
    3: ("pressure", "hPa", 1013.0, 12.0),
}
STATIONS = [1, 2, 3]  # three LoRa nodes

T0 = 1_748_000_000  # base unix time (~2025)
STEP = 900  # 15 min between samples, per the brief's cadence
N_ROUNDS = 60  # 60 rounds × 3 stations × 3 channels ≈ 540 records


def value(ch: int, station: int, t: int) -> float:
    name, _unit, base, swing = CHANNELS[ch]
    # smooth daily-ish wave + a small per-station offset
    phase = (t // STEP) / 12.0
    return base + swing * math.sin(phase) * 0.5 + station * 0.7


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "weather.mla"
    )
    hal = MlaPosixHAL.create(out, file_size=256 * 1024)  # 256 KB container
    with hal:
        core = MlaCore(hal)
        core.format(file_size=256 * 1024, index_kb=4, checkpoint_shift=6)

        t = T0
        for r in range(N_ROUNDS):
            for station in STATIONS:
                for ch in CHANNELS:
                    v = value(ch, station, t)
                    payload = struct.pack("<f", v)  # 4-byte little-endian float
                    core.append(t, station, ch, payload, rec_type=RT_MEASURE)
                # occasional event record (e.g. a status ping)
                if r % 20 == 0:
                    core.append(t, station, 0, b"PING", rec_type=RT_EVENT)
            t += STEP

        core.sync()
        count = core.record_count
    size = os.path.getsize(out)
    print(f"Wrote {out}  ({size} B, {count} records)")


if __name__ == "__main__":
    main()
