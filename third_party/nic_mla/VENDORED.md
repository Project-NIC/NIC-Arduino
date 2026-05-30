# Vendored: NIC-MLA

This directory is a vendored copy of the **NIC-MLA** project (Matroshka Logging
Archive) — the single-file container format that the data logger writes and that
Volkov Data reads/browses.

- **Origin:** NIC-MLA (upstream project), imported as the source of truth for the
  on-medium format.
- **License:** MIT (see file headers / upstream).
- **Why vendored:** the desktop GUI consumes MLA directly via the Python
  reference (`nic_mla.py`, `nic_mla_archive.py`), which is kept byte-identical to
  the C library (`c/`) via the cross-compat test. Keeping it in-tree means one
  source of truth lives next to the app, with no submodule/setup friction.

## What's here

- `nic_mla.py` — complete Python reference (`MlaCore`: format / mount / append /
  read_record / iterate / scan / query / recover). **Primary entry point for the GUI.**
- `nic_mla_archive.py` — `MlaArchive` (file rotation) + host-side `query()` filter.
- `c/` — the byte-identical C core (write-only for ATmega, complete for ARM/PC).
  Kept for the future embedded / remote-viewer port; the desktop does not build it.
- `DESIGN-MLA-v2*.md` — full format specification.

## Updating

Re-copy from upstream and re-run `python3 nic_mla_test.py` (should report all PASS).
Do not edit vendored files locally — fix upstream and re-vendor to avoid drift.
