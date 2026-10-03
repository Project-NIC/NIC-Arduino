# NIC-MSEED — ядро кодека на C

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

*Основной является английская версия.*

**Модуль записи/чтения записей Steim-1/2 + miniSEED 2.x на переносимом C11, без зависимостей.**

Точный, **побайтно идентичный** перенос ядра кодека на Python (`../nic_mseed/steim.py`
+ `mseed.py`) — уровня, «не зависящего от контейнера»: целые числа → кадры Steim →
записи miniSEED и обратно. Он позволяет **станции сбора данных (ESP32) записывать
miniSEED на C**, а не только хост-ПК, и встраивается так же, как и остальная
экосистема NIC на C (без `malloc`, без глобальных переменных — всеми буферами
владеет вызывающий).

Связка MLA + NIC-DMD (`from_mla`) остаётся в инструменте на Python; конвертеру на C
понадобились бы читатели MLA/DMD на C — это отдельная последующая задача. Здесь
находится **кодек** — та часть, которую стоит иметь на устройстве.

## API (`include/nic_mseed.h`)

```c
/* integers -> one Steim record (frames_per_record * 64 B) */
int  nic_steim_encode_record(const int32_t *samples, size_t nsamp, int version,
                             int frames_per_record, int32_t prev,
                             uint8_t *out, size_t *used_samples);
int  nic_steim_decode_record(const uint8_t *frames, size_t len,
                             size_t n_samples, int version, int32_t *out);

/* one channel series -> concatenated fixed-length miniSEED records */
long nic_mseed_write_stream(const nic_mseed_params_t *p, const int32_t *samples,
                            size_t nsamp, int64_t start_unix, double start_frac,
                            uint32_t seq_start, uint8_t *out, size_t out_cap);
int  nic_mseed_write_record(/* one record at a time, no malloc */ ...);
int  nic_mseed_read_record (const uint8_t *rec, size_t cap,
                            nic_mseed_rechdr_t *hdr, int32_t *out, size_t out_cap);
```

`STEIM2` → кодировка 11, `STEIM1` → кодировка 10; длина записи — любая степень двойки
≥ 128 (по умолчанию 512 → 7 кадров). Везде big-endian, только FSDH + Blockette 1000
— универсальное подмножество, которое читают libmseed / ObsPy / SeisComP.

## Сборка и тестирование

```sh
cmake -S c -B c/build && cmake --build c/build
ctest --test-dir c/build --output-on-failure
```

Два набора тестов: `test_steim` и `test_mseed`. Они проверяют внутренние полные
циклы **и** сравнивают результат с эталонными векторами в `test/vectors.h`,
сгенерированными реализацией на Python (`c/tools/gen_vectors.py`), которая сама
проверена с помощью ObsPy. Таким образом, «C совпадает с векторами» ⇒ «C
совпадает с miniSEED уровня ObsPy». Векторы можно сгенерировать заново командой:

```sh
python3 c/tools/gen_vectors.py     # run from the nic-mseed/ package root
```

## Лицензия

MIT — Copyright (c) 2026 NIC — Native Intellect Community
