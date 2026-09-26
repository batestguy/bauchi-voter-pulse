# APM Bauchi Site Expansion Plan

**Status:** approved by owner 26 September 2026. **S0, S1 and S2 complete** (see §9). S3 onward not started.
**Supersedes:** the single-page layout described in `HANDOFF.md` §3 and `IMPLEMENTATION_PLAN.md` "Interactive Expansion Execution Plan"
**Scope:** header/logo repair, bilingual correctness, six-page site, Bauchi LGA map, opinion poll
**Naming:** phases are `S0`–`S7` to avoid collision with the existing `P0`–`P6` series in `IMPLEMENTATION_PLAN.md`

> Phase numbering here is independent of `IMPLEMENTATION_PLAN.md`. The `P4` full-screen
> achievement viewer remains deferred and is not in this plan's scope.

---

## 1. Owner decisions this plan implements

| # | Decision | Answer |
|---|---|---|
| 1 | "APM flag" | There is no flag. There is a wide logo lockup that currently renders as a white rectangle. Fix it, and add an **empty sponsor placeholder slot** (neutral tile + `[ Sponsor name ]`) to be filled later by the owner. |
| 2 | Language control | Must be visibly labelled as a language selector, and language choice must persist across page navigation. |
| 3 | Bilingual correctness | Audit and fix so English mode shows English and Hausa mode shows Hausa. |
| 4 | Poll type | Simple opinion poll, one tap to vote, **plus an optional free-text box for the specific thing they want**. |
| 5 | Poll results | Publish live. |
| 6 | Map | Real LGA boundaries + RA list in a side panel. No approximate ward dots. |
| 7 | Poll backend | Build it disabled until the owner configures the endpoint. |
| 8 | Subpages | Achievements, Poll / Speak to us, APM agenda, LGA atlas (as a map), Sources & methodology. |

---

## 2. Verified baseline

All figures below were measured against the working tree at `2fd12fa`, not estimated.

### 2.1 Renderer shape

| Fact | Value |
|---|---|
| `src/dashboard/render.py` | 1105 lines, imports stdlib only (`csv, datetime, hashlib, html, pathlib, shutil`) |
| Output | a single file, `docs/index.html`, **197,624 bytes** |
| Template | one f-string opened at line 825 and closed at 1098 |
| CSS | lines 833–1060 — 226 lines, 219 base rules, 5 `@media` blocks |
| Body | lines 1062–1084 |
| Script | lines 1085–1096, with two module-level JS blobs: `FEATURED_SCRIPT` (422–471), `REQUEST_SCRIPT` (474–576) |
| Functions | 25 `def`s: 12 pure helpers, 2 validators, 11 HTML emitters |
| Sections emitted | hero+topbar, stats, progress, atlas, continuity, agenda, featured, indicators, requests, sources, footer |
| `id` attributes | 29 |
| In-page anchors | 8 — **all break on a page split** |
| Tests | 40 `unittest` methods at this baseline, **87 after S1/S2**; 2 files read `docs/index.html` (`test_dashboard_contract.py:9,29`, `test_request_form.py:9`) |

`stats` is a real section with **no `id`**, and it sits between `</header>` and `<main>`, not inside `<main>`.

### 2.2 The logo defect (confirmed by screenshot of the live site)

- `assets/brand/apm-logo.png` is **1516×337** RGBA — a horizontal lockup: shield emblem + "ALLIED PEOPLES' MOVEMENT" wordmark + italic motto.
- `render.py:981` applies `.brand img{width:116px;height:auto;filter:brightness(0) invert(1)}`.
- `brightness(0) invert(1)` collapses all colour to solid white. At `width:116px` the rendered box is **116×26** — the wordmark and motto become an illegible white smudge. The screenshot confirms a plain white rectangle.
- The HTML wordmark `Allied Peoples' Movement` is **already** rendered beside it (`render.py:1064`), so the image contributes nothing.
- **Fix:** crop the shield emblem once, at 1:1, and render it at ~40px with **no invert filter**.
- Pillow 12.2.0 is present in the local interpreter but is **not** in `requirements.txt`. Crop once and commit the result so CI gains no dependency. Any new asset must be registered in `data/delivery/asset_register.csv` — see §7.

### 2.3 Bilingual audit — complete findings

**Encoding is healthy.** `docs/index.html` contains 337 occurrences of `ƙ ɓ ɗ ʙ` correctly encoded in UTF-8. There is no mojibake. (Question marks seen in console output are a terminal rendering artefact, not file corruption.)

Of **711** `data-en`/`data-ha` pairs, **227** are byte-identical. These partition exactly, with no residue:

| Bucket | Occurrences | Verdict |
|---|---:|---|
| Electoral RA proper nouns (`lga_wards.csv:ra_name_source`) | 212 | legitimately identical |
| Acronym `LGA` | 4 | legitimately identical |
| Party motto `Integrity · Sacrifice · Service` | 1 | legitimately identical by design |
| **Genuinely untranslated** | **10** | **3 distinct strings — BUG** |

**Bug 1 — 8 occurrences, one line.** `render.py:747` (the indicator card; the second `status_badge` site at 707 is the correct one) calls
`status_badge(row.get("status",""), row.get("status",""))` — passing `status` as *both*
arguments. `indicators.csv` has no `status_ha` column, so all 8 indicator cards render
`Outcome being measured` (×5) and `Progress delivered` (×3) in **both** slots. The correct
pattern already exists at `render.py:596`, which passes `achievements.csv:status_ha`.

**Bug 2 — 1 occurrence.** `render.py:690` sets `ra_placeholder = "Choose a registration area"`
and emits it via `attr()` at line 738. The correct Hausa already exists in the codebase at
`render.py:502`: `Zaɓi wurin ƙaura zaye.`

**Bug 3 — 3 records.** `data/delivery/achievements.csv` has Hausa text in the **English**
`description` column:

| CSV line | `achievement_id` | Note |
|---|---|---|
| 7 | `achievement-raamp-roads` | EN slot is Hausa; `description_ha` has typo `Gihada` → should be `Jihada` |
| 8 | `achievement-kirfi-road` | EN slot is Hausa; `description` == `description_ha` byte-for-byte |
| 9 | `achievement-gadau-road` | EN slot is Hausa (carries `ƙ` in `ƙananin`); produces a *differing* pair, so it escaped the identical-pair count |

