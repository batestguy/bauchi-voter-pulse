/**
 * Run the REQUEST endpoint's validation against test payloads, with the Apps Script
 * globals stubbed out. This is not a simulation of the endpoint -- it loads the real
 * Code.gs and executes the real doPost, with only the platform objects faked.
 *
 * WHY THIS EXISTS, AND WHY IT MATTERS MORE HERE THAN FOR THE POLL
 * The endpoint is a paste-and-deploy step performed by the owner, on a Google account an
 * agent cannot reach. So for the poll it was "the one file nobody can execute"; for this
 * one it is worse. The request form stores a name, a phone number, an email address and a
 * street address. "It looked right when I read it" is not adequate evidence for the code
 * that decides what a member of the public can write into the campaign's private records,
 * and least of all for the code that decides what gets logged.
 *
 * It has already caught real defects: the generator once emitted an empty ward map, which
 * would have made every location unverifiable, and the audit path is asserted to be
 * incapable of holding a contact field at all.
 *
 * Usage:  node docs/requests-script/test_endpoint.mjs
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const here = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(join(here, "Code.gs"), "utf8");

/* --------------------------------------------------------------- stubs */

/* Grid-backed, not `getRange() -> {}`. A stub that returns nothing cannot show what was
 * written, and "what was written" is the entire question for a form that stores PII. */
function makeGrid(rows) {
  const grid = {
    rows,
    appendRow(row) { grid.rows.push(row); },
    getLastRow() { return grid.rows.length; },
    getLastColumn() { return grid.rows.length ? grid.rows[0].length : 0; },
    getRange(row, col, numRows, numCols) {
      const values = grid.rows.slice(row - 1, row - 1 + numRows)
        .map((r) => r.slice(col - 1, col - 1 + numCols));
      return {
        getValues: () => values.map((r) => [...r]),
        setValues: (next) => {
          for (let i = 0; i < next.length; i += 1) {
            grid.rows[row - 1 + i] = [...next[i]];
          }
        },
      };
    },
    setConditionalFormatRules() {},
  };
  return grid;
}

const appended = { requests: [], audit: [] };
const requestSheet = makeGrid(appended.requests);
const auditSheet = makeGrid(appended.audit);
const byName = { Requests: requestSheet, Audit: auditSheet };

const spreadsheets = {
  Sheets: {},
  getActiveSpreadsheet() {
    return {
      getId: () => "SHEET-ID-FOR-TESTS",
      getSheetByName(name) { return byName[name] || null; },
      insertSheet(name) {
        byName[name] = byName[name] || makeGrid([]);
        return byName[name];
      },
    };
  },
};

const properties = {};
const sandbox = {
  SpreadsheetApp: {
    ...spreadsheets,
    newConditionalFormatRule() {
      const rule = {
        whenFormulaSatisfied: () => rule,
        setBackground: () => rule,
        setRanges: () => rule,
        build: () => rule,
      };
      return rule;
    },
  },
  ContentService: {
    MimeType: { JSON: "application/json" },
    createTextOutput(body) {
      return { body, setMimeType() { return this; } };
    },
  },
  PropertiesService: {
    getScriptProperties() {
      return {
        getProperty: (k) => (k in properties ? properties[k] : null),
        setProperty: (k, v) => { properties[k] = v; },
      };
    },
  },
  Utilities: { formatDate: (d) => d.toISOString() },
  Session: { getScriptTimeZone: () => "Africa/Lagos" },
  console,
};
sandbox.globalThis = sandbox;

vm.createContext(sandbox);
vm.runInContext(source, sandbox, { filename: "Code.gs" });

/* --------------------------------------------------------------- helpers */

const post = (payload) => {
  appended.requests.length = 0;
  appended.audit.length = 0;
  const result = sandbox.doPost({ postData: { contents: JSON.stringify(payload) } });
  return {
    status: JSON.parse(result.body),
    requests: [...appended.requests],
    audit: [...appended.audit],
  };
};

const base = {
  lga: "Bauchi",
  ward_code: "RA-012",
  address: "Behind the old primary school, Tudu Wada",
  category: "water",
  details: "The borehole has not produced water for three weeks.",
  consent: true,
};

// Values that must never appear in any response or any audit row.
const SECRETS = {
  name: "Aminu Bala",
  phone: "08012345678",
  email: "aminu.bala@example.com",
  details: "The borehole has not produced water for three weeks.",
  address: "Behind the old primary school, Tudu Wada",
};

let passed = 0;
const failures = [];

function check(name, condition, detail) {
  if (condition) { passed++; return; }
  failures.push(`${name}${detail ? ` -- ${detail}` : ""}`);
}

