"""Fetch the GRID3 / eHealth Africa operational LGA boundaries for Bauchi, once.

This is a *boundary* source, not a news source. It is fetched on demand, cached as a raw
snapshot for provenance, and never called by the weekly Pages build -- the renderer reads
the committed derivative in ``data/derived/lga_paths.json`` instead, so the release stays
deterministic and offline.

Source
    GRID3 NGA - Operational LGA Boundaries, ArcGIS item 2bb616a49ee84f409427cc2143787113
    Layer 0 ``NGA_LGA_Boundaries_2`` (administrative level 2, Nigeria).

Licence
    CC BY 4.0. Commercial use permitted; attribution is the sole obligation and there is
    **no ShareAlike**, so the simplified derivative may be published on our own terms.
    That is exactly why this module must never touch the sibling GRID3 **Wards** layers:
    those are CC BY-SA 4.0 and would force BY-SA onto the whole site.

Status of the boundaries
    *Operational*, descended from eHealth Africa's polio-vaccination microplanning data.
    GRID3 states they are not validated by government authorities and carry no gazetted
    status. Present them as indicative, never as official boundaries.
"""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

from .common import ROBOTS_UNREACHABLE_HOSTS, polite_get

# Repeated at the call site on purpose. common.polite_get refuses a thin exemption, and the
# whole point of the exception is that it stays auditable rather than becoming a blanket
# "skip robots" flag.
ROBOTS_EXEMPTION = (
    "One-time cached fetch of the GRID3 open-data LGA boundary layer. "
    "services3.arcgis.com returns 403 for robots.txt under every user agent, so the file is "
    "WAF-blocked rather than absent; the registrable domain arcgis.com serves a retrievable "
    "permissive robots.txt, and this is ArcGIS's documented public FeatureServer query API. "
    "The layer is CC BY 4.0. The weekly Pages build never makes this request."
)

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOTS = ROOT / "data" / "delivery" / "source_snapshots"

ARCGIS_ITEM_ID = "2bb616a49ee84f409427cc2143787113"
# The service moved org in 2024. Do not hardcode the old services9 host: it 400s.
FEATURESERVER = (
    "https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services"
    "/NGA_LGA_Boundaries_2/FeatureServer/0"
)
QUERY_URL = (
    FEATURESERVER
    + "/query?where=statecode%3D%27BA%27&outFields=*&returnGeometry=true"
    + "&outSR=4326&f=geojson"
)
ITEM_URL = f"https://www.arcgis.com/sharing/rest/content/items/{ARCGIS_ITEM_ID}?f=json"

SNAPSHOT_NAME = "grid3-lga-boundaries-bauchi.geojson"

# Wards are CC BY-SA. Guarded by tests/test_atlas_map.py; kept here as data, not a comment,
# so a test can assert this module never references a ward layer.
FORBIDDEN_LAYER_FRAGMENTS = ("Wards", "ward")

# The exact credit line CC BY requires, plus the change-indication clause. render.py ships
# this verbatim under the map, and a test asserts the page carries it.
ATTRIBUTION = (
    "LGA boundaries: eHealth Africa and Proxy Logics (2020), Nigeria Operational Local "
    "Government Area (LGA) Boundaries, GRID3. Used under CC BY 4.0. Simplified for display."
)

# Canonical repo LGA name keyed by the dataset's stable lgacode (5001-5020). Joining on the
# code rather than the name is what makes the two known name mismatches structurally
# impossible to get wrong: the dataset spells 5010 "Itas/Gadau" and 5011 "Jama'Are".
LGA_BY_CODE = {
    "5001": "Alkaleri",
    "5002": "Bauchi",
    "5003": "Bogoro",
    "5004": "Dambam",
    "5005": "Darazo",
    "5006": "Dass",
    "5007": "Gamawa",
    "5008": "Ganjuwa",
    "5009": "Giade",
    "5010": "Itas-Gadau",
    "5011": "Jamaare",
    "5012": "Katagum",
    "5013": "Kirfi",
    "5014": "Misau",
    "5015": "Ningi",
    "5016": "Shira",
    "5017": "Tafawa-Balewa",
    "5018": "Toro",
    "5019": "Warji",
    "5020": "Zaki",
}


class BoundaryError(RuntimeError):
    """Raised when the cached or fetched boundaries are not the shape we depend on."""


