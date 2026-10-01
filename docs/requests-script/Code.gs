/**
 * APM Bauchi public request intake -- Apps Script endpoint.
 *
 * PASTE THIS WHOLE FILE INTO YOUR SHEET'S BOUND SCRIPT, OR PUSH IT WITH CLASP.
 * See GOOGLE_SHEETS_SETUP.md in docs/ for the exact clicks. Nothing here works until it is
 * deployed and REQUEST_ENDPOINT in src/dashboard/render.py is set to the /exec URL.
 *
 * ============================================================================
 * WHY THIS FILE REPEATS EVERY RULE
 * ============================================================================
 * The browser sends JSON and anyone can send anything. This endpoint is the only
 * trustworthy boundary, so it re-implements every rule in src/requests/validation.py
 * rather than trusting the form. The pure Python module is the source of truth; this is a
 * mirror of it, and tests/test_request_endpoint.py asserts the two have not drifted.
 *
 * If you change a rule, change it in BOTH places or the test will fail.
 *
 * ============================================================================
 * THIS IS NOT THE POLL, AND THE DIFFERENCE IS THE WHOLE DESIGN
 * ============================================================================
 * The opinion poll stores no direct identity at all. This request form DOES: a name, a
 * phone number, an email address and a street address are the point of it. Staff have to
 * be able to find the place and reach the person.
 *
 * That makes this file the highest-risk thing in the repository, and the rules below
 * follow from that rather than from the poll's:
 *
 *  - Never log a name, phone, email, address, detail or payload. Log the rejection CODE
 *    and nothing else. The Audit tab has three columns and cannot hold a fourth.
 *  - Never return anything except { request_id }. Echoing a respondent's own phone number
 *    back into their browser is pointless and puts it in their history.
 *  - Never accept a request_id from the client. It is allocated here, sequentially, and
 *    never derived from the content: a hash of a name and a phone number is a stable
 *    fingerprint that anyone able to guess the person can confirm.
 *  - Do not widen sharing of this Sheet. It is private data with a retention obligation,
 *    unlike the poll's aggregate Sheet.
 *
 * Google retains IP addresses in Apps Script execution logs no matter what this Sheet
 * stores. That is a platform property, not something this code can remove.
 */

/** Registration areas per LGA, generated from data/delivery/lga_wards.csv.
 *  Compact form so the map is reviewable in one glance: "LGA:CODE,CODE;LGA:...".
 *  The same 212 provisional INEC registration areas the public form offers, so a
 *  respondent cannot select an area this endpoint then refuses. */
