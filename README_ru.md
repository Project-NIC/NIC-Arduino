★ N.I.C. ★

# NIC-Arduino — семейство NIC Arduino

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

*Основной является английская версия.*

> ℹ️ **Сторона данных концепции на СТАДИИ ПРОЕКТИРОВАНИЯ.** Эти инструменты для ПК и данных (MLA, DMD, KSF, glue,
> экспорт в mseed и IAGA, VDE) — реальное программное обеспечение, протестированное на хосте и работающее уже сегодня. **Прибор**, которому они служат, —
> сенсорная сеть N.I.C. — является **концепцией на стадии проектирования, ещё не построенной и не
> проверенной на оборудовании.** Итак: формат и инструментарий здесь работают; полевого оборудования, данные которого они
> должны записывать, пока не существует.

**Сторона данных NIC в одном месте: формат логов MLA, его необязательные дополнения, glue, сейсмо- и геомагнитный экспорт и просмотрщик VDE.**

> **v1.2 — финальная версия.** Все компоненты читают 1.2, и семейство закрыто; ничего
> дальнейшего не планируется. Оно создавалось, когда станция была одним сейсмографом; станция,
> в которую она выросла, [NIC-Heimdall](https://github.com/Project-NIC/NIC-Heimdall), ведёт собственный
> архив. Что изменилось по пути: [`mla/RELEASE_NOTES_v1.2.md`](mla/RELEASE_NOTES_v1.2_ru.md).

---

[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](https://opensource.org/licenses/MIT)

---

Это общий зонтик для всего **семейства Arduino** NIC — программной стороны и стороны данных,
выросших вокруг Arduino. Каждый компонент сохраняет собственное имя и собственный README
и остаётся пригодным к самостоятельному использованию (подключается как есть, в стиле библиотек Arduino) — они просто
находятся здесь вместе, чтобы было ясно, что к чему относится.

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

## Как всё это связано

**MLA — это основа.** Узел NIC записывает свои отсчёты в контейнер NIC-MLA — это
сердце стороны данных, и оно самодостаточно. Всё начиналось как
тривиальный контейнер в несколько строк, и даже после того, как набор функций стал богаче,
результат остался таким же простым в использовании; теперь просто есть немного больше опций.

Всё остальное — **необязательное, надстроенное поверх MLA — бонус, а не
требование:**

- **dmd/** — если вы хотите хранить отсчёты в *сжатом* виде, MLA может записывать их
  через NIC-DMD. Обычный MLA прекрасно работает и без него.
- **ksf/** — если вы хотите хранить отсчёты в *зашифрованном* виде, это делает NIC-KSF.
  Опять же необязательно.
- **glue-in/ · glue-out/** — glue, который записывает в лог MLA и читает/экспортирует из
  него. Библиотеки — это детали; glue соединяет их под конкретное применение.
- **mseed/** — сейсмический экспорт. Сейсмограф NIC-Quake сохраняет данные
  в MLA; когда вам нужен *международный* сейсмологический формат, mseed превращает этот
  лог MLA в miniSEED (ObsPy / SeisComp / FDSN). Он существует для сейсмической
  платформы; то, что его может повторно использовать кто-то ещё, — бонус.
- **iaga/** — геомагнитный экспорт. Магнитометр NIC-Gauss сохраняет данные в MLA; iaga
  превращает этот лог в IAGA-2002 (формат обмена INTERMAGNET и то, что
  SuperMAG принимает от вариометров) — откалиброванные nT, `Data Type: variation`.
- **vde/** — просмотрщик VDE (Volkov Data): настольное приложение, которое просматривает и
  экспортирует логи MLA.

## Сборка и тестирование

Каждый компонент собирается и тестируется самостоятельно; см. его папку. Вкратце:

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

## Лицензия

MIT License — Copyright (c) 2026 NIC — Native Intellect Community

★ Viva La Resistánce ★
