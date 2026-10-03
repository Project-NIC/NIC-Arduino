<p align="center">
  <img src="NICKSF.svg" width="200"/>
</p>

---

# NIC-KSF — Kolmogorov Shannon Feistel

*[English](README.md) · [Čeština](README_cs.md) · [Русский](README_ru.md)*

*Основной является английская версия.*

## Библиотека шифрования для встраиваемых устройств

[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](https://opensource.org/licenses/MIT)

---

## Что такое KSF?

NIC-KSF **перемешивает данные так, что прочитать их может только владелец ключа** — это небольшое и быстрое
шифрование, которое всё ещё помещается на крошечном микроконтроллере.

Внутри это лёгкий симметричный шифр на основе **SPECK-128** в **режиме CTR (Counter)**,
разработанный для устройств с ограниченными ресурсами, таких как ATmega328, где RAM и Flash в дефиците, а
вычислительные накладные расходы должны быть минимальными.

У библиотеки одна чёткая задача: **зашифровать или расшифровать блок данных с помощью 128-битного ключа**. Всё управление ключами, вывод ключей, работа с сеансами и логика протокола намеренно переданы на более высокие уровни.

---

## Возможности

- Блочный шифр SPECK-128/128
- Режим CTR — шифрование и расшифрование являются одной и той же операцией (XOR с ключевым потоком)
- Работа на месте (in-place) — дополнительный буфер не нужен
- Поддерживается любая длина полезной нагрузки от 1 до 255 байт
- Без динамического выделения памяти (`malloc`)
- Без зависимостей, кроме `<stdint.h>` и `<string.h>`
- Совместимость с AVR (ATmega328) и стандартными компиляторами C99
- Два варианта реализации — см. ниже

---

## Варианты реализации

Оба варианта имеют один и тот же интерфейс (`nic_ksf.h`) и дают идентичные результаты.

| Файл | Описание |
|---|---|
| `nic_ksf_32.c` | Ручная 32-битная арифметика — для старых версий `avr-gcc` |
| `nic_ksf_64.c` | Нативный `uint64_t` — для новых версий `avr-gcc` и ПК |

Новые версии `avr-gcc` (Arduino IDE) умеют транслировать нативные 64-битные операции в очень эффективную последовательность инструкций `add` / `adc`. Рекомендуем протестировать оба варианта и выбрать тот, который даёт меньший или более быстрый код для вашего конкретного проекта.

---

## Модель безопасности

NIC-KSF — это **чистый криптографический примитив**. Он не управляет ключами, сеансами или счётчиками пакетов.

**Вызывающая сторона отвечает за то, чтобы каждый вызов `ksf_encrypt` получал уникальный 128-битный ключ.**

Если бы один и тот же ключ был использован для двух разных пакетов, злоумышленник мог бы выполнить XOR перехваченных шифротекстов, и ключевой поток взаимно уничтожился бы. Обеспечение уникальности ключей — полная ответственность вызывающего уровня.

---

## API

```c
#include "nic_ksf.h"

/* Encrypts data in-place using a 128-bit key.
 * key  : 16 bytes (128 bits) — provided by the upper layer
 * data : pointer to buffer (overwritten with encrypted result)
 * len  : number of bytes (1–255)
 */
void ksf_encrypt(const uint8_t key[KSF_KEY_SIZE], uint8_t *data, uint8_t len);

/* Decrypts data in-place. Identical to ksf_encrypt in CTR mode. */
void ksf_decrypt(const uint8_t key[KSF_KEY_SIZE], uint8_t *data, uint8_t len);
```

---

## Пример использования

```c
#include "nic_ksf.h"

/* 128-bit key prepared by the calling layer */
uint8_t key[16] = { /* ... 16 bytes ... */ };

/* Data to encrypt */
uint8_t payload[20] = { /* ... data ... */ };

/* Encrypt in-place */
ksf_encrypt(key, payload, sizeof(payload));

/* ... transmit ... */

/* Decrypt on the receiver side */
ksf_decrypt(key, payload, sizeof(payload));
```

---

## Сборка

### ПК / Linux

```bash
# 32-bit variant
gcc -std=c99 -Wall -Isrc -o test_ksf tests/test_ksf.c src/nic_ksf_32.c

# 64-bit variant
gcc -std=c99 -Wall -Isrc -o test_ksf tests/test_ksf.c src/nic_ksf_64.c

./test_ksf
```

Или просто выполните `make` (собирает и запускает оба варианта).

### AVR / ATmega328

```bash
avr-gcc -std=c99 -mmcu=atmega328p -Os -Isrc -o nic_ksf.elf src/nic_ksf_32.c
```

---

## Структура проекта

| Путь | Описание |
|---|---|
| `src/nic_ksf.h` | Публичный интерфейс и константы |
| `src/nic_ksf_32.c` | Реализация SPECK-128 CTR — 32-битный вариант |
| `src/nic_ksf_64.c` | Реализация SPECK-128 CTR — 64-битный вариант |
| `python/nic_ksf.py` | Эталонная реализация на Python (тестирование) |
| `python/ksf_demo.py` | Сквозной демонстрационный скрипт |
| `tests/test_ksf.c` | Набор тестов на C |
| `tests/test_ksf.py` | Набор тестов на Python |
| `Makefile` | Сборка для ПК и AVR |
---

## Лицензия

MIT License — Copyright (c) 2026 NIC — Native Intellect Community

---

## Благодарности

Моему брату — за советы во время разработки этого проекта.
За техническую помощь в оптимизации кода — ИИ-ассистентам Claude (Anthropic) и Gemini (Google).
