# NIC-MSEED

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

**Samostatná datová knihovna NIC — převod NIC-MLA logu do miniSEED (Steim-1 / Steim-2).**

---

[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](https://opensource.org/licenses/MIT)

---

```
   .mla  ──▶  [dekód NIC-DMD, je-li komprimováno]  ──▶  celočíselné counts po kanálech  ──▶  miniSEED
```

> **Co to je.** Jedna ze samostatných datových knihoven NIC (vedle NIC-MLA, NIC-DMD,
> NIC-KSF). NIC node zaloguje vzorky do NIC-MLA kontejneru; **miniSEED** je lingua
> franca seismologie: zapadne rovnou do **ObsPy, SeisComp, SWARM** a celého FDSN
> toolchainu. NIC-MSEED je ten most — přečte `.mla`, dekomprimuje NIC-DMD bloby,
> vytáhne syrové celočíselné counts po SCHEMA kanálech a zapíše standardní miniSEED
> záznamy. Kdo má seismický MLA log (např. z **NIC-Quake** / **NIC-Station**) a
> potřebuje SEED, použije to — **funkční knihovna, ne framework.** (Na ad-hoc kontrolu
> jakéhokoli MLA logu v CSV / SQLite slouží NIC-GLUE-OUT; miniSEED je seismo cesta.)

## Dvě implementace

- **Python** (`nic_mseed/`) — reference: čistý Python 3.10+, žádné externí balíčky.
- **C** (`c/`) — tentýž Steim-1/2 kodek + miniSEED zapisovač v přenositelném C, pro
  on-device / embedded export. Obě jsou host-testované a round-tripují proti vektorům
  té druhé.

## Dvě vrstvy

- **`steim` / `mseed`** — jádro nezávislé na kontejneru: celá čísla → Steim-1/2 rámce
  → miniSEED záznamy, a zpět (minimální čtečka pro round-trip testy). Bez závislostí.
- **`from_mla`** — konvertor, který napojí **NIC-MLA + NIC-DMD** na to jádro:
  per-stanice DMD replay, rozdělení kanálů podle schématu, mapování SEED kódů.

## Rychlý start

```python
from nic_mseed import MseedExporter, STEIM2

stats = MseedExporter(
    sample_rate_hz=100.0,        # ODR zařízení — miniSEED potřebuje vzorkovací frekvenci; MLA ji neukládá
    network="NQ",                # SEED kód sítě
    version=STEIM2,              # nebo STEIM1
    channel_map={"z": "HHZ", "n": "HHN", "e": "HHE"},   # pole SCHEMA → SEED kanál
).export("quake.mla", "quake.mseed")
print(stats)   # {channels, samples, records, bytes, out}
```

```bash
python3 examples/mla_to_mseed.py            # postaví vzorový .mla, převede, vypíše statistiky
python3 tests/test_steim.py                 # round-trip Steim-1/2 kodeku
python3 tests/test_mseed.py                 # miniSEED zapisovač (+ ObsPy zlatý standard, je-li nainstalován)
python3 tests/test_from_mla.py              # end-to-end MLA(+DMD) → miniSEED round-trip
python3 tests/test_to_stationxml.py         # metadata StationXML (+ kontrola schématu ObsPy, je-li nainstalován)
```

## Jak se MLA mapuje na miniSEED

| miniSEED potřebuje | bere se z |
|---|---|
| čas začátku (BTIME) | MLA `timestamp` (u32 s) + `subsec` (u16) prvního záznamu |
| vzorkovací frekvence | **dodáš ji ty** (`sample_rate_hz` = ODR zařízení); `subsec` jen ukotví sub-sekundovou fázi |
| celočíselné counts | MLA payload rozdělený po polích SCHEMA (syrový, nebo NIC-DMD dekomprimovaný) — *syrové* counts, ne škálovaná fyzikální hodnota (kalibrace patří do StationXML) |
| network/station/location | MLA STATION tabulka (nebo `station_map`) |
| kód kanálu | název pole SCHEMA (nebo `channel_map`) |

Každá dvojice `(stanice, pole)` se stane jedním miniSEED kanálem. Konvertor
předpokládá rovnoměrně vzorkovanou, souvislou řadu na kanál (platí pro synchronizovaný
sběr, např. **NIC-Quake**); dělení na mezery (gaps) řeší až pozdější průchod.

## Metadatový sidecar StationXML

miniSEED nese *data*; FDSN nástroje potřebují i *metadata* — identitu stanice,
souřadnice, vzorkovací frekvenci a citlivost count→fyzikální hodnota. To je
**StationXML** a `nic_mseed/to_stationxml.py` jej emituje (FDSN StationXML 1.1):

```python
from nic_mseed import StationXmlExporter

StationXmlExporter(
    sample_rate_hz=100.0,        # MUSÍ se shodovat s frekvencí použitou pro export miniSEED
    network="NQ",                # stejné argumenty konstruktoru jako MseedExporter
).export("quake.mla", "quake.xml")
```

**Páruje se s miniSEED**: kódy Network/Station/Location/Channel (NSLC) i vzorkovací
frekvence se berou ze *stejného* `MseedExporter`, který používá `from_mla.py`, takže
ObsPy / SeisComp přiřadí metadata k datům už z principu. Zbytek dodá MLA prefix:
GPS identita (`dl_gps`) → Latitude/Longitude, pole i16 → Elevation, 32bajtový název →
`<Site><Name>` a `exp10` každého DATA pole → `<InstrumentSensitivity>` (celková
citlivost = counts na fyzikální jednotku = `10**-exp10`) s jednotkou pole
(`m_s`→`m/s`, `degC`, `Pa`, …) jako vstup a `count` jako výstup.

Dvě poctivá omezení (uvedená i v modulu a v XML):

- **Plochá odezva.** Každý kanál nese jen `<InstrumentSensitivity>` (skalární DC
  zisk) — žádné póly/nuly ani kaskádu stupňů, protože MLA frekvenční odezvu nenese.
  Přesné pro ploché meteo senzory; aproximace prvního řádu pro MEMS seismo kanály.
  **Nestačí** pro skutečnou dekonvoluci přístroje.
- **Souřadnice vyžadují GPS identitu.** Latitude/Longitude pocházejí z `dl_gps`
  identity. Hierarchická `dl_ident` identita souřadnice nenese — předej override
  `coords={index: (lat, lon)}`, jinak emitor vyhodí chybu (nikdy tiše nezapíše 0,0).
  Neznámá nadmořská výška (sentinel 0x8000) se zapíše jako zástupná `0`.

```bash
python3 -m nic_mseed.to_stationxml quake.mla quake.xml --rate 100 --network NQ
python3 tests/test_to_stationxml.py         # emitor + párování (+ kontrola schématu ObsPy, je-li nainstalován)
```

## Validace

Kodek i zapisovač projdou round-tripem přes vlastní minimální čtečku tohoto balíku.
miniSEED test navíc validuje proti **ObsPy**, je-li nainstalován — spusť
`python3 tests/test_mseed.py` na stroji s ObsPy pro zlatý standard shody se specifikací.

## Rozložení

```
nic_mseed/          Python: steim (kodek) + mseed (zapisovač) + from_mla (konvertor) + to_stationxml (metadata)
c/                  C: přenositelný Steim-1/2 kodek + miniSEED zapisovač (+ testy, CMake)
examples/           spustitelné demo MLA → miniSEED
tests/              round-trip kodeku, zapisovač, end-to-end konvertor a testy StationXML
third_party/        vendorované NIC-MLA + NIC-DMD (viz VENDORED.md)
```

Python reference je čistý Python 3.10+, žádné externí balíčky (ObsPy je volitelná
kontrola *jen pro testy*). C build se host-testuje přes CMake:

```bash
cmake -S c -B c/build && cmake --build c/build && ctest --test-dir c/build --output-on-failure
```

## Licence

MIT License — Copyright (c) 2026 NIC — Native Intellect Community

---

## Poděkování

Bratrovi za rady při tvorbě tohoto projektu.
Za technickou asistenci s optimalizací kódu AI asistentům Claude (Anthropic) a Gemini (Google).

★ Viva La Resistánce ★
