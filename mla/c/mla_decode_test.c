// SPDX-License-Identifier: MIT
//
// NIC-MLA — C value decoder tests. Vectors match the Python reference
// (mla_schema.mla_decode_value); see the cross-check in the build script.

#include "mla_decode.h"
#include <stdio.h>
#include <string.h>

static int fails = 0;

static void approx(const char *name, double got, double want) {
    double d = got - want; if (d < 0) d = -d;
    printf("  %s %-26s (got %.4f, want %.4f)\n", d < 1e-6 ? "ok  " : "FAIL", name, got, want);
    if (d >= 1e-6) fails++;
}

static double dec(const uint8_t desc[16], const uint8_t *raw) {
    mla_field_t f; mla_field_parse(desc, &f); return mla_decode_value(&f, raw);
}

int main(void) {
    printf("\n=== NIC-MLA C value decoder ===\n\n");

    /* descriptor (v2, 16 B) = width, unit, exp10, flags, off_lo, off_hi,
     * mant_lo, mant_hi, name[8]. mantissa 0 ≡ 1, so exp10-only fields are unchanged. */
    const uint8_t temp[16] = {0x02,0x01,0xFE,0x01,0x00,0x00, 0x00,0x00, 't','e','m','p',0,0,0,0};
    const uint8_t hum[16]  = {0x02,0x04,0xFF,0x00,0x00,0x00, 0x00,0x00, 'h','u','m',0,0,0,0,0};
    const uint8_t toff[16] = {0x02,0x01,0xFE,0x01,0xFB,0xFF, 0x00,0x00, 't','o',0,0,0,0,0,0};  /* offset -5 */
    const uint8_t en[16]   = {0x04,0x0C,0x00,0x00,0x00,0x00, 0x00,0x00, 'e','n','e','r','g','y',0,0};

    /* v2 mantissa cases — the universal user scale (non-powers-of-ten):           */
    const uint8_t two[16]  = {0x02,0x00,0x00,0x00,0x00,0x00, 0x02,0x00, 'x','2',0,0,0,0,0,0};  /* ×2          */
    const uint8_t half[16] = {0x02,0x00,0xFF,0x00,0x00,0x00, 0x05,0x00, 'h','a','l','f',0,0,0,0}; /* 5×10^-1 = ×0.5 */
    const uint8_t adxl[16] = {0x04,0x00,0xF8,0x00,0x00,0x00, 0xF7,0x0E, 'a','d','x','l',0,0,0,0}; /* 3831×10^-8 */

    uint8_t r2545[2]  = {0xF1,0x09};   /* 2545  */
    uint8_t r600[2]   = {0x58,0x02};   /* 600   */
    uint8_t rneg[2]   = {0xC0,0xFE};   /* -320  */
    uint8_t r2550[2]  = {0xF6,0x09};   /* 2550  */
    uint8_t r12345[4] = {0x39,0x30,0x00,0x00};  /* 12345 */
    uint8_t r10[2]    = {0x0A,0x00};            /* 10    */
    uint8_t r1e6[4]   = {0x40,0x42,0x0F,0x00};  /* 1000000 */

    approx("temp 2545",        dec(temp, r2545), 25.45);
    approx("humidity 600",     dec(hum,  r600),  60.0);
    approx("temp -320",        dec(temp, rneg),  -3.20);
    approx("temp+offset 2550", dec(toff, r2550), 25.45);
    approx("energy 12345",     dec(en,   r12345), 12345.0);
    approx("x2 of 10",         dec(two,  r10),   20.0);            /* ×2 — not a power of ten */
    approx("half of 10",       dec(half, r10),    5.0);            /* ×0.5                    */
    approx("adxl 1e6 counts",  dec(adxl, r1e6),  38.31);           /* 1e6 × 3.831e-5 = 38.31  */

    {
        mla_field_t f; mla_field_parse(en, &f);
        printf("  %s name parse 'energy'\n", strcmp(f.name, "energy") == 0 ? "ok  " : "FAIL");
        if (strcmp(f.name, "energy") != 0) fails++;
    }

    printf("\n%s\n", fails ? "FAILURES" : "=== ALL OK ===");
    return fails ? 1 : 0;
}
