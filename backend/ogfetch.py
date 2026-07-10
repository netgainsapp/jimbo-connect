"""Open-graph metadata fetching with SSRF defenses (public-IP validation +
IP pinning against DNS rebinding). Moved verbatim from server.py (M13)."""
import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

import httpx

_OG_RE = re.compile(
    r'<meta\s+(?:[^>]*?\b(?:property|name)\s*=\s*["\']([^"\']+)["\'][^>]*?\bcontent\s*=\s*["\']([^"\']*)["\']'
    r'|[^>]*?\bcontent\s*=\s*["\']([^"\']*)["\'][^>]*?\b(?:property|name)\s*=\s*["\']([^"\']+)["\'])',
    re.IGNORECASE,
)
_TITLE_RE = re.compile(r"<title[^>]*>([^<]+)</title>", re.IGNORECASE)


def _resolve_public_ip(url: str) -> str:
    """Resolve the URL's host and return one public IP to connect to. Raises
    ValueError if the scheme is wrong, the host is missing, or ANY resolved
    address is non-public (SSRF guard: cloud metadata endpoints, localhost,
    private ranges)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("unsupported scheme")
    host = parsed.hostname
    if not host:
        raise ValueError("missing host")
    infos = socket.getaddrinfo(host, None)
    ips = []
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValueError(f"blocked non-public address: {ip}")
        ips.append(ip)
    if not ips:
        raise ValueError("host did not resolve")
    for ip in ips:  # prefer IPv4 for the pinned connection
        if ip.version == 4:
            return str(ip)
    return str(ips[0])


def _pin_url(url: str, ip: str):
    """Rewrite the URL to connect to the validated IP directly, so the actual
    connection cannot be re-routed by a second DNS answer (DNS rebinding).
    Returns (pinned_url, hostname). Any userinfo in the URL is dropped."""
    parsed = urlparse(url)
    host = parsed.hostname
    ip_literal = f"[{ip}]" if ":" in ip else ip
    port = f":{parsed.port}" if parsed.port else ""
    return parsed._replace(netloc=f"{ip_literal}{port}").geturl(), host


async def _safe_fetch_html(url: str, max_redirects: int = 3) -> str:
    """Fetch HTML while validating the target (and each redirect hop) is a
    public host. Redirects are followed manually so an internal target cannot
    be reached via a 3xx bounce, and each request connects to the exact IP
    that passed validation (Host header + SNI carry the real hostname, so
    virtual hosting and certificate verification still work). This closes the
    validate-then-reconnect DNS-rebind window."""
    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=8.0,
        headers={"User-Agent": "Mozilla/5.0 (compatible; IntroConnectBot/1.0)"},
    ) as client:
        for _ in range(max_redirects + 1):
            ip = _resolve_public_ip(url)
            pinned, host = _pin_url(url, ip)
            resp = await client.get(
                pinned,
                headers={"Host": host},
                extensions={"sni_hostname": host},
            )
            location = resp.headers.get("location")
            if resp.is_redirect and location:
                url = urljoin(url, location)
                continue
            return resp.text[:300_000]  # cap
    raise ValueError("too many redirects")


async def fetch_og_metadata(url: str) -> dict:
    """Fetch a URL and return open-graph-ish metadata. Best-effort, never raises."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    out = {
        "title": "",
        "description": "",
        "image_url": "",
        "site_name": "",
    }
    try:
        html = await _safe_fetch_html(url)
    except Exception:
        host = urlparse(url).hostname or url
        out["title"] = host
        out["site_name"] = host
        return out

    meta: dict = {}
    for m in _OG_RE.finditer(html):
        key = (m.group(1) or m.group(4) or "").lower()
        val = m.group(2) if m.group(2) is not None else m.group(3)
        if key and val and key not in meta:
            meta[key] = val.strip()

    out["title"] = (
        meta.get("og:title")
        or meta.get("twitter:title")
        or (_TITLE_RE.search(html).group(1).strip() if _TITLE_RE.search(html) else "")
    )
    out["description"] = (
        meta.get("og:description")
        or meta.get("twitter:description")
        or meta.get("description")
        or ""
    )
    image = (
        meta.get("og:image")
        or meta.get("twitter:image")
        or meta.get("twitter:image:src")
        or ""
    )
    if image:
        out["image_url"] = urljoin(url, image)
    out["site_name"] = meta.get("og:site_name") or (urlparse(url).hostname or "")
    if not out["title"]:
        out["title"] = out["site_name"] or url
    return out
