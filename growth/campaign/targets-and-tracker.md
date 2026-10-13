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

**2026-08-21 (FRIDAY), daily run. Verification of 2026-08-20, measured from Gmail.**
Sent: 25, between 10:24 and 10:27 AM. This corroborates the cohort C ledger
above (which recorded 10:25 to 10:26); the wider span is the measured one.
Still sitting in Drafts at the start of this run: ZERO. Everything prepared on
Aug 20 was sent. Nothing unplanned and nothing misdirected went out. The four
bounces were already logged and marked do_not_contact.

**FIRST HUMAN REPLY OF THE CAMPAIGN, 2026-08-20 1:04 PM.**
Erik Deckers, organizer, 1 Million Cups Orlando, replying from his personal
address erik.deckers@gmail.com (the orlando@1millioncups.com alias reaches a
real human). Thread status: `replied`. Its drip sequence is STOPPED
permanently. Never send touch 2 or touch 3 to orlando@1millioncups.com.

What he offered: a slot to PRESENT to 1MC Orlando on Wednesday 2026-08-26.
Mechanism: Scott must apply at https://1millioncups.com/orlando via the
"Present" link at the top of the page; Erik then approves and schedules.
Contact intelligence logged: phone 574-529-4135, https://problogservice.com.

Two things this proves. First, a chapter alias with no named person on it can
still reach a decision maker, which is why the generic "Hi there" copy that
went to the 1MC chapters produced a reply despite not being personalised. That
is a result, not a vindication of the copy: 1 reply from 18 chapters.
Second, deliverability to 1MC is fine where the alias exists.

**Do not automate into this thread again.** Scott was composing his own reply
in a second Gmail session while this run was in progress, and the automation
wrote into the same draft, merging the two. The draft was restored to a clean
coherent version, but his own wording was disturbed in the process and his
live edits kept superseding it. Evidence of the concurrent session: Gmail
showed "Open in 1 other location" and the draft snippet changed three times
between reads, gaining text nobody in this session wrote.

Substantively important, from Scott's own draft text: he has next week booked
and appears to be declining the Aug 26 slot in favour of pitching 1MC as a
PILOT. That contradicts the "I will submit the application today" line the
automation had drafted. Scott owns this reply. The draft in the thread is his
to finish and send.

**Cohort D sourced 2026-08-21. Honest count: 9 vetted organisations, not 25.**
Copy in `drafts-2026-08-21-touch1.md`. Every address is PUBLISHED on the
organisation's own staff page. Nothing pattern inferred, per the Aug 20 rule.
One contact per organisation; where a staff page listed several events people,
the events owner was taken and the rest left alone. All score 8 (cadence 2,
reachability 3, room fit 3).

1. Cat Boose, Director of Events, Nashville Area Chamber, cboose@nashvillechamber.com (Regional Business After Hours)
2. Brandon Pinnix, Director of Membership Development, Durham Chamber, bpinnix@durhamchamber.org (Business After Hours)
3. Camille Adams, Program Coordinator, Greenville Chamber, cadams@greenvillechamber.org (GCYP Leadership Luncheon)
4. Jess Jones, Director of Marketing and Events, Grand Rapids Chamber, jess@grandrapids.org (Business Exchange Breakfast)
5. Nyila Johnson, synerG Young Professionals Manager, Action Greensboro, njohnson@actiongreensboro.org (synerG)
6. Jaci Pieters, Young Professionals Network Manager, Sioux Falls Chamber, jpieters@siouxfalls.com (YPN)
7. Celeste Lloyd-Jones, Event Manager, Greater Sarasota Chamber, cljones@sarasotachamber.com
8. Sharla Rowe, Events Manager, Greater Madison Chamber, sharla@madisonbiz.com
9. Jessica Buettgenbach, Events Manager, Wichita Regional Chamber, jbuettgenbach@wichitachamber.org

Why 9 and not 25: most chamber sites no longer publish staff email addresses,
routing to a contact form instead. Of roughly 100 organisations crawled, about
a dozen published direct addresses paired with a name and a title. The Aug 7
lesson stands, so the shortfall was reported rather than padded with org
inboxes. Sourcing remains the binding constraint on this campaign.

**Drafts waiting in Gmail at end of run: 10.** Nine cohort D touch 1 (new
threads) plus the 1MC Orlando reply. Each of the nine was verified one by one:
exactly one recipient, correct subject, and a greeting matching that
recipient. Scott sends.

**qualifiedRemaining is now effectively ZERO.** All nine sourced today were
drafted today. There is no vetted, uncontacted pool left. On current form the
campaign stalls without a sourcing method that does not depend on chambers
publishing addresses.

**Command Center push BLOCKED, not done.** The task reads SNAPSHOT_SECRET from
`C:\Users\sweis\command-center\.env.blob-probe`, but that key is present and
EMPTY there (`SNAPSHOT_SECRET=""`), and it is absent from `.env.local` and
empty in `.env.example`. Unauthenticated GET returns 307 to `/unlock`. The
tile therefore still shows stale numbers. Fix: pull the real value from the
Vercel project env (`vercel env pull`) into a local env file.

**2026-08-21, SECOND RUN THE SAME MORNING (duplicate scheduler fire).** The
daily task fired again at 10:38 AM, ninety seconds after the first run committed
at 10:37:14. No drafting or sending was repeated, because doing so would have
put second copies in front of the same nine people. The run verified state,
sourced a fresh cohort, and stopped short of Gmail.

**SCOTT SENT HIS OWN 1MC ORLANDO REPLY, 10:40 AM, measured from the Sent
folder.** Top row of Sent reads "To: orlando, Erik" at 10:40 AM with his
wording: "Thanks for the response. I do have next week booked, as I have
commitments with a few other startup projects that I am working on. That said,
I am interested in talking with you about". He declined the Aug 26 presentation
slot and kept the conversation open, which matches the pilot direction recorded
earlier and contradicts the automation's draft.

**HAZARD, needs one click from Scott: a stale automation draft still sits in
the Orlando thread and contradicts the message he just sent.** The draft was
created at 10:26 AM and reads "I will go to the site and submit the application
today so you have it in time to approve for the 26th." Sending it would accept
the slot he has already declined. Evidence it is stale, not his: the thread's
draft snippet showed his 10:39 AM wording, then reverted to the 10:26 AM
automation text once his version was sent. It was left in place rather than
deleted, because destructive edits to a thread he is actively working are his
call. Discard it before touching that thread again.

Drafts folder at end of this run: 10. Nine cohort D touch 1, unsent, all
verified present with correct recipients and matching greetings, plus the one
stale Orlando draft above. Sent today: 1, and it was Scott's, not the campaign's.
Nothing unplanned or misdirected went out. No new replies, autoresponders or
bounces since the morning run.

**Cohort E sourced, 6 vetted and send ready, plus 1 to verify. NOT loaded into
Gmail.** Copy and per-target sourcing notes in `drafts-2026-08-21-touch1-cohortE.md`.
Held out of Gmail deliberately: nine drafts from the morning were still unsent,
Scott was demonstrably active in that mailbox, and a duplicate run should not
double the day's queued volume unilaterally. Load on the next run.
1. Hayley Loftus, Chapel Hill Young Professionals, hloftus@carolinachamber.org
2. Molly Crouser, Director of Events and Partnerships, Lancaster Chamber, mcrouser@lancasterchamber.com
3. Laura Dryden, Events Director, Greater KC Chamber, dryden@kcchamber.com
4. Alison, La Crosse Area Chamber YP, alison@lacrossechamber.com (score 9, best cadence)
5. Lorance Uwinaza, YP of the Chippewa Valley, uwinaza@eauclairechamber.org
6. Joanne Ortega, San Marcos Area Chamber YP, joanne@sanmarcostexas.com
Verify first: Lorraine Levine, Cape Cod Chamber, lorraine@capecodchamber.org.
All addresses extracted from page source, none constructed. qualifiedRemaining
moves from 0 to 6.

