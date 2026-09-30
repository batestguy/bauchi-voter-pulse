# Connecting the poll — owner guide

**What this is:** about ten minutes of clicking, on your own Google account. Everything
that can be written in advance has been, and tested.

**What is already done for you**, in this folder:

| File | What it is |
|---|---|
| `Code.gs` | The complete endpoint. Paste it, don't edit it. **Generated** — see below. |
| `appsscript.json` | The manifest. |
| `test_endpoint.mjs` | 64 checks that run the real `doPost` against test payloads. |
| `build_code_gs.py` | Regenerates `Code.gs` from `Code.gs.template` + the real ward map. |
| `.claspignore` | Keeps non-script files out of the deployment. |
| `.clasp.json` | Your project id. **Gitignored** — copy `.clasp.json.example` and fill it in. |

**Why the code needed its own test harness.** An agent cannot reach a Google account, so
this file is the one piece of code that would otherwise ship unreviewed by anything that can
execute it. It is not a mock: `test_endpoint.mjs` loads the real `Code.gs` with the Apps
Script globals stubbed and runs the real `doPost`. It found three real bugs before you got
here, including one where the endpoint stored the **raw request body** instead of the
validated record — so the Sheet would have held `bAUcHi` as an LGA name and
`age_unspecified` as a published demographic. Do not skip running it if you edit the code:

```bash
node docs/apps-script/test_endpoint.mjs    # expect: 64/64 checks passed
```

---

## How to push changes: use clasp, not copy-paste

**`clasp` 3.4.1 is installed globally on this machine** (30 September 2026). Pasting code
into the Apps Script editor is slow and unreliable — the editor is a CodeMirror instance
whose select-all does not always behave, and a paste that lands *inside* the default
`myFunction()` stub produces a file that looks fine and deploys as an endpoint with no entry
points. That happened. Use clasp.

### One-time setup (5 min)

1. **Find your Script ID.** In the Apps Script editor: the **gear icon** in the left sidebar
   → **Project Settings** → **Script ID**. It is also in the editor URL, between
   `/dashboards/` and `/edit`.
   > Take it from the project that is **bound to the Sheet**, not a standalone one.
2. **Copy `.clasp.json.example` to `.clasp.json`** in this folder and paste the ID in.
   `.clasp.json` is gitignored on purpose: the script id is deployment-scoped, and the repo
   rule is no Sheet or deployment ids in git. The example file is committed so the workflow
   is discoverable.
3. **Authorise clasp once.** From `docs/apps-script/`:
   ```bash
   clasp login
   ```
   Your default browser opens a Google consent screen. Approve it. This is the only
   browser step clasp needs you for.
4. **Push:**
   ```bash
   clasp push
   ```

After that, editing `Code.gs` in this repo and running `clasp push` is the whole workflow.
No editor, no pasting.

### What clasp still cannot do

**It cannot create a web app deployment.** Steps 3 and 4 below are always done in the
browser. That is a long-standing clasp limitation, not a misconfiguration. What it removes
is every paste, which is where all the friction was.

---

## 1. Create the Sheet (2 min)

1. Go to <https://sheets.new> and create a blank spreadsheet.
2. Name it `APM poll responses` (double-click the tab at the bottom-left). A bound script
   inherits this name.
3. **Leave the columns alone.** You do not type them by hand — step 2 creates both tabs.
   Do not add a name, phone, email, address, NIN, BVN, exact-age, date-of-birth or
   voter-ID column, ever: a column that is never written is still a column someone will
   eventually fill in by hand.

## 2. Add the code (3 min)

**Preferred — clasp.** Do the one-time setup above, then `clasp push`. Skip to step 3.

**Only if clasp is unavailable**, paste it manually:

1. **Extensions → Apps Script** from inside the sheet. This must be a **bound** script; the
   code calls `SpreadsheetApp.getActiveSpreadsheet()`, which returns nothing in a
   standalone project, and `setupSheets` will fail with a `null` error that looks like a
   code bug but is not.
2. In the Files pane, **right-click the default file → Delete**, then **+ → Script**, name
   it exactly `Code.gs`, **Add**. Start from a genuinely empty file rather than pasting over
   the `myFunction()` stub — a paste that lands inside the stub compiles but exposes no
   entry points, and Apps Script will still report "No functions" in the dropdown.
3. Click into the empty editor and paste the whole of `Code.gs`.
4. In Project Settings, tick **"Show `appsscript.json` manifest file in editor"**. Select all
   in that new file and replace it with this folder's `appsscript.json`. This is not
   cosmetic: the default manifest requests access to **all** your spreadsheets, whereas this
   one restricts it to `spreadsheets.currentonly` — only the sheet it is attached to.
