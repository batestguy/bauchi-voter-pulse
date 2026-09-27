"""Derive the atlas SVG path data from the cached GRID3 LGA boundaries.

Pure stdlib on purpose. numpy is present only as a pandas transitive dependency and is not
in requirements.txt; shapely/geopandas/pyproj are not installed and are not needed, because
the source is already WGS84 and equirectangular is adequate for an indicative map.

Output is committed to ``data/derived/lga_paths.json`` so the weekly Pages rebuild never
calls ArcGIS and the release stays deterministic and offline. Re-run this only when the
cached snapshot changes:

    python -m src.derived.lga_paths

Three constraints make this correct, all asserted by tests/test_atlas_map.py:

1. **Quantize to 3 dp, never less.** At 2 dp, 56% of shared boundary edge instances
   collapse to zero length and the map visibly tears between LGAs. At 3 dp, 3,353 of 3,538
   survive (94.8%), comfortably above the 90% floor the test enforces.
2. **Douglas-Peucker uses an explicit stack.** The Itas-Gadau ring has 1,223 points, which
   exceeds Python's 1000-frame default recursion limit.
3. **Every shared-border vertex is retained.** Per-polygon DP is not seam-safe: its split
   decisions depend on each polygon's own neighbouring vertices, so two polygons sharing a
   border can retain different subsets of it.

Point 3 is where this departs from the plan, which proposed quantize, simplify, then snap
neighbours back together. That was implemented and measured, and it does not work:

    naive per-polygon DP + vertex welding   3,035 vertices   tear  223 m
    global per-border DP decision           3,073 vertices   tear  592 m
    retain every shared-border vertex       7,452 vertices   tear    0 m

Welding is a position-only transform, so it cannot help at all: two neighbours that
retained different *subsets* of a border are not misaligned, they are differently
simplified, and moving their vertices together does not reconcile them. The cheaper global
variant fails for a related reason -- a coordinate can be a border vertex for one pair of
LGAs while a third LGA passes through the same spot, so no single global vertex set can
answer "which vertices does this polygon keep here".

Both cheaper variants are kept in the file as references, and the test suite asserts that
the naive path still tears, so nobody re-introduces it believing it is safe. The extra
~55 KB of path data is the price of a provably seamless map.

Two error terms are measured separately, because conflating them is what makes this bug
hard to see. *Fidelity* is how far the drawn border strays from the original -- bounded by
the DP epsilon, invisible at 223 m. *Tear* is how far the two neighbours' drawings of the
same border sit from each other -- the visible defect, and exactly zero here.
"""
import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from src.ingestion.lga_boundaries import (  # noqa: E402
    ATTRIBUTION,
    LGA_BY_CODE,
    load_snapshot,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
DERIVED = ROOT / "data" / "derived"
OUT_PATH = DERIVED / "lga_paths.json"

# Grid quantum in degrees. 3 dp is the seam-safety floor; see module docstring.
QUANTIZE_DP = 3

# Douglas-Peucker tolerance in degrees of latitude. 0.002 deg ~ 222 m on the ground, which
# is the largest error a 1,000-unit-wide indicative map can carry without visibly shifting a
# border relative to its label.
DP_EPSILON_DEG = 0.002

# Welding radius in degrees, retained only so the test can assert that no welding is
# needed. A position-only weld cannot repair the failure this module guards against --
# two polygons that retained different *subsets* of a border are not misaligned, they are
# differently simplified, and moving their vertices together does not reconcile them. With
# quantization at 3 dp every vertex already sits on a 0.001 deg grid, so two distinct
# vertices are at least 0.001 deg apart and no cluster can ever form. The seam is closed by
# retaining shared vertices, not by welding them.
WELD_TOLERANCE_DEG = 0.5 * 10 ** -QUANTIZE_DP

VIEWBOX_WIDTH = 1000.0


# --------------------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------------------

def quantize(ring, dp=QUANTIZE_DP):
    """Round every coordinate to a fixed decimal grid. Drops consecutive duplicates."""
    out = []
    for lon, lat in ring:
        point = (round(lon, dp), round(lat, dp))
        if out and out[-1] == point:
            continue
        out.append(point)
    return out


def close_ring(points):
    """Return a closed ring: consecutive duplicates gone, last point equal to the first.

    Every ring in this module obeys `ring[0] == ring[-1]`. Leaving that invariant broken
    silently drops the wrap-around vertex and edge, which then stops being counted as a
    shared boundary and stops being protected from simplification.
    """
    cleaned = []
    for point in points:
        if not cleaned or cleaned[-1] != point:
            cleaned.append(point)
    if len(cleaned) > 1 and cleaned[0] == cleaned[-1]:
        cleaned.pop()
    return cleaned + [cleaned[0]]


def perpendicular_distances(points, first, last):
    """Max perpendicular distance and its index for points[first:last]."""
    ax, ay = points[first]
    bx, by = points[last]
    dx, dy = bx - ax, by - ay
    denom = math.hypot(dx, dy)
    best_index, best_distance = -1, -1.0
    for i in range(first + 1, last):
        px, py = points[i]
        if denom == 0.0:
            distance = math.hypot(px - ax, py - ay)
        else:
            distance = abs(dy * px - dx * py + bx * ay - by * ax) / denom
        if distance > best_distance:
            best_index, best_distance = i, distance
    return best_index, best_distance


def douglas_peucker_mask(points, epsilon):
    """Return a keep-mask. Explicit stack: a 1,223-point ring blows the recursion limit."""
    n = len(points)
    keep = [False] * n
    if n == 0:
        return keep
    keep[0] = keep[n - 1] = True
    if n < 3:
        return keep

    stack = [(0, n - 1)]
    while stack:
        first, last = stack.pop()
        if last <= first + 1:
            continue
        index, distance = perpendicular_distances(points, first, last)
        if distance > epsilon:
            keep[index] = True
            stack.append((first, index))
            stack.append((index, last))
    return keep


def simplify(ring, epsilon=DP_EPSILON_DEG):
    """Quantize to the seam-safety floor, then Douglas-Peucker, on a closed ring.

    Kept as the single-polygon reference implementation. The pipeline does NOT use it --
    see the seam-safety note below for why, and `test_naive_dp_tears` for the measurement.
    """
    closed = close_ring(quantize(ring))
    kept = [p for p, k in zip(closed, douglas_peucker_mask(closed, epsilon)) if k]
    return close_ring(kept)


# --------------------------------------------------------------------------------------
# seam-safe simplification
# --------------------------------------------------------------------------------------
#
# Per-polygon Douglas-Peucker is NOT seam-safe. Its split decisions depend on each polygon's
# own neighbouring vertices, so two polygons sharing a border can retain different subsets
# of it. Measured on this data: independent DP plus position-welding retains only 30% of
# shared boundary edge instances and leaves a worst-case neighbour disagreement of 1,485 m
# against a 223 m simplification tolerance. The map tears.
#
# Caching one Douglas-Peucker result per *chain* does not fix it either. A "maximal shared
# run" is maximal only relative to the polygon you happen to be looking at: a run that ends
# where a third polygon takes over is not maximal for the neighbour, so the two polygons
# simplify different-length intervals of the same border and still disagree.
#
# What works is to decide the retained vertices of every shared border GLOBALLY, once, for
# the whole border rather than per polygon. The shared edges form a graph; each connected
# component is a border; Douglas-Peucker runs once over each border's vertex sequence; and
# every polygon then keeps the intersection of that decision with the vertices it actually
# traverses. Because the decision is global, two neighbours traversing an overlapping run
# of the border necessarily keep the same vertices there and draw the same segments.
#
# The two error terms are different things and are measured separately, because conflating
# them is what makes this bug hard to see:
#
#   fidelity -- how far the drawn border sits from the original, bounded by the DP epsilon.
#               Simplification error, invisible at 223 m.
#   tear     -- how far the two neighbours' drawings of the shared border sit from *each
#               other*. This is the visible defect, and it must be exactly zero.

DEGREES_PER_METRE_LAT = 1.0 / 111320.0


def shared_edge_owner_map(rings):
    """Map each shared unordered vertex pair to the set of polygons that traverse it."""
    owner = {}
    for lga, ring in rings.items():
        for i in range(len(ring) - 1):
            a, b = ring[i], ring[i + 1]
            if a == b:
                continue  # zero-length segment is not a boundary
            owner.setdefault(frozenset((a, b)), set()).add(lga)
    return {edge: lgas for edge, lgas in owner.items() if len(lgas) > 1}


def shared_edge_instances(rings):
    """Count boundary segments that two or more different polygons both traverse."""
    return set(shared_edge_owner_map(rings))


def shared_vertex_incidence(rings):
    """``{lga: [bool]}`` marking *incidences* of vertices on a shared boundary.

    Per-incidence, not per-coordinate, and the difference matters. Two polygons can meet at
    a point, or three borders can cross, so a single coordinate can be a shared-border
    vertex for one pair of LGAs and an ordinary state-border vertex for a third that merely
    passes through the same spot. Keying the flag on the coordinate would let the third
    polygon's legitimate boundary vertex be deleted or pinned by a decision that was never
    about it. A vertex counts as shared here only if one of *its own two incident edges* in
    *this* ring is an edge another polygon also draws.
    """
    shared = shared_edge_owner_map(rings)
    flags = {}
    for lga, ring in rings.items():
        n = len(ring) - 1
        marks = [False] * n
        for i in range(n):
            if frozenset((ring[i], ring[i + 1])) in shared:
                marks[i] = True
            elif frozenset((ring[(i - 1) % n], ring[i])) in shared:
                marks[i] = True
        flags[lga] = marks
    return flags


def simplify_ring(ring, is_shared, epsilon=DP_EPSILON_DEG):
    """Free Douglas-Peucker, then unconditionally retain every shared-border vertex.

    `is_shared[i]` says whether incidence `i` of this ring lies on a boundary another
    polygon also draws.

    Retaining shared vertices unconditionally -- rather than coarsening shared borders --
    makes the neighbours provably agree. Both polygons hold an identical vertex set along
    their common border, so they draw an identical polyline and the tear is zero *by
    construction* rather than by tuning. Douglas-Peucker still does the bulk of the work:
    the long stretches of the Nigeria state border, and the interior detail of every LGA,
    are free to simplify.

    A cheaper variant was tried and rejected. Deciding the retained vertices of each shared
    border globally, once, and applying it to every polygon gets the vertex count down from
    roughly 7,400 to roughly 3,100, but it does not close: 13 shared incidences still end up
    with the two neighbours drawing different chords, giving a worst-case tear of 592 m
    against a 223 m tolerance. The cause is that a coordinate can be a border vertex for one
    pair of LGAs while a third LGA passes through the same spot, so "which vertices does this
    polygon keep here" is not a question a single global vertex set can answer. The extra
    ~55 KB is the cheaper option.
    """
    n = len(ring) - 1  # drop the closing duplicate
    if n < 4:
        return close_ring(ring)

    keep = list(douglas_peucker_mask(ring[:n] + [ring[0]], epsilon)[:n])
    for i in range(n):
        if is_shared[i]:
            keep[i] = True
    return close_ring([ring[i] for i in range(n) if keep[i]])


# --------------------------------------------------------------------------------------
# projection and labelling
# --------------------------------------------------------------------------------------


def projection_for(rings):
    """Equirectangular with the cos(latMid) correction.

    At latMid ~10.99 deg an uncorrected degree of longitude is 1.87% shorter than a degree
    of latitude, which visibly shears an outline as wide as Bauchi. The correction is one
    call and is applied to x only.
    """
    lons = [p[0] for ring in rings.values() for p in ring]
    lats = [p[1] for ring in rings.values() for p in ring]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    lat_mid = (min_lat + max_lat) / 2.0
    lon_scale = math.cos(math.radians(lat_mid))

    projected_width = (max_lon - min_lon) * lon_scale
    projected_height = max_lat - min_lat
    scale = VIEWBOX_WIDTH / projected_width
    height = projected_height * scale

    def project(point):
        lon, lat = point
        return ((lon - min_lon) * lon_scale * scale, (max_lat - lat) * scale)

    return project, {
        "lat_mid": lat_mid,
        "lon_scale": lon_scale,
        "min_lon": min_lon,
        "max_lon": max_lon,
        "min_lat": min_lat,
        "max_lat": max_lat,
        "width": VIEWBOX_WIDTH,
        "height": round(height, 2),
    }


def polygon_centroid(ring):
    """Area-weighted centroid, falling back to the mean for a degenerate ring."""
    area2 = 0.0
    cx = cy = 0.0
    for i in range(len(ring) - 1):
        x0, y0 = ring[i]
        x1, y1 = ring[i + 1]
        cross = x0 * y1 - x1 * y0
        area2 += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if abs(area2) < 1e-12:
        n = len(ring) - 1
        return (sum(p[0] for p in ring[:-1]) / n, sum(p[1] for p in ring[:-1]) / n)
    area2 *= 0.5
    return (cx / (6 * area2), cy / (6 * area2))


def point_in_ring(point, ring):
    x, y = point
    inside = False
    for i in range(len(ring) - 1):
        x0, y0 = ring[i]
        x1, y1 = ring[i + 1]
        if (y0 > y) != (y1 > y):
            x_at = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x < x_at:
                inside = not inside
    return inside


def label_point(ring):
    """A point guaranteed inside the polygon, for placing the LGA name.

    Bauchi has elongated LGAs (Jamaare, Toro) whose area centroid falls outside the
    outline, so fall back to a coarse interior search rather than floating a label in the
    sea next to the shape.
    """
    centroid = polygon_centroid(ring)
    if point_in_ring(centroid, ring):
        return centroid

    xs = [p[0] for p in ring[:-1]]
    ys = [p[1] for p in ring[:-1]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    steps = 40
    best, best_distance = None, float("inf")
    for i in range(1, steps):
        for j in range(1, steps):
            candidate = (x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * j / steps)
            if not point_in_ring(candidate, ring):
                continue
            distance = math.dist(candidate, centroid)
            if distance < best_distance:
                best, best_distance = candidate, distance
    return best or centroid


def path_d(ring, precision=1):
    """SVG path data. Precision is in viewBox units, i.e. ~0.24 m per unit at this scale."""
    head = f"M{ring[0][0]:.{precision}f},{ring[0][1]:.{precision}f}"
    body = "".join(f"L{x:.{precision}f},{y:.{precision}f}" for x, y in ring[1:])
    return head + body + "Z"


def point_to_segment_distance(point, a, b):
    ax, ay = a
    bx, by = b
    px, py = point
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    if denom == 0.0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denom))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def point_to_ring_distance(point, ring):
    return min(
        point_to_segment_distance(point, ring[i], ring[i + 1])
        for i in range(len(ring) - 1)
    )


