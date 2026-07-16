# SPDX-License-Identifier: MIT
"""
NIC-IAGA — export NIC-MLA magnetometer logs to IAGA-2002.

The geomagnetism-interop bridge of the NIC ecosystem: IAGA-2002 is the exchange
format of ground magnetometry — INTERMAGNET's own, and what **SuperMAG** ingests
from its ~600 variometers worldwide. NIC-Gauss is a variometer, so its data goes
out declared ``Data Type: variation``; the absolute baseline stays the
observatories' job (the variometer doctrine, nic-station ``gauss/README.md``).

    .mla  ──▶  [NIC-DMD decode if compressed]  ──▶  calibrated nT per component  ──▶  IAGA-2002

Two layers, like the rest of the ecosystem:
  • ``iaga``     — container-agnostic core (rows of nT floats → text, + a
                   round-trip reader for tests).
  • ``from_mla`` — the converter that wires NIC-MLA + NIC-DMD to it and applies
                   the SCHEMA calibration (physical = (raw + offset) · 10^exp10).

The vendored dependencies live under ``third_party/`` (the same way NIC-MSEED,
NIC-GLUE-IN and NIC-VDE vendor them). Importing this package puts them on
``sys.path``.
"""
from __future__ import annotations

import os
import sys

# ── Make the vendored libraries importable ──────────────────────────────────
_TP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "third_party"))
for _p in (os.path.join(_TP, "nic_mla"), os.path.join(_TP, "nic_dmd")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from .iaga import (write_iaga2002, parse_iaga2002,  # noqa: E402
                   MISSING, NOT_OBSERVED)
from .from_mla import IagaExporter, export_mla_to_iaga  # noqa: E402

__all__ = [
    "IagaExporter", "export_mla_to_iaga",
    "write_iaga2002", "parse_iaga2002",
    "MISSING", "NOT_OBSERVED",
]

__version__ = "0.1.0"