var WARD_MAP_SOURCE = 'Alkaleri:RA-001,RA-002,RA-003,RA-004,RA-005,RA-006,RA-007,RA-008,RA-009,RA-010,RA-011;Bauchi:RA-012,RA-013,RA-014,RA-015,RA-016,RA-017,RA-018,RA-019,RA-020,RA-021,RA-022,RA-023;Bogoro:RA-024,RA-025,RA-026,RA-027,RA-028,RA-029,RA-030,RA-031,RA-032,RA-033;Dambam:RA-034,RA-035,RA-036,RA-037,RA-038,RA-039,RA-040,RA-041,RA-042,RA-043;Darazo:RA-044,RA-045,RA-046,RA-047,RA-048,RA-049,RA-050,RA-051,RA-052,RA-053,RA-054;Dass:RA-055,RA-056,RA-057,RA-058,RA-059,RA-060,RA-061,RA-062,RA-063,RA-064;Gamawa:RA-065,RA-066,RA-067,RA-068,RA-069,RA-070,RA-071,RA-072,RA-073,RA-074,RA-075;Ganjuwa:RA-076,RA-077,RA-078,RA-079,RA-080,RA-081,RA-082,RA-083,RA-084,RA-085,RA-086;Giade:RA-087,RA-088,RA-089,RA-090,RA-091,RA-092,RA-093,RA-094,RA-095,RA-096;Itas-Gadau:RA-097,RA-098,RA-099,RA-100,RA-101,RA-102,RA-103,RA-104,RA-105,RA-106;Jamaare:RA-107,RA-108,RA-109,RA-110,RA-111,RA-112,RA-113,RA-114,RA-115,RA-116;Katagum:RA-117,RA-118,RA-119,RA-120,RA-121,RA-122,RA-123,RA-124,RA-125,RA-126,RA-127;Kirfi:RA-128,RA-129,RA-130,RA-131,RA-132,RA-133,RA-134,RA-135,RA-136,RA-137;Misau:RA-138,RA-139,RA-140,RA-141,RA-142,RA-143,RA-144,RA-145,RA-146,RA-147;Ningi:RA-148,RA-149,RA-150,RA-151,RA-152,RA-153,RA-154,RA-155,RA-156,RA-157,RA-158;Shira:RA-159,RA-160,RA-161,RA-162,RA-163,RA-164,RA-165,RA-166,RA-167,RA-168,RA-169;Tafawa-Balewa:RA-170,RA-171,RA-172,RA-173,RA-174,RA-175,RA-176,RA-177,RA-178,RA-179,RA-180;Toro:RA-181,RA-182,RA-183,RA-184,RA-185,RA-186,RA-187,RA-188,RA-189,RA-190,RA-191;Warji:RA-192,RA-193,RA-194,RA-195,RA-196,RA-197,RA-198,RA-199,RA-200,RA-201;Zaki:RA-202,RA-203,RA-204,RA-205,RA-206,RA-207,RA-208,RA-209,RA-210,RA-211,RA-212';

var ALLOWED_CATEGORIES = [
  'water', 'electricity', 'roads', 'healthcare', 'education',
  'jobs_agriculture', 'security', 'housing_environment', 'other'
];

var REQUIRED_FIELDS = [
  'lga', 'ward_code', 'address', 'category', 'details', 'consent'
];

/* Optional contact fields. Unlike the poll, storing these is the intended behaviour here,
 * so there is no forbidden-identity list: the list of what we REFUSE is the unknown-field
 * list, and the contract's allowed-field list is mirrored below. */
var OPTIONAL_PRIVATE_FIELDS = ['name', 'phone', 'email'];

var ALLOWED_PAYLOAD_FIELDS = [
  'lga', 'ward_code', 'address', 'category', 'details', 'consent',
  'name', 'phone', 'email', 'website', 'submitted_at'
];

var MAX_LENGTHS = {
  lga: 80, ward_code: 40, category: 32, address: 300, details: 1000,
  name: 120, phone: 40, email: 254
};

var MAX_SUBMITTED_AGE_MINUTES = 24 * 60;
var MAX_SUBMITTED_SKEW_MINUTES = 5;

var SHEET_NAME = 'Requests';
var AUDIT_SHEET_NAME = 'Audit';

/** Column order, asserted by index in test_endpoint.mjs. Matches GOOGLE_SHEETS_SETUP.md
 *  section 1 exactly, so the owner's hand-built Sheet and this writer cannot disagree:
 *   0 request_id 1 created_at 2 lga 3 ward_code 4 address 5 category 6 details
 *   7 name 8 phone 9 email 10 consent 11 validation_status 12 validation_warnings
 *   13 submitted_at */
var COLUMN_REQUEST_ID = 0;
var COLUMN_CREATED_AT = 1;
var COLUMN_LGA = 2;
var COLUMN_WARD_CODE = 3;
var COLUMN_ADDRESS = 4;
var COLUMN_CATEGORY = 5;
var COLUMN_DETAILS = 6;
var COLUMN_NAME = 7;
var COLUMN_PHONE = 8;
var COLUMN_EMAIL = 9;
var COLUMN_CONSENT = 10;
var COLUMN_VALIDATION_STATUS = 11;
var COLUMN_VALIDATION_WARNINGS = 12;
var COLUMN_SUBMITTED_AT = 13;
var COLUMN_COUNT = 14;