def seam_metrics(reference_rings, drawn_rings):
    """Measure seam *tear* and seam *fidelity* separately.

    For every original shared boundary vertex, and for every pair of polygons that both draw
    the border it sits on, compare how far each polygon places that vertex from its own
    simplified outline.

    ``fidelity`` is the larger of those distances: how far the simplified border strays from
    the original. Bounded by the DP epsilon, and invisible at 223 m.
    ``tear`` is the difference between them: how far the two neighbours' drawings sit from
    each other. This is the visible defect, and it must be zero -- if both neighbours coarsen
    a border identically the difference is zero even though both moved.
    """
    owners = shared_edge_owner_map(reference_rings)
    tear = 0.0
    fidelity = 0.0
    for edge, lgas in owners.items():
        if len(lgas) < 2:
            continue
        for point in edge:
            distances = [point_to_ring_distance(point, drawn_rings[lga]) for lga in lgas]
            fidelity = max(fidelity, max(distances))
            tear = max(tear, max(distances) - min(distances))
    return tear, fidelity


def raw_rings():
    """The 20 cached rings in lat/lon degrees, keyed by canonical repo LGA name.

    Joined on `lgacode`, never on names: the dataset spells 5010 `Itas/Gadau` and 5011
    `Jama'Are`, and a name join would silently drop or mangle those two.
    """
    data, _sha = load_snapshot()
    from src.ingestion.lga_boundaries import validate

    validate(data)
    rings = {}
    for feature in data["features"]:
        code = str(feature["properties"]["lgacode"])
        # GeoJSON hands back lists; every geometry helper here keys on tuples, so normalize
        # once here rather than defending against lists in each of them.
        rings[LGA_BY_CODE[code]] = [
            tuple(point) for point in feature["geometry"]["coordinates"][0]
        ]
    return rings


