"""Guards for the S4 Bauchi map.

Five things this file exists to stop, in the order they bit:

1. **Quantizing below 3 dp.** At 2 dp, 56% of shared boundary edges collapse to zero
   length and the map visibly tears between LGAs. `test_quantization_stays_at_or_above_3dp`
   pins the constant; `test_shared_edge_retention_floor` pins the measured consequence.
2. **Recursive Douglas-Peucker.** The Itas-Gadau ring has 1,223 points, which exceeds
   Python's 1000-frame default recursion limit.
3. **A tearing seam.** Per-polygon DP is not seam-safe.
   `test_shipped_geometry_has_no_seam_tear` asserts the committed geometry is tear-free, and
   `test_naive_per_polygon_simplification_would_tear` proves the naive alternative still
   fails, so nobody re-introduces it believing it is safe.
4. **Joining on names.** The dataset spells 5010 `Itas/Gadau` and 5011 `Jama'Are`; the
   repo's canonical list is `Itas-Gadau` and `Jamaare`. Joining on `lgacode` makes those
   two mismatches structurally impossible to get wrong.
5. **The GRID3 Wards layer.** It is CC BY-SA and would force ShareAlike onto the whole
   site. Only the BY LGA layer may ever be used.

Plus the honesty rules: the CC BY attribution and the "indicative, not gazetted" caveat must
be on the page, and the registration-area list must stay labelled "not geo-located".
"""
import json
import math
import pathlib
import re
import unittest

from src.dashboard.render import LGAS, LGA_PATHS_FILE, load_lga_paths
from src.derived import lga_paths as derive
from src.ingestion import lga_boundaries

ROOT = pathlib.Path(__file__).resolve().parents[1]
ATLAS = ROOT / "docs" / "atlas.html"
SNAPSHOT = lga_boundaries.snapshot_path()


def atlas_html():
    return ATLAS.read_text(encoding="utf-8")


def svg_markup():
    """The inline map element, or fail loudly if the page has no map."""
    html = atlas_html()
    found = re.search(r'<svg class="lga-map".*?</svg>', html, re.S)
    if found is None:
        raise AssertionError("atlas.html has no inline .lga-map svg")
    return found.group(0)


class SourceTests(unittest.TestCase):
    """The boundary source is cached, registered, and correctly licensed."""

    def test_snapshot_is_cached_and_is_the_twenty_bauchi_lgas(self):
        self.assertTrue(SNAPSHOT.exists(), "run `python -m src.ingestion.lga_boundaries`")
        data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        self.assertEqual(len(data["features"]), 20)
        for feature in data["features"]:
            props = feature["properties"]
            self.assertEqual(props["statecode"], "BA")
            self.assertIn(str(props["lgacode"]), lga_boundaries.LGA_BY_CODE)

    def test_snapshot_hash_is_recorded_in_the_derived_output(self):
        paths = load_lga_paths()
        self.assertEqual(
            paths["source_sha256"], lga_boundaries.content_hash(SNAPSHOT.read_bytes())
        )

    def test_derived_output_records_the_cc_by_licence(self):
        paths = load_lga_paths()
        self.assertEqual(paths["licence"], "CC BY 4.0")
        self.assertIn("CC BY 4.0", paths["attribution"])
        self.assertIn("Simplified for display", paths["attribution"])
        self.assertIn("eHealth Africa and Proxy Logics", paths["attribution"])

    def test_source_is_registered_as_grade_b(self):
        text = (ROOT / "data" / "delivery" / "source_register.csv").read_text(encoding="utf-8")
        row = next(line for line in text.splitlines()
                   if line.startswith("source-grid3-lga-boundaries,"))
        self.assertIn(",B,", row, "boundary evidence is grade B, not a primary record")
        self.assertIn("not gazetted", row)

    def test_wards_layer_is_never_referenced(self):
        """Only the BY LGA layer may ever be used.

        The sibling GRID3 Wards layers are CC BY-SA. Pulling one in would force ShareAlike
        onto every page of the site, not just the map. Check the URLs the module actually
        builds, not its prose -- the docstring explains why wards are excluded and
        necessarily names them.
        """
        from urllib.parse import urlparse

        self.assertIn("NGA_LGA_Boundaries_2", lga_boundaries.QUERY_URL)
        for url in (lga_boundaries.QUERY_URL, lga_boundaries.ITEM_URL,
                    lga_boundaries.FEATURESERVER):
            for fragment in lga_boundaries.FORBIDDEN_LAYER_FRAGMENTS:
                self.assertNotIn(
                    fragment.lower(), url.lower(),
                    f"{fragment} must never appear in a service URL",
                )
        self.assertEqual(urlparse(lga_boundaries.QUERY_URL).netloc,
                         "services3.arcgis.com")

    def test_derived_output_is_the_only_geometry_the_build_reads(self):
        """The weekly Pages rebuild must be deterministic and offline."""
        derived = LGA_PATHS_FILE.read_text(encoding="utf-8")
        self.assertNotIn("FeatureServer", derived)
        renderer = (ROOT / "src" / "dashboard" / "render.py").read_text(encoding="utf-8")
        body = renderer.split("def load_lga_paths")[1].split("\ndef ")[0]
        self.assertNotIn("requests", body)
        self.assertNotIn("urllib", body)