function rejects(name, payload, code) {
  const r = post(payload);
  check(
    name,
    r.status.error === code && r.requests.length === 0,
    `expected ${code}, got ${JSON.stringify(r.status)}; `
    + `${r.requests.length} row(s) reached the Requests sheet`
  );
  // A rejection must leak nothing it was given.
  const echo = JSON.stringify(r.status) + JSON.stringify(r.audit);
  for (const [label, secret] of Object.entries(SECRETS)) {
    if (JSON.stringify(payload).includes(secret)) {
      check(`${name} [no leak: ${label}]`, !echo.includes(secret), echo);
    }
  }
}

function accepts(name, payload, extra = {}) {
  const r = post(payload);
  const id = r.status.request_id;
  check(
    name,
    /^APM-\d{4}-\d{4,12}$/.test(id || "") && r.requests.length === 1
      && r.status.error === undefined,
    `got ${JSON.stringify(r.status)}; ${r.requests.length} request row(s)`
  );
  for (const [index, value] of Object.entries(extra)) {
    check(
      `${name} [col ${index}]`,
      r.requests[0]?.[index] === value,
      `column ${index} was ${JSON.stringify(r.requests[0]?.[index])}, `
      + `expected ${JSON.stringify(value)}`
    );
  }
  // The response must never carry a stored field back to the browser.
  const body = JSON.stringify(r.status);
  for (const [label, secret] of Object.entries(SECRETS)) {
    check(`${name} [no echo: ${label}]`, !body.includes(secret), body);
  }
  return r;
}

/* ------------------------------------------------------------------ tests */

// Column order is asserted by index, from the header setupSheets() writes, which matches
// GOOGLE_SHEETS_SETUP.md section 1:
//  0 request_id  1 created_at  2 lga  3 ward_code  4 address  5 category  6 details
//  7 name  8 phone  9 email  10 consent  11 validation_status
// 12 validation_warnings  13 submitted_at
const REQUEST_ID = 0, CREATED_AT = 1, LGA = 2, WARD = 3, ADDRESS = 4, CATEGORY = 5;
const DETAILS = 6, NAME = 7, PHONE = 8, EMAIL = 9, CONSENT = 10, STATUS = 11;
const WARNINGS = 12, SUBMITTED_AT = 13;

accepts("minimal valid", { ...base }, {
  [LGA]: "Bauchi", [WARD]: "RA-012", [CATEGORY]: "water",
  [ADDRESS]: SECRETS.address, [DETAILS]: SECRETS.details,
  [NAME]: "", [PHONE]: "", [EMAIL]: "", [CONSENT]: true, [STATUS]: "validated",
});
accepts("full valid", {
  ...base, name: SECRETS.name, phone: SECRETS.phone, email: SECRETS.email,
}, {
  [NAME]: SECRETS.name, [PHONE]: SECRETS.phone, [EMAIL]: SECRETS.email,
});

// The row must be exactly 14 columns wide. A Sheet whose columns reshuffle silently is
// how a name ends up in the address column, so the width is asserted rather than assumed.
{
  const r = post({ ...base });
  check("the request row is exactly 14 columns", r.requests[0]?.length === 14,
    `${r.requests[0]?.length} columns`);
  check("a validated row carries no validation warning", r.requests[0]?.[WARNINGS] === "",
    JSON.stringify(r.requests[0]?.[WARNINGS]));
  check("a validated row is not marked ward_map_missing",
    r.requests[0]?.[STATUS] !== "ward_map_missing", String(r.requests[0]?.[STATUS]));
}

rejects("missing consent", { lga: base.lga, ward_code: base.ward_code,
  address: base.address, category: base.category, details: base.details }, "required");
rejects("consent as string", { ...base, consent: "true" }, "consent_required");
rejects("consent as 1", { ...base, consent: 1 }, "consent_required");
rejects("consent false", { ...base, consent: false }, "consent_required");
rejects("consent null", { ...base, consent: null }, "consent_required");

for (const field of ["lga", "ward_code", "address", "category", "details"]) {
  const payload = { ...base };
  delete payload[field];
  rejects(`missing required field: ${field}`, payload, "required");
}

rejects("unknown field", { ...base, nickname: "x" }, "unsupported_field");
// A client-chosen reference could collide with a real request, so it is refused by name
// rather than left to the generic unknown-field check.
rejects("client-supplied request_id", { ...base, request_id: "APM-2026-000001" },
  "unsupported_field");