var _wardMap = null;

/* ------------------------------------------------------------------ helpers */

function jsonResponse_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function normalizeKey_(value) {
  return String(value).replace(/[\s ]+/g, ' ').trim().toLowerCase();
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

/** Fail loudly if the ward map is empty or incomplete.
 *
 *  src/requests/validation.py tolerates a missing map: it accepts the ward code as typed
 *  and marks the row `ward_map_missing` with a warning, on the understanding that an
 *  operator will notice. For an endpoint that warning would be invisible -- a respondent
 *  could send any ward code with any LGA and the Sheet would fill up with misattributed
 *  locations that still read as validated.
 *
 *  So the endpoint does not tolerate it. The map is generated into this file from
 *  lga_wards.csv, so an empty map means the generator did not run, and that must be a
 *  loud failure at the point where it matters rather than a silent warning nobody reads. */
function requireWardMap_() {
  var map = wardMap_();
  var lgas = Object.keys(map).length;
  var total = 0;
  for (var key in map) {
    if (Object.prototype.hasOwnProperty.call(map, key)) {
      total += map[key].length;
    }
  }
  if (lgas < 20 || total < 200) {
    throw new Error('ward_map_incomplete:' + lgas + '_lgas_' + total + '_areas');
  }
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

function validateCategory_(value) {
  var cleaned = requireText_(value, 'category', true).toLowerCase();
  if (ALLOWED_CATEGORIES.indexOf(cleaned) === -1) {
    reject_('invalid_category', 'category');
  }
  return cleaned;
}

function validateLga_(value) {
  var cleaned = requireText_(value, 'lga', true);
  var canonical = canonicalLgaName_(cleaned);
  if (canonical === null) { reject_('invalid_lga', 'lga'); }
  return canonical;
}

/** The 20 configured LGA names, in the spelling the rest of the site uses.
 *
 *  GENERATED from lga_wards.csv alongside the ward map, not hand-maintained. A second
 *  hand-typed list of the same 20 names would be free to drift from the map below it, and
 *  the symptom of that drift is subtle: an LGA the map knows and the list does not would
 *  be refused with `invalid_lga` on a form that offered it. */
var CANONICAL_LGAS = ["Alkaleri", "Bauchi", "Bogoro", "Dambam", "Darazo", "Dass", "Gamawa", "Ganjuwa", "Giade", "Itas-Gadau", "Jamaare", "Katagum", "Kirfi", "Misau", "Ningi", "Shira", "Tafawa-Balewa", "Toro", "Warji", "Zaki"];

function canonicalLgaName_(value) {
  var key = normalizeKey_(value);
  for (var i = 0; i < CANONICAL_LGAS.length; i++) {
    if (normalizeKey_(CANONICAL_LGAS[i]) === key) { return CANONICAL_LGAS[i]; }
  }
  return null;
}

/** The registration area must belong to the LGA the respondent actually selected.
 *  Accepting a ward from another LGA would misattribute a location, which for this form
 *  means sending staff to the wrong place -- a correctness bug as well as a privacy one. */
function validateWardCode_(value, lga) {
  var cleaned = requireText_(value, 'ward_code', true);
  var map = requireWardMap_();
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

var PHONE_SHAPE = new RegExp(
  '^\\+?[0-9](?:[0-9 ().-]*[0-9])?$'
);

function normalizePhone_(value) {
  var cleaned = requireText_(value, 'phone', false);
  if (!cleaned) { return ''; }
  if (!PHONE_SHAPE.test(cleaned)
      || cleaned.split('(').length !== cleaned.split(')').length
      || cleaned.indexOf('()') !== -1) {
    reject_('invalid_phone', 'phone');
  }
  var digits = cleaned.replace(/\D/g, '');
  if (digits.length < 7 || digits.length > 15) {
    reject_('invalid_phone', 'phone');
  }
  return cleaned.charAt(0) === '+' ? '+' + digits : digits;
}

/** The local part is a dot-atom and MAY contain dots, so "." is in this class and "-" is
 *  kept last so it stays a literal rather than a range. The class originally omitted ".",
 *  which rejected every address shaped `first.last@example.com`; the mirror in
 *  src/requests/validation.py carries the same note. */
var EMAIL_LOCAL = "[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+";
var EMAIL_LABEL = '[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?';
var EMAIL_SHAPE = new RegExp(
  '^' + EMAIL_LOCAL + '@' + EMAIL_LABEL + '(?:\\.' + EMAIL_LABEL + ')*\\.[A-Za-z]{2,63}$'
);

function normalizeEmail_(value) {
  var cleaned = requireText_(value, 'email', false);
  if (!cleaned) { return ''; }
  if (cleaned.indexOf('..') !== -1 || !EMAIL_SHAPE.test(cleaned)) {
    reject_('invalid_email', 'email');
  }
  var at = cleaned.lastIndexOf('@');
  var localPart = cleaned.slice(0, at);
  var domain = cleaned.slice(at + 1);
  // A dot-atom may not begin or end with a dot. The "no .." check above catches neither,
  // and the pattern cannot express both without also rejecting "..".
  if (localPart.charAt(0) === '.' || localPart.charAt(localPart.length - 1) === '.') {
    reject_('invalid_email', 'email');
  }
  if (localPart.length > 64) { reject_('invalid_email', 'email'); }
  var labels = domain.split('.');
  for (var i = 0; i < labels.length; i++) {
    if (labels[i].length > 63) { reject_('invalid_email', 'email'); }
  }
  // Only the domain is lowercased. The local part is case-sensitive per RFC and rewriting
  // it would change an address the respondent gave us.
  return localPart + '@' + domain.toLowerCase();
}

/* --------------------------------------------------------- reference allocation */

/** A tracking reference for one request. NOT a voter ID, and never described as one.
 *
 *  Sequential, never derived from the content. This matters MORE here than it does for the
 *  poll: a content hash of a name, a phone number and an address is a stable fingerprint
 *  that anyone who can guess the person can confirm, and the reference is returned to the
 *  respondent in their browser.
 *
 *  The sequence lives in Script Properties, not in the Sheet, so it cannot be edited by
 *  hand or reset by deleting a row. */
var SEQUENCE_KEY = 'apm_request_sequence_' + SpreadsheetApp.getActiveSpreadsheet().getId();
var YEAR_KEY = 'apm_request_sequence_year_' + SpreadsheetApp.getActiveSpreadsheet().getId();

function nextRequestId_() {
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
  return 'APM-' + year + '-' + ('000000' + next).slice(-6);
}

/* ------------------------------------------------------------------- intake */

function doPost(e) {
  var receivedAt = new Date();
  var payload = null;

  try {
    payload = parseBody_(e);
    // The validated record, NOT the raw payload. validate_ returns a new normalised
    // object -- canonical LGA spelling, a stripped phone, a lowercased email domain,
    // trimmed and length-capped text -- and persisting `payload` instead would throw all
    // of that away and write whatever the client sent.
    var record = validate_(payload, receivedAt);
    var requestId = nextRequestId_();
    persist_(requestId, record, receivedAt);
    return jsonResponse_({ request_id: requestId });
  } catch (error) {
    // Log the CODE only. Never the payload, never the name, phone, email, address or
    // details. The audit row is three narrow columns and cannot hold any of them.
    audit_(receivedAt, 'rejected', error.rejectionCode || 'invalid_record');
    return jsonResponse_({ error: error.rejectionCode || 'rejected' });
  }
}

function parseBody_(e) {
  if (!e || !e.postData || !e.postData.contents) {
    reject_('empty_request');
  }
  var raw = e.postData.contents;
  if (raw.length > 8192) { reject_('payload_too_large'); }
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

  var keys = Object.keys(payload);
  for (var k = 0; k < keys.length; k++) {
    if (ALLOWED_PAYLOAD_FIELDS.indexOf(keys[k]) === -1) {
      reject_('unsupported_field');
    }
  }
  // A client-supplied request_id would let anyone choose their own reference, including
  // one colliding with a real request. The contract's allowed-field list excludes it, so
  // it lands here as an unknown field rather than being quietly ignored.
  if (Object.prototype.hasOwnProperty.call(payload, 'request_id')) {
    reject_('unsupported_field');
  }

  if (Object.prototype.hasOwnProperty.call(payload, 'website')) {
    var honeypot = payload.website;
    if (!(typeof honeypot === 'string' && honeypot.trim() === '')) {
      reject_('honeypot_rejected', 'website');
    }
  }

  for (var r = 0; r < REQUIRED_FIELDS.length; r++) {
    if (!Object.prototype.hasOwnProperty.call(payload, REQUIRED_FIELDS[r])) {
      reject_('required', REQUIRED_FIELDS[r]);
    }
  }

  // The JSON boolean true and nothing else. "true", 1 and "yes" are not consent.
  if (payload.consent !== true) {
    reject_('consent_required', 'consent');
  }

  var lga = validateLga_(payload.lga);
  var wardCode = validateWardCode_(payload.ward_code, lga);
  var category = validateCategory_(payload.category);
  var address = requireText_(payload.address, 'address', true);
  var details = requireText_(payload.details, 'details', true);

  var name = requireText_(payload.name, 'name', false);
  var phone = normalizePhone_(payload.phone);
  var email = normalizeEmail_(payload.email);

  var submittedAt = '';
  if (Object.prototype.hasOwnProperty.call(payload, 'submitted_at')) {
    submittedAt = parseSubmittedAt_(payload.submitted_at, now);
  }

  return {
    lga: lga,
    ward_code: wardCode,
    address: address,
    category: category,
    details: details,
    name: name,
    phone: phone,
    email: email,
    submitted_at: submittedAt
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
    reject_('invalid_submitted_at', 'submitted_at');
  }
  if (submittedMs > nowMs + (MAX_SUBMITTED_SKEW_MINUTES * 60 * 1000)) {
    reject_('invalid_submitted_at', 'submitted_at');
  }
  return value;
}

/* ------------------------------------------------------------------ storage */

/** Write the validated record, column by column, in one append.
 *
 *  Positional rather than header-driven on purpose: an object built from the record and
 *  appended by key would quietly write a DIFFERENT COLUMN ORDER if a key were added or
 *  removed, and a Sheet whose columns silently reshuffle is how a name ends up in the
 *  wrong column and an address goes unread. The harness asserts the exact row width and
 *  the exact index of every column. */
function persist_(requestId, record, receivedAt) {
  var row = [];
  // `new Array(COLUMN_COUNT)` rather than `[]`. With a plain array, a column whose
  // assignment is deleted leaves a hole and `row.length` is still 14, so the count check
  // below cannot see it. Pre-sizing makes the same mistake produce a short row, which is
  // caught. The presence loop is kept anyway: both checks, because one of them failing to
  // fire is how a contact detail ends up in the wrong column.
  row = new Array(COLUMN_COUNT);
  row[COLUMN_REQUEST_ID] = requestId;
  row[COLUMN_CREATED_AT] = formatTimestamp_(receivedAt);
  row[COLUMN_LGA] = record.lga;
  row[COLUMN_WARD_CODE] = record.ward_code;
  row[COLUMN_ADDRESS] = record.address;
  row[COLUMN_CATEGORY] = record.category;
  row[COLUMN_DETAILS] = record.details;
  row[COLUMN_NAME] = record.name;
  row[COLUMN_PHONE] = record.phone;
  row[COLUMN_EMAIL] = record.email;
  row[COLUMN_CONSENT] = true;
  // The endpoint never writes `ward_map_missing`: requireWardMap_() has already refused
  // to run without a complete map, so a validated row is genuinely validated.
  row[COLUMN_VALIDATION_STATUS] = 'validated';
  row[COLUMN_VALIDATION_WARNINGS] = '';
  row[COLUMN_SUBMITTED_AT] = record.submitted_at;

  if (row.length !== COLUMN_COUNT) {
    reject_('internal_column_mismatch');
  }
  // A length check alone is not enough, and this is why. Assigning `row[7] = ''` for an
  // absent name still leaves `row.length === 14`, so a skipped column is a SPARSE array
  // that passes the count and then writes a hole into the Sheet -- which lands the email
  // in the phone column and the address in the details column. Nothing downstream would
  // notice: the row is the right length and every value is a string.
  //
  // So every column is checked for presence, not merely counted. A hole fails here rather
  // than becoming a misfiled contact detail that staff read as a phone number.
  for (var c = 0; c < COLUMN_COUNT; c++) {
    if (!Object.prototype.hasOwnProperty.call(row, c) || row[c] === undefined) {
      reject_('internal_column_missing:' + c);
    }
  }
  sheet_(SHEET_NAME).appendRow(row);
  audit_(receivedAt, 'accepted', '');
}

function formatTimestamp_(when) {
  return Utilities.formatDate(
    when, Session.getScriptTimeZone(), "yyyy-MM-dd'T'HH:mm:ss'Z'");
}

/** Non-identifying operational fields only. No payload, no name, no phone, no email, no
 *  address, no details, no ward. Three columns, and nothing can be added to them here. */
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

/** Run ONCE from the editor to create both tabs with their exact columns.
 *  This is deliberately not automatic: an endpoint must never create schema on a request. */
function setupSheets() {
  requireWardMap_();
  var book = SpreadsheetApp.getActiveSpreadsheet();
  var requests = book.getSheetByName(SHEET_NAME);
  if (!requests) {
    requests = book.insertSheet(SHEET_NAME);
    // request_id, created_at, lga, ward_code, address, category, details, name, phone,
    // email, consent, validation_status, validation_warnings, submitted_at
    requests.appendRow(['request_id', 'created_at', 'lga', 'ward_code', 'address',
                        'category', 'details', 'name', 'phone', 'email', 'consent',
                        'validation_status', 'validation_warnings', 'submitted_at']);
  }
  var audit = book.getSheetByName(AUDIT_SHEET_NAME);
  if (!audit) {
    audit = book.insertSheet(AUDIT_SHEET_NAME);
    // received_at, validation_status, rejection_code
    audit.appendRow(['received_at', 'validation_status', 'rejection_code']);
  }
  // A blunt but effective duplicate guard. The public form deliberately sends no
  // idempotency token, and the one-per-browser localStorage marker is trivially cleared,
  // so the SHEET is the record of what was actually submitted.
  var rule = SpreadsheetApp.newConditionalFormatRule()
    .whenFormulaSatisfied('=COUNTIF($A$2:$A, A2) > 1')
    .setBackground('#f4cccc')
    .setRanges([requests.getRange('A2:A')])
    .build();
  requests.setConditionalFormatRules([rule]);
  return 'setup complete: ' + requests.getLastRow() + ' request row(s)';
}

/** Health check. Run it from the editor, or GET the /exec URL, to prove the deployment is
 *  alive and the ward map parsed. Returns no stored data and no contact field. */
function doGet() {
  var map = requireWardMap_();
  var areas = 0;
  for (var key in map) {
    if (Object.prototype.hasOwnProperty.call(map, key)) { areas += map[key].length; }
  }
  return jsonResponse_({
    status: 'ok',
    categories: ALLOWED_CATEGORIES.length,
    lgas: CANONICAL_LGAS.length,
    wards: Object.keys(map).length,
    ward_areas: areas,
    columns: COLUMN_COUNT,
    requests_sheet: SHEET_NAME,
    audit_sheet: AUDIT_SHEET_NAME
  });
}