# Lead types v2: expanding the hunt beyond chambers and 1MC

Written 2026-09-05, prompted by the Lead Hunt Review Package on Scott's
Desktop. That package's ICP line is the right test and is adopted here:
**"an organization whose value depends on the same people meeting,
networking, and returning repeatedly."**

What the campaign has actually measured, which this document is built on:
- Both human replies AND the one booked call came from founder/entrepreneur
  rooms reached through generic chapter aliases (1MC Orlando, 1MC Dallas).
- ~60 named chamber contacts have produced 0 replies so far (their follow
  ups only just landed; verdict pending, not damning).
- The binding constraint was never the supply of organizations. It was the
  PUBLISHED EMAIL ADDRESS. Every sourcing ceiling (9, 6, 15, 21, 20 per run)
  was an address-publishing ceiling. So new lead TYPES only help if they
  come with new CHANNELS.
- The one call booked (Gabriel, Connected Coworking Dallas) is a coworking
  operator: the package ranked coworking "Medium." Raise it.

## Tier 1: work these next (highest fit, reachable, evidence-backed)

1. **Industry association local chapters.** AMA, PRSA, SHRM, AIGA, PMI, ULI,
   NAIOP, CREW, NAWBO, BOMA and peers. Every metro has chapters; monthly
   mixers and luncheons are the product; boards and events chairs are
   PUBLISHED on chapter sites (associations publish boards far more reliably
   than chambers publish staff). This is the chamber play with denser
   networking intent and better address supply. Sourcing method already
   exists (page extraction + cfemail decode).
2. **The 1MC presenter motion, not just 1MC email.** The campaign's first
   reply was an INVITATION TO PRESENT. Chapters need presenters every single
   week. Applying to present at 1millioncups.com/<city> puts Scott and a
   live IntroConnect directory in front of an entrepreneur room: the
   presentation IS the demo, and it costs nothing. Target: apply to a
   handful of chapters within driving distance or remote-friendly ones.
   This converts the existing 1MC vein from cold email to warm stage time.
3. **Referral loop through the two live relationships.** Erik (Orlando)
   offered their LinkedIn; Gabriel (Dallas) runs a coworking network and
   takes the call Wed Sep 9. Every organizer knows other organizers. The
   ask at the end of each warm conversation: "who are two other organizers
   who should see this?" Zero sourcing cost, highest conversion channel
   that exists.
4. **Coworking community managers, raised from Medium to High.** The
   original campaign docs listed this vein and it produced the only call.
   Community managers are named on space websites, the community events
   calendar proves cadence, and "member community" is their job title.
5. **Alumni association city chapters.** In the original Track B plan,
   never executed. University alumni chapters run recurring happy hours,
   staff carry published .edu addresses, and engagement is what they are
   paid for (donations follow engagement). CO schools first (CU, DU,
   Mines), then big-network schools' Denver chapters.

## Tier 2: strong fit, needs a channel other than email

6. **Meetup.com organizers of recurring professional/social groups.**
   Meetup's own weakness is IntroConnect's core: no private member
   directory, no post-event reconnection. Organizers are one click away
   via Meetup messages: a channel that does not depend on published email.
   Scrapeable by city + event frequency + group size.
7. **Luma / Partiful recurring series hosts (founder dinners, operator
   breakfasts).** Original Track B, never worked; `scrape-organizers.mjs`
   already exists as the starting point. Curated-room hosts feel the
   "room dies between dinners" pain hardest. Contact via the platform or
   the host's public profile.
8. **Run clubs and social fitness clubs.** The 2025-26 wave: people join
   run clubs explicitly to meet people; rooms recur weekly at scale; the
   directory is the missing piece after every run. Organizers live on
   Instagram/Strava, not email, so this lane needs DM outreach (note:
   Attiq's IG DM tooling exists in Scott's portfolio). Free tier fits;
   monetization is weaker; treat as top-of-funnel volume and stories.
9. **Referral/leads groups (independent ones).** Weekly cadence, meeting
   people IS the product. Prefer independent local leads groups: BNI
   corporate has its own app (BNI Connect) and franchise rules, so BNI
   chapters are demo-aware but tool-locked; treat BNI as pattern proof,
   not a target.
