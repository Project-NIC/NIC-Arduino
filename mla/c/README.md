# NIC-MLA — C libraries

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

Two C implementations of the **NIC-MLA** format, sharing one definition
(`nic_mla_format.h`). Binary-**identical to the Python reference** (verified by the
cross-compat test: C writes ↔ Python reads).

| File(s) | Library | For whom |
|---|---|---|
| `nic_mla_format.h` | shared (header-only): constants, CRC16, LE helpers, build/parse log+prefix, `mla_hal_t` | both |
| `nic_mla_write.{h,c}` | **WRITE-ONLY** — `format` / `mount` / `append` | ATmega328 and small Arduinos (write-only stations) |
| `nic_mla.{h,c}` | **COMPLETE** — + `read_record` / `foreach`+filter / `recover` | ARM Arduino (SAMD/STM32/Teensy/ESP), PC |
| `dl_identity.h` | datalogger: encoders of the 8 B station identity (`dl_gps` / `dl_ident` / `dl_raw`), byte-exact with Python | the glue on the master |

> **Why two?** An ATmega only writes (once a minute / every 15 min) and has 2 KB of RAM. The
> write-only library makes no large allocation (largest stack buffer = 32 B, the prefix is
> streamed), so it fits on the tiniest chip. Search, read and recovery run on the host or on
> a bigger chip through the complete library.

## HAL adapters (`hal/`) — you choose the filesystem BELOW the HAL

The core talks only through 4 functions (`mla_hal_t`). Which FS library sits under them is
**a per-platform choice — the core does not change**. Ready adapters:

| Platform | "Below the HAL" (FS) | Adapter | NIC-MLA |
|---|---|---|---|
| **Raspberry Pi / PC** (SSD, SD, USB) | OS: ext4 / exFAT / NTFS / FAT32 / FAT16 | `hal/nic_mla_hal_posix.{h,c}` | Python **or** C complete |
| **Arduino AVR / ESP / STM32duino** | **SdFat** | `examples/atmega_sd_writeonly.ino` (glue) | C write-only / complete |
| **STM32 bare-metal** (CubeIDE/HAL) | **FatFs** (ChaN) | `hal/nic_mla_hal_fatfs.{h,c}` | C write-only / complete |

- **POSIX adapter** (`nic_mla_hal_posix`) — `mla_posix_create/open/hal/close`;
  works on anything with an OS (a Pi + SSD, a PC). The OS handles the FS underneath.
- **FatFs adapter** (`nic_mla_hal_fatfs`) — ~30 lines over `f_read/f_write/
  f_lseek/f_sync`. Compiles in a project that has FatFs (`ff.h`).
- **SdFat** is C++ — see the Arduino example for the hookup; same principle (4 functions).

An adapter for another FS is a few dozen lines; neither the format nor the core changes.

## HAL — what you must provide

Both libraries work through 4 functions (no `malloc`, no filesystem inside):

```c
typedef struct {
    int      (*read)(void *ctx, uint32_t off, void *buf, uint16_t n);   /* 0 = OK */
    int      (*write)(void *ctx, uint32_t off, const void *buf, uint16_t n);
    void     (*sync)(void *ctx);
    uint32_t (*size)(void *ctx);
    void     *ctx;
} mla_hal_t;
```

On an Arduino, `read/write` typically map onto **SdFat** (`file.seek/read/write`)
or onto SPI NOR flash. Offsets are logical (0 .. file_size-1).

## Minimal use (write-only, ATmega)

```c
#include "nic_mla_write.h"

mla_writer_t w;
mla_hal_t hal = my_sd_hal();           /* your HAL over SdFat/NOR */

/* first start: */
mla_w_format(&w, hal, 1UL<<20, MLA_CRC_FULL, /*cluster*/12, /*kf*/0);
/* later starts (after a reset): */
mla_w_mount(&w, hal);

uint8_t sample[5] = { temp_lo, temp_hi, hum, 0, batt };
/* mla_w_append(w, ts, subsec, station, data, len, compressed, kf_back);
   station = 1 B index into the station table in the prefix (0 = none);
   subsec = two opaque bytes, the glue gives them meaning (MLA gives none) — sub-second
   time and/or section/rotation; usable as one u16 or as two bytes;
   RAW data: compressed=0, kf_back=0 */
mla_w_append(&w, unix_time(), /*subsec*/0, /*station*/1, sample, 5, /*compressed*/0, /*kf_back*/0);
```

The tables (schema + stations) from `tools/mla_schema.py` go in through
`mla_w_format_ex(...)`; the library does not read their content, it only writes it.

## Read / query (complete library, host or ARM)

```c
#include "nic_mla.h"

mla_t m; mla_mount(&m, hal);

mla_log_t rec; uint8_t buf[256]; uint16_t len;
mla_read_record(&m, 0, &rec, buf, sizeof(buf), &len);

/* filter: station (index) 1 only, a time window */
mla_filter_t f = {0};
f.has_station = 1; f.station = 1;
f.has_time = 1; f.time_from = t0; f.time_to = t1;
mla_foreach(&m, &f, my_callback, my_user_ptr);
```

## Test (on a PC)

```sh
cc -std=c99 -Wall -Wextra -O2 nic_mla_test.c nic_mla.c nic_mla_write.c \
   hal/nic_mla_hal_posix.c -o mlatest
./mlatest /tmp/mla_c_out.bin       # 56/56 PASS; writes a file for the Python cross-check
python3 cross_check.py /tmp/mla_c_out.bin   # byte-exact C↔Python check (13/13)
```

## Notes

- Everything little-endian, serialised byte by byte → independent of endianness/padding.
- Crash safety: LOCK first, DATA second; discarding a record = overwriting it with zeros
  (the CRC then fails → the reader skips it). The whole 16 B log record is under the CRC.
- File rotation and compression are outside this core (rotation = platform glue over the
  FS; compression = a separate method, the container only marks it with the `compressed` bit
  + `kf_back`, the codec lives in the data block's header).
