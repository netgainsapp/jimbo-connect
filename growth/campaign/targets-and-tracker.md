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

## Send log

**2026-08-12 — named-organizer wave, 12 sent** (~2:17–2:46 PM, from
introconnectme@gmail.com). Personalized Template 1 variants; copy in
`drafts-2026-08-12.md`, targets and scores in `targets-named-organizers.csv`.
Recipients: Denver Metro Chamber (Zarookian), Longmont Chamber (Straubel),
Startup Grind Den+COS (Poelstra), 1MC Denver / Fort Collins / Colo Springs,
Boulder Chamber+BYP (Cordero), Broomfield Chamber (Schierkolk), Greeley
Chamber (Fritzler), Erie Chamber (Thompson), Lafayette Chamber (Green),
The Studio Boulder (Tia). All rows: status → in_sequence, touch1 2026-08-12.
- Touch 2 (day 3, in thread): 2026-08-15. Touch 3 (day 8): 2026-08-20.
- Known defect at send time: account display name was still "rob Alexander".
- The 138 remaining Aug 7 "Greetings" drafts are the retired unvetted batch —
  do not send; the addresses they cover are burned for cold intro purposes.
- Prior wave for context: ~140 unpersonalized "What I missed after hosting my
  event" sends to the unvetted chamber scrape, Aug 7–12. Zero replies; treated
  as list failure, not deliverability (mail-tester 10/10 on 2026-08-12).

**2026-08-19, touch 2 prepared, 12 drafts, NOT YET SENT.** Copy in
`drafts-2026-08-19-touch2.md`. Goes in-thread as a reply to each Aug 12
message. Touch 2 was originally calendared for Aug 15 and did not go out, so
this lands day 7 rather than day 3. Revised cadence: touch 1 Aug 12, touch 2
Aug 19, touch 3 Tue Aug 26 (reminder scheduled).
- Sender display name verified fixed on 2026-08-19: reads "Scott / IntroConnect".
  The "rob Alexander" defect shipped with touch 1 only.
- Reply count on the Aug 12 wave as of 2026-08-19: zero, confirmed by inbox
  inspection, not inferred. At 12 sends and one touch, zero replies is the
  most likely single outcome and is not evidence about copy, list, or product.

**2026-08-19, wave 2 touch 1 prepared, 20 drafts, NOT YET SENT.** Copy in
`drafts-2026-08-19-touch1-wave2.md`, split into Tier A (7 rows, named-organizer
list, send ready) and Tier B (13 rows, verdict `verify`, each needs a human vet
before sending). Only 3 of the 20 clear the "send to 7s and up" bar. Generic
inboxes at orgs already contacted at a named person were deliberately excluded.

**Known gap.** `already_contacted` is still empty on all 33 rows of
`targets-named-organizers.csv` even though 14 of them were contacted on Aug 12.
The CSV disagrees with this file. Fix before the next list rebuild.

**2026-08-19, touch 2 loaded into Gmail as in-thread drafts.** All 12 sit in
introconnectme@gmail.com (slot /u/3) as a reply inside each original Aug 12
thread, created 3:55 to 4:15 PM. Drafts count went 138 to 151. Scott sends.
Verified one by one: each draft's greeting and event match its thread.
- One stray draft to discard: a copy of the Alexandra text landed in the
  unrelated "test" thread to sdwbouldah55 at 3:59 PM (automation clicked a
  stale list row). The correct Alexandra draft exists in the Startup Grind
  thread at 4:02 PM. Discard the 3:59 PM one before sending anything.

**2026-08-19, wave 2 Tier A loaded into Gmail, 7 new-thread drafts.** Westminster
Chamber, Enterprise Coworking, CACI (Summer Asbury), Longmont EDP (Kelly Sage),
Colorado LGBTQ Chamber, Colorado Women's Chamber (Simone Morrison), Louisville
Chamber (Melanie Hassenfratz). Copy in `drafts-2026-08-19-touch1-wave2.md`.
Drafts folder went 138 to 158: 12 touch 2 + 7 touch 1 + 1 stray to discard.

**2026-08-19, daily cadence started.** Scheduled task `intro-connect-daily-outreach`
runs weekdays 9:00 AM: source and vet 25 new named organizers, draft and load
touch 1, plus touch 2 for the cohort at day 7 and touch 3 for the cohort at day
14. Task file: C:\Users\sweis\.claude\scheduled-tasks\intro-connect-daily-outreach\SKILL.md
- Sourcing is the bottleneck, not drafting. At the start of this cadence the
  qualified pool was effectively exhausted: 7 Tier A rows (now all sent as
  drafts), 29 rows marked verify, 24 marked cut. 25 a day means 125 vetted
  named organizers a week must be found. The task is instructed to report the
  true number found and never pad with unvetted org inboxes.
