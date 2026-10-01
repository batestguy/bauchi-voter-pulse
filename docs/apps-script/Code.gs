/**
 * APM Bauchi public opinion poll -- Apps Script intake endpoint.
 *
 * PASTE THIS WHOLE FILE INTO YOUR SHEET'S BOUND SCRIPT, THEN DEPLOY AS A WEB APP.
 * See DEPLOY.md, in this folder, for the exact clicks. Nothing here works until it is
 * deployed and POLL_ENDPOINT in src/dashboard/render.py is set to the /exec URL.
 *
 * ============================================================================
 * WHY THIS FILE REPEATS EVERY RULE
 * ============================================================================
 * The browser sends JSON and anyone can send anything. This endpoint is the only
 * trustworthy boundary, so it re-implements every rule in src/poll/validation.py rather
 * than trusting the form. The pure Python module is the source of truth; this is a mirror
 * of it, and a test in tests/test_poll.py asserts the two vocabularies have not drifted.
 *
 * If you change a rule, change it in BOTH places or the test will fail.
 *
 * ============================================================================
 * WHAT IT MUST NEVER DO
 * ============================================================================
 * - Store or log a name, phone, email, address, NIN, BVN, exact age, date of birth or
 *   any voter ID. Those are REFUSED, not ignored: a silently dropped identity field is
 *   still an identity field in the request body and in the execution log.
 * - Return anything except { response_id }. Echoing the comment back would show it to
 *   the respondent in their own network tab.
 * - Log a comment, or log a whole payload. Log the rejection code and nothing else.
 * - Keep a stored comment forever. See COMMENTS SHEET and COMMENT_RETENTION_DAYS below.
 *
 * Note that Google retains IP addresses in Apps Script execution logs no matter what this
 * Sheet stores. That is a platform property, not something this code can remove.
 */

/** Registration areas per LGA, generated from data/delivery/lga_wards.csv.
 *  Compact form so the map is reviewable in one glance: "LGA:CODE,CODE;LGA:...". */
var WARD_MAP_SOURCE = 'Alkaleri:RA-001,RA-002,RA-003,RA-004,RA-005,RA-006,RA-007,RA-008,RA-009,RA-010,RA-011;Bauchi:RA-012,RA-013,RA-014,RA-015,RA-016,RA-017,RA-018,RA-019,RA-020,RA-021,RA-022,RA-023;Bogoro:RA-024,RA-025,RA-026,RA-027,RA-028,RA-029,RA-030,RA-031,RA-032,RA-033;Dambam:RA-034,RA-035,RA-036,RA-037,RA-038,RA-039,RA-040,RA-041,RA-042,RA-043;Darazo:RA-044,RA-045,RA-046,RA-047,RA-048,RA-049,RA-050,RA-051,RA-052,RA-053,RA-054;Dass:RA-055,RA-056,RA-057,RA-058,RA-059,RA-060,RA-061,RA-062,RA-063,RA-064;Gamawa:RA-065,RA-066,RA-067,RA-068,RA-069,RA-070,RA-071,RA-072,RA-073,RA-074,RA-075;Ganjuwa:RA-076,RA-077,RA-078,RA-079,RA-080,RA-081,RA-082,RA-083,RA-084,RA-085,RA-086;Giade:RA-087,RA-088,RA-089,RA-090,RA-091,RA-092,RA-093,RA-094,RA-095,RA-096;Itas-Gadau:RA-097,RA-098,RA-099,RA-100,RA-101,RA-102,RA-103,RA-104,RA-105,RA-106;Jamaare:RA-107,RA-108,RA-109,RA-110,RA-111,RA-112,RA-113,RA-114,RA-115,RA-116;Katagum:RA-117,RA-118,RA-119,RA-120,RA-121,RA-122,RA-123,RA-124,RA-125,RA-126,RA-127;Kirfi:RA-128,RA-129,RA-130,RA-131,RA-132,RA-133,RA-134,RA-135,RA-136,RA-137;Misau:RA-138,RA-139,RA-140,RA-141,RA-142,RA-143,RA-144,RA-145,RA-146,RA-147;Ningi:RA-148,RA-149,RA-150,RA-151,RA-152,RA-153,RA-154,RA-155,RA-156,RA-157,RA-158;Shira:RA-159,RA-160,RA-161,RA-162,RA-163,RA-164,RA-165,RA-166,RA-167,RA-168,RA-169;Tafawa-Balewa:RA-170,RA-171,RA-172,RA-173,RA-174,RA-175,RA-176,RA-177,RA-178,RA-179,RA-180;Toro:RA-181,RA-182,RA-183,RA-184,RA-185,RA-186,RA-187,RA-188,RA-189,RA-190,RA-191;Warji:RA-192,RA-193,RA-194,RA-195,RA-196,RA-197,RA-198,RA-199,RA-200,RA-201;Zaki:RA-202,RA-203,RA-204,RA-205,RA-206,RA-207,RA-208,RA-209,RA-210,RA-211,RA-212';

