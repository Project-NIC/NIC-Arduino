# NIC-MLA — Specifikace návrhu formátu

*[English](DESIGN-MLA.md) · [Čeština](DESIGN-MLA_cs.md) · [Русский](DESIGN-MLA_ru.md)*

*Závazná je anglická verze.*

> **Stav:** v1.2 — **finální** · **Datum:** 2026-10-03
> **MLA** = *Matroshka Logging Archive* — univerzální jednosouborový kontejner
> (data + log v jednom souboru, jako Matroska / tar / DriveSpace).
>
> Tento dokument definuje formát v1.2, finální verzi NIC-MLA. **Stav implementace:** referenční implementace v Pythonu
> (`nic_mla.py`, `nic_mla_archive.py`, `tools/mla_schema.py`) a knihovny v C
> (`c/` — write-only pro ATmega + kompletní pro ARM/PC) jsou hotové a
> bajtově shodné (ověřeno testem kompatibility C↔Python).
>
> **Princip návrhu — hloupý kontejner.** MLA pouze ukládá bajty: 16B log
> záznam chráněný CRC + datový blok, plus dvě samopopisné tabulky v
> prefixu (názvy/jednotky polí a index stanice → skutečné číslo). Vše chytré
> — komprese, šifrování, překlad čísel stanic, přenos — žije v
> samostatné vrstvě glue.

---

## 1. Účel a rozsah

NIC-MLA je **univerzální kontejner pro záznam dat** z měřicích stanic
(meteostanice, elektroměr, …). Cílem je jediný přenositelný soubor, který nese
**data a log dohromady** a je čitelný napříč platformami.

**Proč existuje:** skoncovat s chaosem milionu formátů. Místo hromad souborů a
nástrojů → **jedna tabulka**, do které můžete „nahackovat“ cokoli. Vytáhnete kartu ze
zařízení, strčíte ji do počítače a **jeden triviální prohlížeč** sestaví strukturu
z interních registrů, které jsou popsané tak dobře, že to zvládne i dítě.
Cílem není být „efektní“ — cílem je **jednoduchý, intuitivní a triviální proces**,
který šetří čas a peníze. (Že části tohoto přístupu existují i jinde, nevadí —
hodnota je v tom, že jsou **pohromadě a samopopisné.**).

### Cílové platformy a role

| Platforma | Role | Co dělá |
|---|---|---|
| **ATmega328** (8bit) | **WRITE-ONLY** | pouze připojuje záznamy (append), v intervalech ~15 min; na čipu žádné vyhledávání ani editace |
| Arduino 32/64bit, STM, ESP | zápis + volitelně čtení | jako ATmega + lokální čtení |
| **Host** (PC / Raspberry) | čtení, vyhledávání, editace | načte celý log do RAM, filtruje, exportuje |

**Klíčový princip:** zápis je triviální a robustní (kvůli ATmega), zatímco veškerá inteligence (vyhledávání, dotazy, editace) běží na hostu, kde se log načte do RAM najednou. **Na disku NENÍ žádný strom/AVL — jen plochý log**, který host prochází sekvenčně. Pole logu jsou navržena tak, aby toto filtrování bylo rychlé (čas, index stanice, typ).

### Mimo rozsah

- **Editace záznamů** → samostatný projekt prohlížeče *Volkov Data Ecosystem* (NIC-VDE).
- **Komprese** → volitelná, řeší ji **samostatná metoda**; kontejner komprimovaná data
  pouze **označí** (jeden bit `compressed` + vzdálenost `kf_back`), samotnou kompresi
  nedefinuje (viz §4).
- **Přímý raw SPI-NOR/NAND** → **experimentální a zmrazené** (viz
  `experimental/`). Cílovým úložištěm je **SD/flash karta** — vlastní řadič karty
  se stará o wear-leveling, ECC a přemapování. Od raw NOR jsme upustili kvůli riziku zablokování (lockdown) některých čipů při zápisech částečných stránek/bloků a kvůli vázanosti na konkrétního výrobce. Simulátor NOR zůstává jen jako důkaz univerzálnosti formátu (jádro je díky HAL nezávislé na úložišti), nikoli jako podporovaná cesta.

---

## 2. Rozvržení souboru

Zachováváme osvědčený fyzický model — **dva proudy rostoucí proti sobě**
v souboru pevné velikosti:

```
offset 0                                                              EOF
┌────────────┬───────────────┬──────────┬─────────────┬──────────────┐
│ PREFIX     │ DATA stream → │ free 0xFF │ ← LOG stream │ PREFIX mirror│
│ 1–255 sec  │ (grows up)    │           │ (grows down) │ (copy)       │
└────────────┴───────────────┴──────────┴─────────────┴──────────────┘
             ▲ data_base      ▲ top_ptr  bot_ptr ▲ region_end
```

- **DATA** roste nahoru od `data_base` (`top_ptr` = kam přijde další blok).
- **LOG** roste dolů od `region_end` (`bot_ptr`; další záznam přijde
  na `bot_ptr − log_rec_size`).
- Mezi nimi je volné místo vyplněné `0xFF`.
- **PREFIX** má ve výchozím stavu jeden sektor 512 B; zvětšuje se (po celých sektorech, až
  do 255) jen tehdy, když se tabulky SCHEMA + STATION nevejdou. `data_base` = velikost prefixu.
- **Zrcadlo PREFIXU**: bajtově shodná kopie prefixu v posledních
  bajtech souboru o velikosti prefixu, takže jediný vadný sektor na offsetu 0 nemůže
  oslepit celý soubor — `mount()` se na ni vrátí. Proud LOG proto
  končí na `region_end = file_size − prefix size`, těsně pod zrcadlem.
  Neexistuje žádná samostatná oblast indexu — na disku není vůbec žádný vyhledávací strom.

### Proč pevná, předem alokovaná velikost

Soubor je během `format()` **celý předem alokován** a vyplněn `0xFF` (přesně jako dnešní
`MlaPosixHAL.create`). Na FAT/SD je to správná volba:

- řetězec clusterů FAT se alokuje předem → soubor neroste, nefragmentuje se,
- všechny **logické offsety zůstávají stabilní** po celou dobu života souboru,
- model „dva ukazatele proti sobě“ sedí na pevnou oblast bez konfliktů se souborovým systémem.

### Podmínka „plný“

```
top_ptr + next_block_size  >  bot_ptr − log_rec_size
```

### Režimy zaplnění (`container_kind` v prefixu)

| Hodnota | Režim | Chování | Doporučení |
|---|---|---|---|
| 0 | **Tvrdé zastavení** | RuntimeError při zaplnění | jednoduché |
| 1 | **Rotace souborů** | při zaplnění se otevře další soubor `NIC0001.MLA`, `NIC0002.MLA`, … ; každý prefix nese `file_seq` | **doporučeno pro FAT/SD** |
| 2 | **Kruhový buffer** | DATA se zalomí zpět na začátek, nejstarší sektor se uvolní (`sector_erase`) a odpovídající sloty LOG se označí jako opuštěné | jen RAW/NOR / experiment |

Rotace má přednost: každý soubor je samostatně připojitelný a odolný proti pádu,
karty jsou obrovské, takže k zaplnění dochází zřídka. Kruhový buffer komplikuje obnovu a
je odložen (viz §9).

### Rozhodnutí: velikost kontejneru a předalokace

- **Volné místo = `0xFF`** (jako čerstvá NOR po vymazání) zůstává — **žádný superblok**.
  Pro MCU je to nejjednodušší: čip jen zapisuje, `mount()` najde hranici
  skenováním `0xFF`. Žádné ukládání ukazatelů v prefixu.
- **Výchozí velikost kontejneru ~1 MB.** Předalokace 1 MB (vyplnění `0xFF`) je
  na MCU rychlá jednorázová operace; pro velké objemy **rotujte více 1MB souborů**.
- **Velké souborové systémy** = mnoho 1MB souborů na obrovské kartě. **Agregaci a čtení napříč soubory
  dělá PC** (`MlaArchive`) — výkonný procesor „spolkne všechno“,
  takže pomalejší předalokace a úplný sken nejsou problém. MCU drží otevřený
  jen jeden 1MB soubor.
- 32bitové adresování → jeden soubor max **4 GB**; nad tím (i pod tím) rotace.
  Pokud vám vadí počet souborů, můžete zvýšit `file_size` (např. 16–64 MB) —
  je to jen volba ve `format()`.

---

## 3. Prefix (1–255 sektorů po 512 B)

Prefix tvoří 34B strukturovaná hlavička, za kterou následují dvě samopopisné tabulky
(SCHEMA + STATION), a končí CRC16 přes vše, co mu předchází. Normálně
je to **jeden sektor 512 B**; pokud se tabulky nevejdou, zvětšuje se po celých sektorech 512 B
(až na **255 ≈ 127 KB**) a CRC se přesune do posledních 2 bajtů prefixu.