**The larger debt — English-only rendering with no bilingual attribute at all.** These emit
no `data-en`/`data-ha`, so they stay English **even in Hausa mode** and would never be caught
by an identical-pair scan. This is the real answer to the owner's question about whether
Hausa mode is actually showing Hausa.

| Content | Count | Render site |
|---|---:|---|
| `source_register.title` (full English headlines) | 27 | `render.py:582` |
| `source_register.usage_note` | 27 | `render.py:584` |
| `achievements.verification_status` | 25 | `render.py:599` |
| `achievements.actor` | 25 | `render.py:599` |
| `indicators.measurement_note` | 8 | `render.py:619` |
| `indicators.current_value` | 8 | `render.py:611` |
| `indicators.current_unit` | 8 | `render.py:609` |
| `Baseline pending` | 8 | `render.py:607` |
| `Target not set` | 8 | `render.py:614` |
| indicator eyebrow uses the raw `sector` key, not `SECTOR_LABELS` | 8 | `render.py:747` (the indicator card; the second `status_badge` site at 707 is the correct one) |

**Hausa quality defects** (text present and correctly encoded, but wrong). The significant ones:

- `render.py:1065` — `Mikaɗin gwamna jihada Bauchi` for "Bauchi State Governor candidate". `Mikaɗin` means "shortage/wanted"; correct is **`Mikaƙin`**.
- `render.py:1065` — `Kadairin kowane` for "Official". Means "every voter"; semantically wrong for a campaign site.
- `render.py:643` — `Bincike na buƙatar al'umma` for "Public need". `Bincike` means "research", not need.
- `render.py:645` — `Acikaken sa na yanzu` for "Current achievement". Non-idiomatic.
- `render.py:1082` — `Bayanan gwamnati ko institucio` — truncated word.
- `render.py:1084` — Hausa footer leaves `private polling` in English.
- `render.py:1070`, `render.py:1072` — missing `ƙ` (`A bayanan` → `Ƙa bayanan`; `A agenda` → `ƙa agenda`).
- `render.py:69` — `SECTOR_HA["governance"]` = `Isar da g hanyayi da gwaji`; stray space.
- `render.py:1241` — LGA panel says `Bari:` while the rest of the page says `Sami na gaba:`.
- `render.py:419` — `...note na hotun yana nuna wanda.` — `wanda` misused, reads as nonsense.
- `needs.csv:8` — `accountability` left untranslated in the Hausa slot.
- `achievements.csv:3` — `Martaba` used for "Malnutrition"; `achievements.csv:6` — `Sectors` untranslated.
- `promises.csv:5` and `promises.csv:6` — duplicate rows whose EN and HA text describe different things.

**Structural fragility to harden:**

- `attr()` (`render.py:103-104`) emits `data-ha=""` for an empty value — there is **no server-side fallback**. Only the client-side `el.dataset[lang] || el.dataset.en` at `render.py:1091` prevents a blank UI.
- `status_badge(status, ha="")` (`render.py:134`) defaults `ha` to empty, so any future call site that forgets the argument silently ships English-in-both-slots. **8 of the 10 bugs came from this one default.**
- Inconsistent `SECTOR_HA` fallbacks: `render.py:401` falls back to the raw snake_case key, `render.py:627` falls back to the English label.
- `Promise to complete` and `Next priority` are mapped by `status_class()` (`render.py:120-121`) but have **no Hausa anywhere in the repo**.
- `class="need-node"` is emitted at `render.py:643` with **no CSS rule** — styled only by `.path-node:nth-child(odd)`.

**Clean, no action needed:** all 14 bilingual CSV column pairs have a populated `_ha` counterpart for every populated English cell — zero gaps. `SECTOR_LABELS`/`SECTOR_HA` are 8/8 complete. `REQUEST_CATEGORIES` is 9/9 complete. `FEATURED_SCOPE_LABELS` is 3/3 complete.

### 2.4 Bauchi boundary data — measured, not assumed

**Source:** GRID3 / eHealth Africa, ArcGIS item `2bb616a49ee84f409427cc2143787113`, layer 0 `grid3_nga_boundary_vacclgas`.
Query: `.../NGA_LGA_Boundaries_2/FeatureServer/0/query?where=statecode='BA'&outFields=*&returnGeometry=true&outSR=4326&f=geojson`

**Licence: CC BY 4.0.** Commercial use permitted. Attribution required — the sole obligation. **No ShareAlike**, so the simplified derivative may be published on our own terms. There is no political-use restriction.
⚠️ The **sibling GRID3 Wards layers are CC BY-SA 4.0** and would force BY-SA on the whole page. Do not pull the ward layer in.

**Required attribution text:** `LGA boundaries: eHealth Africa and Proxy Logics (2020), Nigeria Operational Local Government Area (LGA) Boundaries, GRID3. Used under CC BY 4.0. Simplified for display.` — the "simplified" clause is the CC BY change-indication requirement, and we *are* modifying it.

**Measured geometry:**

| Property | Value |
|---|---|
| Features | **20** (exactly the 20 Bauchi LGAs) |
| Geometry type | `Polygon` only — no MultiPolygon, **1 ring each, 0 holes** |
| Self-intersections | **0** across all 20 rings |
| Rings explicitly closed | 20/20 |
| Winding order | all 20 clockwise (consistent) |
| Total vertices | **10,632** |
| Largest ring | 1,223 (`Itas/Gadau`) |
| Raw response | 388,559 bytes |
| Bounding box | lon **8.7450736484 – 11.0085317052**, lat **9.4473215106 – 12.5324657447** |

⚠️ The real extent is 8.75–11.01 °E and 9.45–12.53 °N. Any viewBox computed from an assumed
"9–10 °E, 9.5–11.5 °N" would clip Gamawa/Katagum in the west and cut off Jama'Are, which
reaches 12.53 °N.

**Projection:** data is already WGS84, so no reprojection library is needed. Equirectangular is
adequate. At latMid 10.99°, 1° lon = 109.278 km vs 1° lat = 111.320 km — a **1.87%** east-west
error if uncorrected. Apply the `cos(latMid)` factor; it costs one function call.
Target: `viewBox="0 0 1000 1388.5"`.

