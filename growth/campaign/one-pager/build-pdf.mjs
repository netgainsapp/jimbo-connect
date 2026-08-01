// Render the one pager to PDF (US Letter) and a PNG proof for visual QA.
// Uses the puppeteer already installed for the marketing prerender:
//   node growth/campaign/one-pager/build-pdf.mjs   (from the repo root)
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";
import fs from "node:fs";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..", "..", "..");
const require = createRequire(path.join(root, "marketing", "package.json"));
const puppeteer = require("puppeteer");

const outDir = path.join(root, "build");
fs.mkdirSync(outDir, { recursive: true });
const pdfPath = path.join(outDir, "intro-connect-one-pager.pdf");
const pngPath = path.join(outDir, "intro-connect-one-pager.png");

const browser = await puppeteer.launch();
try {
  const page = await browser.newPage();
  // Letter at CSS 96dpi is 816x1056. The deviceScaleFactor only affects the
  // PNG proof; the PDF is vector plus the embedded photos.
  await page.setViewport({ width: 816, height: 1056, deviceScaleFactor: 2 });
  await page.goto(pathToFileURL(path.join(here, "one-pager.html")).href, {
    waitUntil: "networkidle0",
  });

  // Guard: everything must fit one Letter page. scrollHeight beyond 1056
  // means the print run would spill to page two and half the design would
  // land there silently.
  const height = await page.evaluate(() => document.body.scrollHeight);
  if (height > 1056) {
    throw new Error(
      `content is ${height}px tall; Letter is 1056. Tighten before printing.`
    );
  }

  await page.pdf({
    path: pdfPath,
    format: "Letter",
    printBackground: true,
    margin: { top: 0, right: 0, bottom: 0, left: 0 },
  });
  await page.screenshot({ path: pngPath, fullPage: true });

  console.log(`content height ${height}px of 1056`);
  console.log(`wrote ${pdfPath} (${(fs.statSync(pdfPath).size / 1024).toFixed(0)} KB)`);
  console.log(`wrote ${pngPath} (proof)`);
} finally {
  await browser.close();
}
