// Runs after `vite build`. Serves the built dist/ folder locally, loads it in
// headless Chrome, waits for React to render, then writes the fully rendered
// DOM back into dist/index.html.
//
// Why: this is a plain client-rendered SPA (no SSR framework), so crawlers
// and link-preview bots that don't execute JavaScript were getting an empty
// <div id="root"> for the homepage. Google's own indexer does eventually
// render JS, but that is a slower second pass, and plenty of other tools
// (Bing, social unfurlers, LLM crawlers) don't render at all.
//
// This is intentionally a small hand-rolled script rather than react-snap:
// react-snap's last release pins puppeteer@1.20.0, which is unmaintained,
// unsupported on current Node, and carries a long list of known CVEs. A
// current `puppeteer` devDependency does the same job without that baggage.
//
// Fails the build loudly (non-zero exit) rather than silently shipping an
// empty prerender if anything goes wrong.
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import puppeteer from "puppeteer";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const distDir = path.join(__dirname, "..", "dist");
const indexPath = path.join(distDir, "index.html");

if (!existsSync(indexPath)) {
  console.error(`[prerender] ${indexPath} not found. Run "vite build" first.`);
  process.exit(1);
}

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".mjs": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".txt": "text/plain; charset=utf-8",
  ".xml": "application/xml; charset=utf-8",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

function serveDist() {
  return new Promise((resolve, reject) => {
    const server = createServer(async (req, res) => {
      try {
        const urlPath = decodeURIComponent((req.url || "/").split("?")[0]);
        let filePath = path.join(distDir, urlPath);
        if (!filePath.startsWith(distDir)) {
          res.writeHead(403);
          res.end();
          return;
        }
        if (!existsSync(filePath) || urlPath.endsWith("/")) {
          filePath = indexPath; // SPA fallback
        }
        const ext = path.extname(filePath).toLowerCase();
        const body = await readFile(filePath);
        res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
        res.end(body);
      } catch (err) {
        res.writeHead(404);
        res.end();
      }
    });
    server.listen(0, "127.0.0.1", () => resolve(server));
    server.on("error", reject);
  });
}

async function main() {
  const server = await serveDist();
  const { port } = server.address();
  const url = `http://127.0.0.1:${port}/`;
  console.log(`[prerender] serving dist/ at ${url}`);

  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });
  try {
    const page = await browser.newPage();
    page.on("pageerror", (err) => console.error("[prerender] page error:", err.message));
    await page.goto(url, { waitUntil: "networkidle0", timeout: 30_000 });
    // Confirm React actually mounted real content, not just the empty shell.
    await page.waitForSelector("h1", { timeout: 15_000 });

    const html = await page.content();
    const wordCount = html.replace(/<[^>]+>/g, " ").trim().split(/\s+/).length;
    if (wordCount < 100) {
      throw new Error(
        `Rendered page has only ${wordCount} words of text; prerender likely captured an empty or broken page.`
      );
    }

    await import("node:fs/promises").then((fs) =>
      fs.writeFile(indexPath, "<!doctype html>\n" + html, "utf-8")
    );
    console.log(`[prerender] wrote ${html.length} bytes to dist/index.html (${wordCount} words)`);
  } finally {
    await browser.close();
    server.close();
  }
}

main().catch((err) => {
  console.error("[prerender] FAILED:", err.message);
  process.exit(1);
});