**Name reconciliation — only 2 of 20 differ from `render.LGAS`:**

| Dataset `lganame` | `lgacode` | Repo canonical |
|---|---:|---|
| `Itas/Gadau` | 5010 | `Itas-Gadau` |
| `Jama'Are` | 5011 | `Jamaare` |

All other 18 are byte-identical. The Damban/Krifi/Miau/Alakali/Dagaurda variants flagged in the
earlier research handoff are **corpus text variants, not boundary-data variants** — they do not
appear in this dataset. `lga_delivery.csv` and `lga_wards.csv` `lga` columns are byte-identical
to `LGAS` with no variants at all.

**Join on `lgacode` (5001–5020), never on names.** This makes the two mismatches structurally
impossible to get wrong.

⚠️ `achievements.csv:lga` contains two pseudo-values that must never be joined:
`Statewide` (8 rows) and `Bauchi North LGAs` (1 row).

**Seam safety — the key technical constraint.** 36 LGA pairs share boundary vertices: **3,538
shared edge instances, all matching exactly at 6 decimal places, all traversed in opposite
direction.** That is a correct planar topology — no gaps, no overlaps.

Because neighbours share *identical* vertices, a **position-only transform is provably
seam-safe** — both polygons round the shared vertex to the same number.

| Quantization | Pairs still sharing edges | Shared edges retained |
|---|---|---|
| 5 dp | 36/36 | 3,538 (100%) |
| 4 dp | 36/36 | 3,531 (99.8%) |
| 3 dp | 36/36 | 3,353 (94.8%) |
| 2 dp | 36/36 | 1,562 (44.2%) ← **tears** |

⚠️ **Never quantize below 3 dp.** At 2 dp, 56% of shared boundary edges collapse and the map
visibly tears between LGAs.

⚠️ **Douglas-Peucker run independently per polygon is *not* provably seam-safe** — its split
decisions depend on each polygon's own neighbouring vertices, so two polygons sharing a border
can retain different subsets of it. Mitigation: quantize to 4 dp first (the seam-safe floor),
then DP, then snap any surviving vertex within 4 dp of a neighbour's vertex back onto it.

**Quantization alone is not a simplifier.** Rounding to 4 dp removes only 22 of 10,632
vertices (0.2%). Real vertex reduction is required.

| Pipeline | Vertices | `d` bytes | Gzipped | Ground tolerance |
|---|---:|---:|---:|---|
| raw | 10,632 | 126,493 | 43,241 | — |
| quantize 4dp only | 10,610 | 126,231 | 43,104 | — |
| quantize 4dp + DP ε=0.001 | 4,350 | 51,802 | **18,224** | ~111 m |
| **quantize 3dp + DP ε=0.002** | **3,070** | **36,585** | **12,510** | ~222 m ← **recommended** |
| quantize 3dp + DP ε=0.005 | 1,668 | 19,887 | 7,105 | ~557 m |

**Pure-stdlib implementation is feasible.** Required: affine projection, `round(x, d)`,
consecutive-dedup, ring-close assertion, path serialisation. No shapely/geopandas/pyproj
required, and none are installed. DP must use an **explicit stack, not recursion** — the
1,223-point ring would exceed Python's 1000-frame default. `numpy` is present but is a
transitive dependency of pandas and is **not** in `requirements.txt`; do not rely on it.

**Required caveat on the page:** these are *operational* boundaries descended from eHealth
Africa's polio-vaccination microplanning data, simplified for display. GRID3 states they are
not validated by government authorities and have no official gazetted status. Present as
**indicative**, never as official boundaries.

### 2.5 Traps in the existing code

🔴 **`render.py:1090` (now `render.py:1241`) was the only un-guarded DOM write in the entire script.**
`document.getElementById('selected-lga').textContent` and `('selected-copy').textContent` are
not null-checked. It is safe today only by transitive reasoning (`selectedLga` stays `''` when
no `[data-lga]` button exists). On a page split — or if `selectedLga` is ever restored from
`localStorage` or a URL hash — this throws a `TypeError` **inside `setLanguage`, killing the
entire language toggle**. Fix first.

🔴 **`rebuild-pages.yml:33` runs `git add docs/index.html docs/assets/`.** Add pages without
changing this and the weekly cron will render them, then silently never commit them, forever.

🔴 **`HANDOFF.md:934-954` is the staging allowlist** and lists only `docs/index.html`. A
maintainer following that handoff verbatim would render, diff and commit **nothing** once five
new pages exist.

⚠️ **`rebuild-pages.yml:19-27` asset check is column-position coupled** — `awk -F, 'NR > 1 && $6 != "campaign approved"'`. Any new asset row must have `usage_status` in **exactly column 6** or CI fails closed.

⚠️ **`.source-link` is defined twice** — `render.py:926` and again at `render.py:1046` (which adds `justify-self:end`). Splitting CSS per page silently drops the override from any page that keeps 926.

⚠️ **The 5 `@media` rules use duplicated breakpoints** — 1056 and 1058 are both `max-width:1050px`; 1057 and 1059 are both `max-width:760px`. They are separate blocks in a load-bearing order: components (1056/1057) precede shell (1058/1059). Merging them naively changes the outcome, e.g. `.request-aside` gets `display:grid`+3 columns at 1056 and 1 column at 1057.

⚠️ **`render.py:1055` contains a global `*` rule** inside `prefers-reduced-motion` — it must ship on every page.

⚠️ **`test_request_form.py:21`** asserts `html.count('data-request-ra-lga=') == 212`, but there are **213 raw occurrences** — 212 `<option>`s plus one inside `REQUEST_SCRIPT:521`. It only passes because the form markup and its JS ship in the same file. Splitting scripts out breaks it.

⚠️ **The arrow-card count is data-dependent, not constant.** The loop at `render.py:802-807` iterates 8 sectors but skips `livelihoods`/`security`/`agriculture` when empty, yielding **6** cards today. A card-count assertion must not hardcode a number.

