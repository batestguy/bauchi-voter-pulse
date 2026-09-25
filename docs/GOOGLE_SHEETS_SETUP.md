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
phone
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

1. Open the Sheet → Extensions → Apps Script.
2. Create a bound script for the Sheet.
3. Implement `doPost(e)` as the intake boundary.
4. Make the endpoint call the same rules documented in
   `src/requests/validation.py` and `src/requests/request_schema.json`; do not
   rely on browser validation.
5. Require the final approved `data/delivery/lga_wards.csv` data to be loaded
   into the script's private configuration. The current 212 RA rows are
   provisional INEC electoral registration areas, not verified administrative
   council wards.
6. Allocate a request ID server-side using the pattern `APM-YYYY-NNNN`. The
   pure Python contract accepts four to twelve sequence digits; the owner guide
   uses four digits for the first release. Keep one documented rule across the
   Sheet, endpoint, and tests.
7. Reject duplicate IDs, invalid LGA/ward pairs, invalid categories, missing
   consent, oversized text, control characters, and populated honeypots.
8. The current public form does not yet send an idempotency token. Design and
   approve a separate privacy-reviewed token contract before enabling duplicate
   detection; do not silently add an unknown field because the current
   validator rejects unknown fields. Never use the official voter ID as a
   deduplication key.
9. Add rate limiting and safe logging. Never log names, phone numbers, email,
   addresses, details, or request payloads.
10. Return JSON with exactly one field: `request_id`, matching
   `^APM-[0-9]{4}-[0-9]{4,12}$`. Do not return private data, contact details,
   or a free-form message. The browser validates the shape before displaying the
   tracking reference.

## 3. Deployment settings

1. Deploy as a web app.
2. Choose the intended execution account only after the owner confirms access.
3. Set access to the narrowest practical audience.
4. Do not paste credentials, Sheet IDs, deployment IDs, or Apps Script code into
   the GitHub repository.
5. Test with dummy records first. Confirm rejected data never reaches the Sheet.

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
- Confirm optional name/phone/email collection.
- Confirm consent text and retention/deletion period.
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
