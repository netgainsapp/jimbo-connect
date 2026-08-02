"""Every scheduled workflow must point at the API that actually exists.

Five of the six workflows spent their whole life curling
`jimbo-connect-api.onrender.com`, which is not the service. The real host has a
`-rdkp` suffix. The wrong host does not fail fast either: it hangs until curl
gives up, so each run burned its timeout and failed, and the symptoms showed up
somewhere else entirely.

What that silently disabled: the blog never generated a post (the reason the
blog had two), the nurture drip never advanced, guest invite reminders never
sent, and keep-warm never warmed anything, which is why the API kept cold
starting in front of people.

Nothing in this repository ran these files before this test existed. It is
cheap insurance against a class of bug that is invisible until you go looking
for a missing email.

Run from backend/: python -m pytest tests/test_cron_targets.py
"""
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO / ".github" / "workflows"
RENDER_YAML = REPO / "render.yaml"

_URL_RE = re.compile(r"https://[a-z0-9.-]*onrender\.com(/[^\s\\)\"']*)?", re.IGNORECASE)


def _api_host_from_render_yaml() -> str:
    """The host Render itself is told to advertise, from API_PUBLIC_URL."""
    text = RENDER_YAML.read_text(encoding="utf-8")
    match = re.search(r'API_PUBLIC_URL\s*\n\s*value:\s*"?(https://[^"\s]+)"?', text)
    assert match, "API_PUBLIC_URL is not set in render.yaml"
    return match.group(1).split("//", 1)[1].strip("/")


def _workflow_files():
    return sorted(WORKFLOWS.glob("*.yml"))


def _onrender_urls(text: str):
    return [m.group(0) for m in _URL_RE.finditer(text)]


def test_there_are_workflows_to_check():
    """Guards against this whole file passing vacuously if the path moves."""
    assert _workflow_files(), "no workflow files found"


@pytest.mark.parametrize("path", _workflow_files(), ids=lambda p: p.name)
def test_workflow_targets_the_real_api_host(path):
    expected = _api_host_from_render_yaml()
    for url in _onrender_urls(path.read_text(encoding="utf-8")):
        host = url.split("//", 1)[1].split("/", 1)[0]
        assert host == expected, (
            f"{path.name} calls {host}, but render.yaml says the API is {expected}. "
            "The wrong host hangs rather than 404s, so this fails silently."
        )


@pytest.mark.parametrize("path", _workflow_files(), ids=lambda p: p.name)
def test_workflow_calls_a_route_that_exists(path):
    """A workflow curling a path the API does not serve is the same class of
    dead cron, just one layer in."""
    inventory = json.loads((Path(__file__).parent / "route_inventory.json").read_text())
    known = {line.split(" ", 1)[1] for line in inventory}
    for url in _onrender_urls(path.read_text(encoding="utf-8")):
        route = "/" + url.split("//", 1)[1].split("/", 1)[1] if "/" in url.split("//", 1)[1] else "/"
        route = route.rstrip(")").rstrip("\\").strip()
        assert route in known, f"{path.name} calls {route}, which is not a route this API serves"
