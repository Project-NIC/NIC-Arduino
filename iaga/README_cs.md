# NIC-IAGA

**Samostatná NIC datová knihovna — převod magnetometrického NIC-MLA logu do IAGA-2002.**

---

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

*(Překlad může zaostávat za anglickým originálem — závazná je anglická verze.)*

[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](https://opensource.org/licenses/MIT)

---

```
   .mla  ──▶  [NIC-DMD dekódování, je-li komprimováno]  ──▶  kalibrované nT po složkách  ──▶  IAGA-2002
```

> **Co to je.** Jedna ze samostatných NIC datových knihoven (vedle NIC-MLA, NIC-DMD,
> NIC-MSEED). **IAGA-2002** je výměnný formát pozemní geomagnetiky — formát
> INTERMAGNETu a vstup **[SuperMAGu](https://supermag.jhuapl.edu/)** (~600 variometrů
> po světě). NIC-Gauss je variometr (hlásí *odchylku* pole, ne absolutní hodnoty),
> takže data odcházejí deklarovaná `Data Type: variation` — přesně třída, kterou
> SuperMAG bere; absolutní baseline zůstává práce observatoří (variometrická
> doktrína, NIC-Heimdall `gauss/README.md`). NIC-IAGA je ten most — přečte `.mla`,
> rozbalí NIC-DMD bloby, aplikuje kalibraci ze SCHEMA
> (`fyzikální = (raw + offset) · 10^exp10` → **nT, ne county**) a zapíše standardní
> IAGA-2002 text, jeden soubor na stanici. **Hotová knihovna, ne framework.**

> **Kde žije kalibrace — jediný záměrný rozdíl proti NIC-MSEED.** miniSEED nese
> surové county a kalibraci nechává na StationXML metadatech; IAGA-2002 nese
> **fyzikální nT**, takže tenhle exportér kalibraci aplikuje na cestě ven. Oba čtou
> tentýž archiv — archiv sám zůstává raw (derive-from-raw).

## Dvě vrstvy

- **`iaga`** — jádro nezávislé na kontejneru: řádky `(unix_s, x, y, z[, f])` v nT →
  IAGA-2002 text (12 povinných 70znakových hlavičkových záznamů, komentáře, hlavička
  sloupců, 67znakové datové řádky; chybějící = `99999.00`, neměřeno = `88888.00`),
  plus minimální čtečka pro round-trip testy.
- **`from_mla`** — konvertor, který k jádru připojí **NIC-MLA + NIC-DMD**: DMD replay
  po stanicích, autodetekce polí X/Y/Z(/F) (nebo jmenovitě), kalibrace, metadata
  stanice z MLA STATION tabulky.

## Rychlý start

```python
from nic_iaga import export_mla_to_iaga

export_mla_to_iaga(
    "gauss.mla", "gauss.iaga2002",
    stations={1: dict(iaga_code="NIC1", latitude=50.086, longitude=14.416,
                      elevation_m=235)},
    sampling="60 seconds", interval_type="1-minute")
```

## Testy

```sh
python3 tests/test_iaga.py       # čistý writer: tvar hlavičky, šířky, round-trip
python3 tests/test_from_mla.py   # end-to-end: MLA (+DMD) → IAGA-2002 → zpětné čtení
```

Vendorované závislosti (`nic_mla`, `nic_dmd`) žijí v `third_party/`, stejně jako u
NIC-MSEED, NIC-GLUE-IN a NIC-VDE.

## Licence

MIT — Copyright (c) 2026 NIC — Native Intellect Community
