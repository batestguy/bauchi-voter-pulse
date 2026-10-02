// Confirm the demo capture wrote nothing to the live Sheets.
//
// The recording must never press send. This is the check that the promise was kept:
// it reads the Responses, Comments and Audit tabs through a logged-in browser and
// reports the row count. Any non-zero count means a demo ballot or a rejected probe
// is sitting in a production Sheet.
//
// It reads the grid via select-all + copy rather than the CSV export endpoint.
// `/export` answers as an attachment, so an in-page fetch of it fails, and `gviz`
// refuses a private Sheet outright (`ACCESS_DENIED`) - both dead ends documented in
// HANDOFF §25a. Select-all and copy works, and writes nothing to the Sheet, which
// matters: §27 records a session where an automated click cleared A1.
//
// Usage:
//   brave.exe --remote-debugging-port=9222
//   node tools/check_no_submission.mjs

const SHEET = '1uvtVDggYj09jqmNMPwwgTIJkG4C9qbIuvh1zc58hlEM';
const TABS = ['Responses', 'Comments', 'Audit'];

class Session {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.pending = new Map();
    ws.addEventListener('message', (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && this.pending.has(m.id)) {
        const { resolve, reject } = this.pending.get(m.id);
        this.pending.delete(m.id);
        m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result);
      }
    });
  }
  static async attach(url) {
    const ws = new WebSocket(url);
    await new Promise((res, rej) => {
      ws.addEventListener('open', res, { once: true });
      ws.addEventListener('error', rej, { once: true });
    });
    return new Session(ws);
  }
  send(method, params = {}) {
    const id = ++this.id;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => this.pending.set(id, { resolve, reject }));
  }
  async eval(expression) {
    const r = await this.send('Runtime.evaluate', {
      expression, awaitPromise: true, returnByValue: true, userGesture: true,
    });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.text);
    return r.result.value;
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const version = await (await fetch('http://127.0.0.1:9222/json/version')).json();
const browser = await Session.attach(version.webSocketDebuggerUrl);
await browser.send('Browser.grantPermissions', {
  origin: 'https://docs.google.com',
  permissions: ['clipboardReadWrite', 'clipboardSanitizedWrite'],
});

const created = await (
  await fetch(`http://127.0.0.1:9222/json/new?${encodeURIComponent(`https://docs.google.com/spreadsheets/d/${SHEET}/edit`)}`, {
    method: 'PUT',
  })
).json();
const s = await Session.attach(created.webSocketDebuggerUrl);
await s.send('Page.enable');
await s.send('Runtime.enable');
await sleep(16000);

let bad = 0;
for (const name of TABS) {
  const picked = await s.eval(`
    (() => {
      const el = [...document.querySelectorAll('div.docs-sheet-tab')]
        .find(e => (e.innerText || '').trim() === ${JSON.stringify(name)});
      if (!el) return false;
      el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
      el.click();
      return true;
    })()
  `);
  if (!picked) {
    console.log(`${name.padEnd(10)} !! tab not found`);
    bad++;
    continue;
  }
  await sleep(4000);

  // Single click in the grid only. A double click opens the cell editor.
  const grid = JSON.parse(
    await s.eval(`
      (() => {
        const r = (document.querySelector('.grid-container') || document.body).getBoundingClientRect();
        return JSON.stringify({ x: Math.round(r.x + 200), y: Math.round(r.y + 150) });
      })()
    `),
  );
  for (const type of ['mousePressed', 'mouseReleased']) {
    await s.send('Input.dispatchMouseEvent', {
      type, x: grid.x, y: grid.y, button: 'left', clickCount: 1,
      buttons: type === 'mousePressed' ? 1 : 0,
    });
  }
  await sleep(1000);
  for (const [key, code, vk] of [['a', 'KeyA', 65], ['c', 'KeyC', 67]]) {
    for (const type of ['keyDown', 'keyUp']) {
      await s.send('Input.dispatchKeyEvent', {
        type, key, code, windowsVirtualKeyCode: vk, nativeVirtualKeyCode: vk, modifiers: 2,
      });
      await sleep(150);
    }
  }
  await sleep(2500);

  const clip = await s.eval('navigator.clipboard.readText().catch(e => "ERR " + e)');
  const lines = String(clip).replace(/\r\n/g, '\n').split('\n').filter((l) => l.trim() !== '');
  const dataRows = Math.max(0, lines.length - 1);
  console.log(`${name.padEnd(10)} header   : ${lines[0] ?? '(none)'}`);
  console.log(`${''.padEnd(10)} data rows: ${dataRows}`);
  if (dataRows !== 0) {
    bad++;
    console.log(`${''.padEnd(10)} !! present:`);
    for (const l of lines.slice(1, 5)) console.log(`${''.padEnd(12)}${l}`);
  }
}

console.log(
  bad === 0
    ? '\nPASS: the capture submitted nothing. All three tabs hold headers only.'
    : `\nFAIL: ${bad} tab(s) have rows. Something reached a production Sheet.`,
);
await fetch(`http://127.0.0.1:9222/json/close/${created.id}`);
s.ws.close();
browser.ws.close();
process.exitCode = bad === 0 ? 0 : 1;