# Fail fast if the query ever moves to a host that has no recorded robots exemption.
if urlparse(QUERY_URL).netloc not in ROBOTS_UNREACHABLE_HOSTS:
    raise BoundaryError(
        f"QUERY_URL host {urlparse(QUERY_URL).netloc!r} is not in ROBOTS_UNREACHABLE_HOSTS. "
        "Either it serves a retrievable robots.txt (drop the exemption) or it needs one "
        "recorded with its justification before this module can fetch from it."
    )


def snapshot_path():
    return SNAPSHOTS / SNAPSHOT_NAME


def content_hash(raw):
    return hashlib.sha256(raw).hexdigest()


def load_snapshot():
    """Read the cached GeoJSON. Raises BoundaryError if it is not cached yet."""
    path = snapshot_path()
    if not path.exists():
        raise BoundaryError(
            f"{path} is missing. Run `python -m src.ingestion.lga_boundaries` once to "
            "fetch and cache the boundaries."
        )
    raw = path.read_bytes()
    try:
        return json.loads(raw.decode("utf-8")), content_hash(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BoundaryError(f"cached snapshot at {path} is not valid UTF-8 GeoJSON: {exc}") from exc


def fetch_snapshot(force=False):
    """Fetch once and cache. Refuses to overwrite an existing snapshot unless forced."""
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    path = snapshot_path()
    if path.exists() and not force:
        return load_snapshot()

    resp = polite_get(QUERY_URL, robots_exemption=ROBOTS_EXEMPTION)
    raw = resp.content
    data = json.loads(raw.decode("utf-8"))
    validate(data)
    path.write_bytes(raw)
    return data, content_hash(raw)


def validate(data):
    """Fail closed on anything the atlas cannot honestly render."""
    features = data.get("features") or []
    if len(features) != 20:
        raise BoundaryError(f"expected 20 Bauchi LGAs, got {len(features)}")

    codes = set()
    for feature in features:
        props = feature.get("properties") or {}
        code = str(props.get("lgacode", ""))
        if code not in LGA_BY_CODE:
            raise BoundaryError(f"unexpected lgacode {code!r} (lganame={props.get('lganame')!r})")
        codes.add(code)

        geom = feature.get("geometry") or {}
        if geom.get("type") != "Polygon":
            raise BoundaryError(
                f"{LGA_BY_CODE[code]} is {geom.get('type')}, not Polygon. The atlas renderer "
                "handles single-ring polygons only; a MultiPolygon would need new code."
            )
        rings = geom.get("coordinates") or []
        if len(rings) != 1:
            raise BoundaryError(
                f"{LGA_BY_CODE[code]} has {len(rings)} rings, expected 1 outer ring and 0 holes."
            )
        ring = rings[0]
        if len(ring) < 4:
            raise BoundaryError(f"{LGA_BY_CODE[code]} ring has only {len(ring)} points")
        if ring[0] != ring[-1]:
            raise BoundaryError(f"{LGA_BY_CODE[code]} ring is not explicitly closed")

    if codes != set(LGA_BY_CODE):
        missing = sorted(set(LGA_BY_CODE) - codes)
        raise BoundaryError(f"missing lgacodes: {missing}")
    return True


def rings_by_lga():
    """Return ``{canonical_lga_name: [ring]}`` joined on lgacode, never on names."""
    data, _ = load_snapshot()
    validate(data)
    out = {}
    for feature in data["features"]:
        code = str(feature["properties"]["lgacode"])
        out[LGA_BY_CODE[code]] = feature["geometry"]["coordinates"][0]
    return out


def item_metadata():
    """Live item metadata. The licence string is the rights record, so keep it readable.

    This host has a retrievable, permissive robots.txt, so it needs no exemption.
    """
    return polite_get(ITEM_URL).json()


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="re-fetch and overwrite the cached snapshot")
    args = parser.parse_args()

    data, sha = fetch_snapshot(force=args.force)
    meta = item_metadata()
    print(f"cached {snapshot_path().relative_to(ROOT)}")
    print(f"  sha256   {sha}")
    print(f"  features {len(data['features'])}")
    print(f"  licence  {meta.get('licenseInfo', '(none)')[:120]}")
    print(f"  credit   {meta.get('accessInformation', '(none)')[:120]}")


if __name__ == "__main__":
    main()