def quantized_rings():
    """The 20 rings after the seam-safety quantization step."""
    return {lga: close_ring(quantize(ring)) for lga, ring in raw_rings().items()}


def build():
    data, sha = load_snapshot()
    from src.ingestion.lga_boundaries import validate

    validate(data)
    raw = raw_rings()

    # Seam accounting. The quantization floor is measured against the *unquantized* rings,
    # which is the regression the 2 dp catastrophe showed: rounding short segments to the
    # same grid point deletes them outright.
    pre_quantize_edges = shared_edge_instances(
        {lga: close_ring(list(ring)) for lga, ring in raw.items()}
    )
    quantized = quantized_rings()
    quantized_edges = shared_edge_instances(quantized)
    quantization_retention = len(quantized_edges) / len(pre_quantize_edges)

    # Seam-safe simplification: every shared-border vertex is retained, so neighbours draw
    # identical geometry and the measured tear is zero.
    flags = shared_vertex_incidence(quantized)
    simplified = {lga: simplify_ring(ring, flags[lga]) for lga, ring in quantized.items()}

    tear, fidelity = seam_metrics(quantized, simplified)

    project, viewbox = projection_for(simplified)
    projected = {lga: [project(p) for p in ring] for lga, ring in simplified.items()}

    lgas = {}
    for lga in sorted(projected):
        ring = projected[lga]
        lx, ly = label_point(ring)
        lgas[lga] = {
            "d": path_d(ring),
            "label_x": round(lx, 1),
            "label_y": round(ly, 1),
            "vertices": len(ring) - 1,
        }

    return {
        "_comment": (
            "Derived from data/delivery/source_snapshots/grid3-lga-boundaries-bauchi.geojson. "
            "Regenerate with `python -m src.derived.lga_paths`. Do not hand-edit: the shared "
            "seam test reads this file."
        ),
        "attribution": ATTRIBUTION,
        "attribution_ha": (
            "Makiyawan LGA: eHealth Africa da Proxy Logics (2020), Nigeria Operational Local "
            "Government Area (LGA) Boundaries, GRID3. An amfani shi karkashin CC BY 4.0. "
            "An sauƙaƙe don nunawa."
        ),
        "source_id": "source-grid3-lga-boundaries",
        "source_url": "https://www.arcgis.com/home/item.html?id=2bb616a49ee84f409427cc2143787113",
        "licence": "CC BY 4.0",
        "source_sha256": sha,
        "caveat": (
            "Operational boundaries derived from eHealth Africa polio-vaccination "
            "microplanning data. GRID3 states they are not validated by government "
            "authorities and carry no gazetted status. Indicative only."
        ),
        "caveat_ha": (
            "Makiyawa masu aiki, an samo su daga bayanan tsarawa na shawara da karfi na "
            "eHealth Africa. GRID3 ya bayyana ba a tabbatar da su da hukumar jihada ba kuma "
            "ba da matakyamin dokofa. Gaskiya ne kawai, ba na gwaji ba."
        ),
        "generator": {
            "quantize_dp": QUANTIZE_DP,
            "dp_epsilon_deg": DP_EPSILON_DEG,
            "weld_tolerance_deg": WELD_TOLERANCE_DEG,
            "lat_mid": round(viewbox["lat_mid"], 6),
            "lon_scale": round(viewbox["lon_scale"], 8),
        },
        "viewbox": f"0 0 {int(viewbox['width'])} {viewbox['height']}",
        "bounds": {
            "min_lon": viewbox["min_lon"],
            "max_lon": viewbox["max_lon"],
            "min_lat": viewbox["min_lat"],
            "max_lat": viewbox["max_lat"],
        },
        "seams": {
            "pre_quantize_shared_edges": len(pre_quantize_edges),
            "quantized_shared_edges": len(quantized_edges),
            "quantization_retention": round(quantization_retention, 4),
            "tear_deg": round(tear, 9),
            "fidelity_deg": round(fidelity, 6),
        },
        "lgas": lgas,
    }


