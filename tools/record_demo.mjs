// Demo capture for the live site. Two takes: 16:9 desktop and a 9:16 phone frame.
//
// Usage:
//   set NODE_PATH=%LOCALAPPDATA%\npm-cache\_npx\9833c18b2d85bc59\node_modules
//   node tools/record_demo.mjs [desktop|phone]
//
// The site is recorded as published. Nothing is submitted: the vote button is
// shown and never pressed, because a demo ballot would write a real row into the
// live Responses Sheet, and deleting it afterwards would still leave it in Sheet
// version history.
//
// A mark is written at the moment the frame changes, not after it has settled.
//
// That distinction is the whole reason this script logs what it logs. Marking a
// shot *after* its hold made every caption land one hold late - roughly a second
// and a half behind the picture - and it was invisible in a contact sheet full of
// captions that all looked plausible. `cut()` is called the instant the new state
// is on screen; the hold that follows is the shot's duration.

import { mkdirSync, writeFileSync, readdirSync } from 'node:fs';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const SITE = 'https://batestguy.github.io/bauchi-voter-pulse';
const OUT = 'build/demo';
const which = process.argv[2] ?? 'desktop';

const TAKES = {
  desktop: { viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1, isMobile: false },
  phone: { viewport: { width: 430, height: 932 }, deviceScaleFactor: 2, isMobile: true },
};

mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });
const context = await browser.newContext({
  ...TAKES[which],
  recordVideo: { dir: `${OUT}/raw-${which}`, size: TAKES[which].viewport },
  reducedMotion: 'reduce',
  locale: 'en-GB',
});
const page = await context.newPage();

const t0 = Date.now();
const marks = [];
/** Log a cut: the frame changed to `label` at this instant. */
function cut(label, note = '', holdMs = 2000) {
  const at = +((Date.now() - t0) / 1000).toFixed(2);
  marks.push({ label, at, note });
  console.log(`${String(at).padStart(6)}s  ${label}${note ? '  — ' + note : ''}  (+${holdMs}ms)`);
  return page.waitForTimeout(holdMs);
}

// Wait for the images that are actually on screen. Capped, because the atlas
// carries sprites that never all report complete and an unbounded wait turned a
// 45-second take into two minutes. If it gives up, it says which image.
async function imagesReady() {
  try {
    await page.waitForFunction(
      () => {
        const inView = [...document.images].filter((i) => {
          const r = i.getBoundingClientRect();
          return r.bottom > 0 && r.top < innerHeight;
        });
        return inView.length > 0 && inView.every((i) => i.complete && i.naturalWidth > 0);
      },
      null,
      { timeout: 8000, polling: 150 },
    );
  } catch {
    const stuck = await page.evaluate(() =>
      [...document.images]
        .filter((i) => !(i.complete && i.naturalWidth > 0))
        .map((i) => i.currentSrc || i.src),
    );
    if (stuck.length) console.warn(`  (still loading after 8s: ${stuck.join(', ')})`);
  }
}

async function go(path) {
  await page.goto(`${SITE}${path}`, { waitUntil: 'commit', timeout: 90000 });
  await page.waitForLoadState('domcontentloaded', { timeout: 30000 }).catch(() => {});
  await imagesReady();
}

async function scrollTo(sel, offset = 60) {
  await page.evaluate(
    ([s, off]) => {
      const el = document.querySelector(s);
      if (!el) throw new Error(`no element for ${s}`);
      window.scrollTo({ top: window.scrollY + el.getBoundingClientRect().top - off, behavior: 'instant' });
    },
    [sel, offset],
  );
}

await go('/');
await cut('home hero', '', 1800);

await scrollTo('#progress', 40);
await cut('the delivery story', 'need to next result', 2600);

await go('/atlas.html');
await scrollTo('svg[role="group"]', 30);
await cut('atlas map', 'nothing selected', 1300);

const clicked = await page.evaluate(() => {
  const path = [...document.querySelectorAll('svg path')].find((p) =>
    /Bauchi/i.test(p.getAttribute('aria-label') || ''),
  );
  if (!path) return false;
  path.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  return true;
});
if (!clicked) throw new Error('could not find the Bauchi LGA path on the atlas');
await cut('atlas selected', 'Bauchi, evidence filled', 2600);

await go('/achievements.html');
await cut('achievements', '', 2600);

await go('/poll.html');
await scrollTo('#poll-sector', 330);
await page.selectOption('#poll-sector', { index: 1 });
await page.selectOption('#poll-lga', { index: 3 });
const wardState = await page.evaluate(() => {
  const w = document.querySelector('#poll-ward');
  const areas = [...w.options].filter((o) => o.value);
  return {
    enabled: !w.disabled,
    total: areas.length,
    // The list is narrowed by hiding, not by removing, so `length` is always 212.
    // The count that means something is how many are no longer hidden.
    offered: areas.filter((o) => !o.hidden).length,
    lga: document.querySelector('#poll-lga').selectedOptions[0].textContent.trim(),
  };
});
if (!wardState.enabled || wardState.offered === 0) {
  throw new Error('the registration-area list did not narrow after choosing an LGA');
}
await cut(
  'poll form',
  `${wardState.lga}: ${wardState.offered} of ${wardState.total} areas offered`,
  2600,
);

await page.evaluate(() => {
  const h = [...document.querySelectorAll('h2')].find((e) => /Sector priorities so far/i.test(e.textContent));
  if (h) window.scrollTo({ top: window.scrollY + h.getBoundingClientRect().top - 120, behavior: 'instant' });
});
await cut('poll dashboard', 'at zero', 3200);

await go('/index.html');
await cut('home returned', 'English', 1400);
await page.evaluate(() => {
  const btn = [...document.querySelectorAll('button, a')].find((b) => (b.textContent || '').trim() === 'HA');
  if (!btn) throw new Error('no Hausa toggle found');
  btn.click();
});
await cut('language switched', 'Hausa', 2200);

await page.setContent(
  `<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
     html,body{margin:0;height:100%}
     body{background:#0b1a2a;color:#f4efe6;font-family:'Segoe UI',system-ui,sans-serif;
          display:flex;align-items:center;justify-content:center;flex-direction:column;gap:20px;text-align:center;padding:40px}
     .eyebrow{letter-spacing:.26em;text-transform:uppercase;font-size:15px;color:#f0a500}
     h1{font-size:56px;margin:0;line-height:1.08;font-weight:600}
     .url{font-size:25px;color:#f0a500}
     .small{font-size:15px;line-height:1.65;color:#c9d3dd;max-width:940px}
   </style></head><body>
     <div class="eyebrow">APM Bauchi Progress &amp; Delivery</div>
     <h1>Bauchi&rsquo;s public record,<br>in one place.</h1>
     <div class="url">batestguy.github.io/bauchi-voter-pulse</div>
     <div class="small">Public-source campaign intelligence. Not private polling.<br>
       Hausa interface strings were AI-drafted, then reviewed by a native speaker.<br>
       Map boundaries: GRID3 / eHealth Africa, CC BY 4.0 &mdash; indicative, not gazetted.</div>
   </body></html>`,
  { waitUntil: 'load' },
);
await cut('end card', '', 2600);

await context.close();
await browser.close();

const webm = readdirSync(`${OUT}/raw-${which}`).find((f) => f.endsWith('.webm'));
writeFileSync(`${OUT}/shots-${which}.json`, JSON.stringify(marks, null, 2));
console.log(`\nraw video: ${OUT}/raw-${which}/${webm}`);
console.log(`shot log:  ${OUT}/shots-${which}.json`);