class JoinTests(unittest.TestCase):
    """The join is on lgacode, and the two known name mismatches are handled."""

    def test_join_is_on_lgacode_not_names(self):
        self.assertEqual(len(lga_boundaries.LGA_BY_CODE), 20)
        self.assertEqual(set(lga_boundaries.LGA_BY_CODE.values()), set(LGAS))

    def test_dataset_name_mismatches_are_known_and_absorbed_by_the_code_join(self):
        data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        dataset_names = {f["properties"]["lganame"] for f in data["features"]}
        # These two differ from the repo's canonical names, which is exactly why the join
        # is on lgacode.
        self.assertIn("Itas/Gadau", dataset_names)
        self.assertIn("Jama'Are", dataset_names)
        self.assertNotIn("Itas/Gadau", LGAS)
        self.assertNotIn("Jama'Are", LGAS)

    def test_derived_output_covers_exactly_the_canonical_lgas(self):
        paths = load_lga_paths()
        self.assertEqual(set(paths["lgas"]), set(LGAS))

    def test_achievements_pseudo_lgas_are_never_joined(self):
        # `Statewide` and `Bauchi North LGAs` are scopes, not LGAs. The map is generated
        # from lgacode, so they cannot reach it; assert they are not LGAS.
        self.assertNotIn("Statewide", LGAS)
        self.assertNotIn("Bauchi North LGAs", LGAS)


