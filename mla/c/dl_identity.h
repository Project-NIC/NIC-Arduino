/*
 * dl_identity.h  —  NIC-MLA datalogger: the 8-byte station-identity encoders.
 *
 * C reference, byte-exact with tools/mla_datalogger.py (dl_gps / dl_ident /
 * dl_raw). The identity is OPAQUE to MLA; this is the glue's choice of meaning.
 * See DESIGN-MLA-datalogger.{md,cs.md,ru.md}.
 *
 * Header-only, reuses the format's little-endian helpers so the bytes match the
 * Python reference exactly. Meant for the master glue that writes the station
 * table on an embedded target.
 *
 * C99  |  MIT  |  ★ Viva La Resistánce ★
 */
#ifndef NIC_DL_IDENTITY_H
#define NIC_DL_IDENTITY_H

#include <stdint.h>
#include "nic_mla_format.h"   /* mla_put_u16/u32, mla_get_u16/u32 (little-endian) */

#define DL_IDENT_LEN 8u

/* Elevation sentinel: i16 0x8000 (INT16_MIN) = unknown/unset. */
#define DL_ELEV_UNKNOWN ((int16_t)0x8000)

/*
 * GPS — latitude + longitude as 2× i32, degrees × 1e7 (~1 cm). This is the form a
 * u-blox / UM980 already reports, so no float is needed on the write path.
 * Recommended for a fixed station: the location IS the identity.
 */
static inline void dl_gps(int32_t lat_e7, int32_t lon_e7, uint8_t out[DL_IDENT_LEN]) {
    mla_put_u32(out + 0, (uint32_t)lat_e7);
    mla_put_u32(out + 4, (uint32_t)lon_e7);
}
static inline void dl_gps_decode(const uint8_t in[DL_IDENT_LEN],
                                 int32_t *lat_e7, int32_t *lon_e7) {
    *lat_e7 = (int32_t)mla_get_u32(in + 0);
    *lon_e7 = (int32_t)mla_get_u32(in + 4);
}

/*
 * Hierarchical — region + number + kind + reserved, 4× u16 (in that byte order).
 * The reserved u16 pads this form to the uniform 8-byte identity (like the GPS
 * lat+lon and the raw form), keeping the station record fixed-size; it is held
 * for a future hierarchical-identity extension, not spare padding to reuse.
 */
static inline void dl_ident(uint16_t region, uint16_t number, uint16_t kind,
                            uint16_t reserved, uint8_t out[DL_IDENT_LEN]) {
    mla_put_u16(out + 0, region);
    mla_put_u16(out + 2, number);
    mla_put_u16(out + 4, kind);
    mla_put_u16(out + 6, reserved);
}

/* Raw — 8 bytes verbatim (the glue assigns the meaning). */
static inline void dl_raw(const uint8_t in[DL_IDENT_LEN], uint8_t out[DL_IDENT_LEN]) {
    for (unsigned i = 0; i < DL_IDENT_LEN; i++) out[i] = in[i];
}

/*
 * Elevation — signed metres as i16 little-endian (2 B). A SEPARATE station-record
 * field, placed after the identity (and after profile_ref in the datalogger
 * table); it is NOT part of the opaque identity. Pass DL_ELEV_UNKNOWN (0x8000,
 * INT16_MIN) when the elevation is unknown/unset. Range ±32767 m, 1 m resolution.
 */
static inline void dl_elev(int16_t metres, uint8_t out[2]) {
    mla_put_u16(out, (uint16_t)metres);
}
static inline int16_t dl_elev_decode(const uint8_t in[2]) {
    return (int16_t)mla_get_u16(in);
}

#endif /* NIC_DL_IDENTITY_H */
