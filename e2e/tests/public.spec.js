// Read-only checks against the live deployment: public content renders, the API
// is healthy, protected routes reject anonymous access, and the published news
// is live with correct SEO markup. No data is created, so this is always safe
// to run against production.
import { test, expect } from "@playwright/test";

test("API health is ok", async ({ request }) => {
  const res = await request.get("/api/health");
  expect(res.status()).toBe(200);
  expect((await res.json()).ok).toBe(true);
});

test("protected routes reject anonymous callers with 401", async ({ request }) => {
  for (const path of ["/api/profile", "/api/events", "/api/admin/stats", "/api/contacts"]) {
    const res = await request.get(path);
    expect(res.status(), `${path} should be 401`).toBe(401);
  }
});

test("robots.txt and both sitemaps are served correctly", async ({ request }) => {
  const robots = await request.get("/robots.txt");
  expect(robots.status()).toBe(200);
  expect(await robots.text()).toContain("Sitemap:");

  const sitemap = await request.get("/sitemap.xml");
  expect(sitemap.status()).toBe(200);
  expect(sitemap.headers()["content-type"]).toContain("xml");
});

test("public news index and a published article render with SEO markup", async ({ request }) => {
  const index = await request.get("/news");
  expect(index.status()).toBe(200);
  const indexHtml = await index.text();
  expect(indexHtml).toContain("/news/");

  const slug = "hilton-report-finds-meeting-new-people-is-the-main-reason-we-gather-in-2026";
  const article = await request.get(`/news/${slug}`);
  expect(article.status()).toBe(200);
  const html = await article.text();
  expect(html).toContain('"@type":"NewsArticle"');
  expect(html).toContain('rel="canonical"');
  expect(html).toContain("intro-connect.com/news/" + slug);
});

test("unknown news slug returns 404", async ({ request }) => {
  const res = await request.get("/news/this-does-not-exist-" + Date.now());
  expect(res.status()).toBe(404);
});
