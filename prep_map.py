"""Prep the world-land coastlines for the 23 Nov newspaper map.

Downloads the Natural Earth 1:110m land TopoJSON from jsDelivr, decodes it
(delta-encoded arcs + transform), drops Antarctica, rounds coordinates to
0.2 degrees, drops consecutive duplicates and rings under 0.8 square
degrees, and writes world_land.json as rings of [lon, lat] with one decimal.

Usage: python3 prep_map.py [out.json]
Default output: world_land.json next to this script.
"""

import json
import math
import sys
import urllib.request

URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/land-110m.json"


def decode_arcs(topo):
    """Return a list of arcs; each arc is a list of absolute [lon, lat]."""
    scale = topo["transform"]["scale"]
    translate = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        pts = []
        x = 0
        y = 0
        for dx, dy in arc:
            x += dx
            y += dy
            lon = x * scale[0] + translate[0]
            lat = y * scale[1] + translate[1]
            pts.append([lon, lat])
        arcs.append(pts)
    return arcs


def arc_points(arcs, index):
    """Points of arc `index`; a negative index means the arc reversed."""
    if index >= 0:
        return arcs[index]
    return list(reversed(arcs[~index]))


def join_arcs(arcs, arc_indices):
    """Join a list of arc indices into one ring, skipping each arc's first
    point after the first arc (the shared join point)."""
    ring = []
    for i, idx in enumerate(arc_indices):
        pts = arc_points(arcs, idx)
        if i == 0:
            ring.extend(pts)
        else:
            ring.extend(pts[1:])
    return ring


def ring_area_sqdeg(ring):
    """Shoelace area in square degrees (absolute value)."""
    total = 0.0
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "world_land.json"
    print("downloading", URL)
    with urllib.request.urlopen(URL, timeout=60) as resp:
        topo = json.load(resp)
    arcs = decode_arcs(topo)
    print("arcs:", len(arcs))

    land = topo["objects"]["land"]
    rings = []
    for geom in land["geometries"]:
        if geom["type"] == "Polygon":
            for arc_list in geom["arcs"]:
                rings.append(join_arcs(arcs, arc_list))
        elif geom["type"] == "MultiPolygon":
            for poly in geom["arcs"]:
                for arc_list in poly:
                    rings.append(join_arcs(arcs, arc_list))
    print("raw rings:", len(rings))

    kept = []
    dropped_antarctica = 0
    dropped_small = 0
    for ring in rings:
        # Drop Antarctica: every ring whose highest latitude is below -55.
        if max(p[1] for p in ring) < -55:
            dropped_antarctica += 1
            continue
        # Round to 0.2 degrees and drop consecutive duplicates.
        rounded = []
        for lon, lat in ring:
            rlon = round(lon / 0.2) * 0.2
            rlat = round(lat / 0.2) * 0.2
            pt = [round(rlon, 1), round(rlat, 1)]
            if not rounded or rounded[-1] != pt:
                rounded.append(pt)
        # Close the ring if the rounding opened it.
        if len(rounded) > 1 and rounded[0] != rounded[-1]:
            rounded.append(rounded[0])
        if len(rounded) < 4:
            dropped_small += 1
            continue
        if ring_area_sqdeg(rounded) < 0.8:
            dropped_small += 1
            continue
        kept.append(rounded)

    total_points = sum(len(r) for r in kept)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(kept, f)
    print("dropped Antarctica rings:", dropped_antarctica)
    print("dropped small rings:", dropped_small)
    print("kept rings:", len(kept))
    print("kept points:", total_points)
    print("wrote", out_path)


if __name__ == "__main__":
    main()