⚠️ **`featured_pending_section()` (`render.py:375-376`)** emits the *same* `id="featured"` with `data-featured-state="pending"`. This variant must also exist on `achievements.html`, or the branch logic breaks.

**Dead code, safe to remove:** CSS `.light-rule` (884), `.intro-grid` (885, 1059), `.intro-copy` (886, 1059), `.note-box` (887), `.hero-note` (865-866); the `portrait_image` variable at `render.py:812` is assigned and never used; `Current value pending` (608), `date unknown` (583), `Untitled source` (582), `No public achievement record yet.` (601) and `Registration areas are not loaded` (693) are unreachable branches.

### 2.6 Working-tree state that must be preserved

| Path | State | Rule |
|---|---|---|
| `2fd12fa` | committed, **ahead of `origin/main` by 1** | push only on explicit owner instruction |
| `src/aggregation/aggregate.py` | modified, uncommitted | **never stage or reset** — legacy track |
| `.evals/2026-W39.md`, `.evals/2026-W39_sample100_filled.csv` | untracked | local-only, not approved for release staging |
| `data/human_review/filled/` | untracked | local-only |
| `.playwright-mcp/` | untracked | local browser artifact, not part of the release |

The legacy P1 evaluation work is a **separate track** and is blocked on a missing
`data/human_review/filled/queue_en_part1.csv`. Nothing in this plan touches it.

---

## 3. Target architecture

Six flat files in `docs/`. **Flat, not nested**, so the existing `assets/brand/...` relative
paths keep working unchanged on every page.

| File | Sections |
|---|---|
| `index.html` | hero, stats, 4-step story + sector filter + arrow cards, continuity, navigation cards to the five subpages |
| `achievements.html` | featured carousel (or the pending variant), full achievement records, indicator ledger |
| `atlas.html` | Bauchi SVG map, 20-LGA selector, per-LGA evidence panel, RA list, attribution |
| `poll.html` | opinion poll + optional free-text box, then the existing request form |
| `agenda.html` | the 8 campaign promises |
| `sources.html` | 33-source register, grading legend, methodology, not-private-polling disclosure |

Every page carries: the shared header, the labelled language control, the shared footer, the
sponsor placeholder slot, and `aria-current="page"` on its own nav link.

**Refactor approach:** Jinja2 templates with a shared layout. Jinja2 is **already** in
`requirements.txt` and currently unused, so this adds no dependency. `HANDOFF.md:298-300`
claims the page is generated with "Python standard-library CSV/HTML generation" — that line
becomes false and must be updated.

**Shared vs per-page CSS.** Only 8 selector groups are genuinely shared and belong in the base
block: `.shell`, `.section`, `.section-head` (+`h2/h3`, `p`), `.eyebrow`, `.source-link`,
`.status*`, `.btn*`, `.reveal`. The topbar and footer rule sets are shell, not page. Everything
else is single-section and moves with its page.

---

## 4. Phase plan

| Phase | Owner | Area | Deliverable | Gate |
|---|---|---|---|---|
| **S0** Baseline commit | Main maintainer | working tree | Plan committed; legacy files left untouched | COMPLETE — see §9 |
| **S1** Bilingual correctness | Executor + reviewer | `render.py`, `data/delivery/*.csv` | 10 untranslated strings fixed, 3 bad records fixed, silent English-only gaps wrapped, `attr()` hardened | COMPLETE — see §9 |
| **S2** Header, emblem, sponsor slot | Executor + reviewer | `render.py`, `asset_register.csv`, `promises.csv` | Legible emblem, labelled language control with `localStorage` persistence, sponsor slot, de-duplicated promises | COMPLETE — see §9 |
| **S3** Multi-page shell | Executor + reviewer | `src/dashboard/templates/`, `render.py` | 6 pages, mobile nav, solid subpage header, `aria-current`, null-guarded JS | All 6 render; nav resolves; no console errors |
| **S4** Bauchi map | Executor + reviewer | `src/ingestion/lga_boundaries.py`, `src/dashboard/map_svg.py` | 20 LGA paths inline, seam-safe, panel + RA list, attribution, indicative caveat | 20 paths match `LGAS`; seams verified visually; no runtime network |
| **S5** Poll | Executor + reviewer | `src/poll/`, `poll.html` | Q1 sector choice + Q2 optional text, live results with disclosure, disabled until endpoint set | Disabled-state tests prove nothing is sent |
| **S6** CI and release gate | Main maintainer + reviewer | workflows, tests | 6 files committed by the cron; asset gate intact; privacy assertions across all pages | Cron dry-run commits all pages |
| **S7** Documentation | Main maintainer | `HANDOFF.md`, `README.md`, `AGENTS.md`, `IMPLEMENTATION_PLAN.md` | All stale claims corrected | Independent review |

Each phase leaves the site deployable. No phase should be left half-merged.

### S0 — Baseline

1. Confirm `2fd12fa` is the intended checkpoint.
2. **Do not** push. The owner has not authorised it.
3. Leave `src/aggregation/aggregate.py` and the four untracked legacy paths exactly as they are.

### S1 — Bilingual correctness

Ordered so each step is independently verifiable:

1. `render.py:747` (the indicator card; the second `status_badge` site at 707 is the correct one) — pass `row.get("status_ha","")` instead of `row.get("status","")`. Fixes 8 of 10.
2. `data/delivery/indicators.csv` — add a `status_ha` column; populate 8 rows. Add `"status_ha"` to the required-column set at `render.py:209-213` and the `required_fields` list at `render.py:183` so it cannot regress.
3. `render.py:690` / `738` — supply the Hausa `Zaɓi wurin ƙaura zaye.` already present at `render.py:502`. Also fix the dead branch at 693.
4. `data/delivery/achievements.csv` lines 7, 8, 9 — write real English into `description`; fix `Gihada` → `Jihada`. Add a `validate_data()` guard rejecting `ƙ ɓ ɗ ʙ` in any non-`_ha` column of `achievements.csv`, so this cannot recur.
5. `render.py:103-104` — add `ha = ha or en` inside `attr()` so an omission self-heals instead of serialising `data-ha=""`.
6. `render.py:134` — make `ha` a required parameter, or default it from a single `STATUS_HA` dict, so the defect class is structurally impossible.
7. `render.py:401` and `render.py:627` — align both `SECTOR_HA` fallbacks to `SECTOR_HA.get(sector, sector_en)`.
8. Add Hausa for `Promise to complete` and `Next priority`, which currently have none.
9. Wrap the silent English-only gaps from §2.3: `source_register` `title`/`usage_note`, `achievements` `verification_status`, `indicators` `measurement_note`/`current_value`/`current_unit`, and the `Baseline pending` / `Target not set` literals. This requires new `_ha` columns in `source_register.csv` and `indicators.csv` — **owner or native-speaker review required for the new Hausa copy.**
10. Route the indicator eyebrow through `SECTOR_LABELS`/`SECTOR_HA` instead of the raw key.
11. Apply the Hausa quality fixes in §2.3 and de-duplicate `promises.csv:5`/`:6`.
12. Fix the `Bari:` vs `Sami na gaba:` inconsistency at `render.py:1241`.

