#!/usr/bin/env python3
"""TEMPORARY HANDOFF COPY — standalone per-site bathymetry for NIC Gaia.

This is a network-capable session's work parcel: the canonical script and
doctrine live in the (private) NIC-Heimdall repo (gaia/tools/gen_bathy.py);
this copy reads sites.json (index, lon, lat, threat bearing) instead of the
Gaia GeoJSON so it can run without access to that repo. The whole
handoff/gaia-bathy/ directory is deleted once the results are merged back.

For each site: fetch a cached ETOPO tile (NOAA ERDDAP, 2-arc-min), walk
LANDWARD against the threat bearing to the real shore, profile SEAWARD along
the bearing, find the slope toe = first crossing of min(4000 m, 0.85 x the
profile's max depth). Writes bathy-per-site.csv: shore position, cable
length (shore -> toe), sonde depth.

Needs outbound HTTPS to coastwatch.pfeg.noaa.gov. Fails loudly on 403.
"""
import csv, json, math, os, sys, time, urllib.request, urllib.error

HERE  = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "bathy_cache")
os.makedirs(CACHE, exist_ok=True)

ERDDAP = ("https://coastwatch.pfeg.noaa.gov/erddap/griddap/etopo180.csv"
          "?altitude%5B({la0}):2:({la1})%5D%5B({lo0}):2:({lo1})%5D")

BOX_DEG      = 3.2
LAND_MAX_KM  = 320.0
SEA_MAX_KM   = 260.0
STEP_KM      = 2.0
TOE_CAP_M    = 4000.0
TOE_FRAC     = 0.85

def fetch(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return r.read().decode()
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            if i == tries - 1: raise
            time.sleep(2 ** (i + 1))

def tile(idx, lon, lat):
    fn = os.path.join(CACHE, f"site_{idx:03d}.csv")
    if not os.path.exists(fn):
        la0, la1 = max(-89.9, lat - BOX_DEG), min(89.9, lat + BOX_DEG)
        lo0, lo1 = lon - BOX_DEG, lon + BOX_DEG
        if lo0 < -180: spans = [(-180, lo1), (lo0 + 360, 180)]
        elif lo1 > 180: spans = [(lo0, 180), (-180, lo1 - 360)]
        else: spans = [(lo0, lo1)]
        chunks = []
        for s0, s1 in spans:
            chunks.append(fetch(ERDDAP.format(la0=la0, la1=la1, lo0=s0, lo1=s1)))
            time.sleep(0.4)
        with open(fn, "w") as f: f.write("\n".join(chunks))
    grid = {}
    for line in open(fn):
        p = line.strip().split(",")
        if len(p) != 3: continue
        try: la, lo, al = float(p[0]), float(p[1]), float(p[2])
        except ValueError: continue
        grid[(round(la, 4), round(lo, 4))] = al
    lats = sorted({k[0] for k in grid}); lons = sorted({k[1] for k in grid})
    return lats, lons, grid

def nearest(vals, x):
    lo, hi = 0, len(vals) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if vals[m] < x: lo = m
        else: hi = m
    return vals[lo] if abs(vals[lo] - x) <= abs(vals[hi] - x) else vals[hi]

def sample(lats, lons, grid, lon, lat):
    lon = (lon + 180) % 360 - 180
    if not lats or not lons: return None
    return grid.get((nearest(lats, round(lat, 4)), nearest(lons, round(lon, 4))))

def walk(lon, lat, bearing_deg, km):
    b = math.radians(bearing_deg)
    dlat = km * math.cos(b) / 111.32
    dlon = km * math.sin(b) / (111.32 * math.cos(math.radians(lat)) or 1e-9)
    return lon + dlon, lat + dlat

def site_numbers(idx, lon, lat, tb):
    lats, lons, grid = tile(idx, lon, lat)
    shore = None
    d = 0.0
    while d <= LAND_MAX_KM:
        x, y = walk(lon, lat, (tb + 180) % 360, d)
        a = sample(lats, lons, grid, x, y)
        if a is not None and a >= 0: shore = (x, y); break
        d += STEP_KM
    if shore is None: return None
    sx, sy = shore
    prof = []
    d = STEP_KM
    while d <= SEA_MAX_KM:
        x, y = walk(sx, sy, tb, d)
        a = sample(lats, lons, grid, x, y)
        if a is not None and a < 0: prof.append((d, -a))
        d += STEP_KM
    if not prof: return None
    dmax = max(p[1] for p in prof)
    target = min(TOE_CAP_M, TOE_FRAC * dmax)
    for d, dep in prof:
        if dep >= target:
            return {"shore_lon": round(sx, 3), "shore_lat": round(sy, 3),
                    "cable_km": round(d), "sonde_depth_m": round(dep),
                    "profile_max_m": round(dmax)}
    d, dep = prof[-1]
    return {"shore_lon": round(sx, 3), "shore_lat": round(sy, 3),
            "cable_km": round(d), "sonde_depth_m": round(dep),
            "profile_max_m": round(dmax), "note": "toe beyond profile reach"}

def main():
    sites = json.load(open(os.path.join(HERE, "sites.json")))
    rows = []
    for s in sites:
        try:
            r = site_numbers(s["i"], s["lon"], s["lat"], s["tb"])
        except Exception as e:
            print(f"[{s['i']:3d}] FETCH FAILED ({e}) — is coastwatch.pfeg.noaa.gov "
                  f"allowed in the network policy?", file=sys.stderr)
            sys.exit(1)
        row = {"site": s["i"], "lon": s["lon"], "lat": s["lat"],
               "threat_deg": s["tb"]}
        if r: row.update(r)
        else: row["note"] = "no shore/profile resolved"
        rows.append(row)
        if s["i"] % 20 == 0: print(f"{s['i']}/{len(sites)} sites done", flush=True)
    cols = ["site","lon","lat","threat_deg","shore_lon","shore_lat",
            "cable_km","sonde_depth_m","profile_max_m","note"]
    out = os.path.join(HERE, "bathy-per-site.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in rows: w.writerow(r)
    ok = [r for r in rows if "cable_km" in r]
    print(f"\nresolved {len(ok)}/{len(rows)} sites, "
          f"total cable ~{sum(r['cable_km'] for r in ok):,} km")
    print(f"wrote {out}")

if __name__ == "__main__":
    main()
