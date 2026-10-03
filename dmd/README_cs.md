<p align="center">
  <img src="NICDMD.svg" width="200"/>
</p>

★ N.I.C. ★

# NIC DMD — Delta Markov Duda

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

*Závazná je anglická verze.*

## Kompresní protokol pro vestavěná zařízení

[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](https://opensource.org/licenses/MIT)

---

## Co je DMD?

DMD je multiplatformní kompresní protokol pro malé datové pakety z meteostanic, elektroměrů, GPS trackerů a dalších vestavěných zařízení. Je navržen pro přenos technologiemi s omezenou šířkou pásma, jako je LoRa.

Protokol je plně funkční na mikrokontroléru ATmega328 a nevyžaduje v paměti žádné velké slovníky ani vyhledávací tabulky. Každý paket je komprimován bez sdíleného slovníku a bez přenášené tabulky — pomocí adaptivního výběru nejlepší metody z pěti kandidátů. **Výjimkou je delta fáze, a ta je pro přenos podstatná:** paket je delta-kódován vůči *předchozímu* paketu a kodér se každý 7. paket (`DMD_KEYFRAME_EVERY`) znovu synchronizuje klíčovým snímkem. Jeden ztracený paket tedy může znehodnotit až šest dalších. Na spolehlivém spoji to nic nestojí; ztrátový spoj musí buď při odesílání vynucovat klíčové snímky, nebo místo toho přenášet bezstavový rámec.

---

## Proč DMD?

Stávající kompresní knihovny pro vestavěná zařízení buď vyžadují stovky bajtů RAM navíc (Heatshrink), nebo musí spolu s daty přenášet Huffmanovu tabulku. DMD volí jiný přístup — kombinuje několik jednoduchých metod s heuristickou analýzou a pro každý paket zvlášť vybere nejlepší výsledek.

**Hlavní výhody:**
- Pevná Huffmanova tabulka pouze v ROM (64B), žádná RAM navíc
- Adaptivní výběr metody pro každý paket — až 5 kandidátů
- Plně deterministická dekomprese — žádná ztráta dat
- Maximální nárůst dat o 1 bajt (hlavička) v nejhorším případě
- Implementace v Pythonu i v C (ATmega328 / Arduino)

---

## Kdy se DMD nevyplatí

DMD je navržen pro data, která se v čase mění pomalu a předvídatelně — hodnoty ze senzorů, souřadnice GPS, průmyslová telemetrie. Pokud jsou vstupní data náhodná, šifrovaná nebo již komprimovaná, DMD přidá jen 1 bajt hlavičky a odešle je jako RAW. To je správné chování — žádná ztrátová komprese, žádná degradace.

---

## Kompatibilita

**Python:** 3.10 nebo novější (používá typové anotace `bytes | None`).

**C:** C99 nebo novější. Testováno s GCC na PC (Linux/Windows) a s AVR-GCC pro ATmega328. Žádné závislosti na standardní knihovně kromě `<string.h>`. Vnitřní buffery jsou dimenzovány pomocí C99 VLA podle skutečné délky paketu.

**Arduino:** Zkopírujte `c/nic_dmd.c` a `c/nic_dmd.h` do složky svého projektu. Kompatibilní s Arduino IDE 1.8+ a 2.x (AVR-GCC podporuje C99 VLA).

**Poznámka k jiným překladačům:** IAR, Keil a MSVC C++ nepodporují VLA. Pro tyto toolchainy můžete při překladu definovat `-DDMD_PKT_MAX_BUILD=N` (např. 32 nebo 64) a buffery budou mít pevnou velikost.

**Závislosti pro fetch/benchmark:** `pip install requests`

**Délka paketu:** Minimální technický limit je 1B, ale pod 16B je komprese prakticky bezcenná — režie hlavičky (1B) a stav ANS (2B) spotřebují většinu potenciální úspory. Doporučené minimum je **16B**. Maximum je **255B**. Pro přenos přes LoRa je praktický limit užitečných dat 51–64B v závislosti na spreading factoru a regionu. Nejlepších výsledků dosahuje DMD u dat, kde se sousední pakety mění pomalu — typicky u telemetrie ze senzorů o velikosti 16–64B.

---

## Validace a integrita dat

V zájmu maximálního výkonu a absolutní minimalizace zátěže procesoru knihovna neprovádí žádné dodatečné kontroly hlavičky ani validaci délky vstupních dat.

Návrh protokolu striktně předpokládá, že kontroly integrity (např. hardwarové CRC) a zahazování poškozených nebo prázdných paketů zajišťuje nižší transportní vrstva nebo hlavní program (typicky samotný rádiový modul, logika sběru dat apod.). Uživatelé knihovny musí na aplikační úrovni zajistit, aby se do kompresních a dekompresních funkcí předávala pouze strukturálně správná data. Přenesením této odpovědnosti bylo dosaženo nízké paměťové režie bez plýtvání cykly procesoru.

---

## Výsledky

Testováno na více než 50 000 vzorcích z 20 reálných a syntetických zdrojů dat (meteostanice, GPS, elektroměry, průmyslové senzory, seismologie, kvalita ovzduší). Chyby při zpětném převodu (round-trip): **0 ve všech datových sadách**.

Sloupec **výstup B/pkt** je průměrná skutečná velikost přenášeného paketu po kompresi (včetně 1B hlavičky). To je rozhodující údaj pro dimenzování vysílacího okna LoRa.

### Tabulka 1 — jednotné int16 (fetch_plus.py)

Všechna pole uložena jako `int16` se škálováním ×100, pakety doplněny nulami na pevnou délku. Datové sady předpovědí mají 384 vzorků (16 dní × 24 hodin), ostatní 8 000–10 000 vzorků.

```
===================================================================================
  Dataset                    | Pkts  | Input | Output  | Saving | Dominant method
------------------------------|-------|-------|---------|--------|------------------
NOAA San Francisco (tides)    |  8184 |  16 B |   6.4 B |  62.2% | DELTA1+ZZ+FLAG
NOAA New York (tides)         |  8184 |  16 B |   6.7 B |  60.6% | DELTA1+ZZ+FLAG
DWD Fichtelberg (meteo)       | 10000 |  16 B |   8.1 B |  52.6% | DELTA1+ZZ+FLAG 75%
DWD Helgoland (meteo)         | 10000 |  16 B |   8.5 B |  49.8% | DELTA1+ZZ+FLAG 74%
DWD Zugspitze (meteo)         | 10000 |  16 B |   8.6 B |  49.2% | DELTA1+ZZ+FLAG 73%
GPS Trek                      | 10000 |  16 B |   8.6 B |  49.3% | DELTA1+ZZ+FLAG 53%
Complex station               | 10000 |  64 B |  38.6 B |  40.7% | DELTA1+ZZ+HUF  84%
AirQuality Brno               |   168 |  16 B |  10.3 B |  39.7% | FLAG + D1+ZZ+FLAG
AirQuality Ostrava            |   168 |  16 B |  10.5 B |  38.4% | FLAG + D1+ZZ+FLAG
Electricity meters            | 10000 |  16 B |  10.6 B |  37.7% | DELTA1+ZZ+HUF  52%
AirQuality Prague             |   168 |  16 B |  10.6 B |  37.6% | FLAG + D1+ZZ+FLAG
Forecast Prague (32B)         |   384 |  32 B |  22.0 B |  33.2% | DELTA1+ZZ+FLAG 58%
Forecast Brno (32B)           |   384 |  32 B |  22.4 B |  32.1% | DELTA1+ZZ+FLAG 55%
IoT building                  | 10000 |  16 B |  11.7 B |  31.3% | DELTA1+ZZ+HUF  84%
Industrial sensor             | 10000 | 128 B |  89.3 B |  30.7% | DELTA1+ZZ+HUF  80%
Forecast Ostrava (16B)        |   384 |  16 B |  12.3 B |  27.3% | DELTA1+ZZ+FLAG 42%
Forecast Prague (16B)         |   384 |  16 B |  12.4 B |  26.8% | DELTA1+ZZ+FLAG 41%
Forecast Brno (16B)           |   384 |  16 B |  12.5 B |  26.5% | DELTA1+ZZ+FLAG 43%
Forecast Bratislava (16B)     |   384 |  16 B |  12.7 B |  25.3% | DELTA1+ZZ+FLAG 38%
USGS seismology               | 10000 |  16 B |  13.9 B |  18.2% | FLAG 29% (chaotic)
===================================================================================
  Range: 18 % – 62 %   |   Errors: 0
===================================================================================
```

### Tabulka 2 — těsné balení podle schématu (fetch_small.py)

Každé pole uloženo v nejmenším potřebném typu (uint8/int16) se škálováním ×10, bez doplňování nulami.

```
===================================================================================
  Dataset                    | Pkts  | Input | Output  | Saving | Dominant method
------------------------------|-------|-------|---------|--------|------------------
Forecast Prague (27B)         |   384 |  27 B |  17.1 B |  39.0% | DELTA1+ZZ+HUF  63%
Forecast Brno (27B)           |   384 |  27 B |  17.2 B |  38.5% | DELTA1+ZZ+HUF  61%
AirQuality Brno (12B)         |   168 |  12 B |   8.3 B |  35.9% | DELTA1+ZZ+HUF  49%
AirQuality Ostrava (12B)      |   168 |  12 B |   8.5 B |  34.8% | DELTA1+ZZ+HUF  47%
AirQuality Prague (12B)       |   168 |  12 B |   8.6 B |  34.2% | DELTA1+ZZ+HUF  44%
Forecast Ostrava (13B)        |   384 |  13 B |   9.3 B |  33.6% | DELTA1+ZZ+HUF  67%
Forecast Brno (13B)           |   384 |  13 B |   9.3 B |  33.3% | DELTA1+ZZ+HUF  69%
Forecast Prague (13B)         |   384 |  13 B |   9.3 B |  33.3% | DELTA1+ZZ+HUF  70%
Forecast Bratislava (13B)     |   384 |  13 B |   9.4 B |  32.5% | DELTA1+ZZ+HUF  72%
DWD Fichtelberg (9B)          | 10000 |   9 B |   6.3 B |  37.0% | D1+ZZ+ANS  49%
DWD Helgoland (9B)            | 10000 |   9 B |   6.4 B |  36.0% | D1+ZZ+ANS  42%
DWD Zugspitze (9B)            | 10000 |   9 B |   6.4 B |  35.6% | D1+ZZ+ANS  42%
USGS seismology (8B)          | 10000 |   8 B |   8.6 B |   3.9% | RAW 79% ⚠ expansion
NOAA New York (3B)            |  8184 |   3 B |   4.0 B |   0.0% | RAW 100% ⚠ expansion
NOAA San Francisco (3B)       |  8184 |   3 B |   4.0 B |   0.0% | RAW 100% ⚠ expansion
===================================================================================
  Range: 0 % – 39 %   |   Errors: 0
  ⚠ For packets < 8B, output is larger than input — header overhead (1B) outweighs savings.
===================================================================================
```

### Tabulka 3 — surový text JSON/CSV (fetch_raw_text.py)

Data přesně tak, jak byla přijata ze zdrojů — bez binárního balení, text jako bajty, doplněný nulami na délku prvního záznamu.

```
===================================================================================
  Dataset                    | Pkts  | Input  | Output  | Saving | Dom. method
------------------------------|-------|--------|---------|--------|---------------
DWD Helgoland (raw CSV)       | 10000 |  72 B  |  21.2 B |  71.0% | D1+ZZ+ANS 69%
DWD Zugspitze (raw CSV)       | 10000 |  72 B  |  21.3 B |  70.9% | D1+ZZ+ANS 68%
DWD Fichtelberg (raw CSV)     | 10000 |  72 B  |  21.4 B |  70.7% | D1+ZZ+ANS 67%
NOAA San Francisco (raw JSON) |  8448 |  72 B  |  26.7 B |  63.4% | D1+ZZ+FLAG 38%
NOAA New York (raw JSON)      |  8448 |  72 B  |  27.3 B |  62.6% | D1+ZZ+FLAG 37%
Forecast Bratislava (raw JSON)|   384 | 200 B  |  73.2 B |  63.6% | D1+ZZ+ANS  40%
===================================================================================
  Range: 63 % – 71 %   |   Errors: 0
===================================================================================
```

---

## Kompresní metody

**1. Delta kódování + ZigZag (DELTA1)**

Kodér odečítá každou hodnotu od předchozí (vytváří rozdíly). Dekodér je zase přičte — plně vratné, nulové ztráty. ZigZag převádí celá čísla se znaménkem (kladná i záporná) na malá celá čísla bez znaménka pro lepší entropii. Tato metoda dominuje přibližně v 70 % testovacích případů, protože přirozená data ze senzorů se mění pomalu.

**2. FLAG — eliminace nul**

Nahrazuje každou posloupnost nulových bajtů bitem v bitové mapě. Užitečná data: `[1B length][bitmap][non-zero bytes]`. Triviální dekódování — žádná plovoucí čárka, žádný stav. Zapíná se, když je >= 30 % bajtů nulových. Velmi účinná na řídkých datech (mnoho nul rozptýlených mezi skutečnými hodnotami).

**3. ANS — Asymmetric Numeral Systems**

Aritmetické kódování bajtů s kódy proměnné délky. Kodér za běhu sestaví tabulku četností a kóduje bajty jako proud. Dekodér používá inverzní stavový automat — není potřeba žádný slovník. Rychlé na malých paketech, zejména u textových a CSV dat.

Užitečná data ANS obsahují délku dat (1B), stav (2B — uint16_t) a zakódované bajty. Uplatní se pouze tehdy, když je podíl nulových bajtů >= 45 % (heuristika). Kodér i dekodér mají předčasné ukončení — pokud výsledek překročí limit, výpočet se okamžitě zastaví.

**4. Nibble Huffman (HUF)**

Pevná Huffmanova tabulka natrénovaná na kombinovaných meteorologických a GPS datech po delta+ZigZag. Kóduje každý bajt jako dva kódy nibblů (hi a lo). Tabulka je uložena v ROM (64 B PROGMEM na ATmega), žádná RAM navíc.

Maximální délka kódu je 6 bitů, průměrně ~3,2 bitu na bajt. Vítězí zejména u IoT, průmyslových a komplexních dat, kde jsou nuly vzácné, ale rozložení nibblů odpovídá tabulce.

**5. Kombinace FLAG+HUF**

FLAG nejprve přesune nulové bajty do bitové mapy, Huffman pak komprimuje zbývající nenulové bajty. Užitečná data: `[1B length][bitmap][1B valid bits HUF][HUF stream]`. To nejlepší z obou světů — deterministická eliminace nul + entropická komprese zbytku.

**Klíčový snímek a počáteční rámec**

Vzorek s číslem 0 je klíčový snímek. Protože neexistuje předchozí paket, vůči kterému by se počítala delta, rozdílová metoda a ZigZag se přeskočí. Data jsou zpracována přímo metodami FLAG, HUF, FLAG+HUF nebo ANS. Klíčový snímek nastává automaticky každých 7 paketů nebo po resetu zařízení.

---

## Plán do budoucna — doménové tabulky (Huffman s více tabulkami)

*Zatím neimplementováno — zde je zaznamenán návrh, aby se neztratil.*

Dnes metoda Huffman (metoda 4) používá **jednu pevnou tabulku**, natrénovanou na kombinovaných meteorologických + GPS
datech a zapečenou do ROM. Tato jediná tabulka je kompromis: „univerzální“ tabulka nikdy nemůže být skvělá pro
všechno — musí pokrýt každý případ, takže si vede dobře na datech podobných těm, na kterých byla natrénována, a hůře
na ostatních (elektroměry, seismologie, …).

**Myšlenka:** udržovat malou **knihovnu tabulek**, z nichž každá je natrénovaná na jednom druhu dat (meteorologie, GPS,
elektřina, seismika, radiace, …). Kompresor použije tabulku, která odpovídá datům — tabulka
natrénovaná na *vašich* datech porazí tu univerzální. (Stejná myšlenka jako trénované slovníky v Zstandardu.)

**Jak to zapadá — bez zásahu do 1bajtové hlavičky:**
Hlavička je už plná a **musí zůstat 1 bajt** — větší hlavička by sežrala úsporu u malých
paketů, což je celý smysl DMD. Tabulka se proto **nepřenáší** v každém paketu. Je to **parametr relace /
inicializace, přesně jako délka paketu** — ta v paketu také není a musí se shodovat na
obou koncích. Obě strany volají `dmd_init(len, table_id)`; **nula bajtů navíc v přenosu.**
- **Jeden spoj LoRa:** oba konce jsou nakonfigurovány se stejnou tabulkou pro daný spoj. Pro přepnutí se mezi
  proudy provede nová inicializace s jinou tabulkou.
- **Uloženo v MLA:** ID tabulky je uloženo **jednou ve schématu, pro každý typ záznamu** (glue už
  popisuje každý záznam) — dekodér ho čte ze schématu, ne z každého paketu. Smíšené MLA
  tak stále dostane pro každý typ dat správnou tabulku a pakety DMD zůstanou nedotčené.
- **ID tabulky 0 = současná univerzální tabulka** → stará data i staré chování beze změny (zpětně
  kompatibilní).

**Proč teď a ne na ATmega328:** původní verze měla jednu 64 B tabulku, protože ATmega měla jen
32 KB flash. Na dnešních čipech (např. 512 KB) se několik tabulek vejde snadno. **Kód i rychlost zůstávají
stejné** — kompresor jen ukazuje na jinou tabulku; roste pouze flash a **formát přenosu zůstává
beze změny** (tabulka je inicializační parametr, ne pole hlavičky). Oba konce musí sdílet stejnou knihovnu
tabulek, indexovanou podle ID.

---

## Použití

### Python

```python
from nic_dmd import DmdEncoder, DmdDecoder

PKT_LEN = 16
enc = DmdEncoder(PKT_LEN)
dec = DmdDecoder(PKT_LEN)

data = bytes([0xFC, 0x18, 0x21, 0x34, 0x01, 0x81,
              0x04, 0xCE, 0x00, 0x00, 0xFC, 0x7C,
              0xFC, 0xA8, 0x00, 0x00])

compressed   = enc.compress(data)
decompressed = dec.decompress(compressed)

print(f"Compressed: {PKT_LEN}B → {len(compressed)}B")
assert decompressed == data
```

### C (ATmega328 / Arduino)

```c
#include "nic_dmd.h"

dmd_encoder_t enc;
dmd_decoder_t dec;

void setup() {
    dmd_encoder_init(&enc, 16);   // packet length — must match on both sides
    dmd_decoder_init(&dec, 16);
}

void loop() {
    uint8_t data[16]          = { /* sensor data */ };
    uint8_t compressed[DMD_OUT_MAX];   // DMD_OUT_MAX = packet length + 1 (up to 256B)
    uint8_t decompressed[16];

    uint16_t comp_len = dmd_compress(&enc, data, compressed);
    lora.send(compressed, comp_len);

    // On the receiver:
    int res = dmd_decompress(&dec, compressed, comp_len, decompressed);
    if (res != 0) {
        // res < 0 → packet is corrupted, see return value table below
    }
}
```

### Návratové hodnoty a chybové kódy

Každá funkce po dokončení vrátí číslo. Toto číslo je jediný způsob, jak vám knihovna sděluje, jak to dopadlo — žádné výpisy, žádné logování (kvůli úspoře paměti a výkonu). Nadřazený program (ten, který knihovnu používá) musí toto číslo přečíst a podle něj jednat.

**`dmd_compress(...)` — komprese**

Vrací **délku výstupu v bajtech** (typ `uint16_t`, tj. 16bitové číslo):

| Vrácená hodnota | Význam | Co dělat |
|---|---|---|
| 2 až 256 | Počet bajtů k odeslání (1B hlavička + komprimovaná data) | Odešlete přesně tolik bajtů z `output` |

Komprese **nikdy neselže** a nemá žádný chybový kód — vždy dostanete platnou délku. V nejhorším případě (255B paket, který nelze komprimovat, např. náhodná nebo šifrovaná data) je výsledek **256 B**, tj. o 1 bajt více než vstup. Tomu se říká maximální nárůst o 1B (ten 1 bajt je povinná hlavička). Proto je návratový typ 16bitový — aby se do něj vešlo číslo 256. Výstupní buffer proto musí mít velikost `DMD_OUT_MAX` (= délka paketu + 1).

**`dmd_decompress(...)` — dekomprese**

Vrací **stavový kód** (typ `int`). Dekomprimovaná data jsou v `output` pouze tehdy, když je kód `0`:

| Vrácená hodnota | Význam | Co dělat |
|---|---|---|
| `0` | OK — vše proběhlo v pořádku, `output` obsahuje původní data | Použijte `output` |
| `-1` | Poškozený nebo neplatný vstup (prázdný paket nebo nesouhlasí délka užitečných dat) | Zahoďte paket, data jsou nepoužitelná |
| `-3` | Rezervovaná verze protokolu (hlavička má `sample_num = 7`) | Tento paket nepatří k této verzi knihovny — zahoďte ho |

Záporné číslo vždy znamená „něco je špatně, data nepoužívejte“. Knihovna sama neprovádí kontroly integrity (CRC apod.) — předpokládá, že poškozené pakety zachytí nižší vrstva (rádiový modul). Kódy `-1` a `-3` jsou jen poslední pojistkou proti zjevně nesmyslnému vstupu.

> **Verze pro Python se chová stejně.** `DmdEncoder.compress()` vrací výstup stejné délky (včetně oněch 256 B v nejhorším případě) a `DmdDecoder.decompress()` při poškozeném nebo neplatném vstupu místo záporného kódu vyvolá **výjimku** — to je pythonovský ekvivalent chyby v C (rezervovaná verze protokolu konkrétně vyvolá `ValueError`). Ošetřete ji pomocí `try/except`. Stejný vstup jinak dává v C i v Pythonu **bajtově identický výstup**, takže můžete komprimovat na zařízení v C a dekomprimovat na serveru/Raspberry Pi v Pythonu (a naopak).

---

### Překlad pro jiné překladače (bez VLA)

Pokud váš překladač nepodporuje C99 VLA (IAR, Keil, MSVC C++), definujte maximální délku paketu při překladu:

```
gcc -DDMD_PKT_MAX_BUILD=32 c/nic_dmd.c ...
```

Buffery budou přeloženy s pevnou velikostí 32B. Pro projekty s jednou pevnou délkou paketu (typický případ použití Arduina) je tato varianta ideální.

---

## Soubory

Repozitář je podle role rozdělen do tří adresářů:

```
c/        C implementation (embedded, ATmega328 / AVR-GCC)
python/   Python reference implementation + its tests
bench/    Benchmarks, data fetching and analysis tooling
makefile  Builds the C library and runs both C and Python tests
```

| Soubor                  | Popis                                               |
| ----------------------- | --------------------------------------------------- |
| `python/nic_dmd.py`     | Implementace v Pythonu — referenční, pro testování  |
| `c/nic_dmd.c`           | Implementace v C pro ATmega328                      |
| `c/nic_dmd.h`           | Hlavičkový soubor                                    |
| `bench/nic_dmd_utils.py`| Pomocné funkce — analýza a výpis výsledků           |
| `makefile`              | Překlad a testování                                 |

### Testování a benchmarky

| Soubor                    | Popis                                                                  |
| ------------------------- | ---------------------------------------------------------------------- |
| `python/nic_dmd_test.py`  | Testy v Pythonu — round-trip, meteo data, klíčový snímek               |
| `c/nic_dmd_test.c`        | Testy v C — round-trip, samé nuly, meteo data                          |
| `bench/fetch_plus.py`     | Benchmark — reálná + syntetická data, jednotné int16 (20 zdrojů)       |
| `bench/fetch_small.py`    | Benchmark — stejné zdroje, těsné balení podle schématu                 |
| `bench/fetch_raw_text.py` | Benchmark — surový text JSON/CSV jako bajty                            |
| `bench/benchmark.py`      | Srovnání DMD vs Huffman vs Heatshrink                                  |

---

## Licence

Licence MIT — Copyright (c) 2026 NIC — Native Intellect Community

---

## Poděkování

Bratrovi za rady během vzniku tohoto projektu.
Za technickou pomoc s optimalizací kódu AI asistentům Claude (Anthropic) a Gemini (Google).
