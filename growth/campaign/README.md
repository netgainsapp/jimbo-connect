# Go to market campaign (2026-07-31)

The revenue push, built under three founder decisions: brand voice only, zero
ad budget, direct outreach first. Two beachheads: Colorado business
organizations, and founder dinner hosts nationally.

`positioning.md` is the source of truth; everything else derives from it.
This folder extends the older `../` growth kit (ICP, generic sequence,
nurture, scraper, warm leads) rather than replacing it. The four leads in
`../leads-seed.csv` are still the warmest names we have and go first.

## The files

| File | What it is |
|---|---|
| positioning.md | ICPs, claims that are allowed, pricing, voice and sending rules |
| outreach-colorado-orgs.md | Track A: 3 touch sequence + reply playbook |
| outreach-founder-dinners.md | Track B: 3 touch sequence + reply playbook |
| targets-and-tracker.md | What a good target is, where to find 50, tracker schema |
| targets-colorado-seed.csv | 60 auto filtered chamber orgs with emails. VET FIRST |
| one-pager.md | Forwardable pitch for warm replies |
| founding-host-offer.md | The closer. Price awaits Scott's sign off |
| social-calendar.md | Two weeks of LinkedIn company page + X posts |
| blog-topics.md | 12 topics for the automated blog engine |
| demo-video-script.md | 90 second screen recording script |

## Week one, in order

1. **Scott signs off the founding offer price** (founding-host-offer.md
   decision box), then the FOUNDINGHOST promo code gets created in Stripe.
2. **Confirm the signal-scout Intro Connect tenant and its sending identity.**
   Outbound never sends from hello@intro-connect.com; that domain carries
   password resets and invitations and must stay clean. If the tenant needs a
   sending domain, buy one (for example introconnect email domain variants),
   warm it, and only then queue sends.
3. **Vet the lists.** The four warm leads in ../leads-seed.csv first, then
   the Colorado seed CSV (expect to keep about a third), then fill to 50
   using targets-and-tracker.md. Every kept row gets a name, not just an org.
4. **Load both sequences into signal-scout** and queue the vetted 7+ scores,
   warmest first, 10 to 15 new sends a day so replies stay handleable.
5. **Record the demo video** (script here) and put the link in the sequences'
   `{track_click_url}`.
6. **Publish week one of the social calendar** so the brand pages look alive
   before recipients go checking.
7. Blog engine gets the first two topics from blog-topics.md.

## What we measure (and nothing else for now)

Replies per 50 sends, walkthrough link clicks, free events created from
outreach, and founding hosts closed. Vanity metrics wait until there is
revenue to be vain about.

## Standing rules

- Every claim in every asset is true in the product on the day it ships.
- Guests never pay. No asset may blur this.
- Stop on reply. do_not_contact is forever.
- Nothing sends from the transactional domain. Ever.
