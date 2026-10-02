# Google Sheets Opinion Poll Setup Guide

**Status: the poll ships disabled.** `POLL_ENDPOINT` in `src/dashboard/render.py` is an
empty string, so the vote button renders `disabled` and no code path can send anything.
This guide is for the owner to work through when you are ready to connect it. Agents can
build and test the contract, but the private Google account, Sheet access, retention
period, and deployment decision belong to you.

The contract this guide wires up is `src/poll/poll_schema.json`, with the pure rules in
`src/poll/validation.py` and the tally in `src/poll/aggregate.py`.

## 0. What this poll is, and what it is not

It is **one question** — which sector should APM prioritise first — asked of people who
choose to answer. That is the only thing it counts.

It is not a survey, not a vote, and not a measurement of how many people in Bauchi hold
any view. Respondents are self-selected visitors. The page says this in both languages
next to the results, and a test asserts the disclosure is present **even in the empty
state**, because the fastest way to lose trust on a campaign site is to let a
self-selected tally imply a mandate.

Everything below serves one rule: **a published number must be traceable, honest about its
sample, and impossible to fabricate.**

## 0b. What the poll collects, and why it is still not identity

| Field | Required? | Why it is safe |
|---|---|---|
| `sector` (Q1) | yes | The only field that moves a number |
| `lga` | yes | 20 broad buckets |
| `ward_code` | **no** | Optional precisely so nobody is forced to narrow further than they want |
| `age_band` | **no** | A group, never a number, from a closed list |
| `gender` | **no** | Closed list of Woman / Man / Prefer not to say |
| `comment` (Q2) | no | Stored, never counted, never published |

Never collected: name, phone, email, address, NIN, BVN, exact age, date of birth, or any
voter ID. Those are **rejected with `identity_field_forbidden`**, not ignored — a dropped
identity field is still an identity field on the wire and in every log.

**The area and demographic fields are the reason suppression is mandatory.** An LGA plus a
sector plus a date is closer to a person than a sector alone. The floor of 5 is what makes
publishing that combination defensible. It is not decoration.

**Google retains IP addresses in Apps Script execution logs** whatever this Sheet stores.
That is a platform property the code cannot remove. Decide about it consciously.

## 1. Create the private Sheet

1. Create a new Google Sheet owned by the campaign organisation account.
2. Rename the first tab `Responses`.
3. Add columns exactly as follows, and no others:

```text
response_id
received_at
sector
lga
ward_code
age_band
gender
comment
consent
validation_status
```

4. Add a second tab named `Audit` containing only non-identifying operational fields:

```text
received_at
validation_status
rejection_code
```

5. **Do not add a name, phone, email, address, NIN, BVN, exact-age, date-of-birth or
   voter ID column.** The validator rejects any of those in a payload, and they must not
   exist in the Sheet either — a column that is never written is still a column someone
   will eventually fill in by hand.

   `age_band` and `gender` are the two that get "just one more thing" added to them. They
   stay as closed lists. An exact-age column would defeat the entire design.
6. Do not share the raw Sheet publicly. Restrict access to campaign staff who need it.

`comment` is the one free-text field and it is the sharp edge of this design. It is capped
at 300 characters, it is never counted, and it is never published. It is still the field
most likely to attract abuse and the field most likely to capture an identifying detail a
respondent typed unprompted, which is why the form warns them not to.

## 2. Create the Apps Script endpoint

**The endpoint is already written and tested. Follow
[`apps-script/DEPLOY.md`](apps-script/DEPLOY.md) instead of this section** — it has the
exact clicks, and it explains why the code needed its own test harness.

| File | What it is |
|---|---|
| [`apps-script/Code.gs`](apps-script/Code.gs) | The complete endpoint. Paste it as-is. Generated from `Code.gs.template` plus the real ward map by `build_code_gs.py`, so its registration-area map cannot drift from the form's. |
| [`apps-script/appsscript.json`](apps-script/appsscript.json) | The manifest. |
| [`apps-script/test_endpoint.mjs`](apps-script/test_endpoint.mjs) | 64 checks that run the real `doPost` with the Apps Script globals stubbed. Run it after any edit: `node docs/apps-script/test_endpoint.mjs`. |

The notes below are the reasoning the implementation already follows, kept because they are
what a future editor needs in order not to undo it. The summary is at `DEPLOY.md`.

1. Open the Sheet → Extensions → Apps Script.
2. Create a bound script for the Sheet.
3. `doPost(e)` is the intake boundary, and it **repeats every rule in
   `src/poll/validation.py`**. Do not trust browser validation: the browser sends JSON and
   anyone can send anything.