> Limit 255 sektorů je pevný strop, nikoli cíl — existuje jen proto, že
> počet je uložen v jednom bajtu. **Doporučené maximum je 16 sektorů (8 KB)**; s
> automaticky dimenzovanými tabulkami SCHEMA/STATION se mu skutečná stanice ani nepřiblíží.

```
[0]   magic[4]        b"MLA\0"
[4]   version         1 B   = 1
[5]   cluster_shift   1 B   8=256B · 10=1KB · 12=4KB · … · 15=32KB
[6]   log_rec_size    1 B   = 16
[7]   flags           1 B   CRC mode (bits 0-1): 0=NONE · 1=DATA · 2=FULL
[8]   file_size       4 B   uint32 LE
[12]  reserved        8 B   0
[20]  container_kind  1 B   0=single · 1=rotation
[21]  file_seq        2 B   uint16 LE  file order in rotation
[23]  keyframe_intv   1 B   keyframe interval for compression (default 0 = N/A)
[24]  enc_caps        1 B   bitmask of encodings this file may carry
[25]  data_base       4 B   uint32 LE  = prefix size (first DATA byte)
[29]  region_end      4 B   uint32 LE  = file_size − prefix size (LOG stream end;
                                         a mirror copy of the prefix follows it)
[33]  reserved        1 B   0
[34]  SCHEMA table    …     §3.1
[..]  STATION table   …     §3.2
[end-2] mla_crc16         2 B   LE  — over everything before it
```

> **Rezervováno, neimplementováno (dohánění dat přes uplink).** Rezervovaných 8 B na **[12]** bylo vyhrazeno
> pro `first_ts` (4 B, Unixové sekundy prvního LOG záznamu souboru) + `last_ts` (4 B, zapsáno při
> rotaci/zavření), aby uplink typu store-and-forward mohl vybrat správný rotační soubor
> jen podle hlavičky. v1.2 je finální a tato pole nenese: v1.2 zapisuje [12] = 0 a čtečka prozkoumá
> první LOG záznam každého souboru.

### 3.1 Tabulka SCHEMA — názvy/jednotky polí pro CSV/SQL

Sestavuje ji a čte `tools/mla_schema.py`. Umožňuje libovolné čtečce exportovat záznamy do CSV/SQL
**bez jakékoli předchozí znalosti** — stanice nese vlastní popisy sloupců.

```
[0] tbl_ver  1 B  = 1 (MLA_SCHEMA_VER)
[1] n_log    1 B  number of LOG fields (describe the timestamp etc.)
[2] n_data   1 B  number of DATA fields (the packed payload columns)
[3 ..]       (n_log + n_data) × 16 B field descriptors:
   width 1 B · unit 1 B · exp10 1 B (i8) · flags 1 B (bit0=signed) ·
   offset 2 B (i16 LE) · mantissa 2 B (i16 LE, user scale numerator, 0 ≡ 1) ·
   name 8 B (UTF-8, NUL-padded)
   physical = (raw + offset) × mantissa × 10^exp10
```

Slovník jednotek je univerzální (platí pro celou specifikaci); jen *složení* polí
(které senzory, měřítko, šířka, **8znakový název**) je specifické pro zařízení a putuje
v souboru.

### 3.2 Tabulka STATION — index → skutečná stanice

```
[0] sta_ver  1 B  = 0x53
[1] n        1 B  number of stations (1..255)
[2 ..]       n × 42 B records (index i in the log → record i-1), each:
                identity(8 B)  + elevation(2 B, i16 LE, metres, 0x8000 = unknown)
                + name(32 B, UTF-8, NUL-padded, all-zero = none)
```

8bajtová **identita je pro MLA neprůhledná** — sestavte ji stejnými enkodéry, jaké
používá formát dataloggeru (`dl_gps` = 2× i32 stupně×1e7, `dl_ident` = region/number/
kind/reserved jako 4× u16, nebo `dl_raw` = 8 bajtů doslovně). Tím se
identita stanice **sjednocuje** na 8bajtovém modelu; starý 6bajtový záznam region/number/reserved
je **vyřazen**. `elevation` je samostatné pole nadmořské výšky ve znaménkových metrech (i16 LE,
`0x8000` = neznámá), oddělené od neprůhledné identity. `name` je samostatný
pevný 32bajtový štítek čitelný pro člověka (UTF-8, doplněný NUL, samé nuly = žádný) —
materiál pro StationXML `<Site><Name>`; jde o metadata uložená **jednou v prefixu**, NENESOU se
v každém 16bajtovém log záznamu. Lidé přidělují čísla stanic s mezerami — glue
je mapuje na kompaktní 1bajtové indexy a zpět.

