★ N.I.C. ★

# NIC-Arduino — rodina NIC Arduino

> ℹ️ **Datová strana KONCEPTU ve fázi návrhu.** Tyto PC/datové nástroje (MLA, DMD, mseed
> export, glue, VDE) jsou skutečný, host-testovaný software, který běží už dnes. **Přístroj**,
> kterému slouží — senzorová síť N.I.C. (viz [NIC-Heimdall](https://github.com/Project-NIC/NIC-Heimdall)) —
> je **koncept ve fázi návrhu, zatím nepostavený a neověřený na hardwaru.** Takže: formát a
> nástroje zde fungují; terénní hardware, který mají zaznamenávat, zatím neexistuje.


**Datová strana NIC na jednom místě: formát logu MLA, jeho volitelné doplňky, lepidlo, seismo export a prohlížeč VDE.**

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

*(Překlad může zaostávat za anglickým originálem — závazná je anglická verze.)*

---

[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](https://opensource.org/licenses/MIT)

---

Tohle je deštník nad celou **Arduino rodinou** NIC — softwarová/datová strana, co
vyrostla kolem Arduina. Každá součást si drží svůj název i svoje README a zůstává
použitelná samostatně (drop-in, ve stylu Arduino knihovny) — jen bydlí pohromadě
tady, aby bylo jasné, co kam patří.

```
NIC-Arduino  (Arduino rodina)
├── NIC-MLA       základ — kontejner/formát logu NIC-MLA
├── NIC-DMD       volitelné: komprese NIC-DMD
├── NIC-KSF       volitelné: šifrování NIC-KSF
├── NIC-GLUE-IN   lepidlo: zápis dat do MLA logu
├── NIC-GLUE-OUT  lepidlo: čtení / export MLA logu (CSV, SQLite, …)
├── NIC-MSEED     seismo export: MLA log → miniSEED (mezinárodní standard)
├── NIC-IAGA      geomag export: MLA log → IAGA-2002 (INTERMAGNET / SuperMAG)
└── NIC-VDE       prohlížeč VDE (Volkov Data) — procházení a export MLA logů
```

## Jak to do sebe zapadá

**MLA je základ.** NIC node loguje vzorky do NIC-MLA kontejneru — to je srdce
datové strany a stojí samo o sobě. Začínalo to jako triviální pár řádků a i po
tom, co to dostalo bohatší výbavu, zůstal výsledek stejně triviální na použití;
jen možností je teď o trošku víc.

Všechno ostatní je **volitelné, navrstvené nad MLA — bonus, ne podmínka:**

- **dmd/** — když chceš vzorky uložené *komprimovaně*, MLA je umí zapsat přes
  NIC-DMD. Čisté MLA se bez toho v pohodě obejde.
- **ksf/** — když chceš vzorky uložené *šifrovaně*, dělá to NIC-KSF. Opět
  volitelné.
- **glue-in/ · glue-out/** — lepidlo, které zapisuje do MLA logu a čte/exportuje
  z něj. Knihovny jsou díly; lepidlo je propojuje podle použití.
- **mseed/** — seismo export. Seismograf NIC-Quake / NIC-Heimdall ukládá do MLA;
  když chceš *mezinárodní* seismologický formát, mseed ten MLA log převede do
  miniSEED (ObsPy / SeisComp / FDSN). Vznikl pro seismo platformu; že to může
  použít i někdo jiný, je bonus.
- **iaga/** — geomag export. Magnetometr NIC-Gauss ukládá do MLA; iaga ten log
  převede do IAGA-2002 (výměnný formát INTERMAGNETu a vstup SuperMAGu pro
  variometry) — kalibrované nT, `Data Type: variation`.
- **vde/** — prohlížeč VDE (Volkov Data): desktopová aplikace na procházení a
  export MLA logů.

## Licence

MIT License — Copyright (c) 2026 NIC — Native Intellect Community

★ Viva La Resistánce ★