4. The permitted payload fields are exactly `sector`, `lga`, `ward_code`, `age_band`,
   `gender`, `comment`, `consent`, and an empty `website` honeypot. Reject anything else.

   - `identity_field_forbidden` for any of `name`, `full_name`, `phone`, `phone_number`,
     `email`, `address`, `voter_id`, `voterid`, `registered_voter_number`, `nin`, `bvn`,
     `date_of_birth`, `dob`, `age`, `age_years`, `exact_age`, `years_old`
   - `invalid_lga` for anything outside the 20 Bauchi LGAs
   - `invalid_ward` for a registration-area code that does not belong to the selected LGA
   - `ward_not_configured_for_lga` if a code arrives with no approved map loaded
   - `invalid_choice` for an age band or gender outside the closed list

   Reject with a specific code rather than silently dropping the field:

   A silently-ignored identity field is still an identity field on the wire and in any
   log between the browser and the Sheet. Reject it instead.
5. **Persist the validated record, not the raw request body.** `validate_` returns a new
   normalised object — canonical LGA spelling, declines collapsed to `''`, trimmed and
   length-capped text. Writing the raw payload instead throws all of that away: it stores
   `bAUcHi` as an LGA name and `age_unspecified` as a *demographic*, which the snapshot would
   then publish as its own slice. This was a real bug in the first draft of `Code.gs`; the
   harness caught it.
6. Allocate `response_id` server-side as `APM-POLL-YYYY-NNNNNN`, sequentially, from Script
   Properties. This is a tracking reference for one response. **It is not a voter ID and
   must never be described as one**, in the Sheet, in the response, or in any UI.
   **Never derive it from the response content**: a content hash is a stable fingerprint
   that anyone who can guess someone's comment can confirm by hash.
7. Reject duplicate IDs. The public form deliberately sends no idempotency token, and the
   one-per-browser marker in `localStorage` is trivially cleared. Treat the Sheet, not the
   browser, as the record of what was actually cast. Never use a voter ID as a
   deduplication key — there is no voter ID. `setupSheets` adds a conditional format that
   highlights a duplicate `response_id` in red.
8. Add rate limiting and safe logging. Never log a comment, and never log a whole payload —
   log the rejection code and nothing else.
9. Return JSON with exactly one field, `response_id`, matching
   `^APM-POLL-[0-9]{4}-[0-9,12}$`. Do not return the comment, the sector, or any stored
   value back to the browser — an endpoint that echoes the comment makes it visible in the
   network tab of the respondent's own browser. The browser validates the shape
   before displaying anything, and treats a violation as a failed vote.

## 3. Deployment settings

1. Deploy as a web app.
2. Choose the intended execution account only after you confirm access.
3. Set access to the narrowest practical audience.
4. Do not paste credentials, Sheet IDs, deployment IDs, or Apps Script source into the
   GitHub repository.
5. Test with dummy records first. Confirm rejected data never reaches the Sheet.

### A note on CORS

Apps Script web apps do not send CORS headers, so a browser `fetch` from a static site
fails on a preflight unless the endpoint is set to serve the page as a web app and return
`ContentService` JSON. This is the single most common reason a Sheets-backed form
"works in curl but not in the browser". Test it from the real deployed page, not from a
command line.

## 4. Connecting it to the site

One line, in `src/dashboard/render.py`:

```python
POLL_ENDPOINT = "https://script.google.com/macros/s/DEPLOYMENT_ID/exec"
```

Then `python src/dashboard/render.py`, commit, and let the weekly cron publish. An empty
endpoint is the disabled state, not a missing feature — leave it empty until you are
confident, because the disabled build is provably inert and a connected build is not.

## 5. Publishing results

The site is static, so results come from a **committed aggregate snapshot**, never from
reading the Sheet in the browser.

1. Export the `Responses` tab: **File > Download > Comma-separated values (.csv)**.
2. Build the snapshot:
   ```bash
   python src/poll/build_snapshot.py ~/Downloads/Sheet1.csv
   ```
   It writes `data/delivery/poll_snapshot.json`, then:

   ```bash
   python src/dashboard/render.py
   git add data/delivery/poll_snapshot.json docs/*.html
   git commit -m "data(poll): publish the weekly aggregate"
   git push
   ```

   The weekly cron then re-renders and commits on its own schedule, but it does **not**
   read the Sheet: this step is the one that brings votes into the published page, and
   skipping it is why the dashboard can sit empty while votes are arriving correctly.

   **Do not hand-assemble the JSON.** `build_snapshot.py` calls
   `src.poll.aggregate.build_public_snapshot(...)`, so the shape is correct by
   construction, small cells are suppressed, and comments are never read. The field set is
   `aggregate.PUBLIC_SNAPSHOT_FIELDS` and a test asserts the file's keys match it exactly:

   ```text
   schema_version            reporting_period_start   reporting_period_end
   total_responses           with_area_responses      with_ward_responses
   with_age_band             with_gender
   by_sector                 by_lga                   by_lga_sector
   by_ward                   by_ward_sector           by_lga_ward
   by_lga_age_band           by_lga_gender
   by_lga_age_band_sector    by_lga_gender_sector
   by_age_band_sector        by_gender_sector
   percentage_floor          small_count_threshold    suppressed_cell_count
   generated_at
   ```

   Every `by_*` map is subject to the same suppression floor. The three-way maps
   (`by_lga_gender_sector`, `by_lga_age_band_sector`) and the area map (`by_ward_sector`)
   are what the interactive dashboard reads; see `SITE_EXPANSION_PLAN.md` for the
   dashboard's scope rules and `AGENTS.md` for the crossings that are refused.
