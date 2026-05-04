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


async def ensure_indexes():
    await users.create_index("email", unique=True)
    await events.create_index("join_code", unique=True)
    await event_attendees.create_index([("event_id", 1), ("user_id", 1)], unique=True)
    await saved_contacts.create_index([("owner_id", 1), ("contact_id", 1)], unique=True)