var ALLOWED_SECTORS = [
  'water', 'electricity', 'roads', 'healthcare', 'education',
  'jobs_agriculture', 'security', 'housing_environment', 'other'
];

var BAUCHI_LGAS = [
  'Alkaleri', 'Bauchi', 'Bogoro', 'Dambam', 'Darazo', 'Dass', 'Gamawa',
  'Ganjuwa', 'Giade', 'Itas-Gadau', 'Jamaare', 'Katagum', 'Kirfi', 'Misau',
  'Ningi', 'Shira', 'Tafawa-Balewa', 'Toro', 'Warji', 'Zaki'
];

var AGE_BANDS = [
  'age_18_25', 'age_26_35', 'age_36_45', 'age_46_55', 'age_56_65',
  'age_66_plus', 'age_unspecified'
];

var GENDER_OPTIONS = ['woman', 'man', 'gender_unspecified'];

/* Exact-age aliases. Refused BY NAME, because these are the keys someone would reach for
 * to defeat the band list. 'age' in particular is the trap: the form sends 'age_band'. */
var FORBIDDEN_IDENTITY_FIELDS = [
  'name', 'full_name', 'phone', 'phone_number', 'email', 'address', 'voter_id',
  'voterid', 'registered_voter_number', 'nin', 'bvn', 'date_of_birth', 'dob',
  'age', 'age_years', 'exact_age', 'years_old'
];

var ALLOWED_PAYLOAD_FIELDS = [
  'sector', 'lga', 'ward_code', 'comment', 'age_band', 'gender', 'consent',
  'website', 'submitted_at'
];

var MAX_LENGTHS = {
  sector: 32, lga: 80, ward_code: 40, comment: 300, age_band: 32, gender: 32
};

var MAX_SUBMITTED_AGE_MINUTES = 24 * 60;
var MAX_SUBMITTED_SKEW_MINUTES = 5;

var SHEET_NAME = 'Responses';
var AUDIT_SHEET_NAME = 'Audit';
var COMMENTS_SHEET_NAME = 'Comments';

var _wardMap = null;

/* ============================================================================
 * COMMENTS SHEET -- WHERE Q2 IS STORED, AND WHY IT IS A SEPARATE TAB
 * ============================================================================
 * The owner wants the complaints kept. They are the part of the poll no tally can
 * replace: a vote says a sector matters, a complaint says WHICH tap has been dry for
 * seven months, and only the second one tells the campaign what to actually do.
 *
 * So they are stored. The reason they are stored apart is that on a single row the free
 * text would sit beside the registration area, the age band and the gender -- and a
 * distinctive complaint plus an area plus two demographics is a person. The Responses row
 * already carries all three, so any row that holds the comment and that row together has
 * already re-identified the writer.
 *
 * This tab therefore carries ONLY: sector, lga, comment, received_at.
 *
 *   - No ward_code.  212 registration areas, and the form itself warns most will be
 *                    suppressed for small counts. Publishing or storing one area
 *                    alongside free text is the re-identification case exactly.
 *   - No age_band, no gender.  Both are answerable by anyone who knows the respondent.
 *   - No response_id.  This is the load-bearing omission. The tracking reference IS the
 *                    join key back to the Responses row that holds the area and the
 *                    demographics. Writing it next to the comment would let the two tabs
 *                    be re-joined by anyone who can read both, which would make this
 *                    split decorative. Without it the comment cannot be re-attached to its
 *                    vote even with full read access to both tabs.
 *
 * The cost is honest and worth stating: a comment cannot be tied back to its own vote.
 * That is the trade being made, and it is the right one -- the qualitative use is reading
 * what people said about a sector in an LGA, which needs none of the join key.
 *
 * ACCESS: restrict this tab to the owner and whoever curates the study. The Responses tab
 * can be shared more freely precisely because it holds no free text.
 */