4. Never commit raw rows, comments, response IDs, or timestamps of individual responses.

### Two column names that do not match, and why it is worth knowing

The `Responses` tab header says **`received_at`**; the aggregator reads **`created_at`**.
They differ by one letter, nothing upstream checks it, and passing the Sheet's own column
name straight through produced a snapshot reporting `counted 0` from twelve perfectly good
rows — a dashboard of nothing, built from real data, with no error anywhere. CSV also has
no booleans, so `consent` arrives as the string `"TRUE"` where the aggregator requires the
JSON boolean `true`.

`build_snapshot.py` performs both mappings explicitly and `tests/test_build_snapshot.py`
asserts them against the real aggregator. If you ever extend that script, keep them: they
fail silently and identically, which is the worst combination available.

### Why this step is manual

A workflow that reads the Sheet needs a Google service-account key committed as a
repository secret. On a public repository that is a real increase in attack surface, and
the alternative keeps every credential out of git entirely. At campaign volumes, exporting
the tab and running one command is the better trade. Revisit it only if the weekly ritual
becomes the bottleneck.

Until that file exists, the page renders an honest empty state: "No responses have been
recorded yet." That is deliberate. **Never seed, example, or placeholder results**, and
never let an empty poll render as a chart of zeros — a row of zero bars reads as data,
and it is not data. A test asserts no snapshot exists while the poll is disconnected.

### Suppression, and what to expect from it

`small_count_threshold` (default 5) replaces any non-zero cell below the floor with
`null`. A threshold of 0 or 1 is **refused** by the validator, because it would publish
single respondents. A cell of **0 is published**, not suppressed: "nobody chose this"
identifies nobody, and hiding it would wrongly read as "too few to say".

Expect the ward breakdown to be almost entirely empty. A local test fixture with 320
responses and 154 registration areas produced publishable figures for all 20 LGAs and for
**zero** LGAs at ward level. That is the arithmetic working, not a bug. The page says "too
few to show" rather than inventing a number.

### The percentage cap

`percentage_floor` (default 10) caps the highest displayed share at `100 - floor`, so a
single response can never render as 100%. Note the direction: the cap **lowers** a share,
it never raises one. Setting the floor to 0 disables it.

## 5a. Comments are kept — on their own tab, for a bounded time

The owner decided the complaints are worth keeping, and they are: a vote says a sector
matters, a complaint says *which* tap has been dry for seven months, and only the second
one tells the campaign what to do. So `setupSheets` creates **four** tabs, not two.

| Tab | Holds | Free text? |
|---|---|---|
| `Responses` | the vote: sector, LGA, area, age band, gender | **no** |
| `Comments` | the complaint: sector, LGA, timestamp, text | yes |
| `Audit` | timestamp, outcome, rejection code | no |
| `Retention` | the policy, in plain text, in the Sheet itself | no |

**Why the comment is on its own tab.** Free text sitting on the same row as a registration
area, an age band and a gender is closer to naming a person than any single field on it.
The `Responses` row already carries all three, so any row holding the comment *and* that
row has already re-identified the writer. Splitting them is what makes keeping the comments
defensible.

**What the `Comments` row deliberately does not have:** `ward_code`, `age_band`, `gender`,
and `response_id`. The last one is the load-bearing omission — the tracking reference is
the join key back to the `Responses` row that *does* carry the area and the demographics,
so shipping it alongside the text would let anyone who can read both tabs re-join them and
make the split decorative.

**The cost, stated plainly:** a comment can no longer be tied back to its own vote. That is
the trade, and it is the right one — reading what people said about a sector in an LGA
needs none of the join key.

### The steps

1. Run `setupSheets` as normal. It creates all four tabs and the `Responses` header no
   longer has a `comment` column.
2. Run `installRetention` **once**, from the dropdown. It installs a daily trigger that
   calls `purgeExpiredComments`. Re-running it is safe — it will not double the trigger.
   The execution log should read `retention installed: daily purge at 180 day(s)`.
3. Restrict sharing. `Comments` is the tab to keep to yourself and whoever curates the
   study. `Responses` can be shared more freely, precisely because it holds no free text.