**Hausa authorship caveat:** items 2, 3, 8, 9 and 11 require new Hausa copy. The existing
`Zaɓi wurin ƙaura zaye.` is reusable as-is, and `achievements.csv:status_ha` already supplies
vocabulary for the status terms. Anything newly authored should be labelled as AI-drafted and
spot-checked by a native speaker, consistent with the existing disclosure on
`.evals/2026-W39.md`.

### S3 — Multi-page shell

1. Extract the f-string into Jinja2 templates under `src/dashboard/templates/` with a shared layout, a `NAV` list, and per-page `title` / `meta description` (currently one hardcoded pair at `render.py:830-832`).
2. Move each section into its page per §3. Reuse the existing fragment builders rather than duplicating markup.
3. Split the CSS: base block for the 8 shared groups plus the topbar/footer/shell rules; per-page blocks for the rest. **Preserve the duplicate-breakpoint cascade order** and keep the global `*` reduced-motion rule on every page. Resolve the double-defined `.source-link` into one rule.
4. Rewrite the nav as page links with `aria-current="page"`. Re-target all 8 anchors per the mapping in §5.
5. Add a mobile navigation menu. `.nav` is `display:none` below 1050px (`render.py:1058`); without this, phones get **no navigation at all** once there are subpages.
6. Add a solid-header variant. `.topbar` is `position:absolute` with white text over the dark hero (`render.py:841`); subpages without a hero need an opaque background.
7. Make `FEATURED_SCRIPT` conditional on `achievements.html` and `REQUEST_SCRIPT` conditional on `poll.html`. Block C/F/G (`render.py:1089-1090, 1093, 1094`) belong to `atlas.html`. Blocks A/D/E — `currentLanguage`, `setLanguage`, the lang binding — must ship on **every** page, in that order, or the toggle throws.
8. Keep `REQUEST_ENDPOINT = ""` (`render.py:21`). `test_request_form.py:29-30` asserts the disabled state.
9. Delete the dead code listed in §2.5.

### S4 — Bauchi map

1. `src/ingestion/lga_boundaries.py` — fetch the GeoJSON **once**, cache it under `data/delivery/source_snapshots/`, and record provenance in `source_register.csv` (grade B, licence CC BY 4.0, retrieval date, the "simplified for display" change note).
2. Derive `data/derived/lga_paths.json` (lgacode → simplified `d` string + bbox) and **commit it**, so `render.py` stays pure/offline and the weekly Pages rebuild never calls ArcGIS. This also makes the build deterministic and auditable.
3. `src/dashboard/map_svg.py` — pure stdlib: quantize to **4 dp** → iterative-stack Douglas-Peucker at ε=0.001 → snap neighbours → project with the `cos(latMid)` correction → serialise to `viewBox="0 0 1000 1388.5"`. Emit at 1 dp. **Never quantize below 3 dp.**
4. Inline the SVG into `atlas.html` — 20 `<path data-lga>` elements, keyboard focusable, click and Enter/Space activating the side panel. **Zero runtime third-party requests.**
5. Side panel: LGA name, its `lga_delivery.csv` evidence row, its RA count from `lga_wards.csv`, and the RA name list — labelled **"not geo-located"**, since `lga_wards.csv` has no coordinates and none will be invented.
6. Show the required attribution text and the indicative-boundaries caveat.
7. Add the existing 20-LGA CSS-tile grid alongside the map, or fold it into the map interaction — owner's preference at implementation time. Do not ship both as competing primary navigation.

### S5 — Poll

1. New `src/poll/` package mirroring the proven structure of `src/requests/`: `poll_schema.json`, `validation.py`, `aggregate.py`, tests. Reuse the validation patterns rather than reinventing them.
2. **Q1, required, single choice:** "Which sector should APM prioritise first?" — options are the **existing 9 `REQUEST_CATEGORIES`** at `render.py:22-32`, so poll results are directly comparable with the request queue.
3. **Q2, optional, ≤300 chars:** the specific thing they want. The UI must label it a comment attached to the vote, and it must be **excluded from the tally**. It is not a second poll question.
4. Results: live horizontal bars, `N` shown prominently, plus the disclosure that respondents are self-selected visitors and not a representative sample.
5. Owner chose immediate publication, so counts publish live. Percentages still sit behind a configurable floor (default 10) so a single vote cannot display as "100%". Owner can set it to 0.
6. On a static host "live" means: read from the endpoint when configured, else fall back to a committed `data/delivery/poll_snapshot.json` that the weekly cron regenerates.
7. `POLL_ENDPOINT = ""` → submit disabled, results read "not yet connected", mirroring `REQUEST_ENDPOINT` and `data-request-configured`.
8. Minimum PII: **no name, phone or email** on the poll (unlike the request form). Honeypot, consent checkbox, no voter ID, one submission per browser via `localStorage` — weak, and labelled as such.
9. Never seed, example or placeholder results. An empty result set must render as empty, not as zeros that imply data.

### S6 — CI and release gate

1. `rebuild-pages.yml:33` — stage all six files plus assets.
2. Keep the asset-authorization gate at lines 19-27 intact, including the column-6 coupling.
3. Add a render check that fails if any expected page is missing.
4. Add a privacy assertion across **all six** pages, not just one — `HANDOFF.md:752-753` makes this an acceptance criterion and it is currently implicit.
5. Add a check that no page ships a section it should not (e.g. a carousel on `poll.html`).

