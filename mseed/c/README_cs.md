# NIC-MSEED — jádro kodeku v C

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

*Závazná je anglická verze.*

**Zapisovač/čtecí program záznamů Steim-1/2 + miniSEED 2.x v přenositelném C11, bez závislostí.**

Věrný, **bajtově přesný** port jádra kodeku z Pythonu (`../nic_mseed/steim.py`
+ `mseed.py`) — vrstvy „nezávislé na kontejneru“: celá čísla → rámce Steim →
záznamy miniSEED, a zpět. Umožňuje, aby **datová stanice (ESP32) zapisovala miniSEED v
C**, nejen hostitelské PC, a dá se vestavět stejně jako zbytek ekosystému NIC v C
(žádný `malloc`, žádné globální proměnné — každý buffer vlastní volající).

Napojení na MLA + NIC-DMD (`from_mla`) zůstává v nástroji v Pythonu; převodník v C
by potřeboval čtecí knihovny MLA/DMD v C — to je samostatný navazující krok. Toto je **kodek**,
část, kterou se vyplatí mít přímo v zařízení.

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

`STEIM2` → kódování 11, `STEIM1` → kódování 10; délka záznamu je libovolná mocnina dvou
≥ 128 (výchozí 512 → 7 rámců). Všude big-endian, pouze FSDH + Blockette 1000
— univerzální podmnožina, kterou čtou libmseed / ObsPy / SeisComP.

## Sestavení a testy

```sh
cmake -S c -B c/build && cmake --build c/build
ctest --test-dir c/build --output-on-failure
```

Dvě sady testů: `test_steim` a `test_mseed`. Kontrolují interní průchody tam i zpět **a**
porovnávají výsledky s referenčními vektory v `test/vectors.h` — vygenerovanými z Pythonu
(`c/tools/gen_vectors.py`), který je sám ověřen proti ObsPy. Takže „C odpovídá
vektorům“ ⇒ „C odpovídá miniSEED na úrovni ObsPy.“ Vektory přegenerujete příkazem:

```sh
python3 c/tools/gen_vectors.py     # run from the nic-mseed/ package root
```

## Licence

MIT — Copyright (c) 2026 NIC — Native Intellect Community
