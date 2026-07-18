// SPDX-License-Identifier: MIT
//
// NIC-MLA — host-side value decoder. Reads a 16 B field descriptor and turns a
// packed value into its physical number, exactly like the Python reference:
//
//     physical = (raw + offset) * mantissa * 10^exp10
//
// The `mantissa` (int16) is what makes the per-field scale UNIVERSAL and fully
// USER-CHOSEN (MLA schema v2): exp10 alone gave only powers of ten (10/100/1000×),
// so a user could not set 2× or 5× or a real instrument sensitivity like the
// ADXL355's 256000 LSB/g. With the mantissa, scale = mantissa × 10^exp10 holds ANY
// value to ~4-5 sig figs (e.g. 3831 × 10^-8 ≈ 3.831e-5 m/s²/count). mantissa 0 is
// read as 1, so an exp10-only field still means scale = 10^exp10.
//
// Shared by the schema and the datalogger (profile-ref) format — both use the same
// 16 B descriptor. Host/PC only (uses double); the write-only MCU path never needs it.

#ifndef NIC_MLA_DECODE_H
#define NIC_MLA_DECODE_H

#include <stdint.h>

#define MLA_FIELD_DESC_SIZE 16
#define MLA_NAME_LEN         8

typedef struct {
    uint8_t  width;        // 1 / 2 / 4 bytes on the wire
    uint8_t  unit;         // code from the universal UNITS vocabulary
    int8_t   exp10;        // signed power of ten
    uint8_t  is_signed;    // flags bit 0
    int16_t  offset;       // additive calibration term (raw units)
    int16_t  mantissa;     // scale = mantissa * 10^exp10 (0 ≡ 1); user-chosen, v2
    char     name[MLA_NAME_LEN + 1];   // NUL-terminated
} mla_field_t;

// Parse a 14 B descriptor into f.
void mla_field_parse(const uint8_t desc[MLA_FIELD_DESC_SIZE], mla_field_t *f);

// Decode one packed value: physical = (raw + offset) * mantissa * 10^exp10.
// `raw` must point to f->width little-endian bytes.
double mla_decode_value(const mla_field_t *f, const uint8_t *raw);

#endif /* NIC_MLA_DECODE_H */
