# NIC-MLA — Formát dataloggeru (profile-ref)

*[English](DESIGN-MLA-datalogger.md) · [Čeština](DESIGN-MLA-datalogger_cs.md) · [Русский](DESIGN-MLA-datalogger_ru.md)*

*Závazná je anglická verze.*

> **Stav:** implementováno (referenční implementace v Pythonu + 33 testů). **Doplňkový** k
> jednoschématovému formátu v1.2 — 16bajtový log záznam se nemění a soubory v1.2
> dál fungují. Reference: `tools/mla_datalogger.py`, testy
> `tools/mla_datalogger_test.py`. Datum: 2026-06-06

## Proč
Datalogger / LoRa repeater přijímá data od **několika typů stanic** (meteo,
elektřina, včelí úl, …) a musí je logovat do **jednoho** `.mla`. v1.2 nese
jediné schéma na soubor (jedno rozvržení + mnoho identit stanic); formát dataloggeru
umožňuje, aby **každá stanice nesla vlastní rozvržení sloupců**, a přitom stále sdílela
rozvržení, pokud jsou stanice shodné.

## Model — profile-ref
- **PROFILE** = rozvržení sloupců (vlastní deskriptory datových polí).
- **STATION** = 8bajtová neprůhledná identita + 1bajtový odkaz na profil.
- 1bajtový **index stanice** v 16bajtovém log záznamu vybírá stanici →
  `{ identity, profile_ref }` → profil → dekódování užitečných dat.

```
log record.index → STATION (identity + profile_ref) → PROFILE (column layout) → values
```

Tím se *rozvržení* sdílí mezi shodnými stanicemi (8 meteostanic → 1 profil
+ 8 řádků stanic), a přesto jsou v jednom souboru možná *různá* rozvržení (meteo + elektřina).

## Binární rozvržení (neseno ve slotu `schema_table` prefixu, za 34B hlavičkou)
Každá sekce je označená tagem a sama určuje svou velikost; čtečka je prochází v pořadí. Celý
blob je pokryt CRC prefixu, přesně jako tabulka schématu ve v1.2.

```
LOG       : 0x4C  n_log         n_log × 16B descriptor      (describes the fixed 16B record)
PROFILES  : 0x50  n_profiles    [ n_data(1B)  n_data × 16B ] × n_profiles
STATIONS  : 0x54  n_stations    [ identity(8B)  profile_ref(1B)  elevation(2B)  name(32B) ] × n_stations
```

`elevation` jsou znaménkové metry jako **i16 little-endian** (`0x8000` = neznámá/nenastavená);
jde o SAMOSTATNÉ pole záznamu umístěné za `profile_ref`, není součástí neprůhledné
identity. `name` je SAMOSTATNÝ pevný 32bajtový štítek čitelný pro člověka (UTF-8,
doplněný NUL, samé nuly = žádný) umístěný jako poslední — materiál pro StationXML `<Site><Name>`;
jde o metadata uložená **jednou v prefixu**, NENESOU se v každém 16bajtovém log záznamu.
8bajtová identita je zde TÝŽ model identity stanice, který nyní používá
i jednoschématový formát — tím se identita stanice **sjednocuje** na 8bajtovém modelu (starý
6bajtový záznam region/number/reserved je vyřazen).

16bajtový deskriptor pole a `physical = (raw + offset) × mantissa × 10^exp10` jsou
**stejné** jako v hlavním formátu (`width 1/2/4 · unit · exp10 i8 · flags · offset i16 · mantissa i16 · name 8B`).
Tagy (0x4C/0x50/0x54) se liší od tagu schématu (0x01), takže jádro
(`_schema_byte_len` v `nic_mla.py`) určí velikost kteréhokoli z obou formátů transparentně — `MlaCore`
jen nese bajty.

## Identita stanice (8 B, neprůhledná)
MLA těmto 8 bajtům nedává žádný význam; dává ho glue. Enkodéry builderu:
- `dl_gps(lat, lon)` — 2× i32 (stupně ×10⁷, ~1 cm)
- `dl_ident(number, region, kind, reserved)` — hierarchická (4× u16)
- `dl_raw(8 bytes)` — cokoli

**Pevná stanice → `dl_gps`, zaměřená jednou při instalaci.** Poloha *je* identita
— žádné samostatné pole polohy, žádné schéma číslování stanic, které by časem nestačilo, globálně jedinečná s přesností
~1 cm a připravená pro prostorové indexování. Tatáž 8bajtová identita slouží každé vstupní
části (seismo, počasí, iono, …); souřadnici zmrazte, aby se neposouvala s každým novým fixem.
`dl_ident` / `dl_raw` zůstávají pro hierarchická nebo vlastní ID.

> Čtyři elektroměry v jedné skříni → 4 stanice se **stejnou GPS, různým
> `number`, stejným profile_ref** (rozvržení je uloženo jen jednou).

## Použití
```python
from mla_schema import MlaField
from mla_datalogger import DataloggerBuilder, DataloggerTables, dl_gps, export_csv
from nic_mla import MlaCore, MlaPosixHAL

# 1) describe profiles + stations
b = DataloggerBuilder()
b.log("datetime")
meteo = b.profile([MlaField("temp", 2, "degC", -2, signed=True),
                   MlaField("hum",  2, "pct",  -1)])
elec  = b.profile([MlaField("power", 2, "W"), MlaField("energy", 4, "kWh")])
b.station(dl_gps(50.0875, 14.4213), meteo)   # station 1
b.station(dl_gps(49.1951, 16.6068), meteo)   # station 2 (same layout)
b.station(dl_gps(50.0875, 14.4213), elec)    # station 3 (different layout)
blob = b.serialize()

# 2) write a real .mla (the tables ride in the schema_table slot)
hal = MlaPosixHAL.create("weather.mla", 64 * 1024)
with hal:
    m = MlaCore(hal); m.format(file_size=64 * 1024, schema_table=blob)
    t = DataloggerTables.parse(blob)
    m.append(1700000000, station=1, data=t.encode(1, {"temp": 25.45, "hum": 60.0}))
    m.append(1700000060, station=3, data=t.encode(3, {"power": 1500, "energy": 12345}))

# 3) export → one CSV / one SQL table per profile
export_csv("weather.mla", "out/")
```

## Limity
- ≤ 255 profilů, ≤ 255 stanic (1bajtové počty / index), ≤ 255 sloupců na profil.
- Užitečná data na jeden záznam ≤ 65535 B (`length` v logu je u16); řádky komprimované DMD ≤ 255 B.
- Soubor je buď ve formátu se schématem v1.2, **nebo** ve formátu dataloggeru; rozliší se podle tagu na offsetu 34.
  Kontejner, CRC, odolnost proti pádu, rotace i komprese jsou totožné s v1.2.

## Co na to navazuje
- `tools/mla_datalogger.py` — builder, čtečka, dekódování podle profilu, enkodéry identity, export CSV/SQL.
- `nic_mla.py` — `_schema_byte_len` určuje velikost blobu dataloggeru (doplňkově).
- Dekódování/export se smíšenými profily je v testech ověřeno end-to-end na skutečném `.mla`.
