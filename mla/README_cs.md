<p align="center">
  <img src="NICMLA.svg" width="200"/>
</p>

---

# NIC-MLA

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

*Závazná je anglická verze.*


[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](https://opensource.org/licenses/MIT)

---

**Matroshka Logging Archive** — univerzální jednosouborový kontejner pro ukládání
dat z měřicích stanic. Data i log jsou v **jednom přenosném
souboru**, čitelném napříč platformami od 8bitového mikrokontroléru po PC.

Jeden soubor, jeden formát, jeden způsob čtení — vytáhnete kartu ze zařízení, zasunete
ji do počítače a máte všechno. Žádný zvěřinec formátů.

> Úplná specifikace formátu: **[`DESIGN-MLA.md`](DESIGN-MLA_cs.md)** · poznámky k vydání: [`RELEASE_NOTES_v1.2.md`](RELEASE_NOTES_v1.2_cs.md) — **v1.2 je finální verze**
>
> Záznam více typů stanic do jednoho souboru (datalogger / opakovač):
> **[`DESIGN-MLA-datalogger.md`](DESIGN-MLA-datalogger_cs.md)**

## Hlavní vlastnosti

- **Jeden soubor = data + log.** Dva proudy rostou proti sobě: data odshora,
  log odspodu.
- **Hloupý kontejner.** MLA pouze ukládá bajty. Veškerá inteligence (komprese,
  šifrování, převod čísel stanic, LoRa/Wi-Fi) sídlí v samostatné vrstvě glue
  — MLA zůstává malý a nikdy nepřekáží.
- **Drobný 16B záznam logu, celý chráněný CRC.** Žádný trik s „příznaky mimo CRC“:
  záznam se zneplatní přepsáním nulami — jeho CRC pak nesedí a
  čtecí programy ho přeskočí.
- **Odolný proti výpadkům.** Commit protokol „nejprve LOCK, potom DATA“ + CRC16 (CCITT-FALSE).
  Po resetu se poslední záznam buď ověří (pokračuje se), nebo se vynuluje a jeho
  místo se znovu využije. Na disku není žádný vyhledávací strom, který by se mohl poškodit.
- **Samopopisný.** Prefix nese tabulku SCHEMA (8znakové názvy polí +
  jednotky → připraveno pro export do CSV/SQL bez jakékoli předchozí znalosti) a tabulku STATION
  (1bajtový index stanice v každém záznamu logu → skutečné číslo stanice).
- **Malý, vhodný pro mikrokontrolér.** ATmega328 (2 KB RAM) pouze zapisuje; žádná
  dynamická alokace, největší buffer 32 B. Vyhledávání a čtení probíhá na hostiteli.
- **Rotace souborů.** Když se jeden soubor zaplní, začne se další; velké objemy =
  mnoho menších souborů, hostitel je čte jako celek.
- **32bitové adresování** → jeden soubor až 4 GB (nad tuto mez rotace).
- **Volitelná komprese.** Kontejner komprimovaná data pouze označí (jeden
  bit `compressed` v záznamu) a vede `kf_back` (vzdálenost zpět k
  příslušnému klíčovému snímku); metodu komprese nedefinuje — který kodek /
  klíčový snímek, to je uvedeno ve vlastní hlavičce datového bloku (např. NIC-DMD).
- **Nezávislý na souborovém systému.** Přístup přes tenkou HAL (4 funkce);
  FAT16 / FAT32 / exFAT / NTFS / ext4 obsluhuje vrstva pod ní
  (OS, SdFat nebo FatFs).

## Struktura souboru

```
offset 0                                                              EOF
┌──────────────────┬──────────────────┬───────────────┬──────────────┐
│ PREFIX           │ DATA  stream  →   │   free  0xFF   │   ← LOG stream│
│ 1–255 sectors    │ (grows up)        │               │ (grows down)  │
│ (512 B each)     │                   │               │               │
└──────────────────┴──────────────────┴───────────────┴──────────────┘
```

- **Prefix:** 34B hlavička + tabulky SCHEMA a STATION, pokryté CRC16
  v posledních 2 bajtech. Obvykle jeden sektor 512 B; roste po celých sektorech
  (až 255 ≈ 127 KB), jen pokud to tabulky vyžadují.
- **Datový blok:** `MAGIC(2) + payload(1..65535) + CRC16(2)`
- **Záznam logu (16 B), celý pokrytý CRC:** offset, časová značka, subsec
  (dva neprůhledné bajty, jejichž význam určuje glue), délka, příznaky (bit7 = compressed,
  bity0-6 = kf_back; 0 = klíčový snímek), stanice (1bajtový index), CRC16.

## Struktura repozitáře

| Cesta | Obsah |
|---|---|
| `nic_mla.py` | Referenční jádro v Pythonu (format / mount / append / read / scan / recover) |
| `nic_mla_archive.py` | Python: rotace souborů (`MlaArchive`) + dotazy na straně hostitele (`mla_query`) |
| `tools/mla_schema.py` | Sestavení/čtení tabulek SCHEMA + STATION; dekódování užitečných dat pro CSV/SQL |
| `nic_mla_test.py` | Sada testů (Python) |
| `c/` | Knihovny v C: pouze zápis (MCU) + úplná (ARM/PC) + adaptéry HAL |
| `DESIGN-MLA.md` | Návrhová specifikace formátu |

## Rychlý start — Python

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

Rotace přes více souborů a filtrování:

```python
from nic_mla_archive import MlaArchive, mla_query
with MlaArchive("/data") as arch:          # MLA00000.MLA, MLA00001.MLA, …
    arch.append(ts, station=1, data=payload)
for rec, data in mla_query(MlaArchive("/data"), station=1, time_from=t0, time_to=t1):
    ...
```

Samopopisný soubor (tabulky schématu + stanic → připraveno pro export do CSV/SQL):

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

Testy:

```sh
python3 nic_mla_test.py
```

## Rychlý start — C

Dvě knihovny sdílejí jednu definici formátu (`c/nic_mla_format.h`):

- **pouze zápis** (`c/nic_mla_write.{h,c}`) — pro ATmega / malá Arduina,
- **úplná** (`c/nic_mla.{h,c}`) — pro ARM Arduino / PC (+ čtení, dotazy, obnova).

HAL (4 funkce) napojíte na svůj souborový systém. Hotové adaptéry v `c/hal/`:

| Platforma | „Pod HAL“ | Adaptér |
|---|---|---|
| Raspberry Pi / PC (SSD, SD, USB) | OS: ext4 / exFAT / NTFS / FAT32 / FAT16 | `hal/nic_mla_hal_posix.{h,c}` |
| Arduino AVR / ESP / STM32duino | SdFat | `examples/atmega_sd_writeonly.ino` |
| STM32 bare-metal (CubeIDE/HAL) | FatFs (ChaN) | `hal/nic_mla_hal_fatfs.{h,c}` |

Sestavení a test na PC:

```sh
cd c
cc -std=c99 -Wall -Wextra -O2 nic_mla_test.c nic_mla.c nic_mla_write.c \
   hal/nic_mla_hal_posix.c -o mlatest
./mlatest
```

Viz **[`c/README.md`](c/README_cs.md)**.

## Poznámky pro integrátory

- **Názvy stanic nejsou v souboru.** Tabulka STATION ukládá pro každou stanici 8bajtovou
  neprůhlednou identitu + 2bajtovou nadmořskou výšku (i16 LE, metry); co
  identita znamená (region / číslo / GPS / …), rozhoduje vaše vrstva glue,
  která si vede vlastní mapování „8 bajtů → význam“. Log nese jen 1bajtový
  index — převést ho na skutečné číslo stanice je úkolem glue, ne
  kontejneru.
- **Pole `subsec` jsou dva neprůhledné bajty, které patří glue.** MLA jim nepřisuzuje
  žádný význam a nikdy na ně nesahá. Název je záměrně dvojznačný: sub-**sec**ond
  (čas v rámci sekundy) *i* sub-**sec**tion (podsekce, např. index rotace / sekce). Vaše glue může
  2 bajty (0..65535) použít jako jednu 16bitovou hodnotu, jako dva nezávislé bajty, nebo
  pro několik věcí současně — např. horní bajt = sekce/rotace, dolní bajt =
  subsekundový tik, takže MLA dobře zvládne vzorkování výrazně nad 1 Hz (např. seismické). Pokud
  se nepoužívá, nastavte ho na 0.

## Přenos dat (LoRa / síť)

**Mimo rozsah projektu** — kontejner slouží k ukládání, ne k přenosu. Každý záznam je
soběstačný (offset + délka + příznaky + CRC), takže poslat ho přes LoRa/síť znamená
„vzít bajty záznamu a odeslat je“. Volbu přenosu projekt ponechává
na uživateli.

## Stav

Referenční implementace v Pythonu i v C jsou kompletní, otestované a **bajt po bajtu
shodné** (soubor zapsaný knihovnou v C přečte Python a naopak).

## Licence

Licence MIT — Copyright (c) 2026 NIC — Native Intellect Community

---

## Poděkování

Mému bratrovi za rady během vývoje tohoto projektu.
Za technickou pomoc s optimalizací kódu AI asistentům Claude (Anthropic) a Gemini (Google).