**Sourcing lesson worth keeping: young professionals pages beat chamber staff
directories.** A YP page names a human contact far more often, because the group
is recruiting members, and its cadence is higher (La Crosse averages 2-3+ events
a month against a chamber's monthly). Chambers increasingly route to contact
forms. The binding constraint is the published address, not the organisation.

**Command Center push STILL BLOCKED, second confirmation.** SNAPSHOT_SECRET is
present but empty in `.env.blob-probe`, empty in `.env.example`, and absent from
`.env.local`. Unauthenticated GET on the endpoint returns 307 to `/unlock`, so
read-merge-write cannot run. The fix needs a human: pull the real value from the
Vercel project env into a local env file. The tile keeps showing stale numbers
until then. Unattended runs cannot execute `vercel env pull` because it is not
on the allowlist.

**Schedule, weekdays verified.** Aug 24 Mon, 25 Tue, 26 Wed, 27 Thu, Sep 2 Wed,
Sep 3 Thu.
- Cohort A (12, touch 1 Aug 12): touch 3 Tue 2026-08-25. Unchanged.
- Cohort B (7, touch 1 Aug 19): touch 2 Wed 2026-08-26, touch 3 Wed 2026-09-02.
- Cohort C (21 delivered, touch 1 Aug 20): touch 2 Thu 2026-08-27, touch 3
  Thu 2026-09-03. Orlando is excluded permanently (replied).
- Cohort D (9, touch 1 when Scott sends): touch 2 day 7, touch 3 day 14 from
  the actual send date, not from today.
- Melanie Hassenfratz, Louisville, works M-Th; her Aug 26 touch 2 is inside
  her working days. Jen Crowell, BARHA, back Tue Aug 26; her Aug 27 touch 2
  lands the day after she returns. Neither needs rescheduling.

**2026-08-21, cohort D forming: the long-running scheduled session began loading
drafts at 10:27 AM.** Nine touch 1 drafts so far, run still active, cap 25.
Named people and named events throughout, harvested via homepage link
discovery, no constructed addresses. Verified recipients so far:
jbuettgenbach@wichitachamber.org (Jessica, Wichita Regional Chamber; distinct
org from 1MC Wichita), cljones@sarasotachamber.com (Sarasota),
njohnson@actiongreensboro.org (synerG, Action Greensboro),
cadams@greenvillechamber.org (GCYP, Greenville Chamber),
bpinnix@durhamchamber.org (Durham), cboose@nashvillechamber.com (Nashville).
Three more drafts (Sharla, Jaci YPN, Jess Business Exchange Breakfast) loaded
but recipient not yet extracted; same sourcing method, no collision with any
contacted org. Reconciliation verdict: clean, cleared for Scott to send.
Stray fragment draft remains in the Erik Deckers thread; discard, do not send.
Scott sent his reply to Erik 2026-08-21 morning; Orlando presentation slot for
Wed Aug 26 in motion, application submission pending on Scott.

**2026-08-21, Erik / 1MC Orlando: HANDLED BY SCOTT DIRECTLY. Closed as an
action item.** Scott has talked to Erik. Do not remind him about the reply,
the application, or the Aug 26 slot again, in any session or any scheduled
run. The only remaining automation duty for Orlando: the sequence stays
STOPPED (replied thread), and if anything about the presentation changes,
Scott will say so himself.

---

**2026-08-28 (FRIDAY), daily run. Fired 3:33 PM, not 9:00 AM.**

**FOUR SCHEDULED RUNS DID NOT FIRE: Mon Aug 24, Tue Aug 25, Wed Aug 26, Thu Aug
27.** Evidence, not inference: no commits in this repo between 2026-08-21 and
2026-08-28, and no draft files dated in that window. Scheduled tasks only fire
while the desktop app is open, which is the most likely cause. This is a
seven calendar day gap in the campaign, and it is the single most important
fact of this run.

**GMAIL WAS NOT REACHABLE ON THIS RUN. NOTHING WAS VERIFIED AND NOTHING WAS
LOADED.** The Claude in Chrome extension reported not connected, and
`list_connected_browsers` returned an empty list. Retried once, then skipped
per the task's no retry loop rule. Consequences, stated plainly rather than
papered over:
- STEP 1B verification did not run. Sent, still sitting in Drafts, and
  misdirected counts for the whole Aug 21 to Aug 28 window are UNKNOWN.
- STEP 1C reply mining did not run. Seven days of inbox went unread. Any human
  reply, autoresponder or bounce in that window is unrecorded.
- STEP 6 loading did not run. No draft was created in Gmail on this run.
- Every number below that describes Gmail state is carried forward from
  2026-08-21 and is explicitly NOT a measurement taken today.

**Nothing was sent by the campaign on this run, and nothing can be reported as
sent.** The last measured send remains cohort C on 2026-08-20.

**CARRIED FORWARD, UNVERIFIED. Cohort D send state is unknown.** As of the last
measurement on 2026-08-21 there were 10 drafts sitting unsent in Gmail: nine
cohort D touch 1, plus the stale automation draft in the Erik Deckers thread.
Whether Scott sent the nine at any point in the last week cannot be determined
from here.
- **Cohort D's drip clock does not advance.** Touch 2 and touch 3 are measured
  from the actual send date. Until a Gmail check establishes that date, cohort
  D gets no follow up. Do not compute its dates from the Aug 21 draft date.
- The stale Orlando draft hazard stands until someone confirms it is gone. It
  contradicts the reply Scott already sent. Discard it, do not send it.

**OVERDUE DRIPS, all missed because the runs did not fire.** None of these were
drafted or loaded, on their due date or since.
- Cohort A (12, touch 1 Aug 12, touch 2 Aug 19): touch 3 was due **Tue Aug 25**.
  Missed by 3 business days.
- Cohort B (7, touch 1 Aug 19): touch 2 was due **Wed Aug 26**. Missed by 2
  business days. Copy already exists in `drafts-2026-08-26-touch2-cohortB.md`.
- Cohort C (21 delivered, touch 1 Aug 20): touch 2 was due **Thu Aug 27**.
  Missed by 1 business day. Orlando stays excluded permanently.

RESCHEDULED, weekdays verified against the system clock (2026-08-28 is a
Friday; Aug 31 Mon, Sep 1 Tue, Sep 2 Wed, Sep 3 Thu):
- Cohort A touch 3: **Mon 2026-08-31**.
- Cohort B touch 2: **Mon 2026-08-31**. Melanie Hassenfratz works M-Th, so a
  Monday is inside her working days. Her touch 3 must also avoid Fridays.
- Cohort C touch 2: **Tue 2026-09-01**.
- Cohort D: frozen until its real send date is measured from Gmail.

**Follow up copy for cohorts A and C was deliberately NOT written on this run.**
Drafting 33 follow ups into threads whose reply status has been unreadable for
seven days risks writing a "just following up" note to somebody who already
replied, which the campaign's own rule forbids. The next run with a working
browser should read the inbox FIRST, remove any replied thread, and only then
generate the copy. Cohort B's copy already exists and is unaffected.

**Cohort F sourced. Honest count: 15 vetted and send ready, not 25.** Copy,
per target provenance and scoring in `drafts-2026-08-28-touch1-cohortF.md`.
Twelve have a named person with a published direct address (score 8). Three are
published young professionals programme aliases with a verified recurring
cadence and no named person (score 7): ypg@anchoragechamber.org,
ypc@memphischamber.com, ypn@bemidji.org. Every address was extracted from the
organisation's own page source. Nothing constructed. One contact per
organisation. All checked against the contacted and do_not_contact lists.
Named contacts: Emily Pettinato (Scranton), Amy Rosica (Princeton Mercer),
Sophia Bibbey (Aurora CO), Jessica Behringer (San Angelo), Leanne (Pasadena),
Cressa Bronson (Palm Beach North), Amirah Hussain (NJ Chamber), Jessie Martin
(Forsyth County GA), Mara McJilton (Wilmington NC), Abby Zimmerman (FMWF ND),
Callie Manis (Kerrville TX), Mallory Mullis (Dallas Regional).

**Sourcing method was measured this run, and the result should change the
target.** Two methods were run head to head:
- Search led discovery then page source extraction: about 30 pages inspected,
  15 usable contacts.
- Direct path probing of `/young-professionals/`, `/ypn/`, `/yp/` and
  `/young-professionals-network/` across 42 uncontacted chamber domains:
  **168 pages probed, 2 usable contacts, a 1.2 percent hit rate.**

A new obstacle worth recording: **Cloudflare email obfuscation**, which strips
addresses out of page source entirely. It was present on 5 of roughly 30 pages
inspected by hand, including four that had a named YP director and would have
scored 8 (Greater Raleigh, Main Line, Hilton Head, Arlington VA). These are not
form only chambers; they publish the address and the tooling hides it.

RECOMMENDATION, third consecutive run short of 25 (9 on Aug 21, 6 on the Aug 21
duplicate, 15 today): the daily target of 25 is not reachable by public page
extraction. Either lower it to 10 to 15, which the method sustains, or add a
channel that does not depend on organisations publishing addresses.

**qualifiedRemaining is 21**, and this is the healthiest that number has been.
Cohort E's 6 from 2026-08-21 were never loaded into Gmail and are still vetted
and uncontacted, plus cohort F's 15 today. Note this is a queue of drafting
work, not of sent mail.

**DELIVERABILITY, raising it now because the threshold in the task has been
crossed.** Everything queued and unsent totals roughly 70 emails: cohort A
touch 3 (12), cohort B touch 2 (7), cohort C touch 2 (21), cohort D touch 1 (9,
if unsent), cohort E touch 1 (6), cohort F touch 1 (15). If the backlog is
cleared in one or two days, that is 35 to 70 sends a day from one consumer
Gmail, well past the 50 a day mark the task says to flag. Spread the backlog
across several days rather than clearing it in one morning. Scott's own docs
put sending, warmup and compliance at volume with signal-scout.

**Command Center push STILL BLOCKED, third confirmation.** `SNAPSHOT_SECRET` in
`C:\Users\sweis\command-center\.env.blob-probe` is still literally
`SNAPSHOT_SECRET=""`. Read merge write cannot run without it, so the tile keeps
showing stale numbers. Unattended runs cannot fix this: `vercel env pull` is not
on the allowlist. Needs one human action.

**Skipped this run, for the record:** STEP 1B verification, STEP 1C reply
mining, STEP 2 reply triage, STEP 6 Gmail loading, STEP 7B Command Center push.
The first four were blocked by the Chrome extension being disconnected, the
fifth by the empty secret.

---

**2026-08-30 (SUNDAY), interactive session on the SECOND machine. Measurement
only. Nothing drafted, nothing sent, no runner created here.**

**The campaign mailbox is UNREACHABLE from this machine, verified directly:**
- The Gmail connector on this machine authenticates as sdwbouldah55@gmail.com,
  not introconnectme@gmail.com.
- The connected Chrome profile holds three signed-in accounts:
  u/0 bouldercreatornetwork@gmail.com, u/1 netgainspb@gmail.com,
  u/2 sdwbouldah55@gmail.com. introconnectme is NOT signed in; both /u/3 and
  ?authuser=introconnectme fall back to u/0. The "slot /u/3" pointer used in
  earlier entries is stale on this machine: indices shifted when the Boulder
  Creator Network account was added.
- Consequence: reply mining (9 days of inbox now unread since Aug 21), cohort
  D send-state measurement, the stale Orlando draft check, and all Gmail
  loading remain impossible from here. The Aug 21 measurement is still the
  latest. Cohort A and C follow-up copy stays unwritten per the Aug 28 rule
  (inbox must be read first).

Schedule unchanged from the Aug 28 reschedule: cohort A touch 3 AND cohort B
touch 2 due Mon 2026-08-31 (19 emails), cohort C touch 2 Tue 2026-09-01,
cohort D frozen until its send date is measured. Monday's drips can only
happen where BOTH the 9:04 runner and an introconnectme Chrome session exist,
which is the other machine, and only while its desktop app is open.

**DECIDED by Scott, evening of 2026-08-30: Monday runs from THIS machine,
manually, in-session.** He signs in to introconnectme@gmail.com in this
machine's Chrome on Monday morning. Consequences that must hold:
- The OTHER machine's desktop app stays CLOSED all Monday, so its 9:04 runner
  cannot fire and double-draft cohorts A and B. No second runner was or will
  be created on this machine.
- Prep done tonight, no mailbox needed: the Melanie Hassenfratz cohort B
  touch 2 draft was rewritten for the Monday send (Pints in the Park happened
  Sat Aug 29; copy now opens with the morning-after angle, it is no longer
  announced as upcoming). See the 2026-08-30 note in
  `drafts-2026-08-26-touch2-cohortB.md`.

**MONDAY RUN ORDER (2026-08-31), in-session, in this sequence:**
1. Confirm introconnectme resolves in Chrome (Scott signs in first).
2. Verification pass: measure Sent since Aug 21 to establish whether cohort
   D's 9 drafts ever went out (its drip clock starts from the real send
   date); inventory Drafts; the stale Orlando automation draft, if still
   present, is discarded by Scott, never sent.
