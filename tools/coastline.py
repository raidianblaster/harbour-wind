#!/usr/bin/env python3
"""Build the embedded coastline (COAST in index.html) from OpenStreetMap.

1. Download OSM coastline ways for the artwork's bbox (Overpass API):
     curl -s --data-urlencode 'data=[out:json][timeout:90];way["natural"="coastline"](22.12,113.80,22.59,114.46);out geom;' \
          https://overpass-api.de/api/interpreter -o coast.json
2. python3 tools/coastline.py coast.json   -> prints stats and writes coast.txt
3. Replace the COAST line in index.html with coast.txt (already a JS-escaped string literal).

Steps: stitch ways into chains by shared end nodes, cut chains to the map bbox
(plus a margin), simplify with Douglas-Peucker in km, drop islets whose
outline is shorter than MIN_LEN_KM, and encode with the Google polyline
algorithm at 1e-4 degree precision (~11 m). Lines are separated by a space
(polyline output only uses ASCII 63-126, so a space can never occur inside one).
Data (c) OpenStreetMap contributors, ODbL.
"""
import json
import math
import sys

LON0, LON1, LAT0, LAT1 = 113.84, 114.42, 22.15, 22.56
MARGIN = 0.01          # degrees kept outside the bbox so lines run off-screen cleanly
TOL_KM = 0.035         # simplification tolerance (~1 px on a 1600 px wide screen)
MIN_LEN_KM = 0.6       # drop rocks and tiny islets
KX = 111.32 * math.cos(math.radians(22.355))
KY = 110.57


def stitch(ways):
    """Join ways that share end nodes into longer chains of (lat, lon)."""
    segs = [(w["nodes"], [(g["lat"], g["lon"]) for g in w["geometry"]]) for w in ways]
    by_start = {}
    for i, (n, _) in enumerate(segs):
        by_start.setdefault(n[0], []).append(i)
    used = set()
    chains = []
    for i, (nodes, pts) in enumerate(segs):
        if i in used:
            continue
        used.add(i)
        chain, tail = list(pts), nodes[-1]
        while True:
            nxt = next((j for j in by_start.get(tail, []) if j not in used), None)
            if nxt is None:
                break
            used.add(nxt)
            chain += segs[nxt][1][1:]
            tail = segs[nxt][0][-1]
        chains.append(chain)
    return chains


def inside(p):
    return LAT0 - MARGIN <= p[0] <= LAT1 + MARGIN and LON0 - MARGIN <= p[1] <= LON1 + MARGIN


def clip(chain):
    """Split a chain into the runs that lie inside the (expanded) bbox."""
    out, run = [], []
    for p in chain:
        if inside(p):
            run.append(p)
        elif run:
            out.append(run)
            run = []
    if run:
        out.append(run)
    return [r for r in out if len(r) > 1]


def km(p):
    return (p[1] * KX, p[0] * KY)


def dp(pts, tol):
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    P = [km(p) for p in pts]
    while stack:
        a, b = stack.pop()
        (ax, ay), (bx, by) = P[a], P[b]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy)
        best, idx = 0.0, -1
        for i in range(a + 1, b):
            px, py = P[i]
            d = abs(dy * (px - ax) - dx * (py - ay)) / L if L else math.hypot(px - ax, py - ay)
            if d > best:
                best, idx = d, i
        if best > tol:
            keep[idx] = True
            stack += [(a, idx), (idx, b)]
    return [p for p, k in zip(pts, keep) if k]


def length_km(pts):
    P = [km(p) for p in pts]
    return sum(math.hypot(P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1]) for i in range(len(P) - 1))


def encode(pts):
    out, plat, plon = [], 0, 0
    for lat, lon in pts:
        ilat, ilon = round(lat * 1e4), round(lon * 1e4)
        for v in (ilat - plat, ilon - plon):
            v = ~(v << 1) if v < 0 else v << 1
            while v >= 0x20:
                out.append(chr((0x20 | (v & 0x1F)) + 63))
                v >>= 5
            out.append(chr(v + 63))
        plat, plon = ilat, ilon
    return "".join(out)


def main():
    src = json.load(open(sys.argv[1]))
    ways = [e for e in src["elements"] if e["type"] == "way" and e.get("geometry")]
    lines = []
    for chain in stitch(ways):
        for run in clip(chain):
            if length_km(run) < MIN_LEN_KM:
                continue
            s = dp(run, TOL_KM)
            if len(s) > 1:
                lines.append(s)
    enc = " ".join(encode(l) for l in lines)
    open("coast.txt", "w").write("const COAST=" + json.dumps(enc) + ";\n")
    print(f"{len(ways)} ways -> {len(lines)} lines, {sum(map(len, lines))} points, {len(enc) / 1024:.1f} KB encoded")


if __name__ == "__main__":
    main()
