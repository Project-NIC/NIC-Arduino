# NIC-MLA — библиотеки на C

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

*Основной является английская версия.*

Две реализации формата **NIC-MLA** на C, использующие одно общее определение
(`nic_mla_format.h`). Двоично **идентичны эталонной реализации на Python** (проверено перекрёстным тестом
совместимости: запись на C ↔ чтение на Python).

| Файл(ы) | Библиотека | Для кого |
|---|---|---|
| `nic_mla_format.h` | общая (header-only): константы, CRC16, вспомогательные функции LE, сборка/разбор лога+префикса, `mla_hal_t` | обе |
| `nic_mla_write.{h,c}` | **WRITE-ONLY** — `format` / `mount` / `append` | ATmega328 и небольшие Arduino (станции только для записи) |
| `nic_mla.{h,c}` | **ПОЛНАЯ** — + `read_record` / `foreach`+фильтр / `recover` | ARM Arduino (SAMD/STM32/Teensy/ESP), PC |
| `dl_identity.h` | datalogger: кодировщики 8-байтной идентичности станции (`dl_gps` / `dl_ident` / `dl_raw`), побайтно совпадают с Python | glue на ведущем устройстве (master) |

> **Почему две?** ATmega только пишет (раз в минуту / раз в 15 мин) и имеет 2 KB RAM. Библиотека
> только для записи не выделяет больших блоков памяти (самый большой буфер на стеке = 32 B, префикс
> передаётся потоком), поэтому поместится даже на совсем крошечном чипе. Поиск/чтение/восстановление выполняются уже на хосте
> или на более мощном чипе с помощью полной библиотеки.

## Адаптеры HAL (`hal/`) — файловую систему вы выбираете ПОД HAL

Ядро общается только через 4 функции (`mla_hal_t`). Какая библиотека ФС находится под ними —
**выбор в зависимости от платформы, ядро не меняется**. Готовые адаптеры:

| Платформа | «Под HAL» (ФС) | Адаптер | NIC-MLA |
|---|---|---|---|
| **Raspberry Pi / PC** (SSD, SD, USB) | ОС: ext4 / exFAT / NTFS / FAT32 / FAT16 | `hal/nic_mla_hal_posix.{h,c}` | Python **или** полная на C |
| **Arduino AVR / ESP / STM32duino** | **SdFat** | `examples/atmega_sd_writeonly.ino` (glue) | C write-only / полная |
| **STM32 bare-metal** (CubeIDE/HAL) | **FatFs** (ChaN) | `hal/nic_mla_hal_fatfs.{h,c}` | C write-only / полная |

- **Адаптер POSIX** (`nic_mla_hal_posix`) — `mla_posix_create/open/hal/close`;
  работает на чём угодно с ОС (Raspberry + SSD, PC). ФС под ним обслуживает ОС.
- **Адаптер FatFs** (`nic_mla_hal_fatfs`) — ~30 строк поверх `f_read/f_write/
  f_lseek/f_sync`. Компилируется в проекте с FatFs (`ff.h`).
- **SdFat** написана на C++ — подключение см. в примере для Arduino; принцип тот же (4 функции).

Написать адаптер для другой ФС = пара десятков строк; ни формат, ни ядро не меняются.

## HAL — что нужно предоставить

Обе библиотеки работают через 4 функции (никакого `malloc`, никакой файловой системы внутри):

```c
typedef struct {
    int      (*read)(void *ctx, uint32_t off, void *buf, uint16_t n);   /* 0 = OK */
    int      (*write)(void *ctx, uint32_t off, const void *buf, uint16_t n);
    void     (*sync)(void *ctx);
    uint32_t (*size)(void *ctx);
    void     *ctx;
} mla_hal_t;
```

На Arduino `read/write` обычно подключаются к **SdFat** (`file.seek/read/write`)
или к SPI NOR flash. Смещения логические (0 .. file_size-1).

## Минимальное использование (write-only, ATmega)

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

Таблицы (схема + станции) из `tools/mla_schema.py` передаются через
`mla_w_format_ex(...)`; библиотека их содержимое не читает, а только записывает.

## Чтение / запрос (полная библиотека, хост или ARM)

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

## Тест (на PC)

```sh
cc -std=c99 -Wall -Wextra -O2 nic_mla_test.c nic_mla.c nic_mla_write.c \
   hal/nic_mla_hal_posix.c -o mlatest
./mlatest /tmp/mla_c_out.bin       # 56/56 PASS; writes a file for the Python cross-check
python3 cross_check.py /tmp/mla_c_out.bin   # byte-exact C↔Python check (13/13)
```

## Примечания

- Всё в little-endian, сериализация побайтная → не зависит от порядка байтов/выравнивания.
- Устойчивость к сбоям: сначала LOCK, потом DATA; отбрасывание записи = перезапись нулями
  (тогда CRC не сходится → читатель пропускает запись). Вся 16-байтная запись лога покрыта CRC.
- Ротация файлов и сжатие находятся вне этого ядра (ротация = платформенный glue поверх
  ФС; сжатие = отдельный метод, контейнер лишь помечает его битом `compressed`
  + `kf_back`, кодек находится в заголовке блока данных).
