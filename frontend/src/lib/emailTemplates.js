// Email templates Jim can use. Variables in {curly_braces} get filled in
// from the selected event (or left as-is for him to edit).
//
// Available variables:
//   {host_name}           — Jim or whoever is logged in as admin
//   {site_url}            — the running app URL
//   {event_name}          — selected event name
//   {event_date}          — formatted date
//   {event_time}          — formatted time
//   {event_location}      — event location string
//   {join_code}           — 8-char join code
//   {attendee_name}       — placeholder, leave for personal merge
//   {attendee_email}      — placeholder
//   {temp_password}       — placeholder
//   {sponsor_name}        — placeholder
//   {audience_description}

export const EMAIL_TEMPLATES = [
  // ----- Per-event lifecycle -----
  {
    id: "save-the-date",
    category: "event",
    title: "Save the date",
    blurb: "Pre-event invite — get them to commit.",
    subject: "You're invited: {event_name}",
    body: `Hi,

I'm hosting {event_name} on {event_date} at {event_location}, and I'd love for you to be there.

After the event, I'll add you to a private directory of everyone who came — a place to follow up, save contacts, and remember who you met. It's free, and the directory is yours forever.

Reply and I'll add you to the list.

— {host_name}`,
  },
  {
    id: "youre-in",
    category: "event",
    title: "You're in (confirmation + login)",
    blurb: "Send after you import them. Includes login.",
    subject: "Welcome to {event_name}",
    body: `Hi {attendee_name},

You're confirmed for {event_name} on {event_date}.

Your private attendee directory is ready: {site_url}
  Email:    {attendee_email}
  Password: {temp_password}

The directory will fill in as more people join. After the event you can save contacts and add private follow-up notes.

— {host_name}`,
  },
  {
    id: "day-of",
    category: "event",
    title: "Day-of reminder",
    blurb: "Send the morning of.",
    subject: "Tonight: {event_name}",
    body: `Hi {attendee_name},

Quick reminder — {event_name} is today at {event_time}, {event_location}.

After the event, log in at {site_url} to save contacts and stay in touch with the folks you meet.

See you tonight,
— {host_name}`,
  },
  {
    id: "post-event",
    category: "event",
    title: "Thanks for coming",
    blurb: "Sent the morning after. Drives directory logins.",
    subject: "Thanks for coming to {event_name}",
    body: `Hi {attendee_name},

Thanks for coming last night.

The full attendee directory is open: {site_url}

Browse, save contacts, add private notes for follow-up. The directory is yours forever — no subscription, no fees.

If anyone you wanted to meet wasn't there, let me know and I'll connect you next time.

— {host_name}`,
  },
  {
    id: "reconnect",
    category: "event",
    title: "Reconnect (a month later)",
    blurb: "Light-touch follow-up to keep the directory alive.",
    subject: "Still keeping in touch?",
    body: `Hi {attendee_name},

It's been a few weeks since {event_name}. Has the directory been useful? Reached out to anyone yet?

A few of your fellow attendees have moved companies, launched things, raised rounds since: {site_url}

If there's someone you want a warm intro to, just reply.

— {host_name}`,
  },

  // ----- Marketing / outreach -----
  {
    id: "what-is-jimbo",
    category: "marketing",
    title: "What is Jimbo Connect?",
    blurb: "Send to a friend / prospect to explain the service.",
    subject: "A better way to follow up after networking events",
    body: `Hi,

Quick share — I've started using something called Jimbo Connect for the networking events I host.

It's a private directory of everyone who came: name, role, company, contact info, what they're looking for. After the event, attendees can browse, save contacts, and add private notes for follow-up.

What it isn't: another social network. Nothing public. No algorithm. No subscription. Always free.

What it is: a way to make sure the people you met don't disappear into a pile of half-remembered business cards.

If you'd like an invite to the next event I host, just reply.

— {host_name}`,
  },
  {
    id: "sponsor-pitch",
    category: "marketing",
    title: "Sponsor pitch",
    blurb: "Approach a business about sponsoring.",
    subject: "Sponsor {event_name}?",
    body: `Hi {sponsor_name},

I'm hosting {event_name} on {event_date}. Audience: {audience_description}.

Wondering if you'd be open to sponsoring. Here's how it works:
  1. Your tile sits at the top of the attendee directory — visible before, during, and forever after the event.
  2. Optional 60-second intro from you at the event itself.

There's no platform fee — sponsorship goes directly to event costs.

Happy to share more if interested.

— {host_name}`,
  },
  {
    id: "host-intro",
    category: "marketing",
    title: "Intro to the host (Jim)",
    blurb: "A short bio email Jim can paste into intros.",
    subject: "Quick intro",
    body: `Hi {attendee_name},

Quick intro — I'm Jim. I host small, curated networking events for founders, operators, and investors in the front range.

If you've ever left a networking event and forgotten half the names, you'll like what we do next: a private directory of everyone who came stays online forever, with contact info and what each person is working on.

If you'd like to come to the next one, reply and I'll send a join link.

— {host_name}`,
  },
];

export const TEMPLATE_CATEGORIES = [
  { id: "event", label: "Per-event emails" },
  { id: "marketing", label: "Marketing & outreach" },
];

const OVERRIDES_KEY = "jimbo_email_template_overrides_v1";

function loadOverrides() {
  try {
    return JSON.parse(localStorage.getItem(OVERRIDES_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveOverrides(map) {
  try {
    localStorage.setItem(OVERRIDES_KEY, JSON.stringify(map));
  } catch {
    // ignore
  }
}

export function getTemplate(id) {
  const base = EMAIL_TEMPLATES.find((t) => t.id === id);
  if (!base) return null;
  const ov = loadOverrides()[id];
  if (!ov) return base;
  return { ...base, subject: ov.subject ?? base.subject, body: ov.body ?? base.body };
}

export function getAllTemplates() {
  const ov = loadOverrides();
  return EMAIL_TEMPLATES.map((t) => {
    const o = ov[t.id];
    if (!o) return t;
    return { ...t, subject: o.subject ?? t.subject, body: o.body ?? t.body };
  });
}

export function saveTemplateOverride(id, subject, body) {
  const ov = loadOverrides();
  ov[id] = { subject, body };
  saveOverrides(ov);
}

export function resetTemplateOverride(id) {
  const ov = loadOverrides();
  delete ov[id];
  saveOverrides(ov);
}

export function isTemplateModified(id) {
  return Boolean(loadOverrides()[id]);
}

export function renderTemplate(template, ctx = {}) {
  const subject = mergeVars(template.subject, ctx);
  const body = mergeVars(template.body, ctx);
  return { subject, body };
}

function mergeVars(text, ctx) {
  return text.replace(/\{(\w+)\}/g, (m, key) => {
    return ctx[key] !== undefined && ctx[key] !== null ? String(ctx[key]) : m;
  });
}
