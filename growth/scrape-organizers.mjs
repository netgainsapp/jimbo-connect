// Event-host lead scraper for Intro Connect outreach.
//
// Runs a set of ICP queries against the Exa search API and writes a deduped CSV
// of recurring-event organizers (the people who buy Intro Connect). Public
// listing pages only; this finds events and their public host pages. Email
// enrichment is a separate, deliberate step (Hunter/Apollo/manual), not done
// here.
//
// Usage:
//   EXA_API_KEY=xxx node growth/scrape-organizers.mjs "Denver" "Boulder" > growth/leads.csv
//
// No dependencies (uses global fetch). The seed list in leads-seed.csv was
// produced by the same query set, by hand-curating one run.

const API_KEY = process.env.EXA_API_KEY;
if (!API_KEY) {
  console.error("Set EXA_API_KEY in the environment.");
  process.exit(1);
}

const cities = process.argv.slice(2);
if (cities.length === 0) cities.push("Denver", "Boulder");

// ICP query templates. Each describes the ideal page rather than keywords, which
// is how Exa ranks best. Add more angles (alumni, chambers, coworking) as needed.
const TEMPLATES = [
  (c) =>
    `recurring professional networking event series in ${c} with a public events page and a named regular host`,
  (c) =>
    `monthly founder dinner or mastermind community in ${c} that publishes its upcoming events`,
  (c) =>
    `${c} meetup group organizer running a regular in person business networking event`,
  (c) =>
    `coworking space or chamber in ${c} hosting recurring member networking events`,
];

async function search(query) {
  const res = await fetch("https://api.exa.ai/search", {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-api-key": API_KEY },
    body: JSON.stringify({ query, numResults: 15, type: "auto" }),
  });
  if (!res.ok) {
    console.error(`Exa ${res.status} for: ${query}`);
    return [];
  }
  const data = await res.json();
  return Array.isArray(data.results) ? data.results : [];
}

function csvCell(value) {
  const s = String(value ?? "");
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

const seen = new Set();
const rows = [];

for (const city of cities) {
  for (const tmpl of TEMPLATES) {
    const results = await search(tmpl(city));
    for (const r of results) {
      const url = (r.url || "").split("?")[0];
      if (!url || seen.has(url)) continue;
      seen.add(url);
      rows.push({
        org: r.title || "",
        city,
        source_url: url,
        published: r.publishedDate || "",
      });
    }
  }
}

const header = ["org", "city", "source_url", "published"];
console.log(header.join(","));
for (const row of rows) {
  console.log(header.map((k) => csvCell(row[k])).join(","));
}
console.error(`Wrote ${rows.length} unique leads across ${cities.length} cities.`);