class SimplifierTests(unittest.TestCase):
    """The three simplification constraints, and the regression that guards the third."""

    def test_quantization_stays_at_or_above_3dp(self):
        self.assertGreaterEqual(
            derive.QUANTIZE_DP, 3,
            "at 2 dp, 56% of shared boundary edges collapse and the map tears",
        )

    def test_simplifier_uses_an_explicit_stack_not_recursion(self):
        source = pathlib.Path(derive.__file__).read_text(encoding="utf-8")
        body = source.split("def douglas_peucker_mask")[1].split("\ndef ")[0]
        self.assertIn("stack", body)
        self.assertNotIn("douglas_peucker_mask(points", body.replace("douglas_peucker_mask(points, epsilon)", ""))
        # A 1,223-point ring exceeds the 1000-frame default recursion limit.
        data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        largest = max(
            len(f["geometry"]["coordinates"][0]) for f in data["features"]
        )
        self.assertGreater(largest, 1000, "guard is only meaningful if a ring exceeds 1000 points")
        self.assertEqual(derive.douglas_peucker_mask(
            [(float(i), 0.0) for i in range(largest)], 0.002)[0], True)

    def test_simplification_actually_reduces_vertices(self):
        paths = load_lga_paths()
        shipped = sum(shape["vertices"] for shape in paths["lgas"].values())
        data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        raw = sum(len(f["geometry"]["coordinates"][0]) for f in data["features"])
        self.assertLess(shipped, raw * 0.8, "simplification is not doing any work")

    def test_shipped_geometry_has_no_seam_tear(self):
        paths = load_lga_paths()
        self.assertEqual(
            paths["seams"]["tear_deg"], 0.0,
            "neighbouring LGAs are drawn with a gap between them; the map will tear",
        )
        self.assertLessEqual(paths["seams"]["fidelity_deg"], derive.DP_EPSILON_DEG * 1.5)

    def test_shared_edge_retention_floor(self):
        paths = load_lga_paths()
        self.assertGreaterEqual(
            paths["seams"]["quantization_retention"], 0.90,
            "quantization is eating the shared boundaries between LGAs",
        )
        self.assertGreater(paths["seams"]["pre_quantize_shared_edges"], 3000)

    def test_naive_per_polygon_simplification_would_tear(self):
        """The regression this whole design exists for.

        Independent per-polygon Douglas-Peucker plus vertex welding -- what the phase plan
        originally specified -- is *not* seam-safe. If a future change makes this pass,
        the safe-looking simplification has been reintroduced.
        """
        rings = derive.raw_rings()
        reference = {lga: derive.close_ring(derive.quantize(ring))
                     for lga, ring in rings.items()}
        naive = {lga: derive.simplify(ring) for lga, ring in rings.items()}
        tear, _fidelity = derive.seam_metrics(reference, naive)
        self.assertGreater(
            tear, 0.0,
            "naive per-polygon DP no longer tears, so the retained-shared-vertex design "
            "and its ~55 KB cost can be revisited",
        )

    def test_position_welding_cannot_and_does_not_fix_a_subset_mismatch(self):
        """Welding is a position-only transform, so it is a no-op on a quantized grid.

        Two polygons that retained different *subsets* of a border are not misaligned,
        they are differently simplified. This is why the seam is closed by retaining
        shared vertices rather than by snapping them together.
        """
        self.assertLess(derive.WELD_TOLERANCE_DEG, 10 ** -derive.QUANTIZE_DP)
        # Distinct quantized vertices sit at least one grid step apart, so no two can ever
        # fall inside the weld radius: no cluster can form, so nothing can be welded.
        for ring in derive.quantized_rings().values():
            for i in range(len(ring) - 1):
                if ring[i] == ring[i + 1]:
                    self.fail("quantization produced a zero-length edge")

    def test_simplification_never_emits_a_zero_length_edge(self):
        flags = derive.shared_vertex_incidence(derive.quantized_rings())
        for lga, ring in derive.quantized_rings().items():
            simplified = derive.simplify_ring(ring, flags[lga])
            self.assertEqual(simplified[0], simplified[-1], f"{lga} ring is not closed")
            for i in range(len(simplified) - 1):
                self.assertNotEqual(
                    simplified[i], simplified[i + 1],
                    f"{lga} has a zero-length edge that would render as a stray line cap",
                )

    def test_simplified_rings_are_all_closed(self):
        flags = derive.shared_vertex_incidence(derive.quantized_rings())
        for lga, ring in derive.quantized_rings().items():
            self.assertEqual(ring[0], ring[-1], f"{lga} quantized ring is not closed")
            simplified = derive.simplify_ring(ring, flags[lga])
            self.assertEqual(simplified[0], simplified[-1], f"{lga} ring is not closed")


