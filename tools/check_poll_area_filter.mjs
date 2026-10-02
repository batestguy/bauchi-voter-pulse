// Does the poll form actually narrow the registration-area list to the chosen LGA?
// The demo caption claims it does, so it gets checked rather than assumed.
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
await page.goto('https://batestguy.github.io/bauchi-voter-pulse/poll.html', { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(1500);

const before = await page.evaluate(() => {
  const w = document.querySelector('#poll-ward');
  return { selectDisabled: w.disabled, total: w.options.length };
});

await page.selectOption('#poll-lga', { index: 3 });
await page.waitForTimeout(600);
const chosen = await page.evaluate(() => document.querySelector('#poll-lga').selectedOptions[0].textContent.trim());

const after = await page.evaluate(() => {
  const w = document.querySelector('#poll-ward');
  const opts = [...w.options].filter((o) => o.value);
  return {
    selectDisabled: w.disabled,
    lga: document.querySelector('#poll-lga').selectedOptions[0].textContent.trim(),
    totalAreaOptions: opts.length,
    notDisabled: opts.filter((o) => !o.disabled).length,
    notHidden: opts.filter((o) => !o.hidden).length,
    visible: opts.filter((o) => o.offsetParent !== null).length,
    firstFew: opts.slice(0, 3).map((o) => [o.textContent.trim(), o.dataset.pollRaLga, o.disabled]),
    matchingLga: opts.filter((o) => o.dataset.pollRaLga === document.querySelector('#poll-lga').value).length,
    matchingLgaByName: opts.filter((o) => o.dataset.pollRaLga === document.querySelector('#poll-lga').selectedOptions[0].textContent.trim()).length,
  };
});

console.log('chosen LGA option text:', JSON.stringify(chosen));
console.log('before:', JSON.stringify(before));
console.log('after :', JSON.stringify(after, null, 2));
await browser.close();