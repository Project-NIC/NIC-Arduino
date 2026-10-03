# NIC-MLA v1.2 — finální verze

*[English](RELEASE_NOTES_v1.2.md) · [Čeština](RELEASE_NOTES_v1.2_cs.md) · [Русский](RELEASE_NOTES_v1.2_ru.md)*

*Závazná je anglická verze.*

**v1.2 je poslední verzí NIC-MLA, a s ní i celé rodiny NIC-Arduino.**
Rodina je uzavřena: každá komponenta je ve verzi 1.2 a nic dalšího se neplánuje.
Stanice, která z těchto nástrojů vyrostla (NIC-Heimdall), si vede vlastní
archiv; MLA zůstává u toho, pro co bylo postaveno — malá zařízení, která logují,
a PC nástroje, které je čtou.

Tyto poznámky shrnují vše od v1.0 na jednom místě. (Mezilehlý tag v1.1
je zahrnut sem: projekt neměl prakticky žádné uživatele, takže je třeba popsat jedno
vydání, ne dvě.) Bajt `version` v prefixu zůstává **1**.

## Co je nového

- **Podsekundové časové značky.** Log záznam nyní nese pole `subsec`
  (index vzorku v rámci sekundy), takže MLA zvládá vzorkování
  výrazně nad 1 Hz — např. MEMS seismograf. Dříve se čas rozlišoval jen na
  celé Unixové sekundy, což vyhovovalo pomalé telemetrii. Pro logování
  po celých sekundách nastavte `subsec = 0`.
- **Kompaktní, konsolidovaný 16bajtový záznam.** Starý bajt `rec_type`/třídy a
  výplňový bajt `reserved` zmizely. Stav kódování je nyní jeden sbalený bajt `flags`:
  **bit 7 = compressed**, **bity 0–6 = `kf_back`** (vzdálenost zpět k
  příslušnému klíčovému snímku; 0 = tento záznam *je* klíčový snímek). Tím se uvolní místo
  pro `subsec`, aniž by záznam narostl.
  - MLA zůstává **nezávislé na kodeku**: bit `compressed` znamená jen „předej
    užitečná data vrstvě kodeku“. *Který* kodek / klíčový snímek / varianta, to žije ve
    vlastní hlavičce datového bloku (NIC-DMD to už dělá), nikdy v MLA.
  - Soubory jsou **homogenní** — co užitečná data znamenají, vyplývá z tabulky SCHEMA,
    ne ze značky typu u jednotlivého záznamu.
- **Robustní rotace souborů.** Každý rotovaný soubor je samostatně připojitelný:
  - při znovuotevření dědí tabulky/parametry formátu z předchozího souboru (už žádná
    rotace do souboru s prázdnými tabulkami);
  - MLA nyní **dává událost rotace najevo** (`MlaArchive.append` vrací, zda
    došlo k rotaci; `will_rotate()` ji předpovídá; spouští se callback `on_rotate`), takže
    glue komprimovaného proudu může vynutit klíčový snímek na začátku každého souboru. U
    RAW dat je to bezpředmětné.
- **Odolnost prefixu.** Na konec souboru se zapisuje bajtově shodná **zrcadlová kopie**
  samopopisného prefixu; `mount()` se na ni vrátí, pokud
  primární kopie na offsetu 0 neprojde kontrolou CRC. Jediný vadný sektor na začátku souboru
  už neoslepí celý soubor. (Oblast logu nyní končí na `region_end =
  file_size − prefix size`.)

- **`subsec` je umístění a patří glue.** Dva bajty jsou pro
  MLA neprůhledné (`subsec_lo` / `subsec_hi`). Při vzorkovací frekvenci, která je mocninou dvou, nesou
  index vzorku (rámce) v rámci sekundy, takže jeho umístění je bitový posun a nikdy se neukládá
  žádný zlomek sekundy; pozice vyžadující více než 16 bitů se
  rozdělí, hrubá polovina v `subsec`, jemná polovina v užitečných datech.
  Exportéry (NIC-MSEED, NIC-IAGA) ho čtou jako index rámce, nikdy jako tik.
- **Obnova po pádu při mount.** `mount()` zneškodní přerušený slot LOG na
  hranici proudu (přepíše ho `0x00`, což je konvence pro zahození) a ověří
  datový blok nejnovějšího záznamu, přičemž přerušený zápis dat vezme zpět. Omezené,
  idempotentní — čistý soubor nedostane jediný zápis — a implementace v Pythonu i C
  obnoví tentýž přerušený vstup na identické bajty.
- **Zesílená nouzová obnova.** `mla_recover` před resynchronizací potvrdí hranici záznamu
  podle magic následujícího záznamu a poškozený primární prefix
  už neurčuje velikost vlastního zrcadla — neporušené zrcadlo se najde skenováním celých
  sektorů.
- **Kalibrované schéma.** Každý deskriptor pole má 16 B a nese vlastní
  mantisu: `scale = mantissa × 10^exp10`, aplikuje se při exportu, samotný archiv
  zůstává surový. Slovník jednotek přibral `m/s²`. Tag tabulky schématu je **1**.
- **Rozvržení dataloggeru** (`DESIGN-MLA-datalogger.md`): mnoho profilů stanic
  v jednom souboru, od jednoschématového rozvržení se rozlišuje tagem na offsetu 34.

## Kompatibilita

- Změny formátu na disku (rozvržení záznamu + koncové zrcadlo). Soubory v1.0 v1.2
  nečte a naopak. Bajt `version` v prefixu zůstává 1.
- Bajtově přesná shoda mezi referenční implementací v Pythonu a knihovnami v C (AVR / ARM / PC) —
  ověřeno pomocí `c/cross_check.py`.

## Ověření

- Sada testů v Pythonu: **122/122 PASS**
- Sada testů v C (write-only + kompletní knihovny): **56/56 PASS**
- Bajtově přesná křížová kontrola C↔Python: **13/13 PASS**
- Navazující komponenty zelené: DMD 18/18, KSF, glue-in, glue-out, NIC-MSEED, NIC-IAGA, VDE