rejects("bad category", { ...base, category: "aircraft" }, "invalid_category");
rejects("bad lga", { ...base, lga: "Kano" }, "invalid_lga");
accepts("lga matched case-insensitively", { ...base, lga: "bAUcHi" }, { [LGA]: "Bauchi" });
// The hyphen is significant: the contract collapses whitespace and case, not punctuation,
// so "tafawa balewa" is a different LGA and is refused rather than fuzzy-matched.
accepts("multi-word lga keeps its configured spelling",
  { ...base, lga: "tafawa-balewa", ward_code: "RA-170" },
  { [LGA]: "Tafawa-Balewa", [WARD]: "RA-170" });
rejects("lga without its hyphen is refused", { ...base, lga: "tafawa balewa", ward_code: "RA-170" },
  "invalid_lga");

rejects("ward not in map", { ...base, ward_code: "RA-999" }, "invalid_ward");
rejects("ward belongs to another lga", { ...base, ward_code: "RA-181" }, "invalid_ward");
accepts("ward in correct lga", { ...base, ward_code: "RA-012" }, { [WARD]: "RA-012" });

rejects("address too long", { ...base, address: "x".repeat(301) }, "too_long");
rejects("details too long", { ...base, details: "x".repeat(1001) }, "too_long");
rejects("name too long", { ...base, name: "x".repeat(121) }, "too_long");
accepts("details at cap", { ...base, details: "x".repeat(1000) });
rejects("control char in details", { ...base, details: "hello world" },
  "control_character_rejected");
rejects("control char in name", { ...base, name: "Aminu Bala" },
  "control_character_rejected");
accepts("control-char escape is not a control char", { ...base, name: "Aminu\\u0000" });

/* ---------------------------------------------- phone and email normalisation */

// These are the fields most likely to be mangled by a careless regex, and a mangled phone
// number means staff cannot call the person who reported the problem.
accepts("phone stripped of formatting", { ...base, phone: "080-1234-5678" },
  { [PHONE]: "08012345678" });
accepts("phone keeps a leading plus", { ...base, phone: "+234 801 234 5678" },
  { [PHONE]: "+2348012345678" });
// Brackets are permitted only INSIDE the number: the pattern requires a leading digit, so
// "(080) 1234 5678" is refused while "080 (1234) 5678" is accepted. That is the contract's
// behaviour and it is asserted rather than assumed.
accepts("phone with brackets inside the number", { ...base, phone: "080 (1234) 5678" },
  { [PHONE]: "08012345678" });
rejects("phone starting with a bracket", { ...base, phone: "(080) 1234 5678" },
  "invalid_phone");
rejects("phone too short", { ...base, phone: "12345" }, "invalid_phone");
rejects("phone too long", { ...base, phone: "1234567890123456" }, "invalid_phone");
rejects("unbalanced brackets in phone", { ...base, phone: "(080 1234 5678" }, "invalid_phone");
rejects("empty brackets in phone", { ...base, phone: "080()1234567" }, "invalid_phone");
rejects("letters in phone", { ...base, phone: "080-CALL-NOW" }, "invalid_phone");
accepts("blank phone is optional", { ...base, phone: "" }, { [PHONE]: "" });

// Only the DOMAIN is lowercased. The local part is case-sensitive per RFC, so rewriting
// it would change an address the respondent gave us.
accepts("email domain lowercased", { ...base, email: "Aminu.Bala@Example.COM" },
  { [EMAIL]: "Aminu.Bala@example.com" });
// The dot in the local part. This is the shape that used to be rejected outright.
accepts("email with a dotted local part", { ...base, email: "aminu.bala@example.com" },
  { [EMAIL]: "aminu.bala@example.com" });
accepts("email with a subdomains and a tag",
  { ...base, email: "first.last+tag@mail.example.co.uk" },
  { [EMAIL]: "first.last+tag@mail.example.co.uk" });
rejects("double dot in email", { ...base, email: "a..b@example.com" }, "invalid_email");
rejects("email local part starting with a dot", { ...base, email: ".aminu@example.com" },
  "invalid_email");
rejects("email local part ending with a dot", { ...base, email: "aminu.@example.com" },
  "invalid_email");
rejects("email without at", { ...base, email: "aminu.example.com" }, "invalid_email");
rejects("email without tld", { ...base, email: "aminu@example" }, "invalid_email");
rejects("email with no local part", { ...base, email: "@example.com" }, "invalid_email");
accepts("blank email is optional", { ...base, email: "" }, { [EMAIL]: "" });

rejects("honeypot filled", { ...base, website: "http://spam" }, "honeypot_rejected");
accepts("honeypot empty", { ...base, website: "" });