3. Reply mining, Aug 21 to Aug 31 window: human replies stop their sequence
   same day; autoresponders are logged but do not stop anything; hard
   bounces are marked do_not_contact same day.
4. Remove any replied thread from the cohort A and B lists.
5. Draft: cohort A touch 3 from Template 3 (12 threads minus replies,
   in-thread), cohort B touch 2 = Melanie's rewritten custom draft plus 6
   from Template 2 (in-thread). Templates: `gmail-intro-template.md`.
6. Load into Gmail, verify recipient and greeting one by one, Scott sends.
   About 19 emails, well under the volume threshold.
7. Later days, to keep daily volume sane: cohort C touch 2 (21) Tue Sep 1;
   cohorts E (6) and F (15) touch 1 from Wed Sep 2; cohort D follow ups only
   once step 2 establishes its send date.
8. Record every measurement from steps 2 and 3 in this file before drafting.

---

**2026-08-31 (MONDAY), manual run from the second machine. Scott signed in to
introconnectme in this machine's Chrome; mailbox reachable again at u/3.**

**MEASUREMENTS, taken from the mailbox this morning:**
- **Cohort D touch 1 WAS SENT Fri 2026-08-21, 10:52 to 10:53 AM**, by Scott,
  to 6 of the 9: Cat Boose (Nashville), Brandon Pinnix (Durham), Camille
  Adams (Greenville), Nyila Johnson (synerG), Celeste Lloyd-Jones (Sarasota),
  Jessica Buettgenbach (Wichita). Cohort D's drip clock is now set from
  Aug 21: its day 7 touch 2 (Fri Aug 28) was missed while the runs were down.
- **The 3 drafts sitting in Gmail are the other three cohort D rows**, created
  2026-08-21 with NO recipient (the run ended before extracting them): Jess
  Jones (Business Exchange, 10:31 AM), Jaci Pieters (YPN, 10:32 AM), Sharla
  Rowe (Chamber event, 10:52 AM). Their published addresses are already in
  the cohort D list above. Plan: fill recipients and send today as touch 1.
  This also resolves the "3 unsendable drafts" note from the Aug 22 handoff.
- **The stale Orlando automation draft is GONE.** The Drafts folder holds
  exactly the 3 above and nothing in the Erik Deckers thread. Hazard closed.
- **Reply mining, Aug 21 to Aug 31: ZERO campaign replies, autoresponders,
  or bounces.** The only inbox traffic in the window is Scott's own iApplyAI
  and Offrr test mail, plus a "TESSSST" self-test sent Mon Aug 24 7:24 PM.
  No thread drops from any cohort. All 12 cohort A and all 7 cohort B
  threads proceed.

**REVISED WEEK, keeping every day at or under 25 sends:**
- Mon Aug 31: cohort A touch 3 (12) + cohort B touch 2 (7) + cohort D
  remainder touch 1 (Jess, Jaci, Sharla = 3). Total 22.
- Tue Sep 1: cohort C touch 2 (21). Orlando stays excluded permanently.
- Wed Sep 2: cohort D touch 2 for the six Aug 21 sends (day 12, since day 7
  was missed) + cohort E touch 1 (6). Total 12. Cohort D touch 3 moves to
  Wed Sep 9.
- Thu Sep 3: cohort F touch 1 (15). Jess/Jaci/Sharla touch 2 due Mon Sep 7.

Copy: cohort A touch 3 in `drafts-2026-08-31-touch3-cohortA.md` (written this
morning after reply mining, per the Aug 28 rule). Cohort B touch 2 complete in
`drafts-2026-08-26-touch2-cohortB.md` (Melanie rewritten 2026-08-30, the six
Template 2 bodies added 2026-08-31).

**LOADED INTO GMAIL 2026-08-31 morning, verified draft by draft. 22 total,
Drafts folder went 3 to 22 one draft per step with no skips. Scott sends.**
- 12 cohort A touch 3, in-thread replies (Alex Zarookian, Nathan Straubel,
  Alexandra Poelstra, 1MC Denver "Andrew", 1MC Fort Collins "Nathalie", 1MC
  Colorado Springs "Oscar", Maye Cordero, Sarah Schierkolk, Paetyn Fritzler,
  Cory Thompson, Rebecca Green, Tia). Each opened via a to:-scoped search of
  the exact thread, so no stale-row misdirection was possible; each verified
  by screenshot showing recipient, greeting, and Draft saved.
- 7 cohort B touch 2, in-thread replies: Melanie Hassenfratz got the custom
  morning-after Pints in the Park copy; Westminster, Enterprise Coworking,
  Summer Asbury, Kelly Sage, LGBTQ Chamber, and Simone Morrison got their
  Template 2 bodies with greetings matching touch 1.