### S7 — Documentation

Stale-claim counts measured during the audit: **21** in `HANDOFF.md`, **6** in `README.md`,
**2** in `AGENTS.md`, **18** in `IMPLEMENTATION_PLAN.md`. All must be corrected.

Highest-risk items:

| File | Line | Problem |
|---|---|---|
| `rebuild-pages.yml` | 33 | stages only `docs/index.html` — 🔴 breaks the whole release |
| `HANDOFF.md` | 934-954 | staging allowlist omits the five new pages — 🔴 commits nothing |
| `HANDOFF.md` | 115 | the `docs/index.html` file table becomes six rows |
| `HANDOFF.md` | 129-140 | "Page features" — every bullet now belongs to a named page |
| `HANDOFF.md` | 298-300 | claims stdlib-only generation; false once Jinja2 renders the pages |
| `HANDOFF.md` | 378-380 | "Commits only `docs/index.html`" — directly contradicted |
| `HANDOFF.md` | 6 | "Current release `b94d4b0`" — already stale, HEAD is `2fd12fa` |
| `AGENTS.md` | 11, 32 | "renders static HTML to `docs/index.html`" |
| `README.md` | 13, 30, 32-34 | product inventory and the local-preview URL list |

`HANDOFF.md:617-618` and `IMPLEMENTATION_PLAN.md:23` are historical decision records — annotate
as superseded rather than rewriting them.

---

## 5. Anchor re-targeting

All 8 current in-page anchors must be rewritten as cross-page links.

| Anchor | Referenced from | Becomes |
|---|---|---|
| `#top` | `.brand` (`render.py:1064`) | `index.html#top` |
| `#progress` | nav 1064, `.btn-primary` 1065 | `index.html#progress` |
| `#atlas` | nav 1064, `.btn-secondary` 1065 | `atlas.html` |
| `#continuity` | nav 1064 | `index.html#continuity` |
| `#agenda` | nav 1064 | `agenda.html` |
| `#indicators` | nav 1064 | `achievements.html#indicators` |
| `#requests` | nav 1064 | `poll.html` |
| `#sources` | nav 1064 | `sources.html` |

`#featured` is not in the nav today; it is reachable only by scroll. The `.source-legend` has
no `id` and is not linkable.

---

## 6. Test plan

Existing: 87 `unittest` methods after S1/S2 (40 at baseline), no pytest/lint/typecheck. Keep it that way for now.
The two guards added in S1/S2 are `tests/test_bilingual.py` and `tests/test_header_brand.py`; the latter
includes a `node --check` parse of the inline script, which is the only thing that catches a
duplicate `const` declaration.

**Re-target the two HTML-reading test files:**

| Test | Assertions | New target |
|---|---:|---|
| `test_dashboard_contract.test_language_toggle_preserves_selected_lga` | 4 | `docs/atlas.html` |
| `test_dashboard_contract.test_featured_section_is_rendered_from_current_data` | 9 | `docs/achievements.html` |
| `test_dashboard_contract.test_featured_lga_scope_matches_achievement_geography` | 0 (CSV only) | unaffected |
| `test_request_form.*` (4 tests) | 24 | `docs/poll.html` |

Both files are **CWD-relative** — tests must run from the repo root.

**New tests:**

1. All six pages exist and are non-empty; every page has the header, nav, footer, language control and sponsor slot.
2. Every nav `href` resolves to a real file and a real `id`.
3. Exactly one page carries `aria-current="page"`, and it matches the file.
4. Shared CSS groups (`.shell`, `.section-head`, `.eyebrow`, `.source-link`, `.status`, `.btn`) are present on every page that uses them.
5. Every relative `assets/...` and `docs/assets/...` path resolves to a file on disk.
6. Bilingual: a denylist of UI strings fails if any ships with `data-ha == data-en`. **Not** a blanket equality check — 217 legitimate pairs exist.
7. Bilingual: every page's language control toggles content, and the choice survives navigation via `localStorage`.
8. No `ƙ ɓ ɗ ʙ` in any non-`_ha` column of `data/delivery/*.csv`.
9. The map SVG contains exactly 20 `data-lga` paths whose names equal `set(render.LGAS)`, with no unmatched path and no missing LGA.
10. Map simplification output is deterministic — same input, byte-identical output.
11. Map seams: quantizing to 3 dp must retain ≥90% of shared edges (guards against the 2 dp tear regression).
12. Map contains no runtime external image or script reference.
13. Poll: validation rules, honeypot, consent, tally arithmetic, the suppression floor, and that an empty result set renders as empty.
14. Poll: a disabled-endpoint build contains no code path that can send a request.
15. Privacy: no personal data, request ID, address or free-text description in **any** generated page.
16. No page ships a section it should not — e.g. `id="featured"` appears exactly once across all six, and `id="requests"` exactly once.
17. Asset gate: every `asset_register.csv` row is `campaign approved` with `usage_status` in column 6 and a matching sha256.

Assert **counts from the data, not constants** — e.g. derive the arrow-card count the way
`render.py:802-807` does, since it is 6 today but data-dependent.

---

## 7. Risks and gates

| # | Risk | Mitigation |
|---|---|---|
| 1 | 🔴 Cron renders the new pages but never commits them | Fix `rebuild-pages.yml:33` in the same phase as S3 |
| 2 | 🔴 Language toggle throws on a page lacking the LGA detail panel | Null-guard `render.py:1241` in S2, before S3 makes it reachable |
| 3 | 🔴 Phones lose all navigation | Mobile menu is a required S3 deliverable |
| 4 | 🔴 CI fails closed on an unapproved asset | Owner must approve the emblem; `usage_status` must sit in column 6 |
| 5 | 🟠 Map tears between LGAs | Never quantize below 3 dp; test asserts ≥90% shared-edge retention |
| 6 | 🟠 Boundaries presented as official | Ship the "operational / simplified / indicative" caveat and the CC BY attribution |
| 7 | 🟠 Accidentally inheriting ShareAlike | Use only the LGA Boundaries layer; never the BY-SA Wards layers |
| 8 | 🟠 Poll read as representative polling | Prominent N, self-selected disclosure, and the existing not-private-polling statement |
| 9 | 🟠 Low-N poll percentages | Configurable floor, default 10 |
| 10 | 🟠 New Hausa copy is AI-drafted and unreviewed | Label as such; native-speaker spot-check, matching the `.evals/2026-W39.md` disclosure |
| 11 | 🟡 CSS cascade regression from merging the duplicate breakpoints | Preserve source order; verify `.request-aside` and `.featured-slide` at 760/1050px |
| 12 | 🟡 `test_request_form.py:21` breaks if scripts move to a shared file | Re-target the assertion when S3 splits scripts |
| 13 | 🟡 Jinja2 whitespace control breaks the exact-string assertion at `test_request_form.py:31` | Verify `data-request-submit disabled` survives templating |