rejects("submitted_at in the past", {
  ...base, submitted_at: "2020-01-01T00:00:00Z",
}, "invalid_submitted_at");
rejects("submitted_at in the future", {
  ...base, submitted_at: "2099-01-01T00:00:00Z",
}, "invalid_submitted_at");
{
  // The endpoint persists the client's own clock reading, which the Python contract
  // validates and then drops. The Sheet has a column for it and it is the only way to
  // diagnose clock skew across respondents, so it is stored -- and the divergence is
  // asserted rather than left for someone to notice as a mismatch.
  const stamp = new Date().toISOString();
  accepts("submitted_at inside the window", { ...base, submitted_at: stamp },
    { [SUBMITTED_AT]: stamp });
}

/* ------------------------------------------------------------- the audit tab */

// The single most important property of this endpoint: the audit tab is three narrow
// columns and cannot hold a contact field, even on a rejection.
{
  const r = post({ ...base, name: SECRETS.name, phone: SECRETS.phone, email: SECRETS.email });
  check("an accepted request is audited", r.audit.length === 1 && r.audit[0][1] === "accepted",
    JSON.stringify(r.audit));
  check("an accepted audit row is exactly 3 columns", r.audit[0]?.length === 3,
    `${r.audit[0]?.length} columns`);
  check("an accepted audit row carries no rejection code", r.audit[0]?.[2] === "",
    JSON.stringify(r.audit[0]));
}
{
  const r = post({ ...base, name: SECRETS.name, phone: SECRETS.phone,
    email: SECRETS.email, category: "aircraft" });
  check("a rejected request is audited by code", r.audit.length === 1
    && r.audit[0][1] === "rejected" && r.audit[0][2] === "invalid_category",
  JSON.stringify(r.audit));
  const flat = JSON.stringify(r.audit);
  for (const [label, secret] of Object.entries(SECRETS)) {
    check(`the audit row never holds ${label}`, !flat.includes(secret), flat);
  }
  check("a rejection leaves no request row", r.requests.length === 0,
    JSON.stringify(r.requests));
}

/* -------------------------------------------------------- reference allocation */

// request_id is sequential, and never derived from the content. This matters MORE here
// than for the poll: a hash of a name and a phone number is a stable fingerprint.
{
  const first = post({ ...base, details: "same" }).status.request_id;
  const second = post({ ...base, details: "same" }).status.request_id;
  const third = post({ ...base, details: "different" }).status.request_id;
  check("identical content yields different ids", first !== second && second !== third,
    `${first}, ${second}, ${third}`);
  const year = new Date().getFullYear();
  // "APM-2026-000001" -> [APM, 2026, 000001], so the sequence is index 2.
  const seq = (id) => Number(id.split("-")[2]);
  check("ids are sequential", seq(second) === seq(first) + 1
    && seq(third) === seq(second) + 1,
  `${seq(first)}, ${seq(second)}, ${seq(third)}`);
  check("ids carry the current year", first.startsWith(`APM-${year}-`), first);
  check("id shape matches the contract", /^APM-\d{4}-\d{4,12}$/.test(first), first);
}

/* --------------------------------------------- a column can never be skipped */

// The strongest way to test the guard is to remove the value it protects. A sparse row
// still has length 14, so a count check alone would pass and the Sheet would end up with
// the email in the phone column and the address in the details column -- every value a
// string, nothing downstream able to tell.
{
  // Test the REAL writer against the exact defect, rather than a stand-in. Handing
  // persist_ a record whose name is absent is what a future edit to the field list would
  // actually do, and it is the shape the guard exists for: a sparse row still reports
  // length 14, so a count check alone passes and the Sheet receives a hole -- the email
  // landing in the phone column and the address in the details column, every value a
  // string and nothing downstream able to tell.
  appended.requests.length = 0;
  let code = "";
  try {
    sandbox.persist_("APM-2026-000001", {
      lga: "Bauchi", ward_code: "RA-012", address: SECRETS.address,
      category: "water", details: SECRETS.details,
      // name deliberately absent, phone and email present
      phone: SECRETS.phone, email: SECRETS.email, submitted_at: "",
    }, new Date());
  } catch (error) {
    code = error.message;
  }
  check("a record missing a column is refused by persist_",
    code.startsWith("internal_column_missing"), code || "no error raised");
  check("the refusal names the column", code.endsWith(":7"), code);
  check("a refused record writes no row", appended.requests.length === 0,
    JSON.stringify(appended.requests));

  // And the same record complete is written in full.
  sandbox.persist_("APM-2026-000002", {
    lga: "Bauchi", ward_code: "RA-012", address: SECRETS.address,
    category: "water", details: SECRETS.details,
    name: SECRETS.name, phone: SECRETS.phone, email: SECRETS.email, submitted_at: "",
  }, new Date());
  const gaps = appended.requests[0] || [];
  const holes = [];
  for (let c = 0; c < 14; c += 1) {
    if (!Object.prototype.hasOwnProperty.call(gaps, c) || gaps[c] === undefined) {
      holes.push(c);
    }
  }
  check("a complete record fills all 14 columns with no holes",
    holes.length === 0 && gaps.length === 14,
    `width ${gaps.length}, holes: ${holes.join(", ")}`);
}