4. Confirm the trigger exists: Triggers (clock icon in the left sidebar) → should show
   `purgeExpiredComments`, running Daily.

### What the purge does, and does not do

At **180 days**, a comment's text is deleted. The row survives — sector, LGA and timestamp
are not identifying on their own, and they are the same fields the published snapshot
already aggregates and suppresses. So you keep the shape of the study (how many
complaints, about what, where, over time) without keeping the words.

An unparseable timestamp is **deleted**, not kept: we cannot prove it is inside the window,
so it goes. Keeping it would be the permissive reading of an unknown.

### Why 180 days, and why there is a ceiling

180 covers a reporting cycle plus a re-run of the analysis. The **hard ceiling is 365**,
and `validate_comment_retention_days` *refuses* anything above it rather than honouring
it. This is the opposite direction to `small_count_threshold`, which refuses values that
are too small — and deliberately so. The risk of holding someone's free text grows with
time, so the value that must be refused is the long one. Raising the ceiling means editing
a bound and re-deriving its justification, not changing a config number.

`0` is refused too, for a separate reason: a 0-day setting reads as "we do not keep these",
so if the purge silently failed to run, the setting would be false in the permissive
direction.

**One thing the purge cannot do.** Google Sheets keeps *version history*, so an expired
comment can still be recovered from the file's revision history even after the cell is
blanked. Blanking is necessary and not sufficient. To actually drop it, prune version
history in the Sheet: **File → Version history → Name current version** (which starts a
new version) and, in Drive, **Activity → Version history** → delete old versions. Do this
on a schedule, not once. This is an owner action; no code can reach it.

And separately, as ever: **Google retains IP addresses in Apps Script execution logs**
regardless of what this Sheet stores. Not fixable in code.

## 6. Owner decisions before deployment

**Update, 2 October 2026:** the poll is deployed and live, and the owner reports the
native-speaker Hausa review complete — including the gender wording below and the
known-suspect strings listed in `AGENTS.md` (three of those four no longer exist; see
`docs/HAUSA_REVIEW.md`). The list is kept as the record of what the review covered, not as
work still outstanding.

These are yours, not the implementer's:

- [ ] Confirm the nine sector labels and their exact bilingual wording.
- [ ] Confirm the six age bands, the two gender options, and the Hausa wording
      ("Mace" / "Miji"). **A native speaker must check these.**
- [ ] **Review the four known-suspect Hausa strings** listed in `AGENTS.md` before the poll
      is connected. One of them says "pain" where it means "vote", and another claims "not
      a survey" without a Hausa word for survey at all. Shipping a garbled disclosure is
      worse than shipping an English one.
- [ ] Confirm the `small_count_threshold` of 5, or raise it. Do not lower it below 2.
- [ ] Confirm the comment cap of 300 characters, or change it in
      `src/poll/validation.py::MAX_LENGTHS`.
- [ ] Confirm the percentage cap, or set `POLL_PERCENTAGE_FLOOR = 0`.
- [ ] **Run `installRetention` once**, after `setupSheets`. This is the step that makes
      comment retention real. Details in §5a.
- [ ] Decide who may read the raw Sheet — and note that the `Comments` tab is the one to
      restrict, because it is the only tab holding free text. Details in §5a.
- [ ] Confirm the results publication cadence.
- [ ] Decide whether the poll closes, and what the page says when it does. A poll left
      open forever slowly becomes a different claim than the one you made.
- [ ] Confirm the consent wording with whoever handles data-protection questions for the
      campaign. This collects no identifying data by design, which is a materially
      lighter position than the request form on the same page — keep it that way.

## 7. What must never happen

- Never collect a name, phone number, email, address, date of birth, NIN, BVN, official
  voter ID or registered voter number from the poll, and never an **exact** age.
- Never add such a column to the Sheet "for later", and never narrow `age_band` or
  `gender` from a closed list to free text.
- Never publish a cell below the suppression floor, and never publish a
  demographic × registration-area cross-tabulation.
- Never count, bucket, summarise or publish the comment.
- Never move the comment back onto the `Responses` row, and never add `ward_code`,
  `age_band`, `gender` or `response_id` to the `Comments` row. That combination is what
  the split exists to prevent, and three tests assert it.
- Never raise `MAX_COMMENT_RETENTION_DAYS` to "keep them indefinitely", and never let the
  daily `purgeExpiredComments` trigger be deleted or paused.
- Never present a poll result as a verified need, achievement, promise, evidence figure or
  outcome measurement. It is a stated preference from a self-selected visitor.
- Never remove the self-selected / not-representative disclosure.
- Never commit the Sheet, the Apps Script source, credentials, Sheet IDs, deployment IDs,
  or any submitted value.