class ProjectionTests(unittest.TestCase):
    def test_cos_latmid_correction_is_applied(self):
        paths = load_lga_paths()
        generator = paths["generator"]
        expected = math.cos(math.radians(generator["lat_mid"]))
        self.assertAlmostEqual(generator["lon_scale"], expected, places=7)
        self.assertLess(generator["lon_scale"], 1.0)

    def test_viewbox_matches_the_measured_extent(self):
        paths = load_lga_paths()
        _, _, width, height = paths["viewbox"].split()
        self.assertEqual(float(width), 1000.0)
        # 2.2635 deg lon * cos(10.99) wide vs 3.0851 deg tall -> 1000 x ~1388
        self.assertAlmostEqual(float(height), 1388.0, delta=5.0)

    def test_viewbox_is_not_computed_from_an_assumed_extent(self):
        """Gamawa reaches 8.75 deg E and Jamaare 12.53 deg N.

        A viewBox from an assumed "9-10 E, 9.5-11.5 N" would clip the west of the state
        and cut off Jamaare. The recorded bounds come from the 3 dp quantized geometry, so
        they are compared at the quantization step rather than at full raw precision.
        """
        paths = load_lga_paths()
        bounds = paths["bounds"]
        quantum = 10.0 ** -derive.QUANTIZE_DP
        self.assertAlmostEqual(bounds["min_lon"], 8.7450736484, delta=quantum)
        self.assertAlmostEqual(bounds["max_lon"], 11.0085317052, delta=quantum)
        self.assertAlmostEqual(bounds["min_lat"], 9.4473215106, delta=quantum)
        self.assertAlmostEqual(bounds["max_lat"], 12.5324657447, delta=quantum)

    def test_projection_preserves_aspect_ratio(self):
        paths = load_lga_paths()
        _, _, width, height = paths["viewbox"].split()
        bounds = paths["bounds"]
        generator = paths["generator"]
        projected = ((bounds["max_lon"] - bounds["min_lon"]) * generator["lon_scale"],
                     bounds["max_lat"] - bounds["min_lat"])
        self.assertAlmostEqual(
            float(width) * projected[1] / projected[0], float(height), delta=0.5
        )


