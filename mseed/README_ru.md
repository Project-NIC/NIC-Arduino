<p align="center">
  <img src="NICMSEED.svg" width="200"/>
</p>

# NIC-MSEED

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

*Основной является английская версия.*

**Самостоятельная библиотека данных NIC — преобразует лог NIC-MLA в miniSEED (Steim-1 / Steim-2).**

---

[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](https://opensource.org/licenses/MIT)

---

```
   .mla  ──▶  [NIC-DMD decode if compressed]  ──▶  per-channel int counts  ──▶  miniSEED
```

> **Что это такое.** Одна из самостоятельных библиотек данных NIC (наряду с NIC-MLA,
> NIC-DMD, NIC-KSF). Узел NIC записывает свои отсчёты в контейнер NIC-MLA; **miniSEED**
> — общепринятый язык сейсмологии, который напрямую загружается в **ObsPy, SeisComp, SWARM**
> и инструментарий FDSN. NIC-MSEED служит мостом — он читает `.mla`, распаковывает
> блобы NIC-DMD, извлекает необработанные целочисленные отсчёты по каждому каналу
> SCHEMA и записывает стандартные записи miniSEED. Её использует любой, у кого есть
> сейсмический лог MLA (например, от **NIC-Quake**) и кому нужен SEED, — **рабочая
> библиотека, а не фреймворк.** (Для разового просмотра любого лога MLA в CSV /
> SQLite используйте NIC-GLUE-OUT; miniSEED — путь для сейсмологии.)

## Две реализации

- **Python** (`nic_mseed/`) — эталонная: чистый Python 3.10+, без внешних пакетов.
- **C** (`c/`) — тот же кодек Steim-1/2 + модуль записи miniSEED на переносимом C,
  для экспорта на самом устройстве / во встраиваемых системах. Обе реализации
  протестированы на хосте и проходят полный цикл на тестовых векторах друг друга.

## Два уровня

- **`steim` / `mseed`** — ядро, не зависящее от контейнера: целые числа → кадры
  Steim-1/2 → записи miniSEED и обратно (минимальный читатель для тестов полного
  цикла). Без зависимостей.
- **`from_mla`** — конвертер, связывающий **NIC-MLA + NIC-DMD** с этим ядром:
  воспроизведение DMD для каждой станции, разделение на каналы по схеме,
  сопоставление кодов SEED.

## Быстрый старт

```python
from nic_mseed import MseedExporter, STEIM2

stats = MseedExporter(
    sample_rate_hz=100.0,        # device ODR — miniSEED needs the rate; MLA doesn't store it
    network="NQ",                # SEED network code
    version=STEIM2,              # or STEIM1
    channel_map={"z": "HHZ", "n": "HHN", "e": "HHE"},   # SCHEMA field → SEED channel
).export("quake.mla", "quake.mseed")
print(stats)   # {channels, samples, records, bytes, out}
```

```bash
python3 examples/mla_to_mseed.py            # builds a sample .mla, converts, prints stats
python3 tests/test_steim.py                 # Steim-1/2 codec round-trip
python3 tests/test_mseed.py                 # miniSEED writer (+ ObsPy gold-standard if installed)
python3 tests/test_from_mla.py              # end-to-end MLA(+DMD) → miniSEED round-trip
python3 tests/test_to_stationxml.py         # StationXML metadata (+ ObsPy schema check if installed)
```

## Как MLA отображается в miniSEED

| Что нужно miniSEED | откуда берётся |
|---|---|
| время начала (BTIME) | `timestamp` MLA (u32 s) + `subsec` (u16) первой записи |
| частота дискретизации | **задаёте вы** (`sample_rate_hz` = ODR устройства); `subsec` лишь фиксирует фазу внутри секунды |
| целочисленные отсчёты | полезная нагрузка MLA, разделённая по полям SCHEMA (raw или распакованная NIC-DMD) — *необработанные* отсчёты, а не масштабированное физическое значение (калибровка относится к StationXML) |
| network/station/location | таблица STATION MLA (или `station_map`) |
| код канала | имя поля SCHEMA (или `channel_map`) |

Каждая пара `(station, field)` становится одним каналом miniSEED. Конвертер
предполагает равномерно дискретизированный непрерывный ряд для каждого канала
(что верно для синхронизированного сбора данных, например **NIC-Quake**);
разбиение по пропускам оставлено на последующий проход.

## Как вычисляются временные заголовки

**Опорная точка и индекс — время записи никогда не читается для каждого отсчёта.**
Время читается только из *первой* записи канала: `t0 = timestamp + subsec / sample_rate_hz`.
Это единственное место, где используется `subsec`; оно фиксирует фазу первого
отсчёта и ничего больше. Затем каждая запись miniSEED получает `t0 + i / sample_rate_hz`,
где `i` — число уже выданных отсчётов; время каждый раз вычисляется от `t0`, а не
от предыдущего заголовка, поэтому ничего не накапливается. Целые секунды идут в
календарные поля BTIME, остаток — в последнее поле BTIME, а частота записывается
как пара SEED `(factor, multiplier)`: 128 Hz — это `(128, 1)`, точно.

`subsec_unit="index"` — это то, что записывает станция NIC: `subsec` — индекс кадра
на сетке со степенью двойки, поэтому `subsec / sample_rate_hz` — точная двоичная
дробь. `"ms"` предусмотрен для лога с метками в миллисекундах; вызываемый объект
(callable) принимает всё остальное.

**Дробная часть BTIME — 0,0001 s, и это предел точности экспорта.** При 128 Hz
отсчёт длится 7812,5 µs, поэтому лишь каждая восьмая граница отсчёта приходится на
целое число 100 µs, а граница записи оказывается там, куда её помещает упаковка
Steim, — поэтому начало записи округляется, на величину до 50 µs. Поле
`time correction` имеет ту же единицу 0,0001 s и ничего не даёт. Это SEED 2.4;
miniSEED v3 несёт время начала с точностью до наносекунды. **Архив сохраняет
полное разрешение — потеря происходит в заголовке SEED, а не в `.mla`.**

## Сопутствующий файл метаданных StationXML

miniSEED несёт *данные*; инструментам FDSN нужны также *метаданные* —
идентичность станции, координаты, частота дискретизации и чувствительность
отсчёт→физическая величина. Это **StationXML**, и его формирует
`nic_mseed/to_stationxml.py` (FDSN StationXML 1.1):

```python
from nic_mseed import StationXmlExporter

StationXmlExporter(
    sample_rate_hz=100.0,        # MUST match the rate used for the miniSEED export
    network="NQ",                # same constructor args as MseedExporter
).export("quake.mla", "quake.xml")
```

Он **составляет пару с miniSEED**: коды Network/Station/Location/Channel (NSLC) и
частота дискретизации берутся из *того же* `MseedExporter`, который использует
`from_mla.py`, поэтому ObsPy / SeisComp привязывают метаданные к данным
уже по самому построению. Остальное предоставляет префикс MLA:
идентичность GPS (`dl_gps`) → Latitude/Longitude, поле i16 → Elevation, 32-байтное
имя → `<Site><Name>`, а `exp10` каждого поля DATA → `<InstrumentSensitivity>`
(общий коэффициент усиления = отсчётов на физическую единицу = `10**-exp10`) с
единицей поля (`m_s`→`m/s`, `degC`, `Pa`, …) на входе и `count` на выходе.

Два честных ограничения (они также указаны в модуле и в XML):

- **Плоская характеристика.** Каждый канал несёт только `<InstrumentSensitivity>`
  (скалярный коэффициент усиления на постоянном токе) — без полюсов/нулей /
  каскада ступеней, поскольку MLA не несёт частотную характеристику. Точно для
  метеодатчиков с плоской характеристикой; приближение первого порядка для
  сейсмических каналов MEMS. Этого **недостаточно** для настоящей деконволюции
  прибора.
- **Для координат нужна идентичность GPS.** Latitude/Longitude берутся из
  идентичности `dl_gps`. Иерархическая идентичность `dl_ident` координат не несёт —
  передайте переопределение `coords={index: (lat, lon)}`, иначе генератор выдаст
  исключение (он никогда молча не записывает 0,0). Неизвестная высота (сигнальное
  значение 0x8000) записывается как заполнитель `0`.

```bash
python3 -m nic_mseed.to_stationxml quake.mla quake.xml --rate 100 --network NQ
python3 tests/test_to_stationxml.py         # emitter + pairing (+ ObsPy schema check if installed)
```

## Проверка

Кодек и модуль записи проходят полный цикл через собственный минимальный
читатель этого пакета. Тест miniSEED дополнительно выполняет проверку с помощью
**ObsPy**, если она установлена, — запустите `python3 tests/test_mseed.py` на
машине с ObsPy для эталонного подтверждения соответствия спецификации.

## Структура

```
nic_mseed/          Python: steim (codec) + mseed (writer) + from_mla (converter) + to_stationxml (metadata)
c/                  C: portable Steim-1/2 codec + miniSEED writer (+ tests, CMake)
examples/           runnable MLA → miniSEED demo
tests/              codec round-trip, writer, end-to-end converter, and StationXML tests
third_party/        vendored NIC-MLA + NIC-DMD (see VENDORED.md)
```

Эталонная реализация на Python — чистый Python 3.10+, без внешних пакетов (ObsPy —
необязательная проверка *только для тестов*). Сборку на C можно протестировать на
хосте с помощью CMake:

```bash
cmake -S c -B c/build && cmake --build c/build && ctest --test-dir c/build --output-on-failure
```

## Лицензия

MIT License — Copyright (c) 2026 NIC — Native Intellect Community

---

## Благодарности

Моему брату — за советы во время разработки этого проекта.
За техническую помощь в оптимизации кода — ИИ-ассистентам Claude (Anthropic) и Gemini (Google).
