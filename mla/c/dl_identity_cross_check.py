#!/usr/bin/env python3
"""
dl_identity_cross_check.py  —  byte-exact C↔Python check for the NIC-MLA
datalogger 8-byte station identity. Proves the C encoders in c/dl_identity.h
produce the same bytes as the Python reference (tools/mla_datalogger.py), so the
embedded master and the host tools share one on-disk identity.

Run (from the mla/ root):
    cc -std=c99 -O2 c/dl_identity_test.c -I c -o /tmp/dlid
    /tmp/dlid /tmp/dlid.bin
    python3 c/dl_identity_cross_check.py /tmp/dlid.bin

Python 3.10+  |  MIT  |  ★ Viva La Resistánce ★
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "tools"))

from mla_datalogger import dl_gps, dl_ident, dl_elev, dl_elev_decode

_passed = _failed = 0


def check(msg, cond):
    global _passed, _failed
    print(f"  {'PASS' if cond else 'FAIL'}  {msg}")
    if cond:
        _passed += 1
    else:
        _failed += 1


def main(path):
    data = open(path, "rb").read()
    c_gps, c_ident = data[0:8], data[8:16]
    c_e235, c_eneg, c_ezero, c_eunk = (data[16:18], data[18:20],
                                       data[20:22], data[22:24])

    print("NIC-MLA datalogger station identity — C→Python cross-check\n")
    check("dl_gps bytes match Python (50.0875, 14.4213)",
          c_gps == dl_gps(50.0875, 14.4213))
    check("dl_ident bytes match Python (region 55, number 25000)",
          c_ident == dl_ident(number=25000, region=55, reserved=0xFFFF))
    check("dl_elev bytes match Python (+235 m)", c_e235 == dl_elev(235))
    check("dl_elev bytes match Python (-412 m)", c_eneg == dl_elev(-412))
    check("dl_elev bytes match Python (0 m)", c_ezero == dl_elev(0))
    check("dl_elev sentinel matches Python (0x8000 = unknown)",
          c_eunk == dl_elev(None) and dl_elev_decode(c_eunk) is None)

    print(f"\nResult: {_passed}/{_passed + _failed} PASS  |  {_failed} FAIL")
    print("C↔Python byte-exact ✓  ★ Viva La Resistánce ★" if not _failed
          else "MISMATCH")
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/dlid.bin"))
