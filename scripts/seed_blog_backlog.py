"""Seed the blog backlog: ten posts from growth/campaign/blog-topics.md.

Written by hand rather than generated, so the house rules in that file hold by
construction: no invented statistics, no made up customer stories, and every
product claim checked against what actually ships.

Each post carries an explicit published_at so the backlog reads as a year of
writing rather than ten posts appearing at once. Ordering is deliberate: posts
that lean on a feature are dated after that feature existed. Announcements,
the three question survey and the cross event directory all shipped in July
2026, so nothing before that date mentions them.

Idempotent: a slug that already exists is skipped, so re running this is safe.
Every post is checked against the real guardrails before it is written, so this
cannot put anything in the database the engine itself would have rejected.

Run it where MONGO_URL is set (Render shell, or locally with the var exported):

    python scripts/seed_blog_backlog.py            # dry run, prints a plan
    python scripts/seed_blog_backlog.py --apply    # writes
"""
import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from blog.guardrails import check_guardrails  # noqa: E402
from blog.schema import GeneratedPost, slugify  # noqa: E402
from blog.store import _existing_for_guardrails  # noqa: E402
from database import blog_post  # noqa: E402


def d(y, m, day):
    return datetime(y, m, day, 15, 0, 0, tzinfo=timezone.utc)