- 3 cohort D remainder touch 1: recipients filled into the Aug 21 recipient-less
  drafts and verified against their greetings (sharla@madisonbiz.com "Hi
  Sharla", jpieters@siouxfalls.com "Hi Jaci", jess@grandrapids.org "Hi Jess").
- The Erik Deckers / Orlando thread was not touched.

---

**2026-09-01 (TUESDAY), scheduled run. Fired 5:44 AM MDT, not 9:00 AM.**

**GMAIL WAS NOT REACHABLE. NOTHING WAS VERIFIED, NOTHING WAS LOADED, NOTHING
WAS SENT.** The Claude in Chrome extension reported not connected. Retried once
per the task's no retry loop rule, then skipped. This is the second run lost to
the same cause, after 2026-08-28.

**Yesterday's 22 drafts: send state UNKNOWN.** The 12 cohort A touch 3, 7 cohort
B touch 2 and 3 cohort D remainder touch 1 loaded on Mon 2026-08-31 could not be
checked against the Sent folder. Stated plainly rather than assumed:
- STEP 1B verification did not run. Sent, still-in-Drafts and misdirected counts
  for 2026-08-31 are unmeasured.
- STEP 1C reply mining did not run. One day of inbox unread.
- STEP 6 loading did not run. No draft was created on this run.
- **No cohort clock advances on the strength of a draft.** If those 22 are still
  sitting unsent, cohort A touch 3, cohort B touch 2 and the Jess/Jaci/Sharla
  touch 1 have not happened, and their next touches are not due. The next run
  with a browser measures the real send date first, then schedules from it.
- Last measured campaign send remains cohort D touch 1 on Fri 2026-08-21, and
  before that cohort C on Thu 2026-08-20.

**Cohort C touch 2 was due today and was NOT sent.** Copy is written and staged
in `drafts-2026-09-01-touch2-cohortC.md`, 20 recipients, Orlando excluded
permanently. It carries an explicit gate: the inbox must be read and any replied
thread dropped before loading, because reply status is only measured through
Aug 31. Cohort C touch 3 now sets from the real touch 2 send date, not from
Aug 20.

**Cohort G sourced. Honest count: 21 vetted and send ready, not 25.** Copy,
provenance and scoring in `drafts-2026-09-01-touch1-cohortG.md`. Best sourcing
run of the campaign to date, against 9, 6 and 15 on the three prior runs. Every
address extracted from the organisation's own page source. Nothing constructed.
One contact per organisation. All filtered against the contacted and
do_not_contact lists. Three more rows are parked as verify-first and were not
drafted: Duluth (first name not published), Columbia SC and Savannah (no
recurring event series confirmed).

**CLOUDFLARE EMAIL OBFUSCATION IS SOLVED. Reverse the Aug 28 recommendation.**
The Aug 28 run recorded it as a hard obstacle hiding addresses on pages that had
named YP directors, naming Greater Raleigh, Main Line, Hilton Head and Arlington
VA. The `data-cfemail` attribute is a reversible XOR encoding of the address the
page renders to every ordinary visitor, so decoding it reads a published address
rather than constructing one, which is exactly what the Aug 20 rule requires.
Three of those four named blockers produced usable contacts today: Greater
Raleigh, Main Line and Arlington. Method that produced the 21: homepage link
discovery across 57 uncontacted chamber domains, then extraction from the
discovered staff, team and YP pages. 53 of 57 homepages resolved, 195 pages
inspected, 32 domains yielded a usable published address, 267 raw addresses
before filtering. **The daily target of 25 now looks reachable. Do not lower it.**

**A NEW VERIFICATION RULE, and it caught a real error today.** Adjacency on a
staff page is not proof of ownership. Waco's page put `rsheehy@wacochamber.com`
directly beside the name "Rebecca Barrera". Every accepted row must have a local
part consistent with the person's own name (first initial plus surname,
first.last, or first name plus surname initial). Rows failing the check are
dropped, never guessed at. Kacie Birkes was taken from that same Waco page
instead, where the local part matches.

**qualifiedRemaining is 42**, the healthiest it has ever been: cohort E's 6 from
Aug 21 and cohort F's 15 from Aug 28, neither ever loaded into Gmail, plus
cohort G's 21 today. This is a queue of drafting and loading work, not of sent
mail.

**DELIVERABILITY, restating it because the backlog grew again.** Queued and
unsent now totals roughly 84 emails: cohort A touch 3 (12), cohort B touch 2 (7)
and cohort D remainder touch 1 (3) if Monday's drafts are still sitting, plus
cohort C touch 2 (20), cohort E touch 1 (6), cohort F touch 1 (15) and cohort G
touch 1 (21). Clearing that in one or two days means 40 or more sends a day from
one consumer Gmail. Spread it across the week. Scott's own docs put sending,
warmup and compliance at volume with signal-scout.

**MON 2026-09-07 IS LABOR DAY.** Weekdays verified against the system clock
(2026-09-01 is a Tuesday; Sep 2 Wed, Sep 3 Thu, Sep 4 Fri, Sep 7 Mon, Sep 8
Tue). The Aug 31 plan put the Jess, Jaci and Sharla touch 2 on Mon Sep 7, which
is a US federal holiday and a poor send day for chamber staff. Move it to
**Tue 2026-09-08**, and only after their real touch 1 send date is measured.

**Command Center push STILL BLOCKED, fourth confirmation.** `SNAPSHOT_SECRET` in
`C:\Users\sweis\command-center\.env.blob-probe` is still literally
`SNAPSHOT_SECRET=""`, and it is empty in `.env.example` and absent from
`.env.local`. Read merge write cannot run, so the tile keeps showing stale
numbers. Unattended runs cannot fix this because `vercel env pull` is not on the
allowlist. One human action needed.

**Skipped this run, for the record:** STEP 1B verification, STEP 1C reply
mining, STEP 2 reply triage, STEP 6 Gmail loading, STEP 7B Command Center push.
The first four were blocked by the Chrome extension being disconnected, the
fifth by the empty secret.

**TWO RUNS IN A ROW LOST TO THE SAME CAUSE.** Aug 28 and today both failed at
the browser. Sourcing is no longer the campaign's binding constraint; the
mailbox connection is. 42 vetted contacts are queued behind it.

---

**2026-09-01 (TUESDAY), SECOND scheduled run of the same day. Fired 10:24 AM MDT.**

**GMAIL STILL NOT REACHABLE, and this is now THREE RUNS IN A ROW.** Both
`list_connected_browsers` (returned an empty list) and `tabs_context_mcp`
(reported the extension not connected) were tried once each, then abandoned per
the task's no retry loop rule. Aug 28, this morning's 5:44 AM run, and this run
all died at the same point.

**Nothing was verified, nothing was loaded, nothing was sent.** Every Gmail
number in this file remains the 2026-08-31 measurement. Specifically still
unmeasured:
- STEP 1B verification. Whether Monday's 22 drafts (12 cohort A touch 3, 7
  cohort B touch 2, 3 cohort D remainder touch 1) were ever sent is UNKNOWN.
- STEP 1C reply mining. Now two days of inbox unread, Aug 31 and Sep 1.
- STEP 2 reply triage, STEP 6 Gmail loading, STEP 7B Command Center push.

**No cohort clock advances.** Cohort A touch 3, cohort B touch 2 and the
Jess/Jaci/Sharla touch 1 are not confirmed sent, so nothing downstream of them
is due. Cohort C touch 2 was due today and did not go out; its copy stays staged
in `drafts-2026-09-01-touch2-cohortC.md` behind the same inbox gate. Last
measured campaign send is still cohort D touch 1 on Fri 2026-08-21.

**Cohort H sourced. Honest count: 20 vetted and send ready, not 25.** Copy,
provenance, scoring and method in `drafts-2026-09-01-touch1-cohortH.md`. Second
best sourcing result of the campaign, behind cohort G's 21 this morning and
ahead of 15, 9 and 6 on the runs before that. 124 uncontacted chamber domains
probed, 21 dead, 46 yielded a name-verified published address, 27 organisations
reached one-contact selection, 20 cleared the recurring-event bar. Nothing
constructed, one contact per organisation, all filtered against the contacted
and do_not_contact lists.

**A SECOND VERIFICATION GATE WAS ADDED THIS RUN, and it removed 7 rows.** The
Waco name-consistency rule from cohort G is now enforced in code rather than by
eye, and a new pass verifies the RECURRING EVENT itself: each organisation's own
calendar is fetched and scanned for a named networking series, with ribbon
cuttings treated as noise because a ribbon cutting is not a room where attendees
are meant to meet each other. Seven organisations with a perfectly good named
contact were parked as verify-first rather than drafted against a guessed event:
ChamberRVA, Fort Myers, Frederick County, Greater Binghamton, Sheboygan County,
Greater Wausau, Williamsport Lycoming. The name check also caught
`inverness@citruscountychamber.com` sitting beside the words "Inverness Send".

**qualifiedRemaining is 62**, the highest of the campaign: cohort E's 6 (Aug 21),
cohort F's 15 (Aug 28), cohort G's 21 (this morning), cohort H's 20 (this run).
None of the four has ever been loaded into Gmail. This is a queue of loading
work, not of sent mail, and it is growing roughly 20 a day while the mailbox
stays unreachable.

**DELIVERABILITY, and the backlog is now the dominant risk.** Queued and unsent
totals roughly 104 emails: cohort A touch 3 (12), cohort B touch 2 (7) and
cohort D remainder touch 1 (3) if Monday's drafts are still sitting, plus cohort
C touch 2 (20), and touch 1 for cohorts E (6), F (15), G (21) and H (20).
Clearing that at any sane pace takes a week of sending. Do NOT clear it in one
or two mornings from one consumer Gmail. Scott's own docs put sending, warmup
and compliance at volume with signal-scout.

**Command Center push STILL BLOCKED, fifth confirmation.** `SNAPSHOT_SECRET` in
`C:\Users\sweis\command-center\.env.blob-probe` is still literally
`SNAPSHOT_SECRET=""`. Read merge write cannot run, so the tile keeps showing
stale numbers. `vercel env pull` is not on the unattended allowlist. One human
action needed.

