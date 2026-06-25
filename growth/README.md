# Intro Connect growth kit

Staged assets for host acquisition. Nothing here sends on its own. You review,
then trigger sends through signal-scout (outbound) or the product (nurture).

## Who we sell to (ICP)

People who run a recurring event and care that the room stays connected:

- Founder dinners, CEO dinners, masterminds, curated clubs
- Meetup and Luma organizers running a monthly or weekly series
- Chamber and BNI chapter chairs, alumni and industry chapter leads
- Coworking community managers

Recurring is the key word. The pain (connections die by Monday) repeats every
cadence, so the value compounds.

## The four channels (cheapest leverage first)

1. **Product-led loop (in-app).** Every attendee already experiences the
   product. The app now prompts attendees to host their own events (see the
   `HostCta` component). This is the cheapest durable channel; everything else
   feeds it.
2. **Outbound to recurring hosts.** Source organizers (see `scrape-organizers.mjs`
   and `leads-seed.csv`), then run `host-outreach-sequence.md` through
   signal-scout as an Intro Connect tenant. Tracked links, three touches, stop
   on reply.
3. **Inbound.** The blog engine is the SEO funnel; the free plan is the
   self-serve close. Both already built.
4. **Nurture.** New free signups get `free-signup-nurture.md` from the product
   (Resend), pacing them from setup to first event to upgrade.

## Files

- `leads-seed.csv` — 10 real Front Range hosts, hand-curated from one scraper
  run. Several have public hosts or org emails. Start here.
- `scrape-organizers.mjs` — dependency-free Exa scraper to expand the list.
  `EXA_API_KEY=xxx node growth/scrape-organizers.mjs "Denver" "Boulder"`.
- `host-outreach-sequence.md` — the cold three-touch drip (#2).
- `free-signup-nurture.md` — the free-signup nurture sequence (#4).

## Loading the outbound drip into signal-scout

signal-scout already handles multi-tenant sequences, tracked links, and
CAN-SPAM footers (`signal-scout.email` sender). To wire this up:

1. Create an Intro Connect tenant / sender identity in signal-scout.
2. Import `leads-seed.csv` (map `host_name` to first name, `source_url` and
   `org` to context).
3. Paste the three touches from `host-outreach-sequence.md`, keeping the
   `{track_click_url}` tokens so clicks attribute back.
4. Set the cadence (day 0, 3, 7) and the stop-on-reply rule.

(Exact signal-scout steps depend on its current tenant model; that wiring lives
in the signal-scout repo and is the one piece still to be done there.)

## Compliance (do not skip)

Cold email needs: a real sender and reply-to, a physical mailing address, and a
working one-click unsubscribe. signal-scout adds these. Only email business
addresses and public organizer contacts. Honor every opt-out immediately. Keep
volume low and personal; this is relationship outreach, not a blast.