### Gates only the owner can pass

1. **Asset approval** for `apm-emblem.png` — `rebuild-pages.yml` hard-fails without it.
2. **Endpoint URLs** for the poll and the request form. Both ship disabled until then.
3. **Push authorisation** for `2fd12fa` and every subsequent phase.
4. **New Hausa copy review** for the strings S1 adds.
5. **Emblem crop approval** — if a square emblem-only asset exists, supply it instead of cropping.

---

## 8. Definition of done

- Six pages render from `python src/dashboard/render.py`, all relative-path, no runtime network calls.
- Every page is reachable at 375px and 1440px with a working mobile nav and zero console errors.
- Language control is labelled, works on all six pages, and persists across navigation.
- The logo is legible; the sponsor slot is visibly a placeholder.
- Hausa mode shows Hausa everywhere, including the previously English-only content.
- The map shows 20 correctly named, seam-free LGA boundaries with the RA list and full attribution.
- The poll is present, honest, and provably inert until an endpoint is configured.
- The weekly cron commits all six pages.
- All 40 existing tests pass, plus the new tests in §6.
- `HANDOFF.md`, `README.md`, `AGENTS.md` and `IMPLEMENTATION_PLAN.md` are accurate.
- An independent review has run before anything is staged or pushed.

---

## 9. Progress log

### S0 — Baseline (complete, commit `9cd101b`)

Plan document committed. `2fd12fa` remains unpushed. The legacy working-tree files
(`src/aggregation/aggregate.py`, `.evals/`, `data/human_review/filled/`) were left untouched
and untracked, as required.

### S1 — Bilingual correctness (complete)

All twelve steps landed. Result: **224 identical `data-en`/`data-ha` pairs remain and every one
is legitimate** (electoral RA proper nouns, LGA names, the `LGA` acronym, the party motto, and
numeric values that are genuinely identical in both languages). Zero unexplained.

Fixed:

- `render.py` indicator card: `status` was passed to `status_badge` as both arguments. Now
  reads `status_ha`.
- `indicators.csv`: added `lga_ha`, `current_value_ha`, `current_unit_ha`, `status_ha`,
  `measurement_note_ha` across all 8 rows.
- `source_register.csv`: added `usage_note_ha` across all 27 rows.
- `achievements.csv`: added `verification_status_ha` across all 25 rows; wrote real English
  into the three `description` cells that held Hausa; fixed `Gihada` → `Jihada`.
- `render.py` RA placeholder now uses the Hausa already present at the old line 502.
- 15 Hausa quality defects corrected, including `Mikaɗin` → `Mikaƙin`, `Bincike` (research) used
  for "need", `Kadairin kowane` ("every voter") used for "official", and the English
  `private polling` left in the Hausa footer.
- `promises.csv` Hausa realigned to the English, which is the citation of record.

Hardening, so these cannot regress:

- `attr()` now falls back `ha or en` instead of serialising `data-ha=""`.
- `status_badge()` defaults `ha` from `STATUS_HA`; the `ha=""` default that caused 8 of the 10
  bugs is gone.
- `STATUS_CLASSES` / `STATUS_HA` / `INDICATOR_STATUSES` are now one controlled vocabulary, so a
  status cannot ship without a Hausa label or drift out of the validator.
- `validate_no_hausain_english_columns()` rejects Hausa in English columns, using **both** an
  orthography test and an absolute function-word-hit test. The orthography test alone caught
  only 1 of 3 offenders; two of the three sentences contain no Hausa-specific characters.
  Swept across every delivery CSV with zero false positives.
- The `🔴` un-guarded `getElementById` write in the LGA detail panel is now null-guarded, so a
  future page split cannot throw inside `setLanguage` and kill the language toggle.
- `source_register.title` is deliberately **not** wrapped for translation. A source title is a
  citation and belongs in its own language.

Tests: `tests/test_bilingual.py`, 17 methods. Suite is **57 passing**, up from 40.

⚠️ **Outstanding, needs a decision:**

1. The 52 new Hausa strings in this phase are **AI-drafted and not native-speaker reviewed**,
   the same caveat already recorded on `.evals/2026-W39.md`. They cover integrity caveats a
   Hausa-reading visitor now sees, so they should be spot-checked before the next push.
2. ~~promises duplication~~ **RESOLVED in S2** - see below.

### S2 - Header, emblem, sponsor slot, language control (complete, commit `533a210`)

#### Emblem

The white rectangle was diagnosed by measurement, not guesswork. `apm-logo.png` is a
1516x337 lockup with an **opaque white background** (RGB 254,254,254, alpha 255), so the old
`filter:brightness(0) invert(1)` turned the background white as well as the artwork. The two
merged into one solid block, rendered at 116x26.

- Measured ink bounds of the emblem: x 31-304, y 5-318 (274x314). There is **no blank row**
  between the "A P M" letters and the shield, so the crop keeps the whole connected mark
  rather than attempting a cut that would decapitate the letters.
- Background removal is a **border flood fill**, not a global white threshold. A threshold
  would also punch out the shield's own white "ALLIED / PEOPLES' / MOVEMENT" lettering,
  which is enclosed by ink and must survive. 38.9% of pixels are now transparent.
- `apm-emblem.png` added to `asset_register.csv` and `ASSET_FILES`; hash-registered. The CI
  asset gate, which validates `usage_status` by **column position**, passes.
