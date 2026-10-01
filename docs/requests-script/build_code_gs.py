"""Generate docs/requests-script/Code.gs from its template plus the real ward map.

The registration areas AND the LGA spellings come from data/delivery/lga_wards.csv, the
same file the request form uses, so the endpoint's idea of which area belongs to which LGA
cannot drift from the form's. Generating the LGA list too removes the last hand-typed copy
of the 20 names.

Regenerate with:  python docs/requests-script/build_code_gs.py
"""
import csv
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.stdout.reconfigure(encoding="utf-8")

TEMPLATE = ROOT / "docs" / "requests-script" / "Code.gs.template"
OUTPUT = ROOT / "docs" / "requests-script" / "Code.gs"
WARDS = ROOT / "data" / "delivery" / "lga_wards.csv"


def build_ward_map() -> tuple[str, list[str]]:
    by_lga: dict[str, list[str]] = {}
    with WARDS.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            lga = (row.get("lga") or "").strip()
            code = (row.get("ward_code") or "").strip()
            if lga and code:
                by_lga.setdefault(lga, []).append(code)
    if not by_lga:
        raise SystemExit("no registration areas found; refusing to write an empty map")
    # Sorted so a regeneration produces a byte-identical file, which keeps the diff honest.
    ward_map = ";".join(
        f"{lga}:{','.join(sorted(codes))}" for lga, codes in sorted(by_lga.items())
    )
    return ward_map, sorted(by_lga)


def main() -> int:
    ward_map, lgas = build_ward_map()
    lga_list = json.dumps(lgas, ensure_ascii=False)
    text = TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("__WARD_MAP__", ward_map).replace("__LGA_LIST__", lga_list)
    for placeholder in ("__WARD_MAP__", "__LGA_LIST__"):
        if placeholder in text:
            raise SystemExit(f"{placeholder} still present after substitution")
    OUTPUT.write_text(text, encoding="utf-8")
    areas = sum(len(codes.split(",")) for codes in ward_map.split(";"))
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    print(f"  {len(lgas)} LGAs, {areas} registration areas, {len(ward_map)} bytes of map")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())