POSTS = [
    # ---------------------------------------------------------------- topic 1
    {
        "topic_id": 1,
        "published_at": d(2025, 12, 9),
        "title": "How to follow up after a networking event",
        "summary": (
            "The follow up almost never happens, and it is rarely because "
            "nobody wanted it. The information decays faster than the intention."
        ),
        "sections": [
            {
                "heading": "The problem is not motivation",
                "body": (
                    "You leave a good event genuinely meaning to reach three "
                    "people. By the time the week starts you have a first name "
                    "with no last name, a company you half remember, and a "
                    "business card in a coat pocket. The intention survived. "
                    "The information did not. Almost every failed follow up "
                    "looks like this, which is why advice about being more "
                    "disciplined tends not to help."
                ),
            },
            {
                "heading": "Write the reason down, not the person",
                "body": (
                    "A name on its own is useless a week later. What you need "
                    "is the reason you wanted to talk again. She is hiring a "
                    "designer in spring. He runs the same stack and has opinions "
                    "about it. That sentence is the whole value of the "
                    "conversation, and it is the first thing you forget. Write "
                    "it while you are still in the room, even badly."
                ),
            },
            {
                "heading": "Be specific and be quick",
                "body": (
                    "A message that refers to something you actually discussed "
                    "will almost always get a reply. A message that could have "
                    "been sent to anyone in the room usually will not. Speed "
                    "matters for the same reason: you are competing with the "
                    "reader's own fading memory of you, and that fades on the "
                    "same curve yours does."
                ),
            },
            {
                "heading": "Fix it for the whole room at once",
                "body": (
                    "Everything above is individual discipline, and individual "
                    "discipline does not scale to a room of fifty. The version "
                    "that scales is a directory of everyone who attended, so "
                    "that finding someone later is a search rather than an act "
                    "of memory. Intro Connect keeps that directory live after "
                    "the night ends, with photos, roles, and private notes only "
                    "you can see."
                ),
            },
        ],
        "cta": (
            "Your next event can keep its own directory. The free plan covers "
            "your first event and your guests never pay anything."
        ),
    },
    # ---------------------------------------------------------------- topic 6
    {
        "topic_id": 6,
        "published_at": d(2026, 1, 13),
        "title": "The 48 hours after your event matter most",
        "summary": (
            "Hosts pour their attention into the night itself. Most of the "
            "value is decided in the two days afterward, when nobody is looking."
        ),
        "sections": [
            {
                "heading": "The night is the easy part",
                "body": (
                    "Venue, food, name badges, running order. All of it is "
                    "visible, all of it gets attention, and all of it is over by "
                    "ten o'clock. The part that determines whether anyone counts "
                    "your event as valuable happens later, in private, with no "
                    "host in the room."
                ),
            },
            {
                "heading": "What decay actually looks like",
                "body": (
                    "On the night, a guest can picture five faces and recall why "
                    "each one mattered. The next morning they can name three. By "
                    "the end of the week they remember that it was a good room "
                    "without being able to reconstruct who was in it. Nothing "
                    "went wrong. Memory simply did what memory does."
                ),
            },
            {
                "heading": "Send one thing, not a campaign",
                "body": (
                    "The instinct is a long recap email with photos and thanks "
                    "and next dates. The version that works is shorter: here is "
                    "where to find everyone who was here. One useful link beats "
                    "five paragraphs of warmth, because it does something for "
                    "the reader instead of asking for their attention."
                ),
            },
            {
                "heading": "Give them somewhere to go back to",
                "body": (
                    "A recap email is read once and then buried. A directory is "
                    "somewhere a guest returns to in March when they finally "
                    "need the person they met in January. That difference, "
                    "between a message and a place, is most of what separates an "
                    "event that fades from one that keeps paying out."
                ),
            },
        ],
        "cta": (
            "Set up your next event in about five minutes and give the room "
            "somewhere to go back to."
        ),
    },
    # ---------------------------------------------------------------- topic 5
    {
        "topic_id": 5,
        "published_at": d(2026, 1, 27),
        "title": "Free alternatives to expensive event apps",
        "summary": (
            "Event software is priced for conferences. Most hosts are running "
            "something much smaller and paying for the wrong problem."
        ),
        "sections": [
            {
                "heading": "What the expensive tools are actually for",
                "body": (
                    "Ticketing, badge printing, check in hardware, session "
                    "tracking across many rooms. Those are real problems and "
                    "the paid tools solve them properly. If you are selling "
                    "tickets to hundreds of people across a multi day "
                    "programme, buy the thing built for that."
                ),
            },
            {
                "heading": "What most hosts actually need",
                "body": (
                    "A dinner, a mixer, a member evening. One room, one "
                    "evening, a guest list that fits on a page. None of the "
                    "expensive machinery applies, and paying for it means "
                    "funding a feature set you will never open."
                ),
            },
            {
                "heading": "Be honest about the gaps",
                "body": (
                    "Intro Connect does not sell tickets, print badges, or run "
                    "check in at a door. If you need any of those, we are not "
                    "the answer and pretending otherwise would waste your time. "
                    "Keep using a ticketing tool for the front door if you have "
                    "one."
                ),
            },
            {
                "heading": "Where the free option is genuinely better",
                "body": (
                    "The part after the event, which the expensive tools treat "
                    "as an afterthought and often switch off when the "
                    "conference ends. Our directory stays live, guests never "
                    "pay anything, and the free plan covers a real event rather "
                    "than a crippled demo of one."
                ),
            },
        ],
        "cta": (
            "Keep your ticketing tool if you need one, and run the part after "
            "the night on the free plan."
        ),
    },
    # --------------------------------------------------------------- topic 10
    {
        "topic_id": 10,
        "published_at": d(2026, 4, 21),
        "title": "How to get sponsors for a small event",
        "summary": (
            "Small events undersell themselves to sponsors by copying the "
            "logo tiers of events ten times their size."
        ),
        "sections": [
            {
                "heading": "Stop selling logo placement",
                "body": (
                    "Gold, silver and bronze tiers are borrowed from "
                    "conferences with thousands of attendees, where a logo is "
                    "genuinely worth something. At a dinner for twenty, nobody "
                    "is buying visibility. They are buying access to the "
                    "specific people in that room."
                ),
            },
            {
                "heading": "Sell the room, honestly",
                "body": (
                    "Tell a prospective sponsor who actually attends: the "
                    "roles, the kinds of companies, roughly how many. A "
                    "sponsor who knows exactly what they are getting and says "
                    "yes is worth more than one who agreed to a vague number "
                    "and feels misled afterward."
                ),
            },
            {
                "heading": "Give them something a person will see",
                "body": (
                    "A logo on a slide that shows for a minute is not a "
                    "deliverable. A place on the page every guest actually "
                    "opens, before and after the event, is. Intro Connect "
                    "builds a sponsor tile from a pasted link, so this costs "
                    "the host no design time and gives the sponsor something "
                    "durable."
                ),
            },
            {
                "heading": "Ask for less than you think",
                "body": (
                    "A first sponsorship that is easy to say yes to buys you a "
                    "relationship and something to point at next time. Hosts "
                    "routinely ask for a large number once, get declined, and "
                    "conclude that sponsors are not interested."
                ),
            },
        ],
        "cta": (
            "Add your sponsor to your next event page in about a minute by "
            "pasting their link."
        ),
    },
    # ---------------------------------------------------------------- topic 9
    {
        "topic_id": 9,
        "published_at": d(2026, 2, 10),
        "title": "Networking event ideas that actually connect people",
        "summary": (
            "Most networking formats let people talk to whoever they arrived "
            "with. A few force the mixing that everyone showed up hoping for."
        ),
        "sections": [
            {
                "heading": "Why the standard mixer underperforms",
                "body": (
                    "Open room, drinks, two hours, good luck. Confident people "
                    "do fine and everybody else talks to the person they came "
                    "with. The format is not neutral. It quietly rewards the "
                    "guests who needed the least help, which is the opposite of "
                    "what a host is trying to do."
                ),
            },
            {
                "heading": "Seat people rather than letting them settle",
                "body": (
                    "Assigned tables feel heavy handed for about ninety seconds "
                    "and then everyone relaxes into them. You are removing a "
                    "decision that guests find genuinely stressful. If you seat "
                    "by something other than industry, you also break up the "
                    "cluster of people who already know each other."
                ),
            },
            {
                "heading": "Give the room a job",
                "body": (
                    "A question everyone answers, a problem each table works on, "
                    "a short round where people say what they are looking for. "
                    "Structure is not the enemy of natural conversation. It is "
                    "the thing that gets people past the part where they are "
                    "deciding what to say."
                ),
            },
            {
                "heading": "Keep the mixing alive afterward",
                "body": (
                    "Every format above works for one evening. What none of them "
                    "does on its own is survive contact with Monday. A shared "
                    "directory of who was there lets the connections you "
                    "engineered keep working long after the tables are stacked."
                ),
            },
        ],
        "cta": (
            "Try one of these formats at your next event, and keep the room "
            "reachable afterward on the free plan."
        ),
    },
    # ---------------------------------------------------------------- topic 4
    {
        "topic_id": 4,
        "published_at": d(2026, 3, 10),
        "title": "How to run a founder dinner people remember",
        "summary": (
            "A dinner is not a small conference. The guest list is the product, "
            "and the host's job is mostly done before anyone arrives."
        ),
        "sections": [
            {
                "heading": "Curation is the whole thing",
                "body": (
                    "Nobody remembers the restaurant. They remember who was "
                    "across from them. The hours you spend deciding who to "
                    "invite are worth more than everything you will spend on the "
                    "evening itself, and they are the part most hosts rush."
                ),
            },
            {
                "heading": "Keep the table small enough for one conversation",
                "body": (
                    "Past a certain size a table stops being a dinner and "
                    "becomes several parallel dinners with bad acoustics. If you "
                    "cannot hear the far end, you have built a room, not a "
                    "table. Smaller than feels efficient is usually right."
                ),
            },
            {
                "heading": "Do the introductions yourself",
                "body": (
                    "You know why each person is there. Nobody else does. Two "
                    "sentences from the host about why these two should talk "
                    "will do more than an hour of unassisted mingling, because "
                    "you are supplying the context that strangers cannot."
                ),
            },
            {
                "heading": "Stay at the center of what you built",
                "body": (
                    "The reason to host is that you become the connective tissue "
                    "of a group that would not otherwise exist. That only "
                    "compounds if the group persists between dinners. Otherwise "
                    "each evening starts over, and the network you are "
                    "assembling never accumulates."
                ),
            },
        ],
        "cta": (
            "Give your table a private directory so the dinner keeps working "
            "after the plates are cleared."
        ),
    },
    # ---------------------------------------------------------------- topic 3
    {
        "topic_id": 3,
        "published_at": d(2026, 4, 7),
        "title": "How chambers prove the value of membership",
        "summary": (
            "Members renew when they can point at something. Events are the "
            "easiest thing to point at, and the hardest to show evidence of."
        ),
        "sections": [
            {
                "heading": "The renewal conversation",
                "body": (
                    "Membership is sold on access to people. When renewal comes "
                    "around, the member tries to recall what that access "
                    "actually produced. If the honest answer is a few pleasant "
                    "evenings they cannot reconstruct, the value was real and "
                    "the evidence was not."
                ),
            },
            {
                "heading": "Attendance is not the metric",
                "body": (
                    "Counting bodies tells you the event happened. It says "
                    "nothing about whether anyone got anything from it. A "
                    "director who reports attendance is reporting effort, and "
                    "effort is not what the board is asking about."
                ),
            },
            {
                "heading": "Make the network visible",
                "body": (
                    "The strongest renewal argument is a member opening a "
                    "directory and seeing the people they have met through you "
                    "across a year of mixers. That is not a claim about value. "
                    "It is the value, sitting there in a list with names and "
                    "faces on it."
                ),
            },
            {
                "heading": "One directory, every event",
                "body": (
                    "Individual event pages help for a week. What changes the "
                    "renewal conversation is continuity across the year, so a "
                    "member sees an accumulating network rather than a series of "
                    "unrelated evenings they half remember."
                ),
            },
        ],
        "cta": (
            "Run your next member event on Intro Connect and give members "
            "something they can point at."
        ),
    },
    # --------------------------------------------------------------- topic 11
    {
        "topic_id": 11,
        "published_at": d(2026, 5, 5),
        "title": "Should your event have an app? Usually not",
        "summary": (
            "Most events that build an app end up with a low install rate and a "
            "budget line. There is one case where it earns its place."
        ),
        "sections": [
            {
                "heading": "Installs are where the plan dies",
                "body": (
                    "Every guest you ask to install something is a guest you "
                    "might lose. Asking busy people to find a store listing, "
                    "download, create an account and remember a password before "
                    "an evening they are already unsure about is a large ask for "
                    "a small return."
                ),
            },
            {
                "heading": "What the app was supposed to solve",
                "body": (
                    "Usually the schedule, which a page can do, and the "
                    "attendee list, which a page can also do. If you strip the "
                    "requirements back to what guests actually open, very little "
                    "of it needs to be an application at all."
                ),
            },
            {
                "heading": "The exception",
                "body": (
                    "A recurring event with the same audience, over years, where "
                    "the audience genuinely lives inside the thing you are "
                    "building. Large annual conferences with loyal returning "
                    "attendees can clear that bar. A quarterly mixer cannot, and "
                    "trying usually produces an expensive way to show a schedule."
                ),
            },
            {
                "heading": "The browser is the honest default",
                "body": (
                    "A link opens. Nothing installs, nothing updates, and nobody "
                    "has to decide whether your event is worth the storage. "
                    "Intro Connect works this way deliberately, because adoption "
                    "is the only feature that matters when the alternative is "
                    "guests not showing up at all."
                ),
            },
        ],
        "cta": (
            "Skip the build. Give your guests a link and see who actually uses "
            "it."
        ),
    },
    # --------------------------------------------------------------- topic 12
    {
        "topic_id": 12,
        "published_at": d(2026, 6, 2),
        "title": "What to write in an event invitation email",
        "summary": (
            "Invitations fail for boring reasons. They bury the details, or "
            "they never say who else is coming."
        ),
        "sections": [
            {
                "heading": "Lead with the room, not the logistics",
                "body": (
                    "People decide based on who will be there. Date and address "
                    "are what they need after they have said yes, not what makes "
                    "them say it. An invitation that opens with a venue address "
                    "has answered a question nobody asked yet."
                ),
            },
            {
                "heading": "A short one you can steal",
                "body": (
                    "We are getting about twenty operators together on the "
                    "fourteenth for dinner. Mostly people running small teams, a "
                    "few investors, no panels and no name badges. Thought you "
                    "would fit the room. Want in? That is the entire message and "
                    "it works better than a page of enthusiasm."
                ),
            },
            {
                "heading": "Say what happens when they arrive",
                "body": (
                    "Uncertainty is the quiet reason people decline. Whether "
                    "there is assigned seating, whether they will be asked to "
                    "speak, whether anyone will introduce them. One sentence "
                    "removing that doubt converts better than another sentence "
                    "of praise for the event."
                ),
            },
            {
                "heading": "Make the reminder do the work",
                "body": (
                    "The first invitation gets read when it is inconvenient. The "
                    "reminder is what people actually act on, so it should carry "
                    "everything they need rather than referring back. Hosts on "
                    "Intro Connect can edit the invitation and event emails into "
                    "their own words and have those become the default for every "
                    "guest."
                ),
            },
        ],
        "cta": (
            "Write the invitation once, in your voice, and let it go out for "
            "every event you host."
        ),
    },
    # ---------------------------------------------------------------- topic 2
    {
        "topic_id": 2,
        "published_at": d(2026, 6, 30),
        "title": "Build an event agenda and export it to Word",
        "summary": (
            "An agenda is a scheduling problem and a document problem. Most "
            "tools solve one and hand you the other."
        ),
        "sections": [
            {
                "heading": "Why agendas take longer than they should",
                "body": (
                    "The thinking is quick. You know roughly what happens and "
                    "when. The time goes into formatting: getting the times to "
                    "line up, keeping the styling consistent, and producing "
                    "something you are willing to send to a venue or a speaker."
                ),
            },
            {
                "heading": "Start from the fixed points",
                "body": (
                    "Doors, the thing everyone came for, and the end. Fill "
                    "between them rather than building forward from the "
                    "beginning, which is how agendas end up with a crowded "
                    "opening and a vague final hour that quietly runs long."
                ),
            },
            {
                "heading": "Leave more gap than feels right",
                "body": (
                    "Every segment runs over. Transitions take longer than "
                    "planned, and the conversations you actually wanted happen "
                    "in the margins you were tempted to cut. A schedule with no "
                    "slack is a schedule that will be wrong by the second item."
                ),
            },
            {
                "heading": "Get a real document at the end",
                "body": (
                    "Venues and speakers want something they can open and edit, "
                    "not a screenshot. The Intro Connect agenda builder exports "
                    "a genuine Word file, and it is free with no account "
                    "required, because a tool that makes you sign up before it "
                    "helps you is not really free."
                ),
            },
        ],
        "cta": (
            "Build your agenda in the free builder and export it to Word "
            "without creating an account."
        ),
    },
    # ---------------------------------------------------------------- topic 7
    {
        "topic_id": 7,
        "published_at": d(2026, 7, 21),
        "title": "How to import a guest list from a spreadsheet",
        "summary": (
            "Guest lists arrive messy. The import should absorb that rather "
            "than sending you back to clean it up."
        ),
        "sections": [
            {
                "heading": "Where your list actually lives",
                "body": (
                    "A ticketing export, a shared spreadsheet, a reply thread "
                    "you have been keeping score in, or all three. Real lists "
                    "are assembled from several places and almost never arrive "
                    "in one tidy format."
                ),
            },
            {
                "heading": "The mess is normal",
                "body": (
                    "Commas inside quoted company names. Phone numbers written "
                    "five different ways. Blank rows, a header that is not the "
                    "first line, the same person twice with two addresses. This "
                    "is what an honest guest list looks like and an import that "
                    "assumes otherwise will fail on the first one."
                ),
            },
            {
                "heading": "Paste it and check the result",
                "body": (
                    "Intro Connect takes a pasted spreadsheet, a comma separated "
                    "file, or an export from a ticketing tool, and handles quoted "
                    "fields and untidy phone numbers rather than refusing them. "
                    "Read what came back before you send anything, because a "
                    "wrong address is a guest who never hears from you."
                ),
            },
            {
                "heading": "Invitations from the same list",
                "body": (
                    "Once the list is in, each guest can be sent a join link "
                    "without you assembling a separate mail merge. The list you "
                    "already had becomes the event, which is the point: importing "
                    "should be the end of the admin, not the middle of it."
                ),
            },
        ],
        "cta": (
            "Paste your guest list and have the invitations go out the same day."
        ),
    },
    # ---------------------------------------------------------------- topic 8
    {
        "topic_id": 8,
        "published_at": d(2026, 8, 1),
        "title": "Event survey questions: why three is enough",
        "summary": (
            "Long surveys produce fewer answers and worse ones. Three questions "
            "get answered in the taxi home."
        ),
        "sections": [
            {
                "heading": "Length is the reason nobody responds",
                "body": (
                    "Every extra question costs you responses from the people "
                    "who were mildly positive, which is most of the room. What "
                    "survives a long survey is the strongly delighted and the "
                    "genuinely annoyed, and a picture built from only those two "
                    "groups is not the picture you needed."
                ),
            },
            {
                "heading": "Ask what you will act on",
                "body": (
                    "If a question's answer would not change what you do next "
                    "time, it is costing you responses for nothing. Most surveys "
                    "are padded with questions asked out of curiosity rather "
                    "than intent, and readers can feel the difference."
                ),
            },
            {
                "heading": "Totals, not names",
                "body": (
                    "People answer honestly when they are confident the answer "
                    "is not attributable. Intro Connect shows a host the totals "
                    "and never who said what, which is a deliberate limit: the "
                    "moment a guest suspects otherwise, the answers start being "
                    "polite instead of true."
                ),
            },
            {
                "heading": "Ask while it is fresh",
                "body": (
                    "A survey sent a week later measures memory, not "
                    "experience. The answers you want exist for roughly a day, "
                    "and after that you are collecting a vaguer version of the "
                    "same opinion."
                ),
            },
        ],
        "cta": (
            "Ask three questions after your next event and see the totals "
            "without ever seeing who said what."
        ),
    },
]


