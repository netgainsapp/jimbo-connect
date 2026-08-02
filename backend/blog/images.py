"""Which picture goes with which post.

Posts are written by a language model, which cannot produce a photograph, so
the image has to come from somewhere else. This picks from the photographs
already in the marketing site's public folder. They are served from the same
origin the blog is (intro-connect.com), so a plain relative path works and
there is no CDN, no upload step, and no third party in the loop.

The choice is derived from the slug, which means a given post always shows the
same photograph: on the index tile, on the article page, and in the Open Graph
card a link preview builds days later. A post can override it by carrying its
own `image_url`, which is how a bespoke image would be introduced later without
touching this.

⚠️ Uses md5, NOT the builtin hash(). Python salts hash() per process, so the
picture would change every time the service restarted, and a link preview
scraped yesterday would stop matching the page today.
"""
import hashlib

#: Photographs from marketing/public/images, checked reachable on 2026-08-02.
#: `2.jpg` lives there too and is deliberately absent: it is six megabytes,
#: which is not a thumbnail. Anything added here should be well under 200kb.
POOL = (
    "/images/networking-mixer.jpg",
    "/images/networking-group.jpg",
    "/images/networking-event.jpg",
    "/images/networking-conference.jpg",
    "/images/conference_networking.jpg",
    "/images/networking_opportunities.jpg",
    "/images/how_to_make_the_most_of_your_next_networking_event_main_image.jpg",
    "/images/AdobeStock_118993437.jpeg",
    "/images/1_0mxqweMEM82n312AIIujng.jpg",
    "/images/360_F_611274126_EdTzIv2Vif6YXqx9jChzDpT3Yj0BRozw.jpg",
)


def image_for(doc: dict) -> str:
    """The image for a post. An explicit image_url on the doc always wins."""
    explicit = (doc or {}).get("image_url")
    if explicit:
        return str(explicit)
    key = (doc or {}).get("slug") or (doc or {}).get("title") or ""
    digest = hashlib.md5(key.encode("utf-8")).digest()
    return POOL[int.from_bytes(digest[:4], "big") % len(POOL)]
