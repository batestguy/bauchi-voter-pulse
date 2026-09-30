"""Generate docs/apps-script/Code.gs from its template plus the real ward map.

The registration areas come from data/delivery/lga_wards.csv, the same file the request
form uses, so the endpoint's idea of which area belongs to which LGA cannot drift from the
form's. Regenerate with:  python docs/apps-script/build_code_gs.py
"""
import csv
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.stdout.reconfigure(encoding="utf-8")

TEMPLATE = ROOT / "docs" / "apps-script" / "Code.gs.template"
OUTPUT = ROOT / "docs" / "apps-script" / "Code.gs"
WARDS = ROOT / "data" / "delivery" / "lga_wards.csv"


def build_ward_map() -> str:
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
    return ";".join(
        f"{lga}:{','.join(sorted(codes))}" for lga, codes in sorted(by_lga.items())
    )


def main() -> int:
    ward_map = build_ward_map()
    areas = sum(len(v) for v in ward_map.split(";")) and ward_map.count(",") + 20
    text = TEMPLATE.read_text(encoding="utf-8").replace("__WARD_MAP__", ward_map)
    if "__WARD_MAP__" in text:
        raise SystemExit("placeholder still present after substitution")
    OUTPUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    print(f"  {ward_map.count(':')} LGAs, {areas} registration areas, "
          f"{len(ward_map)} bytes of map")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