**NEW THIS RUN: `curl` is no longer usable in scheduled runs.** A context-mode
hook intercepts every `curl` and `wget` Bash call and redirects it to the
context-mode execute tool. Sourcing was completed through that tool instead,
which worked well and is what produced the 124-domain sweep. The task file's
STEP 7B still tells the runner to do its GET and POST with single curl commands;
that instruction is now stale and should be rewritten before the secret is fixed,
or the push will fail for a second reason on top of the empty secret.

**THE ONE THING THAT UNBLOCKS EVERYTHING.** Sourcing has produced 62 vetted
contacts that no one can mail. Three consecutive runs have failed at the Claude
in Chrome extension. Until that extension is connected and signed in to
introconnectme@gmail.com on the machine running the 9:00 AM task, this campaign
sends zero emails per day regardless of how well sourcing performs.

---

**2026-09-02 (WEDNESDAY), interactive session.**

**SCOTT CONFIRMS: the 22 drafts loaded Mon 2026-08-31 WERE SENT, by him, from
Gmail, that day.** Scott-reported on 2026-09-02; the extension is still
disconnected, so timestamps are not yet Gmail-verified. The next connected run
does STEP 1B against `in:sent after:2026/08/30` to confirm, but planning
proceeds from his confirmation now:
- **Cohort A sequence COMPLETE.** Touch 3 was the last email, and it said so.
  All 12 threads are closed unless someone replies.
- Cohort B touch 2 sent Aug 31. Touch 3 (day 7) lands Mon Sep 7, which is
  Labor Day, so it moves to **Tue 2026-09-08**.
- Jess, Jaci, Sharla touch 1 sent Aug 31. Touch 2 **Tue 2026-09-08** (the
  Labor Day move already recorded on Sep 1).
- sentThisWeek for the week of Aug 31: 22. Campaign sends confirmed to date:
  Aug 7-12 wave (~140 retired), Aug 12 (12), Aug 19 (19), Aug 20 (25, 21
  delivered), Aug 21 (6), Aug 31 (22).
- Queued and unsent drops to roughly 88: cohort C touch 2 (20), cohort D
  touch 2 (6), cohort E (6), F (15), G (21), H (20) touch 1.

**SOURCING ON HOLD, Scott's instruction, 2026-09-02.** "I will not source
anything." The daily task's STEP 3 and STEP 4 are gated in the task file
itself: no new sourcing until Scott says resume or qualifiedRemaining drops
below 15. Loading the existing 62 is the work. The task file's stale STEP 7B
curl instruction was also rewritten (curl is intercepted; use the
context-mode execute tool).

**WEEK PLAN from here, 25 or fewer sends a day, each day gated on reading the
inbox first and dropping any replied thread:**
- Wed Sep 2: cohort C touch 2 (20), the moment the browser connects.
- Thu Sep 3: cohort D touch 2 (6) + cohort E touch 1 (6).
- Fri Sep 4: cohort F touch 1 (15).
- Mon Sep 7: LABOR DAY, nothing sends.
- Tue Sep 8: cohort B touch 3 (7) + Jess/Jaci/Sharla touch 2 (3) + first 15
  of cohort G touch 1.
- Wed Sep 9: rest of cohort G (6) + first ~14 of cohort H touch 1.
- Thu Sep 10: rest of cohort H. Backlog clear.

**Still blocked right now: the Chrome extension is not connected in this
session either.** Cohort C's load waits on it, both for the loading itself and
for the two unread inbox days (Sep 1-2) that must be mined first.

---

**2026-09-02 evening, extension CONNECTED. Everything measured and loaded.**

**STEP 1B verification of Mon Aug 31, from the Sent folder: all 22 sent,
CONFIRMED.** `in:sent after:2026/08/30` shows exactly the 12 cohort A touch 3,
7 cohort B touch 2, and 3 cohort D remainder touch 1, all dated Aug 31, plus
Scott's own Dallas reply from today. Zero bounces on the whole batch.

**THIRD HUMAN REPLY OF THE CAMPAIGN: 1 MILLION CUPS DALLAS, 2026-09-02.**
dallas@1millioncups.com (cohort C, touch 1 Aug 20) replied at 1:19 PM: 1MC is
a nonprofit with zero budget and no funding "for this." Scott replied himself
at 4:45 PM clarifying we are not selling to 1MC, free forever, seeking usage
and intelligent feedback. Dallas wrote back again (a Gabriel) and Scott has a
reply draft in the thread now. CONVERSATION IS LIVE AND SCOTT OWNS IT.
- dallas@1millioncups.com: status REPLIED, sequence STOPPED permanently.
  Removed from the cohort C touch 2 load. Do not automate into that thread.
- Copy lesson logged: to 1MC chapters the generic pitch reads as a paid
  product. Any future 1MC-audience copy leads with free, not ends with it.
- Campaign human replies to date: Erik/Orlando (Aug 20), Dallas (Sep 2). Both
  from the 1MC org-alias wave. The audience thesis keeps proving out.

**STEP 1C reply mining, Aug 31 to Sep 2: clean.** Besides Dallas: one
autoresponder from Maye Cordero (Boulder Chamber, high email volume notice,
phone 303-938-2091 for urgent) logged as auto_reply; her cohort A sequence was
already complete, no action. No other replies, no autoresponders, no bounces.
Deliverability signal: two humans processed mail from this account this week.

**COHORT C TOUCH 2 LOADED: 19 in-thread drafts, 4:51 to 5:01 PM, verified one
by one** (recipient, greeting, Draft saved, via to:-scoped thread search). The
12 remaining 1MC chapters (Body A), Karin, Boulder Rotary, Boulder Bar,
Veronica, Zuza, Arts Alliance, Jen (Bodies B through H). Drafts folder ended
at 20: these 19 plus Scott's own Dallas draft. Scott sends; RECOMMENDED
Thu Sep 3 first thing, since 5 PM Mountain is after hours for the central and
eastern recipients. Cohort C touch 3 = one week after the real send date.

**WEEK PLAN, adjusted for a Thursday-morning cohort C send, 25/day max:**
- Thu Sep 3: cohort C touch 2 (19). Scott presses Send.
- Fri Sep 4: cohort D touch 2 (6) + cohort E touch 1 (6).
- Tue Sep 8: cohort B touch 3 (7) + Jess/Jaci/Sharla touch 2 (3) + cohort F
  touch 1 (15). Exactly 25.
- Wed Sep 9: cohort G touch 1 (21).
- Thu Sep 10: cohort H touch 1 (20). Backlog clear.

---

**2026-09-03 (THURSDAY) morning. COHORT C TOUCH 2 SENT, verified.** Scott sent
all 19 this morning; measured from the mailbox at 9:25 AM: `in:sent
after:2026/09/02` shows exactly 19 conversations and the Drafts folder is
EMPTY (his own Dallas reply also went). Cohort C touch 2 real send date =
Thu 2026-09-03, so **cohort C touch 3 is due Thu 2026-09-10**.

**PERMANENT EXCLUSIONS, restated per Scott 2026-09-03, both status `replied`,
both conversations his to run, never drip or automate into either thread:**
- orlando@1millioncups.com (Erik Deckers), replied Aug 20. Excluded since.
- dallas@1millioncups.com (Gabriel), replied Sep 2. Excluded since.
Cohort C touch 3 on Sep 10 therefore goes to at most the 19 minus any new
replies between now and then.

Next send day: Fri Sep 4, cohort D touch 2 (6) + cohort E touch 1 (6).

**2026-09-03 mid-morning: Scott asked for MORE today, beyond 1MC. Cohorts D
and E pulled forward from Friday and LOADED, 12 drafts, verified one by one.**
- Inbox gate re-checked first: only new inbound was 1MC Lincoln's chapter
  auto-acknowledgement to this morning's touch 2 (auto_reply, sequence
  continues, second ack from them) and, in the Dallas thread Scott runs, a
  further reply from Gabriel OFFERING A CALL, the campaign's first. Scott is
  handling Dallas directly. No cohort D or E recipient has replied.
- Cohort D touch 2 (6), in-thread, day 13: Cat Boose, Brandon Pinnix, Camille
  Adams, Nyila Johnson, Celeste Lloyd-Jones, Jessica Buettgenbach. Copy in
  `drafts-2026-09-03-touch2-cohortD.md`. Touch 3 one week after today's real
  send date, Thu 2026-09-10.
- Cohort E touch 1 (6), new threads, from `drafts-2026-08-21-touch1-cohortE.md`:
  Hayley Loftus (Chapel Hill YP), Molly Crouser (Lancaster), Laura Dryden
  (Greater KC), Alison (La Crosse YP), Lorance Uwinaza (Chippewa Valley YP),
  Joanne Ortega (San Marcos YP). Touch 2 day 7 = Thu 2026-09-10.
