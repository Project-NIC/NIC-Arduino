<p align="center">
  <img src="NICVDE.svg" width="200"/>
</p>

# Volkov Data Ecosystem

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

*Závazná je anglická verze.*

Multiplatformní dvoupanelový správce souborů ve stylu **Volkov Commanderu**,
napsaný v Pythonu nad knihovnou **prompt_toolkit**. Prochází místní souborový systém a
umí vstoupit *dovnitř* kontejnerů **NIC-MLA**, kde každý zaznamenaný záznam zobrazí jako soubor.

> Stav: **1.2** — sestaveno proti **NIC-MLA v1.2**. Dvoupanelové procházení, souborové
> operace, prohlížeč souborů/záznamů a backend MLA, který prochází a zobrazuje
> záznamy — s omezenou možností úprav samopopisných tabulek (nejde o obecný
> editor záznamů, ale ani o čistě read-only nástroj). MLA je záměrně *hloupý*
> kontejner, a proto se backend opírá o tyto tabulky: **tabulka schématu** dekóduje
> každá zabalená užitečná data na skutečné hodnoty + jednotky a **tabulka stanic** převádí
> jednobajtový index stanice z logu na skutečný region/číslo — obojí putuje přímo
> do exportu CSV/SQL a obojí lze upravovat přímo na místě v editoru tabulek pod `F4`.
>
> Návrh zrcadlí vlastní filozofii MLA — **hloupé knihovny + tenké glue**:
> dole znovupoužitelné knihovny znalé formátu (`export` a k tomu přibalené MLA +
> jeho čtečka schématu), nad nimi backendy jako tenké adaptéry. Celé
> `volkov_core/` je bez GUI, takže ho lze znovu použít i bez grafického rozhraní (headless).

## Spuštění

```bash
pip install -r requirements.txt
python3 volkov_data.py [left_dir] [right_dir]
```

**Klávesy**

| Klávesa | Akce |
|---|---|
| `Tab` | přepnout panel |
| `↑/↓ PgUp/PgDn Home/End` | pohyb kurzoru |
| `Enter` | otevřít adresář / vstoupit do `.mla` / o úroveň výš (`..`) |
| `F1` | informace o vybrané položce / záznamu |
| `F2` | zkontrolovat kontejner `.mla` — hlášení platných / mrtvých / poškozených slotů |
| `F3` | zobrazit soubor nebo užitečná data záznamu (text/hex) |
| `F4` | na záznamu: dekódované hodnoty + jednotky · na `..` uvnitř upravitelného `.mla`: editor tabulky schématu/stanic |
| `F5` | zkopírovat vybraný soubor do druhého panelu |
| `F6` | přejmenovat nebo přesunout — uvnitř `.mla` export všech záznamů do CSV |
| `F7` | vytvořit adresář |
| `F8` | smazat (s potvrzením) |
| `F9` | rozbalovací nabídka (řazení, jazyk, export do SQL, …) |
| `F10` / `q` / `Ctrl-Q` | ukončit · `Esc` zavře jakékoli překryvné okno |

Stiskněte `Enter` na `samples/weather.mla`, abyste vstoupili dovnitř a procházeli jeho záznamy.

## Testy

Logika `volkov_core/` je bez GUI, a proto je pokryta sadou testů ve standardním `unittest`
(bez dalších závislostí):

```bash
python3 -m unittest discover -s tests
```

Testy za běhu vytvářejí dočasné kontejnery MLA a také provádějí základní (smoke) test
souboru `samples/weather.mla`, který je součástí repozitáře.

## Struktura

```
volkov_data.py           prompt_toolkit GUI (thin shell over volkov_core)
volkov_core/             GUI-free logic — reusable headless
  backend.py               storage-backend abstraction (VdeEntry / VdeBackend)
  local.py                 VdeLocalBackend — host filesystem
  mla.py                   VdeMlaBackend — thin adapter: records as "files",
                           schema decode + station resolve + export
  export.py                dumb library — generic rows → CSV / SQLite bytes
  stations.py              glue — station index → real region/number
samples/make_sample.py   generator for a self-describing sample datalogger file
samples/weather.mla      committed sample (packed rows + schema + stations)
tests/                   stdlib unittest suite for volkov_core (GUI-free)
third_party/nic_mla/     vendored NIC-MLA (Python reference) — canonical data format
third_party/nic_dmd/     vendored NIC-DMD — decodes compressed (keyframe/delta) records
  tools/mla_schema.py      host-only schema/station builders + readers (VDE links)
```

Desktopová aplikace čte formát loggeru přes Python referenci MLA
(`third_party/nic_mla/nic_mla.py`) a užitečná data a stanice dekóduje přes
čtecí nástroj jen pro host (`tools/mla_schema.py`); obojí je bajtově shodné s jádrem v C.
Zdrojové kódy Volkov Commanderu slouží **jen jako vzor chování** — nejde o portovaný kód.

## Datalogger (více profilů)

Detekce a export dataloggerového `.mla` (několik profilů stanic v jednom souboru): `volkov_core.datalogger` — `is_datalogger()` + `export_csv()` / `export_sqlite()`. Úplná specifikace je v NIC-MLA `DESIGN-MLA-datalogger.md`.

## Licence

Licence MIT — Copyright (c) 2026 NIC — Native Intellect Community

---

## Poděkování

Mému bratrovi za rady během vývoje tohoto projektu.
Za technickou pomoc s optimalizací kódu AI asistentům Claude (Anthropic) a Gemini (Google).