10. **Rotaract and young-professional service club offshoots.** Chapter
    based, published contacts, 18-30 audience; the Boulder Rotary thread
    already opens this door locally.

## Tier 3: worth a test batch each

11. **Creative Mornings chapters.** 200+ city chapters, hosts named,
    free monthly breakfast, explicitly community-first.
12. **Affinity professional orgs.** ALPFA, NSBE, SHPE, Prospanica, women-
    in-tech groups, young lawyers divisions, Lesbians Who Tech chapters.
    Chapter boards published, mission-driven retention pain.
13. **Real estate investor associations (REIAs).** Paid membership,
    monthly meetings, organizer-owners, unambiguous networking intent.
14. **Event-industry associations (NACE, ILEA, WIPA chapters).** Double
    value: they are users AND a channel, because their members run events
    for everyone else.
15. **Professional community IRL spinoffs.** Pavilion, RevGenius, Hampton
    style communities running city dinners; the buyer is a professional
    Head of Community, the exact ICP title.

## The "not another account" rule (Scott, 2026-09-05)

Scott's objection, adopted as a ranking factor and a positioning line: nobody
wants a LinkedIn account, a national-org account, AND an IntroConnect
account. Consequences:
- **Prefer rooms with NO incumbent member system.** Run clubs, YP groups,
  founder dinners, coworking communities have nothing; the objection never
  comes up. Rooms behind an incumbent portal (Greek nationals on
  KappaSig.Net/Salesforce, BNI Connect, big-association AMS platforms) rank
  lower and get a different pitch or get skipped.
- **Positioning line for the objection when it appears:** IntroConnect is
  not a network you maintain; it is the memory of a room you were already
  in. No install, no feed, join by code in a minute, and your card can be
  just your name and your LinkedIn link.
- **Product notes feeding from this — BOTH SHIPPED 2026-09-05:**
  - *Profile-as-pointer.* LinkedIn is now the second field on the profile
    form (right after name); role and company are optional, not required. A
    pasted "linkedin.com/in/you" is normalized to a clickable https link on
    save, and the profile card shows it as the primary contact route.
  - *Join-by-code never forces account creation.* `/join/:code` now shows a
    name (LinkedIn optional) form instead of bouncing to login. It mints a
    credential-less guest (no email, no password), signs them in with the
    normal session cookie, and drops them straight into the directory.
    Verified live: a guest joined with just a name + LinkedIn and landed in
    the room alongside other email-less guests.
  - Still open as a smaller follow-up: Google sign-in for people who DO want
    a durable account without a password.
  - Greek alumni chapters stay in the alumni lane but pitched ONLY with this
    framing.

## Deliberately NOT pursued

- Toastmasters (members already know each other; speaking, not meeting, is
  the product).
- One-off conferences, virtual-only communities (per the package's
  exclusions, adopted).
- Social sports leagues: real fit, but adjacent to Rally UP; revisit only
  as a deliberate portfolio decision, not a campaign lane.

## Channel expansion (as important as the segments)

The address-publishing ceiling caps email sourcing at ~10-20/day. The mix
that breaks it:
- **Stage time** (1MC presenter applications; association chapters also book
  speakers).
- **Referrals** from every warm conversation, starting Wednesday with
  Gabriel.
- **Platform-native messages** (Meetup, Luma) that need no email at all.
- **LinkedIn** from Scott's own profile to Head of Community / Chapter
  Director titles: his 30-year B2B background carries the credibility cold
  Gmail cannot. Named-but-unpublished contacts (the Cloudflare-blocked and
  form-only orgs already logged) become reachable here instead of being cut.
- Email remains the workhorse for Tier 1 where addresses are published.

## Fixes adopted from the package review (2026-09-05 chat)

- Dedupe against THIS tracker is mandatory and automated before any list
  becomes a cohort (the package itself missed Startup Grind Denver and 1MC
  Denver, both "I will not email again" recipients).
- Scoring renormalizes over known signals so Unknown is arithmetically
  neutral, not a silent penalty.
- Published-address rule and one-contact-per-org rule carry over unchanged
  to every email lane; platform-message lanes have no address requirement.
- Every seed stays "do not send" until verified with a citable source URL.
