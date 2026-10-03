<p align="center">
  <img src="NICMSEED.svg" width="200"/>
</p>

# NIC-MSEED

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

*Závazná je anglická verze.*

**Samostatná datová knihovna NIC — převede log NIC-MLA na miniSEED (Steim-1 / Steim-2).**

---

[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](https://opensource.org/licenses/MIT)

---

```
   .mla  ──▶  [NIC-DMD decode if compressed]  ──▶  per-channel int counts  ──▶  miniSEED
```

> **Co to je.** Jedna ze samostatných datových knihoven NIC (vedle NIC-MLA,
> NIC-DMD, NIC-KSF). Uzel NIC zaznamenává své vzorky do kontejneru NIC-MLA; **miniSEED**
> je lingua franca seismologie, kterou lze rovnou použít v **ObsPy, SeisComp, SWARM**
> a v nástrojích FDSN. NIC-MSEED je most — čte `.mla`, dekomprimuje
> bloby NIC-DMD, vytáhne surové celočíselné hodnoty (counts) pro každý kanál SCHEMA a zapíše
> standardní záznamy miniSEED. Použije ji každý, kdo má seismický log MLA (např. z **NIC-Quake**)
> a potřebuje SEED — **hotová knihovna, ne framework.** (Pro
> ad hoc prohlížení libovolného logu MLA v CSV / SQLite použijte NIC-GLUE-OUT; miniSEED je
> seismologická cesta.)

## Dvě implementace

- **Python** (`nic_mseed/`) — referenční: čistý Python 3.10+, žádné externí balíčky.
- **C** (`c/`) — stejný kodek Steim-1/2 + zapisovač miniSEED v přenositelném C, pro
  export přímo v zařízení / ve vestavěných systémech. Obě jsou otestované na hostiteli a procházejí testy tam i zpět
  proti testovacím vektorům té druhé.

## Dvě vrstvy

- **`steim` / `mseed`** — jádro nezávislé na kontejneru: celá čísla → rámce Steim-1/2
  → záznamy miniSEED, a zpět (minimální čtecí program pro testy tam i zpět). Bez závislostí.
- **`from_mla`** — převodník, který napojuje **NIC-MLA + NIC-DMD** na toto jádro:
  přehrání DMD pro každou stanici, rozdělení kanálů řízené schématem, mapování kódů SEED.

## Rychlý start

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

## Jak se MLA mapuje na miniSEED

| miniSEED potřebuje | pochází z |
|---|---|
| počáteční čas (BTIME) | `timestamp` (u32 s) + `subsec` (u16) prvního záznamu MLA |
| vzorkovací frekvence | **dodáváte ji vy** (`sample_rate_hz` = ODR zařízení); `subsec` pouze ukotvuje fázi v rámci sekundy |
| celočíselné hodnoty (counts) | užitečná data MLA rozdělená podle polí SCHEMA (surová, nebo dekomprimovaná z NIC-DMD) — *surové* hodnoty, ne škálovaná fyzikální hodnota (kalibrace patří do StationXML) |
| síť/stanice/umístění | tabulka STATION v MLA (nebo `station_map`) |
| kód kanálu | název pole SCHEMA (nebo `channel_map`) |

Každá dvojice `(station, field)` se stane jedním kanálem miniSEED. Převodník předpokládá
rovnoměrně vzorkovanou, souvislou řadu pro každý kanál (což platí pro synchronizovaný sběr,
např. **NIC-Quake**); dělení podle mezer je ponecháno na pozdější průchod.

## Jak se počítají časové hlavičky

**Kotva a index — čas záznamu se nikdy nečte pro každý vzorek.** Čas se čte jen z *prvního*
záznamu kanálu: `t0 = timestamp + subsec / sample_rate_hz`.
To je jediné místo, kde se `subsec` používá; ukotvuje fázi prvního vzorku a
nic jiného. Každý záznam miniSEED pak dostane `t0 + i / sample_rate_hz`, kde `i`
je počet již vydaných vzorků — počítáno pokaždé od `t0`, nikdy
od předchozí hlavičky, takže se nic nekumuluje. Celé sekundy jdou do kalendářních
polí BTIME, zbytek do posledního pole BTIME a frekvence se zapíše jako
dvojice SEED `(factor, multiplier)`: 128 Hz je `(128, 1)`, přesně.

`subsec_unit="index"` je to, co zapisuje stanice NIC — `subsec` je index snímku
na mřížce s mocninou dvou, takže `subsec / sample_rate_hz` je přesný binární zlomek.
`"ms"` slouží pro log s časovými značkami v milisekundách; cokoli jiného zpracuje volatelný objekt (callable).

**Zlomková část BTIME má rozlišení 0,0001 s a to je spodní mez exportu.** Při 128 Hz trvá
vzorek 7812,5 µs, takže jen každá osmá hranice vzorku připadne na celých 100 µs
a hranice záznamu padne tam, kam ji umístí balení Steim — začátek záznamu je
proto zaokrouhlen, až o 50 µs. Pole `time correction` je ve stejné
jednotce 0,0001 s a nic nepřinese. Toto je SEED 2.4; miniSEED v3 nese počáteční čas
v nanosekundách. **Archiv si zachovává plné rozlišení — ztráta vzniká v hlavičce SEED,
ne v `.mla`.**

## Doprovodný soubor s metadaty StationXML

miniSEED nese *data*; nástroje FDSN potřebují i *metadata* — identitu
stanice, souřadnice, vzorkovací frekvenci a citlivost counts→fyzikální hodnota. To je
**StationXML** a `nic_mseed/to_stationxml.py` ho generuje (FDSN StationXML 1.1):

```python
from nic_mseed import StationXmlExporter

StationXmlExporter(
    sample_rate_hz=100.0,        # MUST match the rate used for the miniSEED export
    network="NQ",                # same constructor args as MseedExporter
).export("quake.mla", "quake.xml")
```

**Tvoří pár s miniSEED**: kódy Network/Station/Location/Channel (NSLC)
a vzorkovací frekvence se berou ze *stejného* `MseedExporter`, jaký používá `from_mla.py`,
takže ObsPy / SeisComp připojí metadata k datům už z principu konstrukce. Prefix MLA
dodá zbytek: identita GPS (`dl_gps`) → Latitude/Longitude, pole
i16 → Elevation, 32bajtový název → `<Site><Name>` a `exp10` každého pole DATA
→ `<InstrumentSensitivity>` (celkový zisk = counts na fyzikální jednotku =
`10**-exp10`) s jednotkou pole (`m_s`→`m/s`, `degC`, `Pa`, …) jako vstupem a
`count` jako výstupem.

Dvě upřímně přiznaná omezení (uvedená také v modulu a v XML):

- **Plochá odezva.** Každý kanál nese jen `<InstrumentSensitivity>` (skalární
  stejnosměrný zisk) — žádné póly/nuly ani kaskádu stupňů, protože MLA nenese
  frekvenční odezvu. Přesné pro meteorologická čidla s plochou odezvou; aproximace prvního řádu
  pro seismické kanály MEMS. **Nestačí** pro skutečnou dekonvoluci
  přístroje.
- **Souřadnice vyžadují identitu GPS.** Latitude/Longitude pocházejí z identity
  `dl_gps`. Hierarchická identita `dl_ident` nenese žádné souřadnice — předejte
  přepis `coords={index: (lat, lon)}`, jinak generátor vyvolá výjimku (nikdy potichu
  nezapíše 0,0). Neznámá nadmořská výška (zarážková hodnota 0x8000) se zapíše jako
  zástupná hodnota `0`.

```bash
python3 -m nic_mseed.to_stationxml quake.mla quake.xml --rate 100 --network NQ
python3 tests/test_to_stationxml.py         # emitter + pairing (+ ObsPy schema check if installed)
```

## Ověření

Kodek a zapisovač procházejí tam i zpět vlastním minimálním čtecím programem tohoto balíčku.
Test miniSEED navíc ověřuje proti **ObsPy**, pokud je nainstalováno — spusťte
`python3 tests/test_mseed.py` na počítači s ObsPy a získáte referenční důkaz
shody se specifikací.

## Struktura

```
nic_mseed/          Python: steim (codec) + mseed (writer) + from_mla (converter) + to_stationxml (metadata)
c/                  C: portable Steim-1/2 codec + miniSEED writer (+ tests, CMake)
examples/           runnable MLA → miniSEED demo
tests/              codec round-trip, writer, end-to-end converter, and StationXML tests
third_party/        vendored NIC-MLA + NIC-DMD (see VENDORED.md)
```

Referenční implementace v Pythonu je čistý Python 3.10+, bez externích balíčků (ObsPy je volitelná
kontrola *pouze pro testy*). Sestavení v C lze otestovat na hostiteli pomocí CMake:

```bash
cmake -S c -B c/build && cmake --build c/build && ctest --test-dir c/build --output-on-failure
```

## Licence

Licence MIT — Copyright (c) 2026 NIC — Native Intellect Community

---

## Poděkování

Mému bratrovi za rady během vývoje tohoto projektu.
Za technickou pomoc s optimalizací kódu AI asistentům Claude (Anthropic) a Gemini (Google).