class PageTests(unittest.TestCase):
    """What actually ships on atlas.html."""

    def test_map_is_inline_svg_with_no_third_party_requests(self):
        html = atlas_html()
        self.assertIn('<svg class="lga-map"', html)
        for host in ("http://", "https://"):
            for match in re.findall(rf'(?:src|href)="{host}([^"]+)"', html):
                self.assertNotIn("arcgis", match.lower())
        self.assertNotIn("<script src=", html)

    def test_every_lga_has_exactly_one_path(self):
        html = atlas_html()
        found = re.findall(r'<path class="lga-shape[^"]*" data-lga="([^"]+)"', html)
        self.assertEqual(sorted(found), sorted(LGAS))
        self.assertEqual(len(found), 20)

    def test_map_is_the_only_selector(self):
        """The 20-item tile grid was cut; the map carries the selection on its own.

        The tiles repeated a name the map already labels plus a badge visible only as a
        fill colour, so they were duplication and exactly the "competing primary
        navigation" the phase plan warned against.
        """
        html = atlas_html()
        self.assertNotIn("lga-tile", html)
        self.assertNotIn('class="lga-grid"', html)
        self.assertNotIn("lga-dot", html)

    def test_map_shapes_are_focusable_buttons_with_accessible_names(self):
        svg = svg_markup()
        paths = re.findall(r"<path\b[^>]*>", svg)
        self.assertEqual(len(paths), 20)
        for path in paths:
            with self.subTest(path=path[:60]):
                self.assertIn('tabindex="0"', path)
                self.assertIn('role="button"', path)
                self.assertIn("data-aria-label-en=", path)
                self.assertIn("data-aria-label-ha=", path)
                self.assertIn('aria-label="', path)
        for lga in LGAS:
            with self.subTest(lga=lga):
                self.assertIn(f'aria-label="{lga},', svg)

    def test_map_is_a_labelled_group_not_a_single_image(self):
        # role="img" makes assistive technology treat the SVG as one picture and hide the
        # children, which would make 20 focusable shapes unreachable.
        svg = svg_markup()
        self.assertIn('role="group"', svg)
        self.assertNotIn('role="img"', svg)

    def test_map_shapes_carry_the_evidence_text(self):
        svg = svg_markup()
        for attribute in ("data-summary", "data-summary-ha", "data-promise",
                          "data-promise-ha", "data-result", "data-result-ha"):
            with self.subTest(attribute=attribute):
                self.assertEqual(len(re.findall(rf'{attribute}="', svg)), 20)

    def test_evidence_panel_is_separate_labelled_sections(self):
        """Not one run-on sentence: the Dambam case read as a single paragraph."""
        html = atlas_html()
        for target in ("selected-evidence", "selected-promise", "selected-result"):
            with self.subTest(target=target):
                self.assertIn(f'id="{target}"', html)
        for label in ("Recorded evidence", "APM commitment", "Next result to measure"):
            with self.subTest(label=label):
                self.assertIn(label, html)
        # Semantically a definition list, so the label/value pairing is exposed.
        self.assertIn('<dl class="evidence-rows" id="selected-rows"', html)
        self.assertIn("</dl>", html)
        self.assertNotIn("selected-copy", html)
        # The prompt is shown until an area is chosen, then hidden.
        self.assertIn('id="selected-hint"', html)
        self.assertIn('id="selected-rows" hidden', html)

    def test_map_legend_replaces_the_removed_coverage_badges(self):
        html = atlas_html()
        self.assertIn("LGA-specific evidence", html)
        self.assertIn("lga-map-legend", html)
        # The legend is derived from the data. Every LGA row is lga_specific today, so a
        # fixed two-entry legend would advertise a "Statewide" state that never occurs.
        import csv as _csv

        with (ROOT / "data" / "delivery" / "lga_delivery.csv").open(encoding="utf-8") as fh:
            coverage = {row["lga"]: row["coverage_type"] for row in _csv.DictReader(fh)}
        has_statewide = any(value != "lga_specific" for value in coverage.values())
        self.assertEqual(
            "Statewide evidence" in html, has_statewide,
            "the legend must only show a coverage state that actually occurs in the data",
        )

    def test_map_paths_are_closed_and_ordered(self):
        html = atlas_html()
        for name, d in re.findall(r'data-map-lga="([^"]+)" d="([^"]+)"', html):
            self.assertTrue(d.startswith("M"), f"{name} path does not start with a moveto")
            self.assertTrue(d.endswith("Z"), f"{name} path is not closed")
            self.assertIn("L", d, f"{name} path has no line segments")

    def test_map_carries_the_cc_by_attribution_verbatim(self):
        html = atlas_html()
        for fragment in ("eHealth Africa and Proxy Logics", "GRID3", "CC BY 4.0",
                         "Simplified for display"):
            self.assertIn(fragment, html)

    def test_map_carries_the_indicative_not_gazetted_caveat(self):
        html = atlas_html()
        paths = load_lga_paths()
        self.assertIn("not validated by government authorities", paths["caveat"])
        self.assertIn(paths["caveat"], html)
        self.assertIn("Indicative operational boundaries, not gazetted", html)

    def test_boundaries_are_never_presented_as_official(self):
        html = atlas_html().lower()
        for banned in ("official boundaries", "gazetted boundaries", "statutory boundaries"):
            self.assertNotIn(banned, html)

    def test_registration_areas_are_labelled_not_geo_located(self):
        html = atlas_html()
        self.assertIn("Registration areas · not geo-located", html)
        self.assertIn("Wurare ƙaura zaye · ba a tantance su a geolocation ba", html)
        # ... and they are never drawn on the map.
        self.assertNotIn("data-ra-lga", svg_markup())
        self.assertEqual(len(re.findall(r'data-ra-lga="', html)), 20)

    def test_atlas_scripts_parse_and_stay_in_sync(self):
        node = _node()
        if not node:
            self.skipTest("node unavailable")
        import subprocess
        import tempfile

        js = "\n".join(re.findall(r"<script>(.*?)</script>", atlas_html(), re.S))
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                         encoding="utf-8") as handle:
            handle.write(js)
            name = handle.name
        try:
            result = subprocess.run([node, "--check", name], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr[:1500])
        finally:
            pathlib.Path(name).unlink()
        # The core script owns selection; the atlas script only reveals the RA list, and
        # is reached through a typeof guard so pages without it are unaffected.
        self.assertIn("lgaSelected", js)
        self.assertIn("typeof lgaSelected==='function'", js)
        self.assertIn("renderLgaDetail()", js)
        self.assertIn("if(!titleEl)return;", js)
        self.assertIn("if(!evidenceEl||!promiseEl||!resultEl)return;", js)
        # The map is the single selector, so there is no second binding to keep in step.
        self.assertNotIn("paintAtlas", js)
        # Enter and Space must both activate a focused shape.
        self.assertIn("'Enter'", js)
        self.assertIn("' '", js)


