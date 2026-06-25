# Free-signup nurture sequence (inbound / self-serve)

Triggered when a host signs up for the free plan. Goal: get them to set up a
first event, run it, and feel the post-event value, then upgrade when they
outgrow the free limits. These send from the product (Resend, already wired),
not from signal-scout. Plain voice, no dashes, no emoji.

Merge fields: `{host_name}`, `{site_url}`, `{first_event_url}`.

Recommended delivery: email 0 immediately on signup, then the rest paced by a
scheduled tick (the same GitHub Actions pattern the blog cron uses), each gated
so it only sends if the prior step has not been completed.

---

## Email 0 — Immediately on signup

**Subject:** welcome to Intro Connect

Hi {host_name},

You are in. Intro Connect turns each event you host into a private, searchable
directory of everyone who came, so the connections keep going after the night
ends.

The fastest way to feel it is to set up your first event. It takes about five
minutes and you get a join code to share.

Set up your first event: {first_event_url}

Reply to this email any time. A real person reads it.

Scott

---

## Email 1 — Day 2 (if no event created yet)

**Subject:** the five minute setup

Hi {host_name},

If you have five minutes, here is all it takes to get your first event live:

1. Name the event and pick a date. We generate the join code.
2. Share the code or link with your guests.
3. Ask people to add a photo when they join, so the room remembers them.

You can even paste your guest list from any tool and we will create the
accounts for you.

Start here: {first_event_url}

Scott

---

## Email 2 — Day 5 (if event created, before or after it runs)

**Subject:** the part that happens after the event

Hi {host_name},

The night itself is only half the value. The other half is the week after, when
your attendees open the directory, save the people they met, and send the
messages they meant to send.

A few things that help it land:

- Remind guests at the event that the directory is live and how to join.
- Add a short welcome note so the room feels like yours.
- Drop in any speakers or sponsors so attendees can find them too.

Open your event: {first_event_url}

Scott

---

## Email 3 — Day 10 (upgrade nudge, only if active)

**Subject:** when you are ready for more rooms

Hi {host_name},

Glad to see Intro Connect working for you. The free plan covers one event and a
directory that stays live for a month. When you are ready to run more rooms,
keep directories permanent, or connect attendees across every event you host,
the paid plans open that up.

- Starter, 39 dollars a month: a few events and bigger rooms.
- Pro, 99 dollars a month: unlimited events, your whole network in one place,
  and your own custom domain.

See the plans: {site_url}/#pricing

No rush, the free plan is yours for as long as you want it.

Scott
