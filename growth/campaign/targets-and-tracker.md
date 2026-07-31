# Target criteria and tracker

Goal for the first push: 50 vetted targets, roughly 30 track A and 20 track B,
every one reviewed by a human before anything sends.

## What makes a good target (both tracks)

The one non negotiable: **they run a recurring event where attendees are meant
to meet each other.** Recurring, because the pain repeats every cadence and
the directory compounds. Networking intent, because a lecture audience does
not need to find each other afterward.

Score each candidate 1 to 3 on:
1. Cadence: weekly 3, monthly 2, quarterly or annual 1.
2. Reachability: named person with a direct email 3, org email 2, contact form 1.
3. Room size fit: 20 to 250 people 3 (lands in free or Starter naturally),
   under 20 or over 250 gets a 1.

Send to 7s and up first.

## Track A: Colorado business organizations

Start from `targets-colorado-seed.csv` in this folder: 60 rows auto filtered
from the 1,142 member Boulder Chamber directory, all with a direct email.
**The filter is a magnet, not a judge.** It catches "association" and
"collective" in names, so real targets (young professionals groups, business
alliances) sit next to noise (a fiber company, an interiors firm). Vet each
row: keep orgs that run mixers, luncheons, or member events; cut vendors.
Expect to keep roughly a third.

Beyond the seed file, the richest Colorado veins:
- The chambers themselves: Boulder, Denver Metro, Longmont, Louisville,
  Broomfield, Fort Collins. Events staff listed on their sites.
- Young professionals groups attached to each chamber.
- 1 Million Cups chapters (Boulder chapter already in leads-seed.csv).
- Coworking community managers: the community events calendar gives the
  cadence and the manager's name.
- Economic development orgs and startup week organizers.

## Track B: founder and CEO dinner hosts

`../leads-seed.csv` already holds four vetted warm leads (Thunderview,
Startup Grind Denver, 1 Million Cups Boulder, Paired). Extend with:
- Startup Grind chapter directors in other cities: each chapter page lists
  the director by name.
- Luma and Partiful public event pages for recurring "founder dinner",
  "operator dinner", "CEO breakfast" series; the host name is on the page.
  `../scrape-organizers.mjs` is the starting point for pulling these.
- Mastermind and community operators who post recap threads on X or LinkedIn:
  a recap thread is somebody proud of a room they built and losing it weekly.
- Alumni club chapter organizers for CO schools first (Boulder, DU, Mines).

## Tracker

Track everything in one CSV using the leads-seed.csv columns plus status:

```
org, host_name, role, city, cadence, type, source_url, public_contact,
fit_notes, score, status, touch1_date, touch2_date, touch3_date, reply,
outcome
```

status is one of: unvetted, vetted, queued, in_sequence, replied, demo,
won, lost, do_not_contact. The signal-scout tenant is the operational home
once a row hits queued; this file is the human staging area before it.

Rules that keep us honest:
- A reply of any kind stops the sequence the same day.
- do_not_contact is forever and survives list rebuilds.
- Nothing sends to a row a human has not marked vetted.
