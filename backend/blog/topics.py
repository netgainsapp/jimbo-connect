"""Blog topics.

Phase 2: evergreen cornerstone topics only. Per the Attiq playbook, evergreen
posts get a high constant score so they run first; data-backed posts (grounded
in real event/connection volume) mix in later once there is enough data and the
blog_data_posts flag is on.

Topics are kept in code (the seed list below). "Used" is tracked by the
blog_post collection: a topic whose id already has a post is not picked again.
"""
from .schema import slugify

EVERGREEN_SCORE = 1000

EVERGREEN_TITLES = [
    "How to Build a Business Network from Scratch",
    "The Best Places to Meet High-Value Business Contacts",
    "How to Introduce Yourself at Networking Events",
    'What to Say After "So, What Do You Do?"',
    "How to Follow Up Without Sounding Pushy",
    "The Biggest Networking Mistakes Professionals Make",
    "How to Turn Casual Conversations into Business Opportunities",
    "Why Your Network Is More Valuable Than Your Resume",
    "How to Network as an Introvert",
    "The Art of the Warm Introduction",
    "How to Build a Local Business Network",
    "How to Network Online Without Being Annoying",
    "LinkedIn Networking Strategies That Actually Work",
    "How to Write a Connection Request People Accept",
    "What to Post on LinkedIn to Attract Better Contacts",
    "How to Reconnect with Old Business Contacts",
    "How to Ask for Referrals the Right Way",
    "How to Build Trust Before Asking for Anything",
    "Why Giving First Works in Networking",
    "How to Become a Connector in Your Industry",
    "The Difference Between Networking and Selling",
    "How to Network at Conferences",
    "How to Prepare Before Attending a Networking Event",
    "Questions to Ask at Business Networking Events",
    "How to Exit a Conversation Gracefully",
    "How to Remember Names and Details",
    "How to Build a Personal CRM for Your Network",
    "How Often Should You Follow Up with Contacts?",
    "How to Turn Networking into a Weekly Habit",
    "The Best Networking Habits of Successful Entrepreneurs",
    "How Small Business Owners Can Network More Effectively",
    "Networking Tips for Startup Founders",
    "Networking Strategies for Freelancers and Consultants",
    "How Real Estate Professionals Can Build Referral Networks",
    "How Financial Advisors Can Network Ethically",
    "How Service Businesses Can Get More Referrals",
    "How to Network When You Are New to a City",
    "How to Build a Network Before You Need One",
    "How to Create Strategic Partnerships",
    "How to Use Events to Grow Your Business",
    "How to Host Your Own Networking Event",
    "What Makes a Great Business Networking Group?",
    "How to Start a Mastermind Group",
    "How to Build a Referral Partner Program",
    "How to Measure the ROI of Networking",
    "Why Quality Beats Quantity in Business Networking",
    "How to Build Authority Through Networking",
    "How to Network with People More Successful Than You",
    "How to Avoid Transactional Networking",
    "The Future of Business Networking: Online, Offline, and Hybrid",
]


def evergreen_topics() -> list:
    """Each topic: id (slug), title, kind, score."""
    return [
        {"id": slugify(t), "title": t, "kind": "evergreen", "score": EVERGREEN_SCORE}
        for t in EVERGREEN_TITLES
    ]


def select_topic(topics, used_ids):
    """Pure: highest-score topic whose id is not in used_ids. Ties break by list
    order. Returns the topic dict, or None if all are used."""
    used = set(used_ids)
    candidates = [t for t in topics if t["id"] not in used]
    if not candidates:
        return None
    return max(candidates, key=lambda t: t["score"])


async def pick_next_topic():
    """Highest-scoring evergreen topic that has no post yet (any status)."""
    from .store import blog_post

    cursor = blog_post.find({}, {"topic_id": 1})
    used_ids = [doc.get("topic_id") async for doc in cursor]
    return select_topic(evergreen_topics(), [u for u in used_ids if u])
