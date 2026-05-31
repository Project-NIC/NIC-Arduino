# Channel conversion table — design proposal

> Status: **PROPOSAL — needs sign-off on the binary layout before any code.**
> This is a one-way door: once a station's processor starts writing this table,
> the byte layout is hard to change. Confirm the layout first.

## Problem

The MLA kernel deliberately does **not** know what a payload means. The spec
(§4.1) says: *"which byte is temperature, which is humidity is determined by the
station+channel metadata, not by the type byte."* But that metadata is **stored
nowhere**. Today `MlaBackend.decode_value` just *guesses* from payload length
(4 bytes → float, text → text). Export to CSV/SQL inherits the guess, so we ship
**raw, untranslated** values that nobody actually wants in SQL.

## Where it lives — the prefix free space

The 512 B prefix has **~475 B of zeroed, CRC-covered free space** from byte 34
to 509 (`[34] padding 0x00 … to byte 509`). It was reserved exactly for
"settings that travel with the file". The conversion table goes here. No data
block is touched — append-only stays intact; only the prefix is rewritten (and
its CRC recomputed).

The station's processor writes this table at format time, so the file is
**self-describing**: it carries the meaning of its own data wherever it goes.

## Binary layout (everything binary — the MCU only writes, the host renders)

The table is a small header + a flat array of fixed-size channel descriptors,
placed at prefix offset **34**.

```
Conversion-table region (inside prefix, offset 34..509)

[34] tbl_magic    2 B   0xCB 0x01  ("conversion table v1") — 0x0000 = absent
[36] tbl_count    1 B   number of channel descriptors (0..29)
[37] tbl_flags    1 B   reserved (0)
[38] descriptors  count × 16 B   (see below)
...                up to byte 509 → max 29 descriptors fit (472 B / 16)
```

### Channel descriptor (16 B, fixed)

```
[0]  station    2 B  uint16 LE   which station this row describes
[2]  channel    2 B  uint16 LE   which channel within the station
[4]  dtype      1 B              how to read the payload bytes (enum below)
[5]  scale_exp  1 B  int8        real value = raw × 10^scale_exp
                                 (e.g. -2 → ×0.01, matches the ×100 sensor convention)
[6]  unit       4 B  ASCII       null-padded, e.g. "degC" "%" "hPa" "V"
[10] name       6 B  ASCII       null-padded, e.g. "Temp" "Humid" "Press"
```

`dtype` enum (1 B):

```
0x00 RAW       as-is bytes (no conversion; viewer shows hex)
0x01 U8        uint8
0x02 I8        int8
0x03 U16       uint16 LE
0x04 I16       int16  LE
0x05 U32       uint32 LE
0x06 I32       int32  LE
0x07 F32       float32 LE (scale_exp ignored)
0x08 TEXT      UTF-8 string (scale_exp/unit ignored)
```

### Multiple station types (your idea)

Because each descriptor carries its own `station` field, the table naturally
holds rows for **several station types** in one file. A datalogger collecting
from up to ~4 station types just writes one descriptor block per (station,
channel) pair. On read, a record's `station` field (LOG offset 8) + `channel`
(offset 10) selects the matching descriptor; no match → fall back to today's
length-based guess (RAW/hex).

29 descriptors is plenty: e.g. 4 stations × 7 channels = 28.

## How the host uses it

1. **Viewer / F4 Values** — `decode_value` looks up `(station, channel)` in the
   table, reads the payload per `dtype`, applies `× 10^scale_exp`, appends
   `unit`. Falls back to the current guess when there's no descriptor.
2. **Export (CSV / SQL)** — a new choice at export time: **raw** bytes vs.
   **translated** values (default = translated, since nobody wants raw in SQL).
   Same spirit as how the export filename is already built from metadata.
3. **F4 as table editor** — **only inside an open `.mla`**: F4 opens a simple
   editor over the descriptors (like editing a text file), writes the table back
   into the prefix, recomputes the prefix CRC. When F4 is pressed on an `.mla`
   sitting in the *file list* (not opened), show: *"This file type does not
   support that function"* (a table listing, per your note).

## Index rebuild (F2 Repair) — separate but related

Spec §5.3 already allows it: a host reader that finds a **stale or missing**
index (e.g. the card was moved and the skip-table no longer matches) MAY rebuild
it by scanning the LOG once and writing entries back. The embedded writer never
does this — it's host-only. F2 Repair today only *reports* health; this adds an
optional **rebuild the index** action so a relocated/oddly-encoded file gets its
accelerator restored. The log itself is authoritative, so a rebuild can never
lose data.

## Implementation home

All of this goes in **`volkov_core`** (GUI-free), so the MLA edits are a thin
pull from the library and the same logic is reusable headless. The C/MCU side
only ever *writes* the fixed 16 B descriptors — no parsing, no floats unless it
already uses them.

## Open question for sign-off

- Is the **16 B descriptor** (station, channel, dtype, scale_exp, 4 B unit,
  6 B name) the right shape? Specifically: are 6 chars enough for a name and
  4 for a unit, and is `× 10^scale_exp` enough, or do you want a full float32
  scale + float32 offset (bigger entries, fewer rows)?
