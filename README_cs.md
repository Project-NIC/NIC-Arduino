★ N.I.C. ★

# NIC-Arduino — rodina NIC Arduino

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

*Závazná je anglická verze.*

> ℹ️ **Datová strana konceptu ve FÁZI NÁVRHU.** Tyto nástroje pro PC a data (MLA, DMD, KSF, glue,
> exporty mseed a IAGA, VDE) jsou skutečný software otestovaný na hostitelském počítači, který funguje už dnes. **Přístroj**, kterému slouží —
> senzorová síť N.I.C. — je **koncept ve fázi návrhu, dosud nepostavený ani
> neověřený na hardwaru.** Tedy: formát a nástroje zde fungují; terénní hardware, jehož data mají
> zaznamenávat, zatím neexistuje.

**Datová strana NIC na jednom místě: formát logu MLA, jeho volitelné doplňky, glue, seismické a geomagnetické exporty a prohlížeč VDE.**

> **v1.2 — konečná verze.** Všechny komponenty čtou verzi 1.2 a rodina je uzavřená; nic
> dalšího se neplánuje. Vznikla v době, kdy stanicí byl jediný seismograf; stanice,
> v kterou se rozrostla, [NIC-Heimdall](https://github.com/Project-NIC/NIC-Heimdall), si vede
> vlastní archiv. Co se cestou změnilo: [`mla/RELEASE_NOTES_v1.2.md`](mla/RELEASE_NOTES_v1.2_cs.md).

---

[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](https://opensource.org/licenses/MIT)

---

Toto je zastřešení celé **rodiny Arduino** projektu NIC — softwarové a datové strany,
která vyrostla kolem Arduina. Každá komponenta si ponechává vlastní název i vlastní README
a zůstává použitelná samostatně (stačí ji vložit, ve stylu knihoven Arduina) — jen
žijí pohromadě zde, aby bylo jasné, co k čemu patří.

```
NIC-Arduino  (the Arduino family)
├── NIC-MLA       the base — the NIC-MLA log container/format
├── NIC-DMD       optional: NIC-DMD compression
├── NIC-KSF       optional: NIC-KSF encryption
├── NIC-GLUE-IN   glue: write data into an MLA log
├── NIC-GLUE-OUT  glue: read / export an MLA log (CSV, SQLite, …)
├── NIC-MSEED     seismo export: an MLA log → miniSEED (international standard)
├── NIC-IAGA      geomag export: an MLA log → IAGA-2002 (INTERMAGNET / SuperMAG)
└── NIC-VDE       the VDE viewer (Volkov Data) — browse & export MLA logs
```

## Jak to do sebe zapadá

**MLA je základ.** Uzel NIC zaznamenává své vzorky do kontejneru NIC-MLA — to
je srdce datové strany a obstojí samo o sobě. Začínal jako
triviální kontejner o několika řádcích, a i když později získal bohatší sadu funkcí,
výsledek zůstal stejně jednoduchý na použití; jen je teď k dispozici o několik možností víc.

Vše ostatní je **volitelné, navrstvené nad MLA — bonus, nikoli
požadavek:**

- **dmd/** — pokud chcete vzorky ukládat *komprimované*, MLA je umí zapisovat
  přes NIC-DMD. Čisté MLA funguje naprosto dobře i bez něj.
- **ksf/** — pokud chcete vzorky ukládat *šifrované*, postará se o to NIC-KSF.
  Opět volitelné.
- **glue-in/ · glue-out/** — glue, které zapisuje do logu MLA a čte/exportuje
  z něj. Knihovny jsou součástky; glue je propojuje podle konkrétního použití.
- **mseed/** — seismický export. Seismograf NIC-Quake ukládá
  do MLA; když chcete *mezinárodní* seismologický formát, mseed převede tento
  log MLA na miniSEED (ObsPy / SeisComp / FDSN). Existuje kvůli seismické
  platformě; to, že ho může znovu použít i kdokoli jiný, je bonus.
- **iaga/** — geomagnetický export. Magnetometr NIC-Gauss ukládá do MLA; iaga
  převede tento log na IAGA-2002 (výměnný formát INTERMAGNET, a to, co
  SuperMAG přijímá z variometrů) — kalibrované nT, `Data Type: variation`.
- **vde/** — prohlížeč VDE (Volkov Data): desktopová aplikace, která prochází a
  exportuje logy MLA.

## Sestavení a testy

Každá komponenta se sestavuje a testuje samostatně; viz její složka. Ve zkratce:

```bash
# vde — the viewer (Python)
cd vde && python3 -m unittest discover -s tests

# mla (Python reference + C cross-check)        cd mla   && python3 nic_mla_test.py
# dmd (C + Python)                              cd dmd   && make test
# ksf (C 32/64-bit)                             cd ksf   && make
# mseed (Python + C)                            cd mseed && python3 tests/test_mseed.py
# iaga (Python)                                 cd iaga  && python3 tests/test_iaga.py
# glue-in / glue-out (Python)                   cd glue-in && python3 tests/test_glue.py
```

## Licence

Licence MIT — Copyright (c) 2026 NIC — Native Intellect Community

★ Viva La Resistánce ★
