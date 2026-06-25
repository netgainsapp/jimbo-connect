# Host acquisition sequence (cold outbound)

Three touches over about a week, aimed at people who run a recurring event.
Load this into signal-scout as an Intro Connect tenant sequence. Every link
should be a tracked link (signal-scout token `{track_click_url}`) so opens and
clicks attribute back. Keep the brand voice: plain, warm, no dashes, no emoji.

Merge fields: `{first_name}`, `{event_name}`, `{cadence}` (e.g. "monthly"),
`{city}`, `{track_click_url}`.

Sending rules: business hours, weekday, one thread (replies stay in-thread),
real reply-to, physical address and one-click unsubscribe in the footer
(signal-scout handles the footer). Stop the sequence on any reply.

---

## Touch 1 — Day 0

**Subject:** the morning after {event_name}

Hi {first_name},

You spent real effort getting the right people into the room for {event_name}.
Then everyone goes home, the business cards scatter, and the connections you
created quietly go cold by Monday.

I built Intro Connect to fix exactly that. After your event, it turns the guest
list into a private, searchable directory your attendees actually use. They save
each other, add a quick note, and message directly. You stay at the center of
the network you created, every {cadence}.

Worth a quick look? Here is a two minute walkthrough: {track_click_url}

Scott

---

## Touch 2 — Day 3 (no reply)

**Subject:** how it works in five minutes

Hi {first_name},

Quick follow up. Setting up {event_name} on Intro Connect takes about five
minutes:

1. Create the event and we generate a join code.
2. Your guests join with the code or a link, and add a photo so people remember
   them.
3. After the night, the directory stays live. Attendees save contacts, keep
   private notes, and message each other.

Free to start, no credit card, and free for your guests forever. If your
attendees do not use it, you walk away.

Start your first event here: {track_click_url}

Scott

---

## Touch 3 — Day 7 (no reply)

**Subject:** should I close this out?

Hi {first_name},

I do not want to crowd your inbox, so this is my last note. Hosts who run a
recurring room like {event_name} tend to get the most out of Intro Connect,
because the network compounds every {cadence} instead of resetting.

If now is not the time, no worries at all. If you want me to spin up
{event_name} so you can see it with real names, just reply and I will set it up.

Either way, thanks for building good rooms in {city}.

Scott
