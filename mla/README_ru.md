<p align="center">
  <img src="NICMLA.svg" width="200"/>
</p>

---

# NIC-MLA

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

*Основной является английская версия.*


[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](https://opensource.org/licenses/MIT)

---

**Matroshka Logging Archive** — универсальный однофайловый контейнер для
регистрируемых данных измерительных станций. И данные, и лог хранятся в **одном
переносимом файле**, который читается на любой платформе — от 8-битного
микроконтроллера до ПК.

Один файл, один формат, один способ чтения — вынимаете карту из устройства,
вставляете в компьютер, и у вас есть всё. Никакого зоопарка форматов.

> Полная спецификация формата: **[`DESIGN-MLA.md`](DESIGN-MLA_ru.md)** · примечания к выпуску: [`RELEASE_NOTES_v1.2.md`](RELEASE_NOTES_v1.2_ru.md) — **v1.2 является окончательной версией**
>
> Запись станций нескольких типов в один файл (даталоггер / ретранслятор):
> **[`DESIGN-MLA-datalogger.md`](DESIGN-MLA-datalogger_ru.md)**

## Ключевые особенности

- **Один файл = данные + лог.** Два потока растут навстречу друг другу: данные —
  сверху, лог — снизу.
- **«Глупый» контейнер.** MLA только хранит байты. Вся «логика» (сжатие,
  шифрование, преобразование номеров станций, LoRa/Wi-Fi) находится в отдельном
  слое glue — MLA остаётся маленьким и никогда не мешает.
- **Крошечная 16-байтная запись лога, полностью защищённая CRC.** Никакого трюка
  с «флагами вне CRC»: запись отменяется перезаписью нулями — её CRC после этого
  не сходится, и читатели её пропускают.
- **Устойчивость к сбоям.** Протокол фиксации «сначала LOCK, затем DATA» + CRC16
  (CCITT-FALSE). После сброса последняя запись либо проходит проверку (работа
  продолжается), либо обнуляется, а место освобождается. Нет хранящегося на диске
  дерева поиска, которое могло бы повредиться.
- **Самоописание.** Префикс содержит таблицу SCHEMA (8-символьные имена полей +
  единицы → готово к экспорту в CSV/SQL без каких-либо предварительных знаний) и
  таблицу STATION (1-байтный индекс станции в каждой записи лога → реальный номер
  станции).
- **Компактность для микроконтроллера.** ATmega328 (2 KB RAM) только пишет; нет
  динамического выделения памяти, самый большой буфер — 32 B. Поиск и чтение
  выполняются на хосте.
- **Ротация файлов.** Когда один файл заполняется, начинается следующий; большие
  объёмы = много файлов поменьше, хост читает их как единое целое.
- **32-битная адресация** → один файл до 4 GB (сверх этого — ротация).
- **Необязательное сжатие.** Контейнер лишь помечает сжатые данные (один бит
  `compressed` в записи) и ведёт `kf_back` (расстояние назад до соответствующего
  ключевого кадра); метод сжатия он не определяет — какой кодек / ключевой кадр
  используется, указано в собственном заголовке блока данных (например, NIC-DMD).
- **Независимость от файловой системы.** Доступ через тонкий HAL (4 функции);
  FAT16 / FAT32 / exFAT / NTFS / ext4 обслуживаются нижележащим слоем
  (ОС, SdFat или FatFs).

## Структура файла

```
offset 0                                                              EOF
┌──────────────────┬──────────────────┬───────────────┬──────────────┐
│ PREFIX           │ DATA  stream  →   │   free  0xFF   │   ← LOG stream│
│ 1–255 sectors    │ (grows up)        │               │ (grows down)  │
│ (512 B each)     │                   │               │               │
└──────────────────┴──────────────────┴───────────────┴──────────────┘
```

- **Префикс:** 34-байтный заголовок + таблицы SCHEMA и STATION, защищённые CRC16
  в последних 2 байтах. Обычно это один сектор 512 B; он увеличивается целыми
  секторами (до 255 ≈ 127 KB), только если этого требуют таблицы.
- **Блок данных:** `MAGIC(2) + payload(1..65535) + CRC16(2)`
- **Запись лога (16 B), полностью покрытая CRC:** offset, timestamp, subsec
  (два непрозрачных байта, смысл которых определяет glue), length, flags (bit7 = compressed,
  bits0-6 = kf_back; 0 = ключевой кадр), station (1-байтный индекс), CRC16.

## Структура репозитория

| Путь | Содержимое |
|---|---|
| `nic_mla.py` | Эталонное ядро на Python (format / mount / append / read / scan / recover) |
| `nic_mla_archive.py` | Python: ротация файлов (`MlaArchive`) + запросы на стороне хоста (`mla_query`) |
| `tools/mla_schema.py` | Построение/чтение таблиц SCHEMA + STATION; декодирование полезной нагрузки для CSV/SQL |
| `nic_mla_test.py` | Набор тестов (Python) |
| `c/` | Библиотеки на C: только запись (MCU) + полная (ARM/PC) + адаптеры HAL |
| `DESIGN-MLA.md` | Проектная спецификация формата |

## Быстрый старт — Python

```python
from nic_mla import MlaCore, MlaPosixHAL

# First run (creates a 1 MB file pre-filled with 0xFF)
hal = MlaPosixHAL.create("log.mla")
with hal:
    mla = MlaCore(hal)
    mla.format()
    mla.append(timestamp, station=1, data=b"\x01\x02\x03")   # station = table index

# Later runs: mount() restores the state; iteration reads records
with MlaPosixHAL("log.mla") as hal:
    mla = MlaCore(hal); mla.mount()
    for rec, payload in mla:
        ...
```

Ротация по нескольким файлам и фильтрация:

```python
from nic_mla_archive import MlaArchive, mla_query
with MlaArchive("/data") as arch:          # MLA00000.MLA, MLA00001.MLA, …
    arch.append(ts, station=1, data=payload)
for rec, data in mla_query(MlaArchive("/data"), station=1, time_from=t0, time_to=t1):
    ...
```

Самоописывающий файл (таблицы схемы + станций → готово к экспорту в CSV/SQL):

```python
from mla_schema import MlaSchemaBuilder, MlaStationTable, mla_read_schema, \
                       mla_read_stations, mla_decode_payload, mla_split_station, dl_ident

sb = MlaSchemaBuilder()
sb.data("temp", unit="degC", width=2, exp10=-1, signed=True)
sb.data("hum",  unit="pct",  width=2, exp10=-1)
st = MlaStationTable()
# Station record = identity(8B) + elevation(2B) + name(32B). Build the identity
# with dl_ident / dl_gps / dl_raw; elevation is signed metres (None = unknown);
# name is a human label (UTF-8, ≤32 B, "" = none — StationXML <Site><Name>).
st.station(dl_ident(region=55, number=25000), elev_m=235, name="Praha")  # log index 1 → this station

hal = MlaPosixHAL.create("log.mla")
with hal:
    mla = MlaCore(hal)
    mla.format(schema_table=sb.table(), station_table=st.table())
    mla.append(ts, station=1, data=temp.to_bytes(2,"little",signed=True)+hum.to_bytes(2,"little"))

# Any reader recovers names, units, the station identity + elevation + name — no prior knowledge:
with MlaPosixHAL("log.mla") as hal:
    mla = MlaCore(hal); mla.mount()
    pfx = mla._prefix.to_bytes()
    _, fields = mla_read_schema(pfx); stations = mla_read_stations(pfx)
    for rec, data in mla:
        identity, elev_m, name = mla_split_station(stations[rec.station - 1])  # 8 opaque bytes + metres + name
        cols = mla_decode_payload(fields, data)   # [(name, unit, value), …]
```

Тесты:

```sh
python3 nic_mla_test.py
```

## Быстрый старт — C

Две библиотеки используют одно общее определение формата (`c/nic_mla_format.h`):

- **только запись** (`c/nic_mla_write.{h,c}`) — для ATmega / небольших Arduino,
- **полная** (`c/nic_mla.{h,c}`) — для ARM Arduino / ПК (+ чтение, запросы, восстановление).

HAL (4 функции) вы подключаете к своей файловой системе. Готовые адаптеры находятся в `c/hal/`:

| Платформа | «Под HAL» | Адаптер |
|---|---|---|
| Raspberry Pi / ПК (SSD, SD, USB) | ОС: ext4 / exFAT / NTFS / FAT32 / FAT16 | `hal/nic_mla_hal_posix.{h,c}` |
| Arduino AVR / ESP / STM32duino | SdFat | `examples/atmega_sd_writeonly.ino` |
| STM32 bare-metal (CubeIDE/HAL) | FatFs (ChaN) | `hal/nic_mla_hal_fatfs.{h,c}` |

Сборка и тестирование на ПК:

```sh
cd c
cc -std=c99 -Wall -Wextra -O2 nic_mla_test.c nic_mla.c nic_mla_write.c \
   hal/nic_mla_hal_posix.c -o mlatest
./mlatest
```

См. **[`c/README.md`](c/README_ru.md)**.

## Примечания для интеграторов

- **Имён станций в файле нет.** Таблица STATION хранит для каждой станции
  8-байтную непрозрачную идентичность + 2-байтную высоту (i16 LE, метры); что
  означает идентичность (регион / номер / GPS / …), решает ваш слой glue, который
  ведёт собственное соответствие «8 байт → смысл». Лог несёт только 1-байтный
  индекс — преобразовать его в реальный номер станции является задачей glue, а
  не контейнера.
- **Поле `subsec` — это два непрозрачных байта, которыми владеет glue.** MLA не
  придаёт им никакого смысла и никогда их не трогает. Имя намеренно читается
  двояко: sub-**sec**ond (доли секунды) *и* sub-**sec**tion (подраздел, например
  индекс ротации / раздела). Ваш glue может использовать эти 2 байта (0..65535)
  как одно 16-битное значение, как два независимых байта или сразу для нескольких
  целей — например, старший байт = раздел/ротация, младший байт = такт долей
  секунды, чтобы MLA хорошо справлялся с частотой дискретизации значительно выше
  1 Hz (например, в сейсмике). Если поле не используется, установите его в 0.

## Передача данных (LoRa / сеть)

**Вне рамок проекта** — контейнер предназначен для хранения, а не для передачи.
Каждая запись самодостаточна (offset + length + flags + CRC), поэтому отправка её
по LoRa/сети означает «взять байты записи и отправить их». Выбор способа передачи
проект оставляет пользователю.

## Состояние

Эталонные реализации на Python и на C завершены, протестированы и **побайтно
идентичны** (файл, записанный библиотекой на C, читается на Python, и наоборот).

## Лицензия

MIT License — Copyright (c) 2026 NIC — Native Intellect Community

---

## Благодарности

Моему брату — за советы во время разработки этого проекта.
За техническую помощь в оптимизации кода — ИИ-ассистентам Claude (Anthropic) и Gemini (Google).