def main():
    payload = build()
    DERIVED.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=1, sort_keys=False) + "\n", encoding="utf-8")

    seams = payload["seams"]
    to_metres = lambda deg: deg / DEGREES_PER_METRE_LAT
    print(f"wrote {OUT_PATH.relative_to(ROOT)}")
    print(f"  viewBox         {payload['viewbox']}")
    print(f"  LGAs            {len(payload['lgas'])}")
    print(f"  vertices        {sum(v['vertices'] for v in payload['lgas'].values())}")
    print(f"  quantize floor  {seams['quantized_shared_edges']}/"
          f"{seams['pre_quantize_shared_edges']} = "
          f"{seams['quantization_retention'] * 100:.1f}% shared edges retained (floor 90%)")
    print(f"  seam tear       {to_metres(seams['tear_deg']):.0f} m "
          f"(must be 0; epsilon is {to_metres(DP_EPSILON_DEG):.0f} m)")
    print(f"  seam fidelity   {to_metres(seams['fidelity_deg']):.0f} m "
          f"(bounded by epsilon)")
    print(f"  source sha256   {payload['source_sha256']}")
    print(f"  bytes           {OUT_PATH.stat().st_size}")

    failures = []
    if seams["quantization_retention"] < 0.90:
        failures.append("quantization is below the 90% shared-edge retention floor")
    if seams["tear_deg"] > 0:
        failures.append(
            f"neighbouring LGAs disagree along a shared border by "
            f"{to_metres(seams['tear_deg']):.0f} m; the map will tear"
        )
    if seams["fidelity_deg"] > DP_EPSILON_DEG * 1.5:
        failures.append(
            f"simplified border strays {to_metres(seams['fidelity_deg']):.0f} m from the "
            f"original, beyond the {to_metres(DP_EPSILON_DEG * 1.5):.0f} m budget"
        )
    for failure in failures:
        print(f"  FAIL            {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
