// Cloudflare Web Analytics beacon, shared by the Vite build (index.html) and
// the postbuild step (the static privacy and terms pages). Mirrors
// backend/analytics.py so every page on intro-connect.com reports to the same
// site token.
import { readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";

export const BEACON_SRC = "https://static.cloudflareinsights.com/beacon.min.js";

// Site tokens are short alphanumeric strings. The value lands in an HTML
// attribute, so anything else is refused rather than escaped.
const TOKEN_RE = /^[A-Za-z0-9]{16,64}$/;

export function validToken(raw) {
  const t = (raw || "").trim();
  return TOKEN_RE.test(t) ? t : "";
}

export function beaconTag(raw) {
  const t = validToken(raw);
  if (!t) return "";
  return `<script defer src="${BEACON_SRC}" data-cf-beacon='${JSON.stringify({ token: t })}'></script>`;
}

// Static pages copied verbatim from public/, which Vite does not transform.
export const STATIC_PAGES = ["privacy.html", "terms.html"];

export async function injectIntoStaticPages(distDir, raw) {
  const tag = beaconTag(raw);
  if (!tag) return 0;
  let count = 0;
  for (const name of STATIC_PAGES) {
    const file = path.join(distDir, name);
    if (!existsSync(file)) continue;
    const html = await readFile(file, "utf-8");
    if (html.includes(BEACON_SRC) || !html.includes("</head>")) continue;
    await writeFile(file, html.replace("</head>", `${tag}\n</head>`), "utf-8");
    count += 1;
  }
  return count;
}