/* ------------------------------------------------- the audit write never fails a request */

{
  // The audit write must not be able to turn a rejected request into a failure. The
  // respondent already sent their details; the response has to come back, and the vote
  // equivalent of this -- losing an accepted request because a sidecar write failed -- is
  // what the poll endpoint had to be fixed for.
  const realAppend = auditSheet.appendRow;
  auditSheet.appendRow = () => { throw new Error("audit unavailable"); };
  appended.audit.length = 0;
  let body = null;
  let threw = null;
  try {
    body = JSON.parse(sandbox.doPost({
      postData: { contents: JSON.stringify({ ...base, name: SECRETS.name, category: "aircraft" }) },
    }).body);
  } catch (error) {
    threw = error.message;
  }
  check("an audit failure does not throw out of the request", threw === null, String(threw));
  check("an audit failure still returns a stable rejection code",
    body?.error === "invalid_category", JSON.stringify(body));
  check("an audit failure leaks nothing", !JSON.stringify(body).includes(SECRETS.name),
    JSON.stringify(body));
  auditSheet.appendRow = realAppend;
}

/* --------------------------------------------------- the ward map is not optional */

// requireWardMap_() is the guard that makes the Python contract's `ward_map_missing`
// state unreachable from this endpoint. An incomplete map means the generator did not run.
{
  const map = sandbox.wardMap_();
  const total = Object.values(map).reduce((sum, codes) => sum + codes.length, 0);
  check("ward map is complete", total === 212 && Object.keys(map).length === 20,
    `${Object.keys(map).length} LGAs, ${total} areas`);
  check("the canonical lga list is complete", sandbox.CANONICAL_LGAS.length === 20,
    `${sandbox.CANONICAL_LGAS.length} LGAs`);
  // The list and the map are generated from one file, but they are two structures in one
  // generated file, and the symptom of disagreement is an LGA the form offers and the
  // endpoint refuses.
  const listed = new Set(sandbox.CANONICAL_LGAS.map((l) => String(l).toLowerCase()));
  const mapped = new Set(Object.keys(map));
  check("every mapped lga is in the canonical list",
    [...mapped].every((l) => listed.has(l)),
    [...mapped].filter((l) => !listed.has(l)).join(", "));
  check("every canonical lga has areas", [...listed].every((l) => mapped.has(l)),
    [...listed].filter((l) => !mapped.has(l)).join(", "));
}

{
  // An empty map must fail loudly rather than accept anything.
  const real = sandbox.WARD_MAP_SOURCE;
  try {
    sandbox.WARD_MAP_SOURCE = '';
    sandbox._wardMap = null;
    let code = '';
    try {
      sandbox.requireWardMap_();
    } catch (error) {
      code = error.message;
    }
    check("an empty ward map is refused loudly",
      code.startsWith("ward_map_incomplete"), code);
    // And the endpoint refuses rather than storing an unverifiable location.
    appended.requests.length = 0;
    const r = sandbox.doPost({ postData: { contents: JSON.stringify(base) } });
    check("an empty ward map stops the request",
      appended.requests.length === 0, JSON.stringify(appended.requests));
  } finally {
    sandbox.WARD_MAP_SOURCE = real;
    sandbox._wardMap = null;
  }
}

/* --------------------------------------------------------- the health check */

{
  const r = sandbox.doGet();
  const body = JSON.parse(r.body);
  check("doGet is a health check", body.status === "ok" && body.wards === 20,
    JSON.stringify(body));
  check("doGet reports the real area count", body.ward_areas === 212,
    String(body.ward_areas));
  check("doGet reports the column count", body.columns === 14, String(body.columns));
  check("doGet leaks no stored data",
    !("requests" in body) && !Object.keys(body).some((k) => SECRETS[k] !== undefined),
  JSON.stringify(body));
}

/* ----------------------------------------------------------------- report */

const total = passed + failures.length;
if (failures.length) {
  console.error(`FAILED ${failures.length} of ${total}\n`);
  for (const failure of failures) { console.error(`  FAIL  ${failure}`); }
  process.exit(1);
}
console.log(`request endpoint harness: ${passed}/${total} checks passed`);