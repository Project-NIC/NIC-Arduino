# Channel conversion table — design proposal

> Status: **PROPOSAL — needs sign-off on the binary layout before any code.**
> One-way door: once a station's processor starts writing this table, the byte
> layout is hard to change. Confirm the layout first.

## Problem

The MLA kernel deliberately does **not** know what a payload means. The spec
(§4.1) says: *"which byte is temperature, which is humidity is determined by the
station+channel metadata, not by the type byte."* But that metadata is **stored
nowhere**. Today `MlaBackend.decode_value` just *guesses* from payload length
(4 bytes → float, text → text). Export to CSV/SQL inherits the guess, so we ship
**raw, untranslated** values that nobody actually wants in SQL.

## Design principle — keep it dead simple

Real sensors don't send floats. The station's MCU reads the sensor, converts it
to **one small integer**, and sends that. So this format makes one firm choice:

- **Every measured value is a 2-byte integer** (`int16` LE). No float. No
  per-channel byte-width picking (1 B / 2 B / 4 B) — that only adds complexity
  for no real gain. Two bytes covers every common sensor: temperature can go
  negative, pressure/humidity start at some number and rise, etc.
- The only other payload kind is **text** (event/status records).

The *human* meaning (a temperature of 23.5 °C arriving as the integer `235`) is
restored on the **host** (Volkov), never on the MCU. The MCU only ever writes a
few constant bytes; all interpretation runs where there's CPU to spare.

## Where it lives — the prefix free space

The 512 B prefix has **~475 B of zeroed, CRC-covered free space** from byte 34
to 509 (`[34] padding 0x00 … to byte 509`). It was reserved exactly for
"settings that travel with the file". The conversion table goes here. No data
block is touched — append-only stays intact; only the prefix is rewritten (and
its CRC recomputed).

The station's processor writes this table at format time, so the file is
**self-describing**: it carries the meaning of its own data wherever it goes.

## Binary layout (all binary — the MCU writes constants, the host renders)

A small header + a flat array of fixed-size channel descriptors, at prefix
offset **34**.

```
Conversion-table region (inside prefix, offset 34..509)

[34] tbl_magic    2 B   0xCB 0x01  ("channel table v1") — 0x0000 = absent
[36] tbl_count    1 B   number of channel descriptors
[37] tbl_flags    1 B   reserved (0)
[38] descriptors  count × 24 B   (see below)
...                up to byte 509 → max 19 descriptors fit (472 B / 24)
```

### Channel descriptor (24 B, fixed)

```
[0]  station    2 B  uint16 LE   which station this row describes
[2]  channel    2 B  uint16 LE   which channel within the station
[4]  kind       1 B              0 = int16 value · 1 = text · 0xFF = unused row
[5]  flags      1 B  reserved (0)
[6]  unit       6 B  ASCII/UTF-8 null-padded, e.g. "degC" "%" "hPa" "V"
[12] name       8 B  ASCII/UTF-8 null-padded, e.g. "Temp" "Humidity" "Press"
[20] formula    4 B  see below   how to turn the int16 into the real value
```

Because the value type is fixed (`int16`), the descriptor spends its bytes on
what actually varies between channels: the **name**, the **unit**, and a tiny
**conversion**.

### The conversion (`formula`, 4 B) — two options to sign off

**Option A — scale + offset (compact, fixed math).** The host computes
`value = raw / divisor + offset`:

```
[20] divisor   2 B  uint16 LE   e.g. 10 → one decimal, 100 → two decimals
[22] offset    2 B  int16  LE   added after scaling (e.g. sensor with a bias)
```

Covers "235 → 23.5 °C" (`divisor=10`), pressure offsets, etc. Trivial, no parser.

**Option B — text micro-formula (more flexible).** Those 4 B instead hold a tiny
expression like `x/10`, evaluated host-side by a small safe arithmetic parser
(**never Python `eval`**). More general (could do `(x-32)*5/9`), but 4 B is short
— realistically needs widening the field, costing descriptors.

> Given your "keep it simple", **Option A is the recommendation**: it matches how
> sensors are actually scaled and needs zero parser. Option B is here only so the
> trade-off is on record.

### Multiple station types (your idea)

Each descriptor carries its own `station`, so one file can describe **several
station types** at once. A datalogger reading up to ~4 station types writes one
descriptor per (station, channel). On read, a record's `station` (LOG offset 8)
+ `channel` (offset 10) selects the row; no match → fall back to today's
length-based guess. With 24 B rows: 19 channels per file (e.g. 2–3 station types
× ~7 channels). If 4 full station types are needed, the table can spill into the
optional INDEX region — noted as an open question, not built yet.

## How the host uses it

1. **Viewer / F4 Values** — look up `(station, channel)`, read the 2-byte value,
   apply the conversion, append `unit`. No descriptor → current guess.
2. **Export (CSV / SQL)** — a new choice at export time: **raw** integers vs.
   **translated** values (default = translated; nobody wants raw in SQL). Same
   spirit as building the export filename from metadata.
3. **F4 as table editor** — **only inside an open `.mla`**: F4 opens a simple
   editor over the descriptors (like editing a text file), writes the table back
   into the prefix and recomputes the prefix CRC. Pressed on an `.mla` sitting in
   the *file list* (not opened) → show a small table saying *"This file type does
   not support that function."*

## Index rebuild (F2 Repair) — separate but related

Spec §5.3 already allows it: a host that finds a **stale or missing** index
(e.g. the card was moved and the skip-table no longer matches) MAY rebuild it by
scanning the LOG once and writing entries back. The embedded writer never does
this — host-only. F2 Repair today only *reports* health; this would add an
optional **rebuild index** action so a relocated file gets its accelerator back.
The log is authoritative, so a rebuild can never lose data.

## Implementation home

All of this lives in **`volkov_core`** (GUI-free): the MLA edits are a thin pull
from the library and the same logic is reusable headless. The C/MCU side only
ever *writes* the fixed 24 B descriptors (constant bytes) — no math, no float.

## Open questions for sign-off

1. **Conversion = Option A (divisor + offset)?** — recommended, simplest. Or B?
2. **Descriptor size 24 B → 19 channels/file.** Enough? If you really want 4 full
   station types (~28 channels), do we shorten name/unit, or spill into INDEX?
3. **Name 8 B / unit 6 B** — long enough for your labels?