/** Mirrors DEFAULT_COMMENT_RETENTION_DAYS in src/poll/validation.py. */
var COMMENT_RETENTION_DAYS = 180;

/** Mirrors MAX_COMMENT_RETENTION_DAYS. A comment older than this is deleted, not kept. */
var MAX_COMMENT_RETENTION_DAYS = 365;

/** Mirrors MIN_COMMENT_RETENTION_DAYS. 0 is refused: "delete on arrival" is not retention,
 *  and a 0-day setting that silently failed to delete would be a lie in the permissive
 *  direction. */
var MIN_COMMENT_RETENTION_DAYS = 1;

/* ------------------------------------------------------------------ helpers */

function jsonResponse_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function normalizeKey_(value) {
  return String(value).replace(/[\s ]+/g, ' ').trim().toLowerCase();
}

/** Control characters are rejected in every free-text field. Built with
 *  String.fromCharCode rather than a /[\\x00-\\x1f]/ literal, because a literal control
 *  byte in a source file survives copy-paste unpredictably and some editors silently drop
 *  it, which would turn this guard into a no-op that always passes. */
var CONTROL_CHARS = new RegExp(
  '[' + String.fromCharCode(0) + '-' + String.fromCharCode(31)
  + String.fromCharCode(127) + '-' + String.fromCharCode(159) + ']'
);

function hasControlCharacters_(value) {
  return CONTROL_CHARS.test(value);
}

function sheet_(name) {
  var book = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = book.getSheetByName(name);
  if (!sheet) {
    throw new Error('missing_sheet:' + name);
  }
  return sheet;
}

function wardMap_() {
  if (_wardMap !== null) { return _wardMap; }
  var map = {};
  var groups = String(WARD_MAP_SOURCE).split(';');
  for (var i = 0; i < groups.length; i++) {
    var parts = groups[i].split(':');
    if (parts.length !== 2) { continue; }
    var lga = parts[0];
    var codes = parts[1] ? parts[1].split(',') : [];
    map[normalizeKey_(lga)] = codes;
  }
  _wardMap = map;
  return map;
}

/* ------------------------------------------------------------- validation */

/** Throw a rejection carrying a stable code. The code never contains the submitted
 *  value, so it is safe to log and safe to return. */
function reject_(code, field) {
  var error = new Error(code + (field ? ':' + field : ''));
  error.rejectionCode = code;
  error.rejectionField = field || null;
  throw error;
}

function requireText_(value, field, required) {
  var max = MAX_LENGTHS[field];
  if (max === undefined) { reject_('unsupported_validation_field', field); }
  if (value === null || value === undefined) {
    if (required) { reject_('required', field); }
    return '';
  }
  if (typeof value !== 'string') { reject_('invalid_type', field); }
  if (hasControlCharacters_(value)) { reject_('control_character_rejected', field); }
  var cleaned = value.trim();
  if (required && !cleaned) { reject_('required', field); }
  if (cleaned.length > max) { reject_('too_long', field); }
  return cleaned;
}

function validateSector_(value) {
  var cleaned = requireText_(value, 'sector', true).toLowerCase();
  if (ALLOWED_SECTORS.indexOf(cleaned) === -1) {
    reject_('invalid_sector', 'sector');
  }
  return cleaned;
}

function validateLga_(value) {
  var cleaned = requireText_(value, 'lga', true);
  var key = normalizeKey_(cleaned);
  for (var i = 0; i < BAUCHI_LGAS.length; i++) {
    if (normalizeKey_(BAUCHI_LGAS[i]) === key) {
      return BAUCHI_LGAS[i];           // return the configured spelling
    }
  }
  reject_('invalid_lga', 'lga');
}

/** The registration area must belong to the LGA the respondent actually selected.
 *  Accepting a ward from another LGA would misattribute a cell, which is a correctness
 *  bug as well as a privacy one. */
function validateWardCode_(value, lga) {
  var cleaned = requireText_(value, 'ward_code', false);
  if (!cleaned) { return ''; }        // optional, so declining is not an error
  var map = wardMap_();
  var codes = map[normalizeKey_(lga)];
  if (!codes || !codes.length) {
    reject_('ward_not_configured_for_lga', 'ward_code');
  }
  var key = normalizeKey_(cleaned);
  for (var i = 0; i < codes.length; i++) {
    if (normalizeKey_(codes[i]) === key) { return codes[i]; }
  }
  reject_('invalid_ward', 'ward_code');
}

