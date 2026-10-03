<p align="center">
  <img src="NICVDE.svg" width="200"/>
</p>

# Volkov Data Ecosystem

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

*Основной является английская версия.*

Кроссплатформенный двухпанельный файловый менеджер в стиле **Volkov Commander**,
написанный на Python с использованием **prompt_toolkit**. Он просматривает локальную файловую систему и
позволяет заходить *внутрь* контейнеров **NIC-MLA**, показывая каждую занесённую в лог запись как файл.

> Статус: **1.2** — собран под **NIC-MLA v1.2**. Двухпанельный просмотр, файловые
> операции, просмотрщик файлов/записей и бэкенд MLA, который просматривает и показывает
> записи — с ограниченным редактированием самоописывающих таблиц (это не универсальный
> редактор записей, но и не строго только для чтения). MLA — намеренно *глупый*
> контейнер, поэтому бэкенд опирается на эти таблицы: **таблица схемы** декодирует
> каждую упакованную полезную нагрузку в реальные значения + единицы измерения, а **таблица станций** превращает
> 1-байтовый индекс станции из лога в реальный регион/номер — и то, и другое идёт прямо
> в экспорт CSV/SQL, и оба можно редактировать на месте через редактор таблиц `F4`.
>
> Архитектура повторяет собственную философию MLA — **глупые библиотеки + тонкий glue**:
> внизу — повторно используемые библиотеки, знающие формат (`export`, плюс встроенный (vendored) MLA +
> его читатель схемы), а бэкенды — тонкие адаптеры поверх них. Весь
> `volkov_core/` не зависит от GUI, поэтому его можно использовать повторно без интерфейса (headless).

## Запуск

```bash
pip install -r requirements.txt
python3 volkov_data.py [left_dir] [right_dir]
```

**Клавиши**

| Клавиша | Действие |
|---|---|
| `Tab` | переключить панель |
| `↑/↓ PgUp/PgDn Home/End` | переместить курсор |
| `Enter` | открыть каталог / зайти в `.mla` / подняться выше (`..`) |
| `F1` | информация о выбранном элементе / записи |
| `F2` | проверить контейнер `.mla` — отчёт о действительных / мёртвых / повреждённых слотах |
| `F3` | просмотр файла или полезной нагрузки записи (текст/hex) |
| `F4` | на записи: декодированное значение (значения) + единицы измерения · на `..` внутри редактируемого `.mla`: редактор таблиц схемы/станций |
| `F5` | скопировать выбранный файл на другую панель |
| `F6` | переименовать или переместить — внутри `.mla`: экспортировать все записи в CSV |
| `F7` | создать каталог |
| `F8` | удалить (с подтверждением) |
| `F9` | выпадающее меню (сортировка, язык, экспорт в SQL, …) |
| `F10` / `q` / `Ctrl-Q` | выход · `Esc` закрывает любое всплывающее окно |

Нажмите `Enter` на `samples/weather.mla`, чтобы зайти внутрь и просмотреть его записи.

## Тесты

Логика `volkov_core/` не зависит от GUI, поэтому она покрыта набором тестов на стандартном `unittest`
(без дополнительных зависимостей):

```bash
python3 -m unittest discover -s tests
```

Тесты на лету создают временные контейнеры MLA, а также выполняют дымовую проверку
закоммиченного `samples/weather.mla`.

## Структура

```
volkov_data.py           prompt_toolkit GUI (thin shell over volkov_core)
volkov_core/             GUI-free logic — reusable headless
  backend.py               storage-backend abstraction (VdeEntry / VdeBackend)
  local.py                 VdeLocalBackend — host filesystem
  mla.py                   VdeMlaBackend — thin adapter: records as "files",
                           schema decode + station resolve + export
  export.py                dumb library — generic rows → CSV / SQLite bytes
  stations.py              glue — station index → real region/number
samples/make_sample.py   generator for a self-describing sample datalogger file
samples/weather.mla      committed sample (packed rows + schema + stations)
tests/                   stdlib unittest suite for volkov_core (GUI-free)
third_party/nic_mla/     vendored NIC-MLA (Python reference) — canonical data format
third_party/nic_dmd/     vendored NIC-DMD — decodes compressed (keyframe/delta) records
  tools/mla_schema.py      host-only schema/station builders + readers (VDE links)
```

Настольное приложение читает формат логгера через Python-эталон MLA
(`third_party/nic_mla/nic_mla.py`) и декодирует полезную нагрузку и станции через
читатель только для хоста (`tools/mla_schema.py`); оба побайтно совпадают с ядром на C.
Исходники Volkov Commander — **только образец поведения**, а не перенесённый код.

## Даталоггер (несколько профилей)

Определение и экспорт `.mla` даталоггера (несколько профилей станций в одном файле): `volkov_core.datalogger` — `is_datalogger()` + `export_csv()` / `export_sqlite()`. Полная спецификация — в NIC-MLA `DESIGN-MLA-datalogger.md`.

## Лицензия

MIT License — Copyright (c) 2026 NIC — Native Intellect Community

---

## Благодарности

Моему брату — за советы во время разработки этого проекта.
За техническую помощь в оптимизации кода — ИИ-ассистентам Claude (Anthropic) и Gemini (Google).
