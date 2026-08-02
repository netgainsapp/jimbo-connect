"""Post artwork: stable choice, tiles on the index, a larger copy on the article.

The property that matters is stability. The same post has to show the same
photograph on the index tile, on its own page, and in the Open Graph card a
link preview scrapes days later. That rules out the builtin hash(), which
Python salts per process, so the picture would change on every restart.

Run from backend/: python -m pytest tests/test_blog_images.py
"""
import re
import subprocess
import sys

from blog import images, render

POST = {
    "slug": "how-to-build-a-business-network-from-scratch",
    "title": "How to Build a Business Network from Scratch",
    "summary": "Where to start when you know nobody.",
    "sections": [{"heading": "Start small", "body": "Go to one thing."}],
    "cta": "Try Intro Connect.",
}


def _posts(n=3):
    return [dict(POST, slug=f"post-{i}", title=f"Post number {i}") for i in range(n)]


# --- choosing ---------------------------------------------------------------


def test_same_post_always_gets_the_same_image():
    assert images.image_for(POST) == images.image_for(dict(POST))


def test_choice_survives_a_fresh_interpreter():
    """hash() is salted per process. If this module ever switches to it, the
    image changes on every restart and link previews go stale. Runs a separate
    interpreter with hash randomisation on to prove the choice is not affected."""
    code = (
        "import sys; sys.path.insert(0, '.');"
        "from blog import images;"
        f"print(images.image_for({POST!r}))"
    )
    runs = {
        subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, check=True
        ).stdout.strip()
        for _ in range(3)
    }
    assert len(runs) == 1, f"image is not stable across processes: {runs}"
    assert runs.pop() == images.image_for(POST)


def test_an_explicit_image_on_the_post_wins():
    assert images.image_for(dict(POST, image_url="/images/custom.jpg")) == "/images/custom.jpg"


def test_every_pooled_image_is_a_site_relative_path():
    for path in images.POOL:
        assert path.startswith("/images/"), path


def test_the_six_megabyte_file_is_not_in_the_pool():
    """2.jpg is 6MB. It is in the same folder and must never be a thumbnail."""
    assert not any(p.endswith("/2.jpg") for p in images.POOL)


def test_posts_spread_across_the_pool():
    """A hash that lands everything on one image would pass every other test."""
    chosen = {images.image_for(p) for p in _posts(30)}
    assert len(chosen) >= 5, f"only {len(chosen)} distinct images across 30 posts"


# --- rendering --------------------------------------------------------------


def test_index_renders_one_tile_per_post_each_with_a_thumbnail():
    html = render.render_index(_posts(3))
    assert html.count('class="tile"') == 3
    assert html.count('class="thumb"') == 3


def test_index_uses_the_wide_container_so_three_fit():
    assert 'class="wrap wide"' in render.render_index(_posts(3))


def test_whole_tile_is_clickable_not_just_the_headline():
    html = render.render_index(_posts(1))
    assert re.search(r'<a href="/blog/post-0"[^>]*>\s*<img', html), "the image is outside the link"


def test_thumbnails_are_lazy_but_the_article_image_is_not():
    """Below-the-fold tiles should wait; the article's own image is the thing
    the reader is already looking at."""
    assert 'loading="lazy"' in render.render_index(_posts(3))
    post_html = render.render_post(POST)
    hero = re.search(r'<img class="hero"[^>]*>', post_html).group(0)
    assert 'loading="lazy"' not in hero
    assert 'fetchpriority="high"' in hero


def test_article_shows_the_same_image_as_its_tile():
    expected = images.image_for(POST)
    assert expected in render.render_index([POST])
    assert expected in render.render_post(POST)


def test_article_image_becomes_the_open_graph_card():
    """A shared link should show the post's own picture, not nothing."""
    html = render.render_post(POST)
    slug_image = images.image_for(POST)
    assert re.search(
        rf'<meta property="og:image" content="https?://[^"]*{re.escape(slug_image)}"', html
    ), "og:image is missing or not absolute"


def test_decorative_images_have_empty_alt():
    """The headline sits directly under the picture and says the same thing;
    alt text here would be announced twice."""
    for html in (render.render_index(_posts(2)), render.render_post(POST)):
        for tag in re.findall(r"<img[^>]*>", html):
            assert 'alt=""' in tag, tag


def test_empty_blog_still_renders_without_a_grid():
    html = render.render_index([])
    assert 'class="empty"' in html
    assert 'class="tile"' not in html