/** A closed list, never free text. A decline is stored as '' so it is excluded from the
 *  demographic breakdowns rather than becoming a slice of its own.
 *
 *  The decline marker is namespaced (`age_unspecified`, `gender_unspecified`), so it is
 *  matched as a SUFFIX. This used to be a fixed-offset slice, which was wrong: the offset
 *  was computed against the bare word 'unspecified' while the values actually sent carry
 *  a prefix, so no decline ever matched. A respondent who chose "prefer not to say" was
 *  written to the Sheet as a demographic literally called "age_unspecified", and would
 *  have been published as its own slice in the snapshot. Matching on the literal prefix
 *  removes the arithmetic that was silently wrong. */
var DECLINE_SUFFIX = '_unspecified';

/** Mirrors validate_comment_retention_days in src/poll/validation.py.
 *
 *  A CEILING with a floor under it, and the direction is the point: holding someone's
 *  free text gets riskier the longer it is held, so the value that must be REFUSED is
 *  the large one. This exists so "keep it forever" cannot be reached by editing one
 *  number. */
function validateRetentionDays_(value) {
  if (typeof value !== 'number' || isNaN(value) || Math.floor(value) !== value) {
    reject_('invalid_comment_retention_days', 'comment_retention_days');
  }
  if (value < MIN_COMMENT_RETENTION_DAYS || value > MAX_COMMENT_RETENTION_DAYS) {
    reject_('invalid_comment_retention_days', 'comment_retention_days');
  }
  return value;
}

function validateClosedChoice_(value, allowed, field) {
  if (value === null || value === undefined) { return ''; }
  if (typeof value !== 'string') { reject_('invalid_type', field); }
  if (hasControlCharacters_(value)) { reject_('control_character_rejected', field); }
  var cleaned = value.trim();
  if (!cleaned) { return ''; }
  if (cleaned.length > MAX_LENGTHS[field]) { reject_('too_long', field); }
  var normalized = cleaned.toLowerCase();
  if (allowed.indexOf(normalized) === -1) { reject_('invalid_choice', field); }
  if (normalized === 'unspecified'
      || normalized.slice(-DECLINE_SUFFIX.length) === DECLINE_SUFFIX) {
    return '';
  }
  return normalized;
}

/* --------------------------------------------------------- reference allocation */

/** A tracking reference for one response. NOT a voter ID, and never described as one.
 *
 *  Sequential, never derived from the response content. A content hash is a stable
 *  fingerprint: anyone who can guess someone's comment can confirm it by hash, which
 *  defeats the anonymity the whole design rests on.
 *
 *  The sequence lives in Script Properties, not in the Sheet, so it cannot be edited by
 *  hand or reset by deleting a row. */
var SEQUENCE_KEY = 'apm_poll_sequence_' + SpreadsheetApp.getActiveSpreadsheet().getId();
var YEAR_KEY = 'apm_poll_sequence_year_' + SpreadsheetApp.getActiveSpreadsheet().getId();

function nextResponseId_() {
  var props = PropertiesService.getScriptProperties();
  var year = new Date().getFullYear();
  var storedYear = props.getProperty(YEAR_KEY);
  var next;
  if (storedYear !== String(year)) {
    next = 1;                          // a new year restarts the sequence
    props.setProperty(YEAR_KEY, String(year));
  } else {
    var current = parseInt(props.getProperty(SEQUENCE_KEY) || '0', 10);
    next = current + 1;
  }
  props.setProperty(SEQUENCE_KEY, String(next));
  return 'APM-POLL-' + year + '-' + ('000000' + next).slice(-6);
}

/* ------------------------------------------------------------------- intake */

function doPost(e) {
  var receivedAt = new Date();
  var payload = null;

  try {
    payload = parseBody_(e);
    // The validated record, NOT the raw payload. validate_ returns a new normalised
    // object -- canonical LGA spelling, declines collapsed to '', trimmed and
    // length-capped text -- and persisting `payload` instead would throw all of that away
    // and write whatever the client sent. That bug stored "bAUcHi" as the LGA and
    // "age_unspecified" as a demographic, and wrote `undefined` for every absent optional
    // field. The harness caught it; a visual read of this file would not have.
    var record = validate_(payload, receivedAt);
    var responseId = nextResponseId_();
    persist_(responseId, record, receivedAt);
    persistComment_(record, receivedAt);
    return jsonResponse_({ response_id: responseId });
  } catch (error) {
    // Log the CODE only. Never the payload, never the comment, never the submitted value.
    audit_(receivedAt, 'rejected', error.rejectionCode || 'invalid_record');
    return jsonResponse_({ error: error.rejectionCode || 'rejected' });
  }
}