async def main(apply: bool) -> int:
    existing = await _existing_for_guardrails()
    existing_slugs = {p.get("slug") for p in existing}
    planned, skipped, blocked = [], [], []

    for raw in POSTS:
        post = GeneratedPost(
            title=raw["title"],
            summary=raw["summary"],
            sections=raw["sections"],
            cta=raw["cta"],
        )
        slug = slugify(post.title)
        if slug in existing_slugs:
            skipped.append(slug)
            continue
        # Compare against everything already stored plus everything queued in
        # this run, so two of these cannot ship as near duplicates of each other.
        reasons = check_guardrails(
            post, existing + planned, slug=slug, topic_id=raw["topic_id"]
        )
        if reasons:
            blocked.append((slug, reasons))
            continue
        doc = {
            "slug": slug,
            "title": post.title,
            "summary": post.summary,
            "sections": [s.model_dump() for s in post.sections],
            "cta": post.cta,
            "topic_id": raw["topic_id"],
            "is_data_post": False,
            "status": "published",
            "guardrail_reasons": [],
            "created_at": raw["published_at"],
            "published_at": raw["published_at"],
        }
        planned.append(doc)

    for doc in planned:
        print(f"  + {doc['published_at'].date()}  {doc['slug']}")
    for slug in skipped:
        print(f"  = exists, skipped: {slug}")
    for slug, reasons in blocked:
        print(f"  ! BLOCKED {slug}: {', '.join(reasons)}")

    if blocked:
        print("\nRefusing to write anything while a post fails guardrails.")
        return 1
    if not apply:
        print(f"\nDry run. {len(planned)} would be written. Re run with --apply.")
        return 0
    if planned:
        await blog_post.insert_many(planned)
    print(f"\nWrote {len(planned)} posts.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main("--apply" in sys.argv)))
