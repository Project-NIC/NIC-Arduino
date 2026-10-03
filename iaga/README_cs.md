<p align="center">
  <img src="NICIAGA.svg" width="200"/>
</p>

# NIC-IAGA

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

*Závazná je anglická verze.*

**Samostatná datová knihovna NIC — převede log magnetometru NIC-MLA na IAGA-2002.**

---

[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](https://opensource.org/licenses/MIT)

---

```
   .mla  ──▶  [NIC-DMD decode if compressed]  ──▶  calibrated nT per component  ──▶  IAGA-2002
```

> **Co to je.** Jedna ze samostatných datových knihoven NIC (vedle NIC-MLA,
> NIC-DMD, NIC-MSEED). **IAGA-2002** je výměnný formát pozemního geomagnetismu —
> vlastní formát INTERMAGNET a to, co **[SuperMAG](https://supermag.jhuapl.edu/)** přijímá
> ze svých ~600 variometrů po celém světě. NIC-Gauss je variometr (hlásí *odchylku*
> pole, ne absolutní hodnoty), takže jeho data odcházejí deklarovaná jako `Data Type: variation` —
> přesně ta třída, kterou SuperMAG přijímá; absolutní základní úroveň zůstává úkolem observatoří
> (doktrína variometru). NIC-IAGA je most —
> čte `.mla`, dekomprimuje bloby NIC-DMD, aplikuje kalibraci ze SCHEMA
> (`physical = (raw + offset) · 10^exp10` → **nT, ne počty impulzů (counts)**) a zapisuje standardní
> text IAGA-2002, jeden soubor na stanici. **Hotová knihovna, ne framework.**

> **Kde žije kalibrace — jediný záměrný rozdíl oproti NIC-MSEED.**
> miniSEED nese surové počty (counts) a kalibraci ponechává na metadatech StationXML; IAGA-2002
> nese **fyzikální nT**, takže tento exportér aplikuje kalibraci ze SCHEMA cestou
> ven. Oba čtou tentýž archiv — archiv sám zůstává surový (odvozuj ze surových dat).

## Dvě vrstvy

- **`iaga`** — jádro nezávislé na kontejneru: řádky `(unix_s, x, y, z[, f])` jako nT floaty →
  text IAGA-2002 (12 povinných 70znakových záznamů hlavičky, komentáře, hlavička sloupců,
  67znakové datové řádky; chybějící = `99999.00`, nepozorované = `88888.00`) a k tomu minimální
  čtečka pro testy zpětného převodu (round-trip).
- **`from_mla`** — převodník, který napojuje **NIC-MLA + NIC-DMD** na toto jádro:
  přehrání DMD pro každou stanici zvlášť, automatická detekce polí X/Y/Z(/F) (nebo podle názvu), kalibrace, metadata
  stanic z tabulky STATION v MLA.

## Čas

**Každý řádek nese vlastní časovou značku** — IAGA-2002 je textová tabulka, ne ukotvená
řada, takže na rozdíl od NIC-MSEED se čas čte z každého záznamu: `timestamp` je
celá sekunda, `subsec` určuje polohu uvnitř této sekundy. `subsec_unit="index"` je
výchozí hodnota a to, co zapisuje stanice NIC — `subsec` je index snímku na
mřížce s mocninou dvou a zlomek sekundy je `subsec / sample_rate_hz`, přesně. Proud dat
z observatoře, označený celými sekundami, ponechává `subsec` na 0 a nepotřebuje žádnou
vzorkovací frekvenci; `"ms"` je k dispozici pro log s časovými značkami v milisekundách, volatelný objekt (callable) pro cokoli
jiného. **Formát zapisuje časovou značku s přesností na milisekundu** (`hh:mm:ss.sss`) — to je
dáno IAGA-2002 a je to spodní hranice přesnosti tohoto exportu, nikoli archivu.

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
python3 tests/test_iaga.py       # the pure writer: header shape, widths, round-trip
python3 tests/test_from_mla.py   # end-to-end: MLA (+DMD) → IAGA-2002 → parse-back
```

Přibalené závislosti (`nic_mla`, `nic_dmd`) jsou uloženy v `third_party/`, stejně
jako je přibalují NIC-MSEED, NIC-GLUE-IN a NIC-VDE.

## Licence

MIT — Copyright (c) 2026 NIC — Native Intellect Community