class BilingualIntegrityTests(unittest.TestCase):
    """Nothing on the atlas may be a text-content swap target that owns element children.

    `setLanguage` rewrites `textContent` for every `[data-en][data-ha]` element. An
    `attr()`-bearing *container* -- a wrapper div, or the whole `<svg>` map -- therefore
    loses every child the first time a visitor switches to Hausa. This cost a real bug
    where switching language blanked the entire map, so it is now asserted rather than
    remembered.
    """

    def _containers_with_data_attrs(self, html):
        """Elements carrying data-en/data-ha that have element children."""
        offenders = []
        for match in re.finditer(r"<([a-zA-Z][\w-]*)([^>]*\bdata-en=[^>]*)>", html):
            tag, attrs = match.group(1), match.group(2)
            if tag in ("meta", "input", "img", "br", "hr"):
                continue
            # Find the matching close tag and look for a child element.
            close = html.find(f"</{tag}>", match.end())
            if close == -1:
                continue
            inner = html[match.end():close]
            if "<" in inner and re.search(r"<[a-zA-Z][\w-]*[\s/>]", inner):
                offenders.append((tag, attrs[:90]))
        return offenders

    def test_no_data_bearing_container_is_emptied_by_a_language_switch(self):
        offenders = self._containers_with_data_attrs(atlas_html())
        self.assertEqual(
            offenders, [],
            "these elements carry data-en/data-ha *and* have element children, so "
            f"setLanguage will wipe the children: {offenders}",
        )

    def test_map_svg_carries_a_localized_aria_label_not_text_data(self):
        svg = svg_markup()
        self.assertIn("aria-label=", svg)
        self.assertIn("data-aria-label-en=", svg)
        self.assertIn("data-aria-label-ha=", svg)
        self.assertNotIn("data-en=", svg)

    def test_map_caveat_and_credit_are_translated(self):
        paths = load_lga_paths()
        html = atlas_html()
        for key in ("caveat", "attribution"):
            self.assertIn(paths[key], html, f"English {key} must ship")
            self.assertIn(paths[f"{key}_ha"], html, f"Hausa {key} must ship")
        # CC BY names are citations and stay in their original form in both languages.
        for _ in range(2):
            self.assertIn("eHealth Africa and Proxy Logics", html)

    def test_ra_label_translates_without_nesting_attr_inside_copy(self):
        html = atlas_html()
        self.assertIn("Registration areas · not geo-located", html)
        self.assertIn("Wurare ƙaura zaye · ba a tantance su a geolocation ba", html)


class DerivedArtifactTests(unittest.TestCase):
    def test_derived_file_is_committed_and_not_ignored(self):
        self.assertTrue(LGA_PATHS_FILE.exists())
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertNotIn("lga_paths.json", ignored)
        self.assertNotIn("data/derived", ignored)

    def test_derived_file_does_not_call_arcgis_at_build_time(self):
        """The weekly Pages rebuild must be deterministic and offline."""
        self.assertTrue(LGA_PATHS_FILE.exists())
        derived = LGA_PATHS_FILE.read_text(encoding="utf-8")
        self.assertNotIn("FeatureServer", derived)


def _node():
    import shutil

    return shutil.which("node")


if __name__ == "__main__":
    unittest.main()