5. **Ctrl+S.**

## 3. Run setupSheets (1 min)

1. In the function dropdown, select **`setupSheets`**.
2. **Run.** First run: **Review permissions → Advanced → Go to (project name) → Allow.**
3. The **Execution log** at the bottom should end with:
   ```
   setup complete: 0 response row(s)
   ```

It creates two tabs: `Responses` (10 columns) and `Audit` (3 columns), and adds a
conditional format on column A that highlights a duplicate `response_id` in red. The public
form sends no idempotency token and the one-per-browser marker in `localStorage` is
trivially cleared, so **the Sheet is the record of what was actually cast**.

## 4. Deploy (3 min)

1. **Deploy → New deployment**.
2. Gear beside *Select type* → **Web app**.
3. **Description:** `APM poll intake`.
4. **Execute as:** **Me** (`<your email>`).
5. **Who has access:** **Only myself**.
   > Apps Script offers three levels. *Only myself* is correct and it is not a limitation:
   > the deployment's access level governs *who can use the script*, not who can send it a
   > request. Anyone who can load the page can POST to it — which is exactly why the
   > validation in step 2 matters and must not be skipped.
6. **Deploy**, approve the authorisation screen, and copy the **Web app URL**. It ends
   `/exec`.


## 4. Connect it to the site (1 min)

In `src/dashboard/render.py`, one line:

```python
POLL_ENDPOINT = "https://script.google.com/macros/s/DEPLOYMENT_ID/exec"
```

Then:

```bash
python src/dashboard/render.py
python -m unittest discover -s tests -q     # expect 279 OK (1 skip)
```

**The button will now be live.** Before you commit, do step 5.

## 5. Prove it works from the real page (5 min — do not skip)

This is the step everyone skips, and it is the single most common reason a Sheets-backed
form "works in curl but not in the browser": **Apps Script web apps do not send CORS
headers**, so a `fetch` from a static site can fail on preflight even though the deployment
is healthy.

1. Push the site, or open `docs/poll.html` from a local server:
   ```bash
   cd docs && python -m http.server 8000
   ```
2. Cast one vote through the form.
3. Check the `Responses` tab has one row, and `Audit` has an `accepted` row.
4. Check the browser console (F12) — there should be **no** CORS error.
5. Send a deliberately bad request and confirm it is refused and **not** stored:
   ```bash
   curl -X POST "YOUR_EXEC_URL" -H "Content-Type: text/plain" \
     -d '{"sector":"water","lga":"Bauchi","consent":true,"name":"Aminu"}'
   ```
   Expect `{"error":"identity_field_forbidden"}`, and no new row in `Responses`.
   If the `name` field had been silently ignored instead of refused, that is a real bug —
   report it before connecting.

## 6. Publishing results — a separate step

Connecting the endpoint collects votes. It does **not** put anything on the website.

A scheduled, owner-controlled job must read the `Responses` tab and write a snapshot to
`data/delivery/poll_snapshot.json`. Until that file exists, the page correctly shows "No
responses have been recorded yet" — that is the honest empty state, and there is a test that
fails the build if a placeholder snapshot is committed. See `POLL_SETUP.md` §5.

The snapshot's field set is `aggregate.PUBLIC_SNAPSHOT_FIELDS`, not a list to be chosen by
hand. Build it with:

```python
from src.poll.aggregate import build_public_snapshot
snapshot = build_public_snapshot(rows_from_the_responses_tab)
```

---

## Retain, or the poll is not anonymous

The `comment` column is 300 characters of free text. It is never counted and never
published, but **an anonymous poll that keeps free text forever is not anonymous in any
meaningful sense.** Set a retention period — 90 days is a defensible default — and a process
that actually deletes on schedule, not a note in a document.

Separately: **Google retains IP addresses in Apps Script execution logs** regardless of what
the Sheet stores. That is a platform property this code cannot remove. Decide about it
consciously, and do not pretend the poll collects no data at all.

## If something goes wrong

| Symptom | Cause |
|---|---|
| Button greyed out | `POLL_ENDPOINT` is still `""`, or the page wasn't re-rendered |
| `invalid_ward` on an area the form offered | the endpoint's map drifted; run `python docs/apps-script/build_code_gs.py` |
| CORS error in the console | redeploy as **Web app** (not *Execute as me* API), then reload hard |
| `authorization` error | the Google account lost access to the script |
| Votes arrive but the page shows nothing | expected: no snapshot has been built yet (§6) |