> **Hloupý kontejner.** Obě tabulky se předávají shora a zapisují doslovně; cesta C/MCU
> je nikdy neinterpretuje. Komprese, šifrování, překlad čísel stanic
> i přenos žijí v samostatné vrstvě glue.

---

## 4. Příznak komprese (žádný registr typů)

### 4.1 Jeden bit, ne bajt typu

v1.2 **nenese žádný** bajt `rec_type`/třídy (měření / událost /
konfigurace / delta / klíčový snímek / …). Soubory jsou **homogenní** — co užitečná data
*znamenají* (který bajt je teplota, který vlhkost), vyplývá z **tabulky
SCHEMA** (§3.1), nikdy ze značky typu u jednotlivého záznamu. Značka typu závislá na glue
časem chátrá; SCHEMA ne.

LOG záznam místo toho nese jen bajt `flags` (§5):

- **bit 7 — `compressed`**: užitečná data jsou blob kodeku (např. NIC-DMD).
  Kontejner se nikdy nedívá dovnitř; tento bit znamená jen „při čtení předej užitečná data
  vrstvě kodeku“.
- **bity 0–6 — `kf_back`**: u komprimovaného proudu udává, o kolik záznamů zpět leží
  příslušný klíčový snímek (0 = tento záznam **je** klíčový snímek). Plných 7 bitů → 0..127,
  takže interval klíčových snímků je volbou zapisovače/zařízení a čtečce se nikdy
  nemusí sdělovat (klíčový snímek = `kf_back == 0`).

### 4.2 Který kodek — to je v datovém bloku, ne v záznamu

Formát **nese** bit komprese, ale **nedefinuje metodu**.
KTERÝ kodek / klíčový snímek / varianta je zakódován ve **vlastní hlavičce datového bloku**
(NIC-DMD to už dělá: bajt 0 blobu). Přidání nového kodeku je tedy pár
řádků v glue a kontejner se nikdy nemění. Dvě úrovně:

- **LOG záznam** je index — hledání/filtrování (vč. podle bitu `compressed`)
  bez čtení dat;
- **DATOVÝ blok** je samopopisný, neprůhledný blob:
  `MAGIC · [codec hdr 1–4 B][compressed data] · CRC`.

`keyframe_intv` (bajt prefixu 23) je pouze nápověda pro čtečku — kadence, kterou zapisovač
*zamýšlí* — a ve výchozím stavu je 0. Nikdy není směrodatný; směrodatné je `kf_back == 0`.

**Praktický příklad:**
1. Glue zakóduje: vzorek 0 = klíčový snímek (surová kotva), vzorky 1..6 = delty, vzorek
   7 = opět klíčový snímek (výchozí kadence DMD je 7).
2. Kontejner uloží každý blob s `compressed = 1` a `kf_back` = vzdálenost
   ke klíčovému snímku (0 u klíčových snímků) — žádná interpretace, jen indexování.
3. Při čtení dekompresor (ne jádro) přehrává od nejbližšího záznamu,
   jehož `kf_back == 0`.

### 4.3 Schopnosti kódování (`enc_caps`)

Bajt prefixu 24 (`enc_caps`) je pozůstatková bitová maska sloužící jako **nápověda** pro čtečku,
ponechaná kvůli dopředné kompatibilitě; v1.2 ji ve výchozím stavu nechává **0**. Nikdy nepředstavuje
omezení — směrodatné informace o kódování nese vlastní hlavička každého datového bloku,
takže čtečka musí každý blok vždy zpracovat podle jeho vlastních pravidel.

---

## 5. Log záznam (16 bajtů)

Log záznam žije v proudu LOG (roste dolů od `region_end`, tj.
těsně pod koncovým zrcadlem prefixu). Má pevnou velikost
**16 bajtů** a **celý záznam je pokryt CRC** — neexistuje žádné
pole „flags mimo CRC“.