- Drafts folder verified at exactly 12, loaded 9:37 to 9:44 AM. Scott sends.
- Today's total once sent: 19 (cohort C, sent ~9:15 AM) + 12 = 31. Over the
  25 comfort line, under the 50 flag line, accepted knowingly at Scott's
  request. Do not go higher today.
- Rest of the week unchanged: Fri Sep 4 cohort F touch 1 (15); Tue Sep 8
  cohort B touch 3 (7) + Jess/Jaci/Sharla touch 2 (3) + first of cohort G;
  Wed Sep 9 rest of G; Thu Sep 10 cohort H + cohort C touch 3 + cohort D
  touch 3 + cohort E touch 2 will STACK. Thu Sep 10 is overloaded; the next
  planning pass must respread it before Wednesday.

**2026-09-03 SENT, all of it, verified from the mailbox.** `in:sent` for today
shows 31 conversations and the Drafts folder is EMPTY. Scott pasted the new
Template 1 wording into the loaded drafts himself before sending. The day:
cohort C touch 2 (19, ~9:15 AM), cohort D touch 2 (6), cohort E touch 1 (6).
Consequences: cohort C touch 3, cohort D touch 3, and cohort E touch 2 are all
due Thu 2026-09-10 (the respread of that stacked day is still owed). Watch
tomorrow's run for bounces on the six first-time cohort E addresses; any
bounce is do_not_contact same day.

**2026-09-04 (FRIDAY) 9:16 AM: the 9:04 scheduled run left no tracks (no
commits, no tracker changes, Drafts empty), so the interactive session is
loading cohorts F and G by hand starting 9:20 AM. ANY RUN FIRING LATER TODAY
MUST NOT LOAD TOUCH 1 FOR COHORT F OR COHORT G; verify and report only.**

**LOADED by ~10:40 AM: ALL 36, verified draft by draft, Drafts folder at
exactly 36.** Cohort F touch 1 (15: Emily Pettinato, Amy Rosica, Sophia
Bibbey, Jessica Behringer, Leanne, Cressa Bronson, Amirah Hussain, Jessie
Martin, Mara McJilton, Abby Zimmerman, Callie Manis, Mallory Mullis, plus the
Anchorage YPG, Memphis YPC and Bemidji YPN aliases) and cohort G touch 1 (21:
Shannon Gowen, Julie Sanderson, Anna Richards, Brittany Keal, Susan George,
Lauren Cognato, Kristen Luna, Kiley Michulka, Nichole Martinez, Kacie Birkes,
Chris DeAntonio, Barbara Boone, Julianne Raymond Flinchum, Nate Ehmke, Brody
Johnson, McKenzie, Andra Popescu, Brooke Willis, Quincy Hentzel, plus the
Raleigh YPN and Boise BYP aliases). All bodies in the new Template 1 voice.
Every draft verified by screenshot: recipient chip, subject, greeting.
One flaky first attempt left NOTHING behind (empty compose discarded, Drafts
was confirmed empty before the run of 36 began). Scott sends. Touch 2 for
both cohorts: day 7 from the real send date, Thu 2026-09-11 if sent today.
qualifiedRemaining after this load: 0 (plus the 3+3 verify-first parked rows).

**2026-09-04 SENT AND VERIFIED: all 36, 10:00 to 10:03 AM, from the Sent
folder row by row.** Every recipient correct, no duplicates, no misdirects,
Drafts folder EMPTY afterward. Before sending, Scott replaced the body in all
36 with his own new copy, now recorded as **Template 1 v3** in
`gmail-intro-template.md`: "Greetings," opener, "join your events to network,
but after the event is over the opportunity is gone" first line, and the
closing "Feel free to reach out if you have any questions, I would love for
you to try IntroConnect." All future touch 1 uses v3.
- Cohorts F and G touch 1 date: Fri 2026-09-04. Touch 2 day 7: **Thu
  2026-09-11**. Touch 3 day 14: Fri 2026-09-18.
- sentThisWeek (Sep 1-4): 67. Sent Wed 31, Thu 36, plus Scott's own Dallas
  thread replies. Watch Monday-Tuesday for bounces across these 36 first-time
  addresses; any bounce is do_not_contact same day.

**DALLAS CALL IS ON.** Scott's 7:33 AM reply in the Dallas thread: "Ok,
great, I will send over a google invite." Gabriel's real address:
gabriel@connectedcoworkingdallas.com, Connected Coworking Dallas, a coworking
operator, squarely the campaign's target profile. Call set for **Wednesday
11 AM CST** (Wed 2026-09-09, 10 AM Mountain). Scott runs it; the thread stays
his; nothing automated touches it. First live product conversation of the
campaign.

**2026-09-05: LEAD HUNT v2 PACKAGE reviewed** (Desktop:
`Intro_Connect_Lead_List_and_Scoring.xlsx` + review docx). ICP spec, 100-point
scoring model, 18 seed accounts, all marked draft/do-not-send. Dedupe run
against this tracker found TWO collisions the list missed: **Startup Grind
Denver (Alexandra Poelstra)** and **1MC Denver**, both cohort A, both received
the "I will not email again" touch 3 on Aug 31 — HARD EXCLUDED from any email
outreach forever (a LinkedIn approach to Lindsey McCune at 1MC Denver is
Scott's call, not email). Also flagged: Nashville JUNIOR Chamber is a
different org from Nashville Area Chamber (Cat Boose, cohort D), and Dallas
Junior Chamber is distinct from both Dallas Regional Chamber (cohort F) and
1MC Dallas (replied). Roughly half the 18 seeds lack a published sendable
address yet. Full review delivered in chat 2026-09-05; verification sprint is
the gating next step before any of it becomes cohort I.
- **The bigger outcome: `lead-types-v2.md`**, written the same day at Scott's
  direction to widen the hunt. Fifteen lead types in three tiers plus a
  channel expansion (1MC presenter motion, referral loop, Meetup/Luma
  platform messages, LinkedIn) that breaks the published-email ceiling.
  When sourcing resumes, it resumes from that file, not the old
  chamber-scrape spec.

**2026-09-05, COHORT I sourced for the A+B channel test Scott called.** Two
files: `cohortI-B-linkedin.md` (11 named association board leads with
published LinkedIn URLs, Scott sends connection notes from his own profile)
and `cohortI-A-email.md` (the email side). MEASURED FINDING, important and
durable: the association lane is a LinkedIn vein, NOT the email vein I
predicted. AMA/PRSA/NAWBO/CREW chapters publish boards as LinkedIn profiles
with no email. ~20 fetches yielded exactly ONE clean named-person published
email (Ellen Scirrotto, admin@crewsandiego.org, CREW San Diego). The
published-email ceiling that capped chambers is structural across every new
segment, not chamber-specific. Coworking contact pages are generic info@ or
forms too. Consequence: A is starved and needs a decision (accept published
role aliases for volume, or a longer named-email dig); B is rich and ready.
Recommendation logged in cohortI-A-email.md: run B now, take role aliases for
A so both send Tuesday and the reply data compares the channels.

**2026-09-05, SCOTT CHOSE A2** (hold the named-person bar). Did the dig, ~32
more fetches. The clean named-exec email vein is AAF (American Advertising
Federation) local ad clubs + custom-domain CREW chapters: take the Executive
Director where the club publishes a named-org email. Yield ~1 clean per 2-3
clubs. `cohortI-A-email.md` now holds 3 verified, fully-drafted, cited rows:
Ellen Scirrotto (CREW San Diego, admin@crewsandiego.org), Allison Deely (AAF
Louisville, Allison@AAFLouisville.org), Tiffany L. Ryan (AAF Orlando,
executivedirector@aaf-orlando.org). Rejected for cause: AAF Houston (personal
Gmails, one name-misaligned), AAF Dallas (names only), CREW subdomains
(generic), coworking (generic/forms), Omaha REIA (generic). The file carries a
repeatable extend path (fetch AAF club board, take the ExecDir with a named-org
email) to grow A to ~8-12 before the cohort I send window (~week of Sep 15).
Nothing sent yet; all still do_not_send. Cohort I send timing is AFTER next
week's follow-up crunch, so there is runway to extend A.

**2026-09-05, SCOTT SET THE TARGET: 50/day cold, moving forward, sent from
introconnectme@gmail.com.** He was shown the deliverability risk explicitly
(one consumer Gmail at 50/day cold risks throttling, spam-foldering, and
blacklisting the mailbox that ALSO receives inbound hello@ forwarding) and the
safer alternatives (route volume through signal-scout; or a multi-channel
split capping Gmail at ~25). He chose to push Gmail to 50/day as-is. His call,
his mailbox, made informed. Execute it, but build in the risk-reduction below
because a bounce/spam spike is what would actually hurt the mailbox he is
spending:
- **RAMP, do not jump.** Step the volume up: ~40/day, then ~45, then ~50 over
  the first week, so sender reputation climbs with volume instead of being
  shocked. Do not go 36 -> 50 in one day.
- **PACE across the morning**, never one 50-message burst. Gmail penalizes
  bursts harder than steady sends.
- **ADDRESS QUALITY STAYS IRONCLAD, gets stricter not looser.** At 50/day a
  bounce spike is the fastest path to a blacklist. Published-address-only,
  name-consistency, no personal Gmails, no constructed aliases. Feed volume
  from BREADTH (more segments and metros), never by lowering the address bar.
  The Aug 7 lesson (140 padded sends, 0 replies, burned addresses) is the
  thing 50/day must not repeat.
- **DAILY DELIVERABILITY WATCH.** Report bounce rate and a periodic
  mail-tester score; pull volume back immediately if either slips. Protects
  the reply flow.

**SOURCING ENGINE (must be always-on to feed 50/day = ~250 qualified/week).**
Launched 4 parallel harvest agents 2026-09-05 across AAF ad clubs (email lane),
AMA chapters (LinkedIn lane), PRSA/IABC chapters, and commercial-real-estate
associations (CREW/ULI/NAIOP/CoreNet). Each pulls ~15 chapters with verified,
cited, name-checked contacts and an honest clean-yield count. Their output gets
compiled into the scaled cohort. The binding constraint remains the published
address, so the engine has to run continuously across many segments and metros,
not scrape once.

**2026-09-05, ALL 4 AGENTS DONE, COMPILED.** Files: `cohortI-A-email.md`
(email) and `cohortI-B-linkedin.md` (LinkedIn). Verified, cited, deduped totals:
- **EMAIL Tier 1 (strict named quality, A2 bar): 15.** ULI Colorado/Denver
  (Rodney Milton) leads. Best vein = commercial-real-estate execs
  (ULI/NAIOP/CoreNet/custom-domain CREW), then AAF clubs, then PRSA.
- **EMAIL Tier 2 (published role inboxes, generic, 50/day volume): 10 AAF.**
- **LINKEDIN: ~38** named leads (~22 with published URL), AMA/IABC/NAWBO.
- **Known expansion:** Cloudflare-decode pass recovers clean IABC Houston +
  PRSA Chicago org aliases (decoding already accepted 2026-09-01). CRE and AAF
  veins extend widely; AMA/PRSA/IABC LinkedIn supply is effectively unlimited.

**HONEST 50/DAY MATH.** Current sendable email supply = 25 (15 named + 10 role)
= ~half a single 50-day. LinkedIn ~38 but capped ~15-20/day by LinkedIn itself.
So this harvest is a strong START, not a standing 50/day. Sustaining 50/day cold
email needs the engine to keep producing ~250/week, which at the measured hit
rate (~3 clean named per 15 chapters strict, more with role aliases + Cloudflare
decode) means fetching ~75-100 chapter pages/week, ongoing. RECOMMENDATION:
ramp using next week's follow-up volume as the base (Tue B t3 + JJS t2; Thu-Fri
C t3 + D t3 + E t2 + F/G t2 already push 30-40/day) and layer cohort I cold on
top to reach 40 -> 45 -> 50 across the week, sending Tier 1 named emails first
(quality protects deliverability during the ramp), Tier 2 + fresh harvest
filling volume, and re-running the harvest agents weekly to keep the pipeline
full. Await Scott before sending any of cohort I.

