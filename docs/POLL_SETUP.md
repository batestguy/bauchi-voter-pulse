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

1. Open the Sheet → Extensions → Apps Script.
2. Create a bound script for the Sheet.
3. Implement `doPost(e)` as the intake boundary.
4. **Repeat every rule in `src/poll/validation.py`. Do not trust browser validation.** The
   browser sends JSON; anyone can send anything.
5. The permitted payload fields are exactly `sector`, `lga`, `ward_code`, `age_band`,
   `gender`, `comment`, `consent`, and an empty `website` honeypot. Reject anything else.

   - `identity_field_forbidden` for any of `name`, `full_name`, `phone`, `phone_number`,
     `email`, `address`, `voter_id`, `voterid`, `registered_voter_number`, `nin`, `bvn`,
     `date_of_birth`, `dob`, `age`, `age_years`, `exact_age`, `years_old`
   - `invalid_lga` for anything outside the 20 Bauchi LGAs
   - `invalid_ward` for a registration-area code that does not belong to the selected LGA
   - `ward_map_required_for_ward_code` if a code arrives with no approved map loaded
   - `invalid_choice` for an age band or gender outside the closed list

   Reject with a specific code rather than silently dropping the field:

   A silently-ignored identity field is still an identity field on the wire and in any
   log between the browser and the Sheet. Reject it instead.
6. Allocate `response_id` server-side using `APM-POLL-YYYY-NNNN`. This is a tracking
   reference for one response. **It is not a voter ID and must never be described as
   one**, in the Sheet, in the response, or in any UI.
7. Reject duplicate IDs. The public form deliberately sends no idempotency token, and the
   one-per-browser marker in `localStorage` is trivially cleared. Treat the Sheet, not the
   browser, as the record of what was actually cast. Never use a voter ID as a
   deduplication key — there is no voter ID.
8. Add rate limiting and safe logging. Never log a comment, and never log a whole payload.
9. Return JSON with exactly one field, `response_id`, matching
   `^APM-POLL-[0-9]{4}-[0-9]{4,12}$`. Do not return the comment, the sector, or any stored
   value back to the browser — an endpoint that echoes the comment makes it visible in
   the network tab of the respondent's own browser. The browser validates the shape
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

1. A scheduled, owner-controlled job reads the `Responses` tab and builds a snapshot with
   `src.poll.aggregate.build_public_snapshot(...)`.
2. Write it to `data/delivery/poll_snapshot.json`. **The field set is not yours to choose** —
   it is `aggregate.PUBLIC_SNAPSHOT_FIELDS`, and a test asserts the file's keys match it
   exactly. Build the snapshot with `build_public_snapshot` rather than assembling the
   dictionary by hand, and the shape is correct by construction:

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
3. Commit it. The weekly `rebuild-pages.yml` cron picks it up and republishes.
4. Never commit raw rows, comments, response IDs, or timestamps of individual responses.

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

## 6. Owner decisions before deployment

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
- [ ] Set a **retention period** for the comment column, and a process that actually
      deletes on schedule. An anonymous poll that keeps free text forever is not anonymous
      in any meaningful sense.
- [ ] Decide who may read the raw Sheet.
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
- Never present a poll result as a verified need, achievement, promise, evidence figure or
  outcome measurement. It is a stated preference from a self-selected visitor.
- Never remove the self-selected / not-representative disclosure.
- Never commit the Sheet, the Apps Script source, credentials, Sheet IDs, deployment IDs,
  or any submitted value.
