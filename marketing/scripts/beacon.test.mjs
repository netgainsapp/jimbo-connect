// Run: node --test scripts/
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { beaconTag, validToken } from "./beacon.mjs";

const TOKEN = "0123456789abcdef0123456789abcdef";

test("no beacon without a token", () => {
  assert.equal(beaconTag(undefined), "");
  assert.equal(beaconTag(""), "");
});

test("beacon carries the token when one is set", () => {
  const tag = beaconTag(TOKEN);
  assert.match(tag, /src="https:\/\/static\.cloudflareinsights\.com\/beacon\.min\.js"/);
  assert.ok(tag.includes(`data-cf-beacon='{"token":"${TOKEN}"}'`));
});

test("malformed tokens are refused, never injected", () => {
  for (const bad of ['a"><script>x</script>', "has space", "x".repeat(200)]) {
    assert.equal(validToken(bad), "", bad);
    assert.equal(beaconTag(bad), "", bad);
  }
});

test("static sitemap lists every public page on the marketing host", () => {
  const xml = readFileSync(new URL("../public/sitemap.xml", import.meta.url), "utf-8");
  const locs = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
  for (const p of ["/", "/agenda", "/blog", "/privacy.html", "/terms.html"]) {
    assert.ok(locs.includes(`https://intro-connect.com${p}`), p);
  }
  assert.ok(!locs.some((l) => l.endsWith("/news")), "retired /news stays out");
});