```
[0]  offset      4 B  uint32 LE  byte offset of the data block in DATA
[4]  timestamp   4 B  uint32 LE  Unix seconds (from the caller's RTC/GPS)
[8]  subsec      2 B  uint16 LE  two opaque bytes (0..65535); meaning owned by the glue, MLA assigns none
[10] length      2 B  uint16 LE  payload size (1..65535 B)
[12] flags       1 B  uint8      bit7 = compressed, bits0-6 = kf_back (records back
                                  to the owning keyframe; 0 = this record IS a keyframe)
[13] station     1 B  uint8      index 1..255 into the prefix station table (0 = none)
[14] mla_crc16       2 B  LE  — CRC16 over [0..13]
```

Proč 16 B: je to mocnina dvou, takže záznam nikdy nepřekročí hranici 512B sektoru a
adresování slotů je bitový posun, ne násobení — nejpřívětivější velikost pro MCU.
Pole `subsec` tvoří dva neprůhledné bajty, které kontejner pouze
přenáší — MLA jim nepřiděluje žádný význam. Název se záměrně čte oběma způsoby:
pod**sek**undový čas *i* pod**sek**ce (např. index rotace / sekce). Rozhoduje
vrstva glue — může pole použít jako jednu 16bitovou hodnotu, jako dva nezávislé
bajty, nebo pro několik věcí najednou (např. horní bajt = sekce/rotace, dolní bajt
= podsekundový tik pro vzorkování výrazně nad 1 Hz). Pokud se nepoužívá, nastavte ho na 0.
Jediný bajt `flags` sdružuje bit `compressed` a vzdálenost `kf_back` (viz §4).

**Jde o umístění, ne o úplnou časovou značku.** Dva bajty nesou *index vzorku* — 0..127
pro kanál 128/s, 0..8191 pro kanál 8192/s — a všude, kde je vzorkovací frekvence mocninou dvou,
je převod tohoto indexu na jemnější mřížku bitovým posunem: nic neukládá přesný zlomek
sekundy a nic nedělí, aby ho zpětně přečetlo. Volající, jehož podsekundová pozice potřebuje více
než 16 bitů, ji rozdělí na dvě části — hrubá polovina umístí záznam sem, jemná polovina se veze
v užitečných datech, kam u takového kanálu přesný okamžik stejně patří.

### 5.1 Stavy záznamu (žádné pole flags)

Slot se interpretuje čistě podle svých bajtů:

| Stav | Bajty | Detekce |
|---|---|---|
| **Volný** | samé `0xFF` | čerstvé / vymazané médium |
| **Živý** | data + odpovídající CRC | `mla_crc16(body) == stored CRC` |
| **Opuštěný** | samé `0x00` | CRC nesedí (vynulované tělo **nedává** hash `0x0000`) |

Opuštění záznamu = **přepsání 16 B nulami**. Jeho CRC pak už nesedí,
takže ho každá čtečka přeskočí. To nahrazuje starý trik „překlopení jednoho bajtu flags
mimo CRC“ a umožňuje opatřit kontrolním součtem celý záznam.

### 5.2 `station` je index, ne číslo

`station` je **1bajtový index** (1..255; 0 = žádná) do tabulky STATION v
prefixu (§3). Skutečná čísla stanic/regionů — která lidé a nástroje přidělují,
jak se jim zlíbí, s mezerami — žijí v této tabulce; kontejner index nikdy
neinterpretuje. Překlad index ↔ skutečné číslo je úkolem glue na hostu.

> Žádné kontrolní body. Velikost souboru je pevná a log má pevný krok, takže
> `mount()` najde hranici binárním vyhledáváním a přečte `offset + length`
> nejnovějšího platného záznamu, čímž obnoví `top_ptr` — není co
> ukládat, takže žádný záznam kontrolního bodu neexistuje.

---

## 6. Datový blok (proměnná délka)

Užitečná data zapisovaná do proudu DATA:

```
[0]       magic       2 B  0xAB 0xCD  (sync word)
[2]       <payload>   N B  app data (1 to 65535 B)
[2+N]     mla_crc16       2 B  LE  — CRC16 over the payload (0xFFFF if CRC mode = NONE)
```

**Proč v bloku není bajt typu?** Ve v1.2 neexistuje vůbec žádný typ jednotlivých záznamů —
soubory jsou homogenní a význam vychází ze SCHEMA, ne ze značky. Díky tomu zůstává
datový proud **čistě řízený aplikací**. Se schématem v prefixu jsou užitečná data
sloupce senzorů naskládané těsně za sebou (§3.1); `mla_decode_payload()` je rozdělí
a přepočítá na `(name, unit, value)` pro CSV/SQL.

---

## 7. Odolnost proti pádu

Protokol — **nejdřív LOCK, potom DATA**:

1. **Přerušený zápis zámku** (přerušení během zápisu LOG záznamu) → ten slot má
   špatné CRC → při mount se přeskočí. Hledání hranice binárním vyhledáváním pokračuje.
2. **Přerušený zápis dat** (LOG v pořádku, ale datový blok je neúplný) → chybí jeho `MAGIC`
   → při mount se zámek **vynuluje** (celých 16 B se přepíše
   `0x00`, takže jeho CRC nesedí) a `top_ptr` se vrátí na `rec.offset`.
3. **Opuštění** libovolného záznamu stejným způsobem — přepište ho nulami; CRC pak
   nesedí a čtečky ho přeskočí. Neexistuje žádný bajt flags a nic mimo CRC.
4. `recover()`: najde `MAGIC`, zkouší délky 1..65535, dokud nenajde takovou, pro niž
   `CRC16(payload)` sedí; obnovené záznamy se označí jako nekomprimované (`compressed = 0`,
   `kf_back = 0`), protože kódování nelze obnovit ze samotného bloku.
5. Žádné kontrolní body: velikost souboru je pevná a log má pevný krok, takže
   binární vyhledávání plus přečtení nejnovějšího záznamu obnoví stav přímo.
   Začněte sken s hrubým krokem (např. 256, nebo 2000 u velkého souboru) a
   když narazíte na `0xFF`, vraťte se o jeden krok zpět — na disku není potřeba nic opravovat.

---

## 8. Konfigurovatelné parametry (nastavují se při `format()`, ukládají se v prefixu)

| Parametr | Kde | Volby | Výchozí |
|---|---|---|---|
| `cluster_shift` | bajt 5 | 8…15 (256 B … 32 KB) | 12 (4 KB) |
| `flags` (CRC) | bajt 7, bity 0-1 | NONE / DATA / FULL | FULL |
| `container_kind` | bajt 20 | single / rotation | single |
| `file_seq` | bajt 21 | 0…65535 | 0 |
| `keyframe_intv` | bajt 23 | 0…255 | 0 |
| `enc_caps` | bajt 24 | bitová maska kódování | dle použití |
| `schema_table` | [34..) | z `tools/mla_schema.py` | prázdná |
| `station_table` | za schématem | z `tools/mla_schema.py` | prázdná |

`log_rec_size` je pevně **16** a `data_base` se odvozuje (= velikost prefixu,
což je 512 B, pokud tabulky nepřetečou do více sektorů).

## 9. Mimo rozsah (žije ve vrstvě glue, ne v MLA)

MLA je hloupý kontejner; následující věci záměrně **nejsou** jeho úkolem:

- **Překlad čísel stanic** — log ukládá 1bajtový index; jeho mapování na
  skutečné číslo stanice, případně s mezerami, je věcí glue (přes tabulku STATION,
  kterou zapsalo).
- **Komprese** — MLA ji jen označí (bit `compressed`; `kf_back` váže
  záznam k jeho klíčovému snímku, 0 = klíčový snímek). Kodek i jeho varianta jsou samostatné
  a žijí ve vlastní hlavičce datového bloku.
- **Šifrování** — totéž: samostatná knihovna; MLA ukládá jakékoli bajty, které dostane.
- **Přenos (LoRa / Wi-Fi / síť)** — každý záznam je soběstačný
  (délka + CRC), takže „odeslat záznam“ = odeslat jeho bajty. Přenos je
  volbou glue.
- **Rotace souborů** napříč mnoha soubory — platformní glue nad souborovým systémem
  (`MlaArchive` v Pythonu); každý soubor je díky `file_seq` samostatně připojitelný.
  Glue může také **pojmenovat každý soubor podle jeho `first_ts`** (např. datovou značkou `YYYYMMDD`), aby
  výpis adresáře byl samozřejmým časovým indexem pro dohánění dat typu store-and-forward. Jde
  *pouze o politiku pojmenování* — `file_seq` a hlavička (vč. rezervovaného slotu `first_ts`) zůstávají
  směrodatné, protože hodiny mohou být v okamžiku vytvoření nenastavené (studený start před získáním GPS) a FAT 8.3
  omezuje krátké názvy (záložně použijte název podle `file_seq`, volitelně soubor přejmenujte, jakmile je čas znám).

Toto oddělení udržuje MLA dost malé pro ATmega (write-only, 16B log, jeden
512B sektor prefixu) a zároveň umožňuje schopnému hostu postavit nad ním
libovolně chytrý systém.
