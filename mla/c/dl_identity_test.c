/*
 * dl_identity_test.c  —  round-trip the 8-byte station-identity encoders and write
 * the canonical bytes for the Python cross-check (dl_identity_cross_check.py).
 *
 *   cc -std=c99 -O2 c/dl_identity_test.c -I c -o /tmp/dlid
 *   /tmp/dlid /tmp/dlid.bin
 *   python3 c/dl_identity_cross_check.py /tmp/dlid.bin
 *
 * C99  |  MIT  |  ★ Viva La Resistánce ★
 */
#include "dl_identity.h"
#include <stdio.h>
#include <string.h>

static int fails = 0;
static void ok(const char *m, int c) {
    printf("  %s  %s\n", c ? "ok " : "FAIL", m);
    if (!c) fails++;
}

int main(int argc, char **argv) {
    printf("\n=== NIC-MLA datalogger — station identity (C) ===\n\n");
    uint8_t id_gps[8], id_ident[8], rout[8];
    int32_t lat, lon;

    /* dl_gps round-trip (Prague: 50.0875, 14.4213 → × 1e7) */
    dl_gps(500875000, 144213000, id_gps);
    dl_gps_decode(id_gps, &lat, &lon);
    ok("gps round-trips", lat == 500875000 && lon == 144213000);

    /* dl_ident: region 55, number 25000, kind 0, reserved 0xFFFF */
    dl_ident(55, 25000, 0, 0xFFFF, id_ident);
    ok("ident region/number bytes",
       id_ident[0] == 55 && id_ident[1] == 0 &&
       id_ident[2] == 0xA8 && id_ident[3] == 0x61);

    /* dl_raw verbatim */
    uint8_t raw[8] = { 1, 2, 3, 4, 5, 6, 7, 8 };
    dl_raw(raw, rout);
    ok("raw is verbatim", memcmp(raw, rout, 8) == 0);

    /* dl_elev — i16 LE metres, round-trips incl. negative / zero / sentinel */
    uint8_t e235[2], eneg[2], ezero[2], eunk[2];
    dl_elev(235, e235);
    dl_elev(-412, eneg);
    dl_elev(0, ezero);
    dl_elev(DL_ELEV_UNKNOWN, eunk);
    ok("elev 235 m bytes (EB 00)", e235[0] == 0xEB && e235[1] == 0x00);
    ok("elev -412 m bytes (64 FE)", eneg[0] == 0x64 && eneg[1] == 0xFE);
    ok("elev sentinel bytes (00 80)", eunk[0] == 0x00 && eunk[1] == 0x80);
    ok("elev round-trips (235/-412/0/unknown)",
       dl_elev_decode(e235) == 235 && dl_elev_decode(eneg) == -412 &&
       dl_elev_decode(ezero) == 0 && dl_elev_decode(eunk) == DL_ELEV_UNKNOWN);

    printf("\n%s\n", fails ? "=== FAILED ===" : "=== ALL OK ===");

    /* hand the canonical dl_gps + dl_ident + elevation bytes to the cross-check */
    if (argc > 1) {
        FILE *f = fopen(argv[1], "wb");
        if (f) {
            fwrite(id_gps, 1, 8, f);
            fwrite(id_ident, 1, 8, f);
            fwrite(e235, 1, 2, f);     /* +235 m */
            fwrite(eneg, 1, 2, f);     /* -412 m */
            fwrite(ezero, 1, 2, f);    /*    0 m */
            fwrite(eunk, 1, 2, f);     /* unknown (0x8000) */
            fclose(f);
        }
    }
    return fails ? 1 : 0;
}