function parseBody_(e) {
  if (!e || !e.postData || !e.postData.contents) {
    reject_('empty_request');
  }
  var raw = e.postData.contents;
  if (raw.length > 4096) { reject_('payload_too_large'); }
  try {
    return JSON.parse(raw);
  } catch (parseError) {
    reject_('invalid_json');
  }
}

/** The whole contract, in the order that produces the clearest rejection code. */
function validate_(payload, now) {
  if (payload === null || typeof payload !== 'object' || Array.isArray(payload)) {
    reject_('invalid_payload');
  }

  // Identity fields first, and by name, so a misconfigured form fails legibly instead of
  // looking like a typo.
  for (var f = 0; f < FORBIDDEN_IDENTITY_FIELDS.length; f++) {
    var forbidden = FORBIDDEN_IDENTITY_FIELDS[f];
    if (Object.prototype.hasOwnProperty.call(payload, forbidden)) {
      reject_('identity_field_forbidden', forbidden);
    }
  }

  var keys = Object.keys(payload);
  for (var k = 0; k < keys.length; k++) {
    if (ALLOWED_PAYLOAD_FIELDS.indexOf(keys[k]) === -1) {
      reject_('unsupported_field');
    }
  }

  if (Object.prototype.hasOwnProperty.call(payload, 'website')) {
    var honeypot = payload.website;
    if (!(typeof honeypot === 'string' && honeypot.trim() === '')) {
      reject_('honeypot_rejected', 'website');
    }
  }

  if (!Object.prototype.hasOwnProperty.call(payload, 'consent')) {
    reject_('consent_required', 'consent');
  }
  // The JSON boolean true and nothing else. "true", 1 and "yes" are not consent.
  if (payload.consent !== true) {
    reject_('consent_required', 'consent');
  }

  var sector = validateSector_(payload.sector);
  var lga = validateLga_(payload.lga);
  var wardCode = validateWardCode_(payload.ward_code, lga);
  var comment = requireText_(payload.comment, 'comment', false);
  var ageBand = validateClosedChoice_(payload.age_band, AGE_BANDS, 'age_band');
  var gender = validateClosedChoice_(payload.gender, GENDER_OPTIONS, 'gender');

  if (Object.prototype.hasOwnProperty.call(payload, 'submitted_at')) {
    var submitted = parseSubmittedAt_(payload.submitted_at, now);
    return {
      sector: sector, lga: lga, ward_code: wardCode, comment: comment,
      age_band: ageBand, gender: gender, submitted_at: submitted
    };
  }

  return {
    sector: sector, lga: lga, ward_code: wardCode, comment: comment,
    age_band: ageBand, gender: gender, submitted_at: ''
  };
}

function parseSubmittedAt_(value, now) {
  if (typeof value !== 'string' || !value.trim() || value.length > 64) {
    reject_('invalid_submitted_at', 'submitted_at');
  }
  var parsed = new Date(value);
  if (isNaN(parsed.getTime())) {
    reject_('invalid_submitted_at', 'submitted_at');
  }
  var nowMs = now.getTime();
  var submittedMs = parsed.getTime();
  if (submittedMs < nowMs - (MAX_SUBMITTED_AGE_MINUTES * 60 * 1000)) {
    reject_('submitted_at_too_old', 'submitted_at');
  }
  if (submittedMs > nowMs + (MAX_SUBMITTED_SKEW_MINUTES * 60 * 1000)) {
    reject_('submitted_at_in_future', 'submitted_at');
  }
  return value;
}

/* ------------------------------------------------------------------ storage */

/* Column order, asserted by index in test_endpoint.mjs:
 *   0 response_id  1 received_at  2 sector  3 lga  4 ward_code  5 age_band  6 gender
 *   7 consent      8 validation_status
 *
 * There is no comment column here, and that is the change. The comment moved to its own
 * tab because a row carrying free text AND a registration area AND two demographics is
 * closer to a person than any single field on it. See the COMMENTS SHEET block above. */
