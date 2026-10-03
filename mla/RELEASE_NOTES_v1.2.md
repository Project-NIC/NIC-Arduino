# NIC-MLA v1.2 — the final version

*[English](RELEASE_NOTES_v1.2.md) · [Čeština](RELEASE_NOTES_v1.2_cs.md) · [Русский](RELEASE_NOTES_v1.2_ru.md)*

**v1.2 is the last version of NIC-MLA, and of the NIC-Arduino family with it.**
The family is closed: every component reads 1.2, and nothing further is planned.
The station that grew out of these tools (NIC-Heimdall) keeps an archive of its
own; MLA stays what it was built for — small devices that log, and the PC tools
that read them.

These notes collect everything since v1.0 in one place. (The intermediate v1.1
tag is folded in here: the project had essentially no users, so there is one
release to describe, not two.) The prefix's `version` byte stays **1**.

## What's new

- **Sub-second timestamps.** The log record now carries a `subsec` field
  (the sample index within the second), so MLA handles sampling
  well above 1 Hz — e.g. a MEMS seismograph. Previously time resolved only to
  whole Unix seconds, which suited slow telemetry. Set `subsec = 0` for
  whole-second logging.
- **Compact, consolidated 16-byte record.** The old `rec_type`/class byte and
  the `reserved` padding byte are gone. Encoding state is now one packed `flags`
  byte: **bit 7 = compressed**, **bits 0–6 = `kf_back`** (distance back to the
  owning keyframe; 0 = this record *is* a keyframe). This frees room for
  `subsec` without growing the record.
  - MLA stays **codec-agnostic**: the `compressed` bit only means "hand the
    payload to the codec layer". *Which* codec / keyframe / variant lives in the
    data block's own header (NIC-DMD already does this), never in MLA.
  - Files are **homogeneous** — what a payload means comes from the SCHEMA
    table, not a per-record type tag.
- **Robust file rotation.** Each rotated file is independently mountable:
  - it inherits the previous file's tables/format params on reopen (no more
    rotating into a file with empty tables);
  - MLA now **surfaces the rotation event** (`MlaArchive.append` returns whether
    it rotated; `will_rotate()` predicts it; an `on_rotate` callback fires) so a
    compressed stream's glue can force a keyframe at the start of each file. For
    RAW data this is moot.
- **Prefix resilience.** A byte-identical **mirror copy** of the self-describing
  prefix is written at the tail of the file; `mount()` falls back to it if the
  primary copy at offset 0 fails its CRC. A single bad sector at the head no
  longer blinds the whole file. (The log region now ends at `region_end =
  file_size − prefix size`.)

- **`subsec` is a placement, owned by the glue.** The two bytes are opaque to
  MLA (`subsec_lo` / `subsec_hi`). On a power-of-two sample rate they hold the
  sample (frame) index within the second, so placing it is a shift and no
  fraction of a second is ever stored; a position needing more than 16 bits
  splits, the coarse half in `subsec`, the fine half in the payload. The
  exporters (NIC-MSEED, NIC-IAGA) read it as the frame index, never as a tick.
- **Crash recovery at mount.** `mount()` neutralises a torn LOG slot at the
  stream boundary (overwritten with `0x00`, the discard convention) and verifies
  the newest record's data block, reclaiming a torn data write. Bounded,
  idempotent — a clean file gets zero writes — and the Python and C
  implementations recover the same torn input to identical bytes.
- **Hardened emergency recovery.** `mla_recover` confirms a record boundary on
  the next record's magic before resyncing, and a corrupt primary prefix no
  longer sizes its own mirror — the intact mirror is found by scanning whole
  sectors.
- **Calibrated schema.** Each field descriptor is 16 B and carries a per-field
  mantissa: `scale = mantissa × 10^exp10`, applied on export, the archive itself
  stays raw. The unit vocabulary gained `m/s²`. The schema-table tag is **1**.
- **The datalogger layout** (`DESIGN-MLA-datalogger.md`): many station profiles
  in one file, told apart from the single-schema layout by the tag at offset 34.

## Compatibility

- On-disk format changes (record layout + tail mirror). v1.0 files are not
  read by v1.2 and vice-versa. The prefix `version` byte remains 1.
- Byte-exact across the Python reference and the C libraries (AVR / ARM / PC) —
  verified by `c/cross_check.py`.

## Verification

- Python suite: **122/122 PASS**
- C suite (write-only + complete libs): **56/56 PASS**
- C↔Python byte-exact cross-check: **13/13 PASS**
- Consumers green: DMD 18/18, KSF, glue-in, glue-out, NIC-MSEED, NIC-IAGA, VDE