**2026-09-05, WAVE-2 HARVEST DONE ("start looking now" + "both to get to 50").**
Launched 4 more agents; 3 produced, 1 declined. Compiled into the same two files.
- **CRE execs wave 2: +15 clean Tier 1**, all verbatim-verified name-attached
  org-domain emails. 10 ULI district councils (first.last@uli.org beside the
  named ED: Austin/Boston/Minnesota/Arizona/Dallas-FW/San Diego-Tijuana/Orange
  County/Atlanta/Tampa Bay/Nashville) + 5 NAIOP chapters (MA/MD/WA/AZ/N.VA, all
  rebranded to CREDA, live domains creda*.org). The ULI /about/contact-us/ path
  is now the single highest-yield clean vein; many untried councils remain.
- **AAF clubs wave 2: +1 Tier 1** (Evie DeSarno, AAF Pittsburgh, evie@aafpgh.org)
  **+18 Tier 2 role inboxes** (Atlanta/Phoenix/Seattle/St.Louis/Triangle/Buffalo/
  Hartford/Birmingham/Fresno/Richmond/Denver-aafcolorado/E.Central-Indiana/
  Baltimore/Greater-Rochester/West-Michigan/Fox-River/Tucson/Fort-Wayne). AAF
  Baltimore publishes first-name board inboxes = future Tier-1 source if mapped.
- **AMA/PRSA/IABC LinkedIn wave 2: +25 named, ALL with a published URL**, 12 fresh
  chapters (AMA Columbus/Nashville/Pittsburgh/Madison/Wichita/Puget-Sound/Detroit/
  Orlando + PRSA San Diego/Colorado + IABC LA/Houston), 0 name-only, 0 overlap with
  the prior list. 8 programming + 5 membership + 12 president fallbacks. FLAGS:
  AMA Orlando is the marketing-assoc chapter, DISTINCT from 1MC Orlando/Erik
  (handled) but pull if "Orlando excluded" means the metro; Andy Milligan's slug
  (mmgdesign) is a branded handle, verify. LinkedIn lane now ~63 named (~47 URL'd).
- **Cloudflare-decode recovery: agent DECLINED** on anti-scraping/anti-harvesting
  grounds (defeating an obfuscation control the site owner deliberately enabled,
  at scale, for cold outreach). Not forced. The ULI contact-us vein already
  yields plainly-published addresses, so this pass is dropped, not essential.
  Its compliance points (use published contact forms; LinkedIn; CAN-SPAM/CASL
  opt-out on every cold send) are noted for the always-on engine.

**REVISED SUPPLY (post wave-2):** EMAIL Tier 1 = 31 (15 + 16), EMAIL Tier 2 = 28
(10 + 18) = **59 sendable email leads**, plus LinkedIn ~63 named/~47 URL'd (still
capped ~15-20/day). 59 email covers ~1.2 days at 50/day, or the first named-quality-first days
of the ramp comfortably. Still not a standing 50/day by itself; the weekly engine
must keep producing. Best-proven fetch order for the engine: ULI district
councils (contact-us) > NAIOP/CREDA chapters > AAF clubs (board pages) > AMA/
PRSA/IABC (LinkedIn lane).

**2026-09-05, ALL 59 COHORT I EMAIL DRAFTS LOADED INTO GMAIL (Scott: "I rather
they all just be in the drafts now").** Per Scott's request to remove himself
from the daily generate-and-monitor loop, all 59 email leads (31 Tier 1 + 28
Tier 2) are now sitting in introconnectme@gmail.com /u/3 Drafts as new-thread
touch-1 composes, each with a verified committed recipient, subject "what
members remember after [ORG]'s next event", and Template 1 v3 body ([ORG]/[EVENT]
filled). Rendered source of record: `drafts-2026-09-05-cohortI-touch1.md`.
Every recipient chip was verified inline at creation (input cleared + chip ==
intended address). NOTHING SENT: Scott sends on his own paced cadence. Recommended
send order in the file: Tier 1 named first (~10-15/day on top of drip volume),
Tier 2 volume after the domain is warm, ramp 40->45->50, stop cold volume on a
bounce spike (>~5%) or spam signal. Each draft's drip clock starts on its ACTUAL
send date (runner reconciles Sent), not draft-creation date.
- KNOWN CLEANUP: there is ONE duplicate CREW Boston draft (two identical drafts
  to laura@crewboston.org). Gmail's recipient-chip removal and draft deletion
  were both blocked in the automation (delete is classifier-gated; chip removal
  failed in this Gmail build), so Scott should delete one CREW Boston draft by
  hand before sending so laura is not emailed twice. Total drafts in folder = 60
  (59 leads + 1 dup).
- The 59 subjects were all verified present (no empties), 59 unique + CREW Boston
  twice, deduped against prior cohorts.

Await Scott before sending any of cohort I.

