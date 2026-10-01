# Google Sheets Request Intake Setup Guide

Use this guide when the campaign owner is ready to enable public submissions.
Agents can build and test the adapter, but the private Google account, Sheet
access, consent copy, retention period, and deployment decision belong to the
owner.

## 1. Create the private Sheet

1. Create a new Google Sheet owned by the campaign organization account.
2. Rename the first tab `Requests`.
3. Add columns exactly as follows:

```text
request_id
created_at
lga
ward_code
address
category
details
name
email
consent
validation_status
validation_warnings
submitted_at
```

4. Add a second tab named `Audit` with only non-identifying operational fields:

```text
received_at
validation_status
rejection_code
```

5. Do not share the raw Sheet publicly. Restrict access to campaign staff who
   need follow-up access.

## 2. Create the Apps Script endpoint

**The endpoint is written and tested. You do not write it.**

`docs/requests-script/` contains the complete intake endpoint, generated and verified:

| File | What it is |
|---|---|
| `Code.gs` | the file you paste or push — **generated, never hand-edited** |
| `Code.gs.template` | the source; edit this and regenerate |
| `build_code_gs.py` | `Code.gs.template` + `lga_wards.csv` → `Code.gs` |
| `test_endpoint.mjs` | 268 checks that run the real `doPost` |

```bash
python docs/requests-script/build_code_gs.py   # after any edit to the template
node  docs/requests-script/test_endpoint.mjs  # expect 268/268
```

1. Open the Sheet → Extensions → Apps Script.
2. Create a **bound** script for the Sheet (a standalone project makes `setupSheets` fail
   with a confusing `null`).
3. Paste the whole of `docs/requests-script/Code.gs`, or push it with `clasp` (below).
   **Delete the default `myFunction()` stub and add a fresh file named `Code.gs`** — a
   paste that lands *inside* the stub still compiles but leaves `doPost` non-top-level, so
   the function dropdown reads "No functions".
4. Run **`setupSheets`** → Run → approve. It creates `Requests` (14 columns, matching
   section 1) and `Audit`, and highlights duplicate references in red. The log should read
   `setup complete: 0 request row(s)`.
5. Deploy → New deployment → Web app, Execute as **Me**, access **Only myself** → approve →
   copy the `/exec` URL.
6. Give the `/exec` URL to an agent, who sets `REQUEST_ENDPOINT` in
   `src/dashboard/render.py`, re-renders and runs the suite.

### Pushing with clasp instead of pasting

`clasp` 3.4.1 is installed globally (`npm i -g @google/clasp`).

1. Copy `.clasp.json.example` to `.clasp.json` in `docs/requests-script/` and paste your
   script ID in. **`.clasp.json` is gitignored and must stay that way.**
2. `clasp login` from that folder — one Google consent screen, once.
3. `clasp push`. `.claspignore` keeps the generator, harness and template out of the
   deployment, so `clasp status` must show only `Code.gs` and `appsscript.json`.
4. `clasp push` also replaces the manifest, so the manual manifest step is unnecessary.
   The default manifest requests access to **all** the owner's spreadsheets; ours restricts
   it to `spreadsheets.currentonly`.

`clasp` cannot create a web app deployment. That and the two Google authorisation screens
remain owner actions.

### What the endpoint enforces for you

You do not need to remember these; they are code, tested, and cannot be forgotten:

- **Every rule in `src/requests/validation.py`**, re-implemented server-side because the
  browser cannot be trusted. A test fails if the two ever disagree.
- **The registration-area map is generated in**, all 212 areas, so an area cannot be
  accepted for the wrong LGA. The endpoint **refuses to run** without a complete map rather
  than storing unverifiable locations.
- **The tracking reference is sequential**, never a hash of the content — a hash of a name
  and a phone number is a fingerprint anyone who can guess the person can confirm.
- **The response is `{ request_id }` and nothing else.** No name, phone, email or address
  is ever sent back to the browser.
- **The `Audit` tab has three columns and cannot hold a fourth**: a timestamp, an outcome
  and a stable rejection code. A rejected request carries all five private fields and
  leaves only the code behind.
- **Nothing reaches the Sheet that failed validation.**

## 3. Deployment settings

1. Deploy as a web app (step 2.5 above).
2. Choose the intended execution account only after the owner confirms access.
3. Set access to the narrowest practical audience.
4. Do not paste credentials, Sheet IDs, deployment IDs, or Apps Script code into
   the GitHub repository. `Code.gs` is committed deliberately: it holds no
   credential, no Sheet ID and no deployment ID, and its only data is the public
   registration-area map, which is already in `lga_wards.csv` and on the form.
5. Test with dummy records first. Confirm rejected data never reaches the Sheet.

### Two things that are still not solved

- **No rate limiting.** The honeypot and the control-character rejection discourage
  automated submission; neither stops a determined one. Adding real rate limiting means
  deciding what to count, and counting by IP would store a new identifier this system
  currently does not hold. That is an owner decision, not an implementation detail.
- **Google retains IP addresses in Apps Script execution logs** regardless of what this
  Sheet stores. Not fixable in code. Decide about it consciously.

## 4. Aggregate publishing

1. A scheduled owner-controlled job reads consented and validated private rows.
2. Apply the approved LGA/category aggregation rules.
3. The current threshold applies only to any hypothetical ward-level output;
   the public snapshot publishes no ward-level cells. LGA/category counts remain
   exact aggregate counts and require owner review before release.
4. Write only the fixed public snapshot fields:

```text
reporting_period_start
reporting_period_end
total_requests
by_lga
by_category
by_lga_category
generated_at
small_count_threshold
suppressed_ward_count
```

5. Never publish raw rows, request IDs, contact fields, addresses, ward codes,
   details, or validation metadata.
6. The static site may load a sanitized snapshot weekly. It must never read the
   private Sheet directly from the browser.

## 5. Owner decisions before deployment

- Confirm the request categories and exact bilingual labels.
- Confirm optional name/phone/email collection. **This is the sensitive one:** unlike the
  opinion poll, this form stores personal data by design.
- **Confirm the consent wording with whoever handles data-protection questions.** The
  consent text must say plainly what is stored (name, phone, email, address, and what they
  wrote), who can read it, and how long it is kept.
- **Set a retention/deletion period for the `Requests` tab.** This is not hypothetical: the
  rows are private data with a name and a street address on them, and an unbounded queue of
  those is a liability that grows every day. Decide the period and who deletes closed
  requests. Nothing in the code does this for you, and unlike the poll's free-text comment
  there is no automatic purge here — a request you delete is a request you cannot action.
- Confirm whether the RA label is acceptable for the MVP.
- Confirm the private Sheet owner, staff access list, and Apps Script execution
  account.
- Confirm the weekly reporting schedule and the privacy threshold.

## 6. Verification checklist

- [ ] Dummy valid submission creates exactly one private row.
- [ ] Duplicate retry does not create a second row.
- [ ] Invalid LGA/ward pair is rejected.
- [ ] Invalid category is rejected.
- [ ] Missing consent is rejected.
- [ ] Oversized details/address is rejected.
- [ ] Honeypot submission is rejected.
- [ ] Optional contact data is private and not in public output.
- [ ] Public snapshot contains aggregate fields only.
- [ ] Small ward counts are suppressed.
- [ ] Confirmation page shows only the generated request ID.
- [ ] Owner has reviewed the final consent/retention policy.
