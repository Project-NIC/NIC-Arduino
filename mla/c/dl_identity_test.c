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

    /* dl_name — 32 B UTF-8, NUL-padded; ASCII, empty, and a multibyte diacritic */
    uint8_t n_ascii[DL_STA_NAME_LEN], n_empty[DL_STA_NAME_LEN], n_multi[DL_STA_NAME_LEN];
    char    nback[DL_STA_NAME_LEN + 1];
    dl_name("Praha", n_ascii);
    dl_name("", n_empty);
    dl_name("Libu\xC5\xA1", n_multi);           /* "Libuš" in UTF-8 (š = C5 A1) */
    ok("name 'Praha' first bytes + NUL pad",
       n_ascii[0]=='P' && n_ascii[4]=='a' && n_ascii[5]==0 && n_ascii[31]==0);
    ok("empty name is all zeros", n_empty[0]==0 && n_empty[31]==0);
    ok("multibyte name bytes (Libu C5 A1)",
       n_multi[0]=='L' && n_multi[3]=='u' &&
       n_multi[4]==0xC5 && n_multi[5]==0xA1 && n_multi[6]==0);
    dl_name_decode(n_ascii, nback);
    ok("name decode round-trips ('Praha')", strcmp(nback, "Praha") == 0);
    dl_name_decode(n_empty, nback);
    ok("empty name decodes to \"\"", nback[0] == '\0');

    printf("\n%s\n", fails ? "=== FAILED ===" : "=== ALL OK ===");

    /* hand the canonical dl_gps + dl_ident + elevation + name bytes to the cross-check */
    if (argc > 1) {
        FILE *f = fopen(argv[1], "wb");
        if (f) {
            fwrite(id_gps, 1, 8, f);
            fwrite(id_ident, 1, 8, f);
            fwrite(e235, 1, 2, f);     /* +235 m */
            fwrite(eneg, 1, 2, f);     /* -412 m */
            fwrite(ezero, 1, 2, f);    /*    0 m */
            fwrite(eunk, 1, 2, f);     /* unknown (0x8000) */
            fwrite(n_ascii, 1, DL_STA_NAME_LEN, f);   /* "Praha" + NUL pad */
            fwrite(n_empty, 1, DL_STA_NAME_LEN, f);   /* "" (all zeros) */
            fwrite(n_multi, 1, DL_STA_NAME_LEN, f);   /* "Libuš" (UTF-8) */
            fclose(f);
        }
    }
    return fails ? 1 : 0;
}