- Scheduled tasks only fire while the desktop app is open.
- Volume warning to revisit near 50 a day: 25 cold sends daily from one consumer
  Gmail, rising toward 75 once all three drips overlap, risks throttling and
  spam foldering. signal-scout is the documented home for sending at volume.

**2026-08-19, SENT. 19 emails out between 4:35 and 4:37 PM.**
- Cohort A (12 named organizers, touch 1 on Aug 12): touch 2 sent. Touch 3 due
  Tue 2026-08-26 (day 14).
- Cohort B (7 Tier A orgs, first contact): touch 1 sent. Touch 2 due Tue
  2026-08-26 (day 7), touch 3 due Tue 2026-09-02 (day 14).
- So 2026-08-26 carries BOTH cohort A touch 3 and cohort B touch 2. The daily
  task handles both via its day-7 and day-14 rules. The separate one-off
  touch-3 reminder task was deleted to stop it double drafting cohort A.
- The 138 retired "Greetings" drafts were deleted by Scott the same evening.
- Correction to the earlier note: the stray draft in the "test" thread was NOT
  discarded, it was sent, at 4:37 PM to sdwbouldah55 (Scott's own address). No
  external recipient saw it and no outreach thread was affected.

**2026-08-19, first response: an out of office.** Auto responders are NOT
replies and must not stop a sequence, since the recipient has not read the
message. Log as auto_reply with the stated return date, push that thread's
remaining touches to at least one business day after they are back, and resume
from whichever touch was next. Hard bounces are different: mark do_not_contact.
The daily task prompt was updated on 2026-08-19 to encode this distinction.
An out of office is also a mild positive deliverability signal: it proves the
message reached a live mailbox and was processed rather than silently dropped.

**DATE CORRECTION, 2026-08-19.** 2026-08-19 is a WEDNESDAY. The Aug 12 handoff
labelled 2026-08-15 as a Friday and 2026-08-20 as a Wednesday; both are wrong
(Aug 15 was a Saturday, Aug 20 is a Thursday) and the error was repeated in
this session before being caught. Verified weekdays:
Aug 24 Mon, Aug 25 Tue, Aug 26 Wed, Aug 29 Sat, Sep 2 Wed.

CORRECTED SCHEDULE:
- Cohort A (12, touch 1 Aug 12, touch 2 Aug 19): **touch 3 Tue 2026-08-25**,
  per Scott's "next Tuesday". This is day 13, not day 14, and overrides the
  daily task default.
- Cohort B (7, touch 1 Aug 19): touch 2 Wed 2026-08-26, touch 3 Wed 2026-09-02.
- The two cohorts therefore fall on different days, Aug 25 and Aug 26, rather
  than stacking 19 emails on one morning as previously recorded.

**LOUISVILLE CHAMBER, auto_reply, 2026-08-19 4:34 PM.** Melanie Hassenfratz,
Engagement Manager. Out of office, responding to email again from **Mon Aug 24**.
Signature intelligence worth keeping:
- **In-office hours M-Th 9:30 to 4:30.** Never land a touch on a Friday for this
  contact. Her scheduled touch 2 on Wed Aug 26 is two days after she returns and
  inside her working days, so no reschedule is needed.
- **"Pints in the Park", Saturday Aug 29**, tickets on Eventbrite. A real, dated,
  ticketed event with an actual attendee list, three days after her touch 2
  lands. Far stronger personalization than the generic Leaders Luncheon angle.
  Her touch 2 was rewritten to lead with it.
- Autoresponder offers Director@louisvillechamber.com for urgent matters. Logged
  as a known second contact. Do NOT use it for the pitch: a cold sales follow up
  is not an urgent matter and jumping to the director would burn both contacts.

**2026-08-19, inbound mail RESOLVED.** hello@intro-connect.com forwarding
through ImprovMX is working. Verified end to end at 8:56 PM: a test from
sdwbouldah55@gmail.com landed in the Primary inbox of introconnectme@gmail.com,
over TLS, mailed-by intro-connect.com. The 2026-08-01 ImprovMX notices saying
forwarding was not active, and that Google blocked a forwarded test, were stale.
DNS had been correct all along (MX to mx1/mx2.improvmx.com, SPF include).
- Consequence worth remembering: hello@ forwards into the SAME mailbox the
  outreach is sent from. Website enquiries and cold-email replies land in one
  inbox, so do not assume every new message belongs to a campaign thread.
- The From line on all app transactional mail is therefore reply-able. Nothing
  is being lost.

**2026-08-20, 25 touch 1 drafts loaded into Gmail, 10:04 to 10:13 AM.** Copy and
per-target vetting in `drafts-2026-08-20-touch1.md`. Composition: 1 verified
named chamber contact (Karin Jimenez, Tempe, karin@tempechamber.org), 18 1MC
chapters (weekly by program design; four multi-word-city addresses are pattern
inferred and may bounce: desmoines, cedarrapids, iowacity, kansascity, plus
fortworth), 6 promoted Tier B rows reusing the 2026-08-19 wave 2 copy (Boulder
Rotary, Boulder Bar, BOLO, BARHA, BCIV, Arts Alliance). Scott sends. Any bounce
gets marked do_not_contact same day. Cohort C touch 1 = send date; touch 2 due
day 7, touch 3 day 14.

Context: the scheduled runner failed three times (23:29, 8:28 stall, 9:03
skipped-because-running), so this batch was built and loaded manually in the
main session. Permission allowlist for unattended runs was added to
~/.claude/settings.json the same morning; tomorrow's 9:04 run is the test.

**2026-08-20, cohort C SENT, 25 emails, 10:25 to 10:26 AM. Delivery verified
from the inbox within minutes.**

Bounced, 4, all @1millioncups.com aliases that do not exist. Marked
do_not_contact permanently:
- cedarrapids@1millioncups.com
- waco@1millioncups.com
- fortworth@1millioncups.com
- chattanooga@1millioncups.com

Delivered with POSITIVE confirmation, 2:
- lincoln@1millioncups.com: chapter auto-acknowledgement ("1MC LNK"), live
  mailbox, offers their LinkedIn for faster response.
- jen@barhaonline.org: out of office from Jen Crowell, Executive Director,
  BARHA. Out Thu/Fri/Mon, back Tue 2026-08-26, so her cohort C touch 2 on Wed
  2026-08-27 lands the day after she returns. No reschedule needed. Alternate
  contact meghan@barhaonline.org logged, do NOT pitch it.

Accepted without bounce, 19: austin, orlando, dallas, columbia, dubuque, ames,
lima, desmoines, iowacity, kansascity, tulsa, wichita, omaha @1millioncups.com,
plus karin@tempechamber.org, clubadmin@boulderrotary.org, bay@boulder-bar.org,
veronica@bolorealtors.com, zuza.bohley@bciv.org, info@bouldercountyarts.org.

Calibration lesson, recorded so it is not repeated: word count predicted
nothing. "High confidence" waco bounced while pattern-inferred desmoines,
iowacity and kansascity all delivered. The alias exists only if the chapter
registered it. NEW RULE: no more constructed addresses; only addresses
published somewhere, and any bounce is marked do_not_contact same day.

Effective cohort C: 21 delivered of 25 sent. Bounce rate 16 percent, one-time,
noted for sender reputation; keep future batches to published addresses.

**2026-08-21, FIRST HUMAN REPLY. 1MC ORLANDO INVITED SCOTT TO PRESENT.**
Erik Deckers (erik.deckers@gmail.com, 574-529-4135, problogservice.com),
organizer of 1 Million Cups Orlando, replied 2026-08-20 1:04 PM, 2.5 hours
after touch 1: "Would you be interested in presenting that to our group? We do
have an opening for next week, August 26th." Application: 1millioncups.com/orlando,
Present button; Erik approves and schedules.

- orlando@1millioncups.com: status REPLIED. Sequence STOPPED per campaign rule.
  No touch 2 or 3 to Orlando, ever, unless the relationship goes cold months out.
- Reply draft staged in-thread 2026-08-21: accepts, asks the one open question
  (remote presenter vs in person, Scott is in Boulder), and offers to run a
  live Intro Connect directory during the session so the presentation is a
  working demo. Scott reviews and sends, then submits the application form
  himself the same day so Erik can approve in time for the 26th.
- A partial earlier draft may exist in the same thread (list showed "Draft 3"
  with different opening text). If two drafts appear in the thread, keep the
  complete one, discard the fragment.
- Note for the story this proves: the reply came from a 1MC org address wave
  that also produced 4 bounces. Deliverability was never the problem; the
  audience was right. One warm presentation slot from 21 delivered in 3 hours.