- Header and favicon both use the emblem; the invert filter is gone. The wordmark
  "Allied Peoples' Movement" stays as HTML text beside it.
- The original `apm-logo.png` is retained.

#### Sponsor slot

Footer only, three labelled fields per owner direction: photo, name, and a **prominent
contribution line**. Bilingual, dashed border, and deliberately unfilled. A test asserts the
slot carries no amount, no four-digit figure, and no invented name or organisation.

#### Language control

- Now labelled with a globe glyph plus `Language` / `Harshe`, so it is self-describing
  rather than a bare `EN | HA` pill. Grouped with `role="group"` and `aria-labelledby`.
- The choice persists in `localStorage` under `apm-lang` and is restored on load. Both read
  and write are wrapped in try/catch so blocked storage cannot break the toggle, and only
  `en`/`ha` are accepted from storage.
- Verified by browser: switched to Hausa, reloaded the page, and Hausa was still active.

#### Promises duplication - resolved from source evidence

Read the archived campaign page (`delivery-89aec627d08a.html`, grade D, cited by all eight
promises). The published manifesto has **five pillars** and **no standalone water pillar**.
Searching the whole document, `water` appears exactly twice, while `sanitation`, `WASH`,
`borehole`, `toilet`, `drainage` and `climate` appear **zero times**.

`promise-wash` was therefore a **phantom row** created to fill the sector grid, holding a
byte-for-byte copy of `promise-infrastructure` - including `success_indicator`. The agenda
rendered the same commitment twice under two sectors.

- `promise-infrastructure` keeps the full published pillar text, unchanged.
- `promise-wash` is re-scoped to the **water clause of that same published commitment** and
  labelled honestly: `promise_type` = `Published commitment clause`, `approval_status` =
  `Published clause of the Infrastructure Development commitment`, with a water-specific
  `success_indicator`. Nothing is invented; every word traces to the source.
- **New validator `validate_unique_promises()`** rejects any two promise rows sharing
  `promise_text`. This guards the bug class, not just the instance. Proven to fire by
  reintroducing the duplicate, then restoring.

Verified in the browser: 8 agenda cards, no duplicates, water and infrastructure distinct.

#### Bug caught during S2

Adding the persistence wrapper left **two `const setLanguage` declarations** in the same
scope. That is a `SyntaxError`, which would have silently disabled *every* script on the
page - the HTML still renders, so nothing looks wrong in a visual check. Caught by
inspection, fixed, and now guarded three ways: a `node --check` parse of the extracted
inline script, a duplicate top-level `const` detector, and an exact-count assertion on
`setLanguage`.

#### Verification

87 tests pass (was 57). Browser-verified at 375px and 1440px: emblem renders in colour,
language label switches EN/Hausa, choice survives reload, sponsor tile renders and
translates, agenda de-duplicated, no horizontal overflow at 375px, **zero console errors**.

---

## 10. Next session - start here

**State at handoff (26 September 2026):** S0, S1 and S2 complete and committed. `main` is
**4 commits ahead of `origin/main` and nothing has been pushed** (including the pre-existing
`2fd12fa`). The site is still a single
page. 87 tests pass.

### Do this first

1. Work from `D:\APMdeliverable` and run `python -m unittest discover -s tests -q`. Expect
   **87 OK**.
2. Run `python src/dashboard/render.py`. It must render without raising.
3. Confirm the preserved local work is still untracked/modified and do **not** touch it:
   `src/aggregation/aggregate.py`, `.evals/`, `data/human_review/filled/`, `.playwright-mcp/`.
4. Read section 3 (target architecture) and section 5 (anchor re-targeting) above, then
   start **S3**.

### S3 scope in one paragraph

Extract the single f-string in `render()` into a Jinja2 shared layout. Jinja2 is already in
`requirements.txt` and currently unused, so this adds no dependency. Emit six **flat** files
in `docs/` - `index.html`, `achievements.html`, `atlas.html`, `poll.html`, `agenda.html`,
`sources.html` - so the existing `assets/brand/...` relative paths keep working unchanged.
Every page gets the shared header, the labelled language control, the footer with the
sponsor slot, and `aria-current="page"` on its own nav link.

### Three things S3 must not miss

1. **A mobile navigation menu.** `.nav` is `display:none` below 1050px. With subpages, phones
   get **no navigation at all**.
2. **A solid-header variant.** `.topbar` is `position:absolute` with white text over the dark
   hero. A subpage without a hero needs an opaque background or the header renders
   white-on-cream.
3. **The two release traps in `HANDOFF.md` section 20**, fixed *in the same change*:
   `rebuild-pages.yml:33` stages only `docs/index.html`, and the staging allowlist in
   `HANDOFF.md` section 18 names only `docs/index.html`. Both fail silently.

### Re-target these tests

| Test | Assertions | Move to |
|---|---:|---|
| `test_dashboard_contract.test_language_toggle_preserves_selected_lga` | 4 | `atlas.html` |
| `test_dashboard_contract.test_featured_section_is_rendered_from_current_data` | 9 | `achievements.html` |
| `test_request_form.*` (4 tests) | 24 | `poll.html` |

`test_request_form.py:21` asserts `data-request-ra-lga=` appears 212 times, but there are 213
raw occurrences - the extra one is inside `REQUEST_SCRIPT`. It only passes because the markup
and its JS ship in the same file.

### Owner gates still open

- Ratify or correct the `apm-emblem.png` rights record in `asset_register.csv`.
- Native-speaker review of the **53 AI-drafted Hausa strings** (27 `usage_note_ha`, 25
  `verification_status_ha`, 1 wash-promise clause). These are integrity caveats a
  Hausa-reading voter now sees.
- Push authorisation for the four unpushed commits.
- Decide whether to narrow the `wash` sector label from "Water and climate resilience" - the
  published campaign source contains zero climate content.

### If you only have time for one thing

Run the S1 and S2 guards against your change:

```text
python -m unittest tests.test_bilingual tests.test_header_brand -v
```

These cover the defects that are invisible in a visual check: untranslated strings, Hausa
pasted into an English column, a missing emblem hash, an invert filter creeping back,
invented sponsor content, and a duplicate `const` that would disable every script on the page.