function persist_(responseId, record, receivedAt) {
  var sheet = sheet_(SHEET_NAME);
  // One append, one row, positional. appendRow is atomic enough here and avoids the
  // read-modify-write race of getRange/setValues under concurrency.
  sheet.appendRow([
    responseId,
    formatTimestamp_(receivedAt),
    record.sector,
    record.lga,
    record.ward_code,
    record.age_band,
    record.gender,
    true,
    'accepted'
  ]);
  audit_(receivedAt, 'accepted', '');
}

function formatTimestamp_(when) {
  return Utilities.formatDate(
    when, Session.getScriptTimeZone(), "yyyy-MM-dd'T'HH:mm:ss'Z'");
}

/** Store Q2 on its own tab, stripped to sector, lga, comment and received_at.
 *
 *  Mirrors src/poll/validation.py::comment_record. The four fields are written
 *  positionally, and test_endpoint.mjs asserts both what is present and what is absent --
 *  a sixth column appearing here would be invisible in a visual read of this file.
 *
 *  A vote with no comment writes no row. There is nothing to study, and an empty row per
 *  vote would inflate the Comments tab into a second copy of the vote count.
 *
 *  The write MUST NOT be allowed to fail the request. The vote is already recorded in
 *  Responses by this point, and telling a respondent their vote was rejected because a
 *  sidecar write failed would lose the vote and teach them to retry -- which is how you
 *  get duplicate votes. So a failure is swallowed here, exactly as an audit-write failure
 *  is, and recorded as a code. */
function persistComment_(record, receivedAt) {
  var comment = record.comment;
  if (!comment) { return; }
  try {
    sheet_(COMMENTS_SHEET_NAME).appendRow([
      record.sector,
      record.lga,
      formatTimestamp_(receivedAt),
      comment
    ]);
  } catch (writeError) {
    // Never let a sidecar-write failure turn an accepted vote into a rejected response.
    // No comment value, no payload, nothing identifying -- only the fact that it failed.
    audit_(receivedAt, 'comment_write_failed', 'comment_sidecar_failed');
  }
}

/** Delete comments older than the retention ceiling. Run daily by installRetention_.
 *
 *  This is the function that makes keeping the comments defensible. Without it,
 *  "retained for 180 days" is a sentence in a document; with it, the sheet cannot keep
 *  growing past it whether or not anyone remembers.
 *
 *  It deletes the free text and keeps the rest of the row. The sector, LGA and timestamp
 *  are not identifying on their own -- they are the same fields the published snapshot
 *  already aggregates and suppresses -- so keeping them preserves the shape of the study
 *  (how many complaints, about what, where, over time) without retaining the words.
 *
 *  Deliberately NOT deleting the whole row: an empty comment cell is the audit trail that
 *  the retention policy ran and applied, which is worth more than the row's own contents.
 */
function purgeExpiredComments() {
  var retention = validateRetentionDays_(COMMENT_RETENTION_DAYS);
  var sheet = sheet_(COMMENTS_SHEET_NAME);
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) { return 'purge: no comments to review'; }

  var cutoff = new Date(new Date().getTime() - (retention * 24 * 60 * 60 * 1000));
  var range = sheet.getRange(2, 1, lastRow - 1, sheet.getLastColumn());
  var values = range.getValues();
  var cleared = 0;
  var kept = 0;

  for (var r = 0; r < values.length; r++) {
    var stamp = values[r][2];
    var text = values[r][3];
    if (!text) { continue; }               // already purged
    var parsed = new Date(stamp);
    if (isNaN(parsed.getTime())) {
      // An unparseable timestamp is the one case that cannot be argued about: we cannot
      // prove it is inside the window, so it goes. Keeping it would be the permissive
      // reading of an unknown.
      values[r][3] = '';
      cleared++;
      continue;
    }
    if (parsed.getTime() < cutoff.getTime()) {
      values[r][3] = '';
      cleared++;
    } else {
      kept++;
    }
  }

  if (cleared) { range.setValues(values); }
  return 'purge: ' + cleared + ' comment(s) expired, ' + kept + ' retained';
}

/** Install the daily purge. Idempotent -- safe to re-run; it never doubles the trigger. */
function installRetention() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === 'purgeExpiredComments') {
      return 'retention already installed: ' + COMMENT_RETENTION_DAYS + ' day(s)';
    }
  }
  ScriptApp.newTrigger('purgeExpiredComments').timeBased().everyDays(1).create();
  return 'retention installed: daily purge at ' + COMMENT_RETENTION_DAYS + ' day(s)';
}

