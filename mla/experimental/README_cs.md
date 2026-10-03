# experimental/ — zmrazeno, čistě teoretické

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

*Závazná je anglická verze.*

> **Tento adresář je experimentální a dále se nevyvíjí.** Jeho obsah zůstává jako reference/teoretická možnost, nikoli jako cílová cesta projektu.

## `nic_mla_hal_nor.py` — HAL pro holou SPI-NOR (simulátor)

Simulátor NOR flash třídy W25Q v RAM (`MlaNorSimHAL`) — modeluje omezení holé NOR: Page Program po 256 B blocích, zápis jako AND (pouze 1→0), mazání po sektorech na 0xFF. Slouží k otestování, že se jádro chová správně i na médiu se sémantikou „smazat před zápisem“ (erase-before-write).

### Proč je zmrazeno (rozhodnutí)

Přímá práce s holou SPI-NOR/NAND byla **opuštěna** ve prospěch **SD/flash karet**:

- **Riziko zablokování čipu.** Některé řadiče NOR/NAND mají bezpečnostní / blokovací (lockdown) mechanismy; zápisy částečných stránek nebo částečných bloků (když nezapíšete celý blok) je mohou po několika desítkách bloků uvést do chybového stavu.
- **Závislé na výrobci.** Udělat to pořádně by znamenalo psát to pro konkrétní řady (Winbond W25Q atd.) — nízká univerzálnost, vysoké nároky na údržbu.
- **SD má vlastní řadič.** Karta **sama zajišťuje wear-leveling, ECC a přemapování bloků**. Pro stanici s intervaly ~15 min je to spolehlivější a jednodušší — i na Arduinu používáme kartu.

### Důsledky

- **Žádný skutečný HAL pro SPI-NOR se nepíše** (ani v C). Knihovny v C cílí na SD (SdFat).
- Simulátor a jeho testy zůstávají funkční (jádro je díky HAL nezávislé na médiu), ale slouží jako **důkaz univerzálnosti**, nikoli jako podporovaný scénář.
- Pokud to někdy oživíte, mějte na paměti, že protokol potvrzení zápisu (commit; nejprve LOCK, příznaky mimo CRC) je pro NOR navržen záměrně — ale riziko zablokování u konkrétních čipů budete muset ověřit v jejich datasheetech.
