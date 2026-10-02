// Print an HTML file to PDF with installed Chrome, keeping hyperlinks alive.
//
// Usage:
//   set NODE_PATH=%LOCALAPPDATA%\npm-cache\_npx\9833c18b2d85bc59\node_modules
//   node tools/print_pdf.mjs <input.html> <output.pdf> [links.json]
//
// Why this exists rather than a `python -m` PDF library: the brief is only
// interactive if the QR codes, the page-to-page jumps in the footer, and every
// `Open the live site` link survive as real PDF link annotations. A library that
// draws boxes produces a flat document that looks interactive and is not.
//
// Why the third argument exists: Chrome's print-to-PDF keeps external hrefs but
// silently DROPS fragment-only links, so the page-to-page navigation measured
// 29 dead rectangles out of 44 links -- a document that looks clickable and is
// not. Those are measured here and written back as real /Dest annotations by
// make_brief.py. Verified by re-reading the finished file: every link must carry
// an action, or the build fails.
//
// A4 with zero margin is deliberate: the stylesheet owns the margins as real
// padding, so a page cannot gain a second sheet from a printer's default margin.

import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { createRequire } from "node:module";

// Playwright is resolved through NODE_PATH from the npx cache, exactly as
// tools/record_demo.mjs does it. An ESM `import` would not honour NODE_PATH, so
// the CommonJS resolver is used deliberately here.
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

// One A4 sheet at 96dpi. The viewport is pinned to this so that the measured
// geometry below is the print geometry: `margin: 0 auto` would otherwise centre
// the sheet in a wider viewport and every x would be wrong once printed.
const VIEWPORT = { width: 794, height: 1123 };
const SHEET_PX = 1122.52; // 297mm at 96dpi
const PT_PER_PX = 0.75; // 96dpi -> 72dpi

async function main() {
  const [, , input, output, linksOut] = process.argv;
  if (!input || !output) {
    console.error("usage: node tools/print_pdf.mjs <input.html> <output.pdf> [links.json]");
    process.exit(2);
  }

  const browser = await chromium.launch({ channel: "chrome" });
  try {
    const page = await browser.newPage({ viewport: VIEWPORT });
    await page.goto(pathToFileURL(path.resolve(input)).href, {
      waitUntil: "networkidle",
    });
    await page.emulateMedia({ media: "print" });

    // Fonts and images must be settled before measuring or printing, or a
    // fallback face is measured into the layout and the rects land on the wrong
    // text -- and a link rectangle over the wrong text is worse than no link.
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(250);

    const internal = await page.evaluate((sheetPx) => {
      const sheets = [...document.querySelectorAll(".sheet")];
      return [...document.querySelectorAll('a[href^="#"]')]
        .map((a) => {
          const id = a.getAttribute("href").slice(1);
          const target = document.getElementById(id);
          const from = a.closest(".sheet");
          // The target must be a sheet, but it need not be the SAME sheet: a
          // cross-sheet jump is the whole point of the pager. An earlier version
          // of this check required containment and so silently measured only the
          // 5 self-links -- the 24 jumps it was written to protect went unverified.
          const toSheetNode = target && target.closest(".sheet");
          if (!from || !toSheetNode) return null;
          const r = a.getBoundingClientRect();
          const fromSheet = sheets.indexOf(from) + 1;
          return {
            href: a.getAttribute("href"),
            fromSheet,
            toSheet: sheets.indexOf(toSheetNode) + 1,
            top: r.y - (fromSheet - 1) * sheetPx,
            left: r.x,
            width: r.width,
            height: r.height,
          };
        })
        .filter(Boolean);
    }, SHEET_PX);

    if (linksOut) {
      fs.writeFileSync(path.resolve(linksOut), JSON.stringify(internal, null, 1));
      console.log(`measured ${internal.length} internal links`);
    }

    await page.pdf({
      path: path.resolve(output),
      format: "A4",
      printBackground: true,
      preferCSSPageSize: true,
      displayHeaderFooter: false,
      margin: { top: "0", right: "0", bottom: "0", left: "0" },
    });
    console.log(`wrote ${output}`);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});