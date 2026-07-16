# NIC-IAGA

**Самостоятельная библиотека данных NIC — преобразование магнитометрического лога NIC-MLA в IAGA-2002.**

---

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](https://opensource.org/licenses/MIT)

---

```
   .mla  ──▶  [декодирование NIC-DMD, если сжато]  ──▶  калиброванные нТл по компонентам  ──▶  IAGA-2002
```

> **Что это.** Одна из самостоятельных библиотек данных NIC (наряду с NIC-MLA,
> NIC-DMD, NIC-MSEED). **IAGA-2002** — обменный формат наземной геомагнитики: формат
> самого INTERMAGNET и вход **[SuperMAG](https://supermag.jhuapl.edu/)** (~600
> вариометров по всему миру). NIC-Gauss — вариометр (сообщает *отклонение* поля, а не
> абсолютные значения), поэтому данные выходят с декларацией `Data Type: variation` —
> именно тот класс, который принимает SuperMAG; абсолютная базовая линия остаётся
> делом обсерваторий (вариометрическая доктрина, NIC-Heimdall `gauss/README.md`).
> NIC-IAGA — этот мост: читает `.mla`, распаковывает блобы NIC-DMD, применяет
> калибровку из SCHEMA (`физ = (raw + offset) · 10^exp10` → **нТл, не отсчёты**) и
> пишет стандартный текст IAGA-2002, один файл на станцию. **Готовая библиотека, а не
> фреймворк.**

> **Где живёт калибровка — единственное намеренное отличие от NIC-MSEED.** miniSEED
> несёт сырые отсчёты, оставляя калибровку метаданным StationXML; IAGA-2002 несёт
> **физические нТл**, поэтому этот экспортёр применяет калибровку на выходе. Оба
> читают один и тот же архив — сам архив остаётся сырым (derive-from-raw).

## Два слоя

- **`iaga`** — ядро, независимое от контейнера: строки `(unix_s, x, y, z[, f])` в нТл
  → текст IAGA-2002 (12 обязательных 70-символьных заголовочных записей, комментарии,
  заголовок столбцов, 67-символьные строки данных; пропуск = `99999.00`, не
  измерялось = `88888.00`), плюс минимальный ридер для round-trip тестов.
- **`from_mla`** — конвертер, подключающий **NIC-MLA + NIC-DMD** к этому ядру: DMD
  replay по станциям, автоопределение полей X/Y/Z(/F) (или по именам), калибровка,
  метаданные станции из таблицы STATION.

## Быстрый старт

```python
from nic_iaga import export_mla_to_iaga

export_mla_to_iaga(
    "gauss.mla", "gauss.iaga2002",
    stations={1: dict(iaga_code="NIC1", latitude=50.086, longitude=14.416,
                      elevation_m=235)},
    sampling="60 seconds", interval_type="1-minute")
```

## Тесты

```sh
python3 tests/test_iaga.py       # чистый writer: форма заголовка, ширины, round-trip
python3 tests/test_from_mla.py   # end-to-end: MLA (+DMD) → IAGA-2002 → обратное чтение
```

Вендоренные зависимости (`nic_mla`, `nic_dmd`) лежат в `third_party/` — так же, как у
NIC-MSEED, NIC-GLUE-IN и NIC-VDE.

## Лицензия

MIT — Copyright (c) 2026 NIC — Native Intellect Community
