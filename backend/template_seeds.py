"""Default email templates seeded on first run.

Each template has:
  template_id   — stable ID used by the API
  category      — for grouping in the admin UI
  title         — what Jim sees in the picker
  blurb         — one-line description in the picker
  subject       — supports {var} merge tokens
  body          — supports {var} merge tokens
  system        — True for templates the SERVER actually sends.
                  These cannot be deleted (still editable).
                  Right now: password-reset, invitation.

Available merge variables (always-on for both client & server):
  host_name, site_url, event_name, event_date, event_time,
  event_location, join_code, attendee_name, attendee_email,
  temp_password, sponsor_name, audience_description, reset_url
"""

DEFAULT_TEMPLATES = [
    # ----- System (server-sent) -----
    {
        "template_id": "password-reset",
        "category": "system",
        "title": "Password reset",
        "blurb": "Sent when an attendee uses 'Forgot password'.",
        "system": True,
        "subject": "Reset your Jimbo Connect password",
        "body": (
            "Hi {attendee_name},\n\n"
            "Tap this link to set a new password (or just log in — same link works):\n\n"
            "{reset_url}\n\n"
            "Link expires in 2 hours. If you didn't request this, ignore this email.\n\n"
            "— {host_name}"
        ),
    },
    {
        "template_id": "invitation",
        "category": "system",
        "title": "Invitation (with login)",
        "blurb": "Sent automatically when Jim imports an attendee.",
        "system": True,
        "subject": "You're invited to {event_name}",
        "body": (
            "Hi {attendee_name},\n\n"
            "You're invited to {event_name} on {event_date} at {event_location}.\n\n"
            "Log in to your private attendee directory:\n"
            "  {site_url}\n"
            "  Email:    {attendee_email}\n"
            "  Password: {temp_password}\n\n"
            "The directory fills in as more people join. After the event you can save "
            "contacts and add private notes.\n\n"
            "— {host_name}"
        ),
    },

    # ----- Per-event lifecycle (admin copy/paste) -----
    {
        "template_id": "save-the-date",
        "category": "event",
        "title": "Save the date",
        "blurb": "Pre-event invite — get them to commit.",
        "system": False,
        "subject": "You're invited: {event_name}",
        "body": (
            "Hi,\n\n"
            "I'm hosting {event_name} on {event_date} at {event_location}, and I'd "
            "love for you to be there.\n\n"
            "After the event, I'll add you to a private directory of everyone who "
            "came — a place to follow up, save contacts, and remember who you met. "
            "It's free, and the directory is yours forever.\n\n"
            "Reply and I'll add you to the list.\n\n"
            "— {host_name}"
        ),
    },
    {
        "template_id": "youre-in",
        "category": "event",
        "title": "You're in (manual)",
        "blurb": "Same as the auto invitation — copy if you'd rather hand-send.",
        "system": False,
        "subject": "Welcome to {event_name}",
        "body": (
            "Hi {attendee_name},\n\n"
            "You're confirmed for {event_name} on {event_date}.\n\n"
            "Your private attendee directory is ready: {site_url}\n"
            "  Email:    {attendee_email}\n"
            "  Password: {temp_password}\n\n"
            "After the event you can save contacts and add private follow-up notes.\n\n"
            "— {host_name}"
        ),
    },
    {
        "template_id": "day-of",
        "category": "event",
        "title": "Day-of reminder",
        "blurb": "Send the morning of.",
        "system": False,
        "subject": "Tonight: {event_name}",
        "body": (
            "Hi {attendee_name},\n\n"
            "Quick reminder — {event_name} is today at {event_time}, "
            "{event_location}.\n\n"
            "After the event, log in at {site_url} to save contacts and stay in "
            "touch with the folks you meet.\n\n"
            "See you tonight,\n— {host_name}"
        ),
    },
    {
        "template_id": "post-event",
        "category": "event",
        "title": "Thanks for coming",
        "blurb": "Sent the morning after. Drives directory logins.",
        "system": False,
        "subject": "Thanks for coming to {event_name}",
        "body": (
            "Hi {attendee_name},\n\n"
            "Thanks for coming last night.\n\n"
            "The full attendee directory is open: {site_url}\n\n"
            "Browse, save contacts, add private notes for follow-up. The directory "
            "is yours forever — no subscription, no fees.\n\n"
            "If anyone you wanted to meet wasn't there, let me know and I'll connect "
            "you next time.\n\n"
            "— {host_name}"
        ),
    },
    {
        "template_id": "reconnect",
        "category": "event",
        "title": "Reconnect (a month later)",
        "blurb": "Light-touch follow-up to keep the directory alive.",
        "system": False,
        "subject": "Still keeping in touch?",
        "body": (
            "Hi {attendee_name},\n\n"
            "It's been a few weeks since {event_name}. Has the directory been "
            "useful? Reached out to anyone yet?\n\n"
            "A few of your fellow attendees have moved companies, launched things, "
            "raised rounds since: {site_url}\n\n"
            "If there's someone you want a warm intro to, just reply.\n\n"
            "— {host_name}"
        ),
    },

    # ----- Marketing / outreach -----
    {
        "template_id": "what-is-jimbo",
        "category": "marketing",
        "title": "What is Jimbo Connect?",
        "blurb": "Send to a friend / prospect to explain the service.",
        "system": False,
        "subject": "A better way to follow up after networking events",
        "body": (
            "Hi,\n\n"
            "Quick share — I've started using something called Jimbo Connect for "
            "the networking events I host.\n\n"
            "It's a private directory of everyone who came: name, role, company, "
            "contact info, what they're looking for. After the event, attendees can "
            "browse, save contacts, and add private notes for follow-up.\n\n"
            "What it isn't: another social network. Nothing public. No algorithm. "
            "No subscription. Always free.\n\n"
            "What it is: a way to make sure the people you met don't disappear into "
            "a pile of half-remembered business cards.\n\n"
            "If you'd like an invite to the next event I host, just reply.\n\n"
            "— {host_name}"
        ),
    },
    {
        "template_id": "sponsor-pitch",
        "category": "marketing",
        "title": "Sponsor pitch",
        "blurb": "Approach a business about sponsoring.",
        "system": False,
        "subject": "Sponsor {event_name}?",
        "body": (
            "Hi {sponsor_name},\n\n"
            "I'm hosting {event_name} on {event_date}. Audience: "
            "{audience_description}.\n\n"
            "Wondering if you'd be open to sponsoring. Here's how it works:\n"
            "  1. Your tile sits at the top of the attendee directory — visible "
            "before, during, and forever after the event.\n"
            "  2. Optional 60-second intro from you at the event itself.\n\n"
            "There's no platform fee — sponsorship goes directly to event costs.\n\n"
            "Happy to share more if interested.\n\n"
            "— {host_name}"
        ),
    },
    {
        "template_id": "host-intro",
        "category": "marketing",
        "title": "Intro to the host",
        "blurb": "A short bio email to paste into intros.",
        "system": False,
        "subject": "Quick intro",
        "body": (
            "Hi {attendee_name},\n\n"
            "Quick intro — I'm {host_name}. I host small, curated networking events "
            "for founders, operators, and investors in the front range.\n\n"
            "If you've ever left a networking event and forgotten half the names, "
            "you'll like what we do next: a private directory of everyone who came "
            "stays online forever, with contact info and what each person is "
            "working on.\n\n"
            "If you'd like to come to the next one, reply and I'll send a join link.\n\n"
            "— {host_name}"
        ),
    },
]

CATEGORIES = [
    {"id": "system", "label": "Automated (sent by Jimbo)"},
    {"id": "event", "label": "Per-event emails"},
    {"id": "marketing", "label": "Marketing & outreach"},
]
