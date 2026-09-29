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
choose to answer. That is all.

It is not a survey, not a vote, and not a measurement of how many people in Bauchi hold
any view. Respondents are self-selected visitors. The page says this in both languages
next to the results, and a test asserts the disclosure is present, because the fastest way
to lose trust on a campaign site is to let a self-selected tally imply a mandate.

Everything below serves one rule: **a published number must be traceable, honest about its
sample, and impossible to fabricate.**

## 1. Create the private Sheet

1. Create a new Google Sheet owned by the campaign organisation account.
2. Rename the first tab `Responses`.
3. Add columns exactly as follows, and no others:

```text
response_id
received_at
sector
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

5. **Do not add a name, phone, email, address, ward, LGA, age, date of birth, NIN, BVN or
   voter ID column.** The validator rejects any of those in a payload, and they must not
   exist in the Sheet either — a column that is never written is still a column someone
   will eventually fill in by hand.
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
5. The permitted payload fields are exactly `sector`, `comment`, `consent`, and an empty
   `website` honeypot. Reject anything else.

   Reject with a specific code rather than silently dropping the field:

   - `identity_field_forbidden` for any of `name`, `phone`, `email`, `address`,
     `ward_code`, `voter_id`, `registered_voter_number`, `nin`, `bvn`, `lga`, `age`,
     `date_of_birth`
   - `unsupported_field` for anything else unrecognised
   - `invalid_sector` for a value outside the nine categories
   - `consent_required` unless the JSON boolean `true`
   - `honeypot_rejected` for a populated `website`
   - `too_long` for a comment over 300 characters
   - `control_character_rejected` for control characters

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
2. Write it to `data/delivery/poll_snapshot.json` with exactly these fields:

```text
schema_version
reporting_period_start
reporting_period_end
total_responses
by_sector
percentage_floor
generated_at
```

3. Commit it. The weekly `rebuild-pages.yml` cron picks it up and republishes.
4. Never commit raw rows, comments, response IDs, or timestamps of individual responses.

Until that file exists, the page renders an honest empty state: "No responses have been
recorded yet." That is deliberate. **Never seed, example, or placeholder results**, and
never let an empty poll render as a chart of zeros — a row of zero bars reads as data,
and it is not data. A test asserts no snapshot exists while the poll is disconnected.

### The percentage cap

`percentage_floor` (default 10) caps the highest displayed share at `100 - floor`, so a
single response can never render as 100%. The reason is that 100% reads as a unanimous
mandate, and a sample of one is not a mandate.

Note the direction: the cap **lowers** a share, it never raises one. Setting the floor to
0 disables the cap if you want raw percentages.

## 6. Owner decisions before deployment

These are yours, not the implementer's:

- [ ] Confirm the nine sector labels and their exact bilingual wording.
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

- Never collect a name, phone number, email, address, ward, LGA, age, date of birth, NIN,
  BVN, official voter ID or registered voter number from the poll.
- Never add such a column to the Sheet "for later".
- Never count, bucket, summarise or publish the comment.
- Never present a poll result as a verified need, achievement, promise, evidence figure or
  outcome measurement. It is a stated preference from a self-selected visitor.
- Never remove the self-selected / not-representative disclosure.
- Never commit the Sheet, the Apps Script source, credentials, Sheet IDs, deployment IDs,
  or any submitted value.
