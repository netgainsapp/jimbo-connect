import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "jimbo_connect")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

users = db["users"]
events = db["events"]
event_attendees = db["event_attendees"]
saved_contacts = db["saved_contacts"]
event_sponsors = db["event_sponsors"]
messages = db["messages"]
email_templates = db["email_templates"]
blog_post = db["blog_post"]
blog_topic = db["blog_topic"]
app_flags = db["app_flags"]
event_invites = db["event_invites"]
outreach_leads = db["outreach_leads"]
suppressed_emails = db["suppressed_emails"]
news_article = db["news_article"]
# Saved agendas from the Agenda Builder. Anonymous drafts are NOT stored here:
# they live in the visitor's own browser, so there is nothing to orphan. A row
# appears only once someone signs in and claims their draft.
agendas = db["agendas"]
# Host announcements shown on the event page, plus one read marker per user per
# event (not per announcement: see announcements.py).
event_announcements = db["event_announcements"]
announcement_reads = db["announcement_reads"]
# One survey per event, keyed by event_id rather than an id of its own: the
# event IS the survey's identity. One response per person per event, which is
# what makes a second submission an edit instead of a second vote.
event_surveys = db["event_surveys"]
survey_responses = db["survey_responses"]
# A host's rewrites of the emails sent in their name. One row per (host,
# template); absence means the default applies, so reset is a delete.
host_email_templates = db["host_email_templates"]


async def ensure_indexes():
    await users.create_index("email", unique=True)
    await events.create_index("join_code", unique=True)
    # created_by is queried on nearly every host action (create/list/nurture).
    await events.create_index("created_by")
    await event_attendees.create_index([("event_id", 1), ("user_id", 1)], unique=True)
    await saved_contacts.create_index([("owner_id", 1), ("contact_id", 1)], unique=True)
    await event_sponsors.create_index("event_id")
    await messages.create_index([("thread_id", 1), ("sent_at", 1)])
    await messages.create_index([("to_user_id", 1), ("read_at", 1)])
    await email_templates.create_index("template_id", unique=True)
    await blog_post.create_index("slug")
    # Every agenda read is "mine", newest first.
    await agendas.create_index([("user_id", 1), ("updated_at", -1)])
    await event_announcements.create_index([("event_id", 1), ("created_at", -1)])
    await announcement_reads.create_index(
        [("event_id", 1), ("user_id", 1)], unique=True
    )
    await event_surveys.create_index("event_id", unique=True)
    # Unique so a double submit is an edit, not a second vote. The upsert in
    # surveys.respond relies on this pair, and without the constraint a race
    # between two clicks writes two rows and quietly doubles that person's
    # weight in the averages.
    await survey_responses.create_index(
        [("event_id", 1), ("user_id", 1)], unique=True
    )
    await host_email_templates.create_index(
        [("host_id", 1), ("template_id", 1)], unique=True
    )
    await blog_post.create_index([("status", 1), ("published_at", -1)])
    await event_invites.create_index([("event_id", 1), ("email", 1)], unique=True)
    await event_invites.create_index([("joined_at", 1), ("reminder_step", 1)])
    await outreach_leads.create_index("email", unique=True)
    await outreach_leads.create_index([("status", 1), ("created_at", -1)])
    await suppressed_emails.create_index("email", unique=True)
    await news_article.create_index("slug", unique=True)
    await news_article.create_index([("status", 1), ("published_at", -1)])