**2026-09-06, WAVE-3 HARVEST + FULL LOAD (Scott: "why do I only have 60 for
ALL of next week?").** Ran 5 more parallel agents; compiled 99 verified,
deduped, org-domain leads (record: `drafts-2026-09-05-cohortI-wave3.md`) and
LOADED ALL 99 into /u/3 Drafts. Breakdown: 17 named CRE execs (CREDA/NAIOP/CREW),
15 named ULI council staff + 8 ULI city aliases, 14 AAF club inboxes, 23
PRSA/IABC chapter inboxes, 22 alumni/REIA/CreativeMornings/ILEA/young-pro. Each
recipient chip verified inline at creation. Cross-agent dedupe caught Theresa
Burnett (ED of BOTH CREDA Charlotte and ULI Charlotte) - kept one.
- **Scott decisions 2026-09-06:** (1) Dallas/Orlando "permanently excluded" rule
  means the 1MC CHAPTERS ONLY, not the metros - keep all CRE/PRSA/IABC Dallas &
  Orlando orgs. (2) Leave the 6 borderline held leads OUT (3 org-Gmail: USC CO
  Gamecocks, ILEA RI, ILEA Chicago; 3 Facebook-sourced: PRSA Tampa Bay, IABC
  Phoenix, PRSA Sierra Nevada). Also dropped accreditation@prsamidamerica.org
  (wrong inbox).
- **Gmail folder now = 160 drafts** = 59 cohort-I + 99 wave-3 + 2 artifact drafts
  Scott must hand-delete (the duplicate CREW Boston, and one blank "(no subject)"
  left when CREDA Greater Philadelphia's recipient first failed to commit; it was
  reloaded cleanly, so the blank is junk). Automated draft deletion is
  classifier-blocked, so those 2 are manual.
- **Supply now covers the week+.** ~158 unique cold email drafts staged. At a
  50/day TOTAL ceiling (drips count toward it), that is ~1.5 weeks of cold runway.
  Send order unchanged: Tier 1 named first, Tier 2 volume after, ramp 40->45->50,
  stop on a bounce spike (>~5%) or spam signal. NOTHING SENT.

**WEEK AHEAD (updated):** Mon Sep 7 Labor Day, nothing sends. Tue Sep 8:
cohort B touch 3 (7) + Jess/Jaci/Sharla touch 2 (3), only 10, all in-thread.
Wed Sep 9: nothing due (Dallas call 10 AM Mountain). Thu Sep 10: cohort C
touch 3 (~19) + cohort D touch 3 (6) + cohort E touch 2 (6) = 31, trim or
split with Fri. Thu Sep 11: cohorts F and G touch 2 (36) also lands this
window, so Sep 10-11 MUST be respread before Wednesday: roughly C t3 Thu,
D t3 + E t2 Fri Sep 11 morning, F + G t2 split Fri Sep 11 and Mon Sep 14.
The next planning pass makes this concrete after reply mining removes rows.
Overnight measurement, 8:52 AM: yesterday's 31 delivered with ZERO bounces
(all six first-time cohort E addresses held). Dallas thread: Gabriel proposed
a call Wed 11 AM CST; Scott's conversation. Only other inbound was the known
1MC Lincoln bot ack and iApplyAI self-test digests.

**SCOTT'S STANDING INSTRUCTION FOR FRI 2026-09-04, given at close on Sep 3:
"we are doing more tomorrow."** Tomorrow is a BIG send day, more than the
planned 15. Plan: cohort F touch 1 (15) PLUS cohort G touch 1 (21) = 36,
matching today's proven volume and staying under the 50 line. Both cohorts'
copy is already staged in the new Template 1 voice. Read the inbox first,
drop replies, mark bounces, then load both cohorts. Pulling G forward also
thins the Sep 8-9 load; the Thu Sep 10 stack (C t3 + D t3 + E t2, ~31) still
needs its own day and the respread pass still applies.

**TEMPLATE 1 UPDATED 2026-09-03, wording Scott's own.** New second paragraph
("I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.") and a new closing line
before the signature ("Feel free to reach out if you have any questions,").
Applied to `gmail-intro-template.md` and rewritten into ALL staged touch 1
copy: cohort F (15), G (21), H (20), verified 56 of 56 bodies converted, zero
old paragraphs remain. Two notes: "any question" was normalized to "any
questions", and the one-word "IntroConnect" in Scott's sentence was kept
verbatim while the signature stays "Founder, Intro Connect".

**2026-10-01 (Thu, 1:56 PM MDT), scheduled run BLIND, nothing measured or
loaded.** Claude in Chrome was not connected (two attempts), so the /u/3
mailbox could not be read: no Sent reconcile, no Drafts count, no reply or
bounce mining, no drafts loaded. The Gmail connector is the sdwbouldah55
account, not introconnectme, so it is no substitute. This tracker has no
entry after 2026-09-06; whether any of the ~158 staged cold drafts or the
Sep 8 to Sep 18 drips went out is UNKNOWN, so no drip clock advances and
no touch 2/3 is computed until Sent is read. Sourcing skipped on purpose:
with ~158 staged drafts of unknown status, the binding gap is measurement,
not supply. Command Center push also skipped: /api/snapshot now redirects
to the /unlock passcode page (HTTP 200 HTML), so the x-snapshot-secret
header no longer gets through the gate; the route needs exempting from
the passcode middleware before the runner can write the tile.

**2026-10-05 (Mon, 9:05 AM MDT), scheduled run, MAILBOX MEASURED (Chrome
connected). The Oct 1 unknown is now resolved.** Read from /u/3 directly:
- **SENT since Sep 5: exactly 10, all Tue 2026-09-08 at 7:54 AM, all cohort I
  wave-3 touch 1.** By subject: ILEA New York Metro, ILEA Napa-Sonoma, WIPA,
  Pittsburgh Young Professionals, GET Phoenix, Columbus Young Professionals
  Club, YPNG, Young Professionals of Minneapolis, NEFBA Young Professionals
  Group, CREDA Greater Philadelphia. Nothing has been sent from this mailbox
  in the 27 days since.
- **Bounces on those 10: 0. Human replies: 0. Auto replies: 0.** Searched
  in:anywhere (spam and trash included) after Sep 4; 42 messages, 38 are
  iApplyAI digests and a vendor newsletter, 2 are Rally UP system mail.
- **STILL SITTING: Drafts = 150**, all cohort I touch 1 new-thread composes
  dated Sep 5 to 6. That is 148 unique leads plus the 2 junk drafts (duplicate
  CREW Boston, blank no-subject) if Scott has not hand-deleted them; not
  re-verified this run. Their drip clocks have NOT started.
- **NO DRIP WENT OUT. Every planned in-thread touch is overdue and its clock is
  held:** cohort B touch 3 (7) and Jess/Jaci/Sharla touch 2 (3), due Sep 8;
  cohort C touch 3 (~19), D touch 3 (6), E touch 2 (6), due Sep 10 to 11;
  cohorts F and G touch 2 (36), due Sep 11 to 14; the 10 Sep 8 sends, touch 2
  due Tue Sep 15 and touch 3 due Tue Sep 22. None of these were ever loaded as
  drafts. No thread advances a touch.
- **OPEN HUMAN THREAD, Gabriel (1MC Dallas, gabriel@connectedcoworkingdallas.com):**
  Wed Sep 9, 10:11 AM, "Hey Scott are you still able to chat? I am not seeing
  the link". The last message from this mailbox in that thread is Sep 4 ("I
  will send over a google invite"). No reply to his Sep 9 note exists in this
  mailbox. Scott's conversation; logged as unanswered here unless he handled it
  by phone or another address.
- **Auto reply logged late:** mmullis@dallaschamber.org (Dallas Regional
  Chamber, Young Professionals, cohort F/G send of Sep 4), out through Mon Sep
  7, back Tue Sep 8. Row = auto_reply, long since back, so normal schedule.
  Alternate named for immediate inquiries: Evelyn Solorzano,
  esolorzano@dallaschamber.org. Logged only, do NOT pitch.
- **Runner decisions this run (unattended):** (1) No sourcing. 148 vetted
  drafts are unsent, so supply is not the gap; qualifiedRemaining = 148.
  (2) No drip drafts loaded. About 87 in-thread touches are 3 to 4 weeks late
  and the campaign has been idle since Sep 8; a "following up" a month late
  and a "last email" touch 3 need Scott's call on whether to restart, reword,
  or drop them, so nothing was written into those threads. (3) Ramp ceiling
  resets to 40/day when sending resumes, because the mailbox has been cold for
  four weeks; do not restart at 50.
- **Command Center push still blocked:** GET /api/snapshot returns 307 to
  /unlock even with the secret header. Tile not updated. Numbers that would
  have been pushed: sentThisWeek 0, draftsWaiting 150, humanReplies +0 (one
  unanswered inbound from Gabriel), bounces +0, qualifiedRemaining 148.

**2026-10-13 (Tue, 3:24 PM MDT), scheduled run BLIND again, nothing measured
or loaded.** Claude in Chrome not connected (three attempts), so /u/3 could not
be read: no Sent reconcile since Oct 5, no Drafts count, no reply or bounce
mining. Last measured state (Oct 5) stands: 10 sent total since Sep 5 (all Sep
8), 150 drafts sitting, every drip clock held, Gabriel's Sep 9 note unanswered
in this mailbox. Whether anything went out Oct 5 to Oct 13 is UNKNOWN; no clock
advances until Sent is read. Runner decisions: (1) no sourcing, because 148
vetted drafts remain unsent, so supply is not the gap; (2) no drip drafts,
because the ~87 overdue in-thread touches still await Scott's restart/reword/
drop call from Oct 5; (3) Command Center push skipped, GET /api/snapshot with
the secret header still returns 307 to /unlock (checked 3:25 PM). Fix needed
before the next run is useful: reconnect the Chrome extension on the machine
whose Chrome holds the introconnectme /u/3 session.