/** Non-identifying operational fields only. No payload, no comment, no ward. */
function audit_(receivedAt, status, code) {
  try {
    sheet_(AUDIT_SHEET_NAME).appendRow([
      formatTimestamp_(receivedAt),
      status,
      code
    ]);
  } catch (writeError) {
    // Never let an audit-write failure turn a rejected request into a 500 that leaks.
  }
}

/* --------------------------------------------------------------------- setup */

/** Run ONCE from the editor to create all three tabs with their exact columns.
 *  This is deliberately not automatic: an endpoint must never create schema on a request. */
function setupSheets() {
  var retention = validateRetentionDays_(COMMENT_RETENTION_DAYS);
  var book = SpreadsheetApp.getActiveSpreadsheet();
  var responses = book.getSheetByName(SHEET_NAME);
  if (!responses) {
    responses = book.insertSheet(SHEET_NAME);
    // response_id, received_at, sector, lga, ward_code, age_band, gender,
    // consent, validation_status
    // NOTE: no comment column. It moved to the Comments tab -- see the block above.
    responses.appendRow(['response_id', 'received_at', 'sector', 'lga', 'ward_code',
                         'age_band', 'gender', 'consent', 'validation_status']);
  }
  var audit = book.getSheetByName(AUDIT_SHEET_NAME);
  if (!audit) {
    audit = book.insertSheet(AUDIT_SHEET_NAME);
    // received_at, validation_status, rejection_code
    audit.appendRow(['received_at', 'validation_status', 'rejection_code']);
  }
  var comments = book.getSheetByName(COMMENTS_SHEET_NAME);
  if (!comments) {
    comments = book.insertSheet(COMMENTS_SHEET_NAME);
    // sector, lga, received_at, comment -- and nothing else. Deliberately no ward_code,
    // no age_band, no gender and no response_id. The last one is the join key back to the
    // Responses row that HAS those, so shipping it here would undo the whole split.
    comments.appendRow(['sector', 'lga', 'received_at', 'comment']);
  }
  var retentionNote = book.getSheetByName('Retention');
  if (!retentionNote) {
    retentionNote = book.insertSheet('Retention');
    retentionNote.appendRow(['What', 'Value']);
    retentionNote.appendRow(['Comment retention (days)', String(retention)]);
    retentionNote.appendRow(['Hard ceiling (days)', String(MAX_COMMENT_RETENTION_DAYS)]);
    retentionNote.appendRow(['Automatic purge', 'daily, purgeExpiredComments']);
    retentionNote.appendRow(['What is purged', 'the free text only; sector, LGA and '
                             + 'received_at are kept']);
    retentionNote.appendRow(['Never stored with a comment',
                             'ward_code, age_band, gender, response_id']);
    retentionNote.appendRow(['Who may read this Sheet',
                             'owner + the study curator. Comments are free text.']);
    retentionNote.appendRow(['Also note',
                             'Google retains IP addresses in Apps Script execution logs '
                             + 'regardless of what this Sheet stores.']);
  }
  // A blunt but effective duplicate guard. The public form deliberately sends no
  // idempotency token, and the one-per-browser localStorage marker is trivially cleared,
  // so the SHEET is the record of what was actually cast.
  var rule = SpreadsheetApp.newConditionalFormatRule()
    .whenFormulaSatisfied('=COUNTIF($A$2:$A, A2) > 1')
    .setBackground('#f4cccc')
    .setRanges([responses.getRange('A2:A')])
    .build();
  responses.setConditionalFormatRules([rule]);
  return 'setup complete: ' + responses.getLastRow() + ' response row(s); '
    + COMMENTS_SHEET_NAME + ' holds comments for ' + retention + ' day(s). '
    + 'Now run installRetention once.';
}

/** Health check. Run it from the editor, or GET the /exec URL, to prove the deployment
 *  is alive and the ward map parsed. Returns no stored data. */
function doGet() {
  return jsonResponse_({
    status: 'ok',
    lgas: BAUCHI_LGAS.length,
    sectors: ALLOWED_SECTORS.length,
    wards: Object.keys(wardMap_()).length,
    responses_sheet: SHEET_NAME,
    audit_sheet: AUDIT_SHEET_NAME,
    comments_sheet: COMMENTS_SHEET_NAME,
    comment_retention_days: COMMENT_RETENTION_DAYS
  });
}
