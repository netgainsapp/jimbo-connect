"""Production smoke audit for Intro Connect.

Read-only by default. The signup check (which sends a real welcome email) only
runs when you pass an inbox you control via SMOKE_SIGNUP_EMAIL, so casual runs
never generate bouncing mail that harms Resend sender reputation.

Run (read-only):   python tests/smoke_prod.py
Run (with signup): SMOKE_SIGNUP_EMAIL=you+test@yourdomain.com python tests/smoke_prod.py

Requires: httpx  (pip install httpx)
"""
import os
import uuid
import httpx

API = os.getenv("SMOKE_API", "https://jimbo-connect-api-rdkp.onrender.com")
APP_ORIGIN = os.getenv("SMOKE_APP_ORIGIN", "https://app.intro-connect.com")
SIGNUP_EMAIL = os.getenv("SMOKE_SIGNUP_EMAIL")  # opt-in; sends a real email

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")


# 1. API health
try:
    r = httpx.get(f"{API}/api/health", timeout=90)
    check("api_health", r.status_code == 200 and r.json().get("ok") is True, str(r.status_code))
except Exception as e:  # noqa: BLE001
    check("api_health", False, repr(e))

# 2. CORS preflight from the app origin (browser login depends on this)
try:
    r = httpx.options(
        f"{API}/api/auth/login",
        headers={
            "Origin": APP_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=90,
    )
    acao = r.headers.get("access-control-allow-origin", "")
    check("cors_allows_app_origin", acao == APP_ORIGIN, f"status={r.status_code} ACAO='{acao}'")
except Exception as e:  # noqa: BLE001
    check("cors_allows_app_origin", False, repr(e))

# 3. Blog serves real blog HTML from the API (not the marketing SPA shell)
try:
    r = httpx.get(f"{API}/blog", timeout=90)
    is_blog = r.status_code == 200 and "Blog" in r.text and "stronger connections" not in r.text
    check("blog_api_serves_posts", is_blog, str(r.status_code))
except Exception as e:  # noqa: BLE001
    check("blog_api_serves_posts", False, repr(e))

# 4. Optional signup (sends a real welcome email — only with an inbox you control)
if SIGNUP_EMAIL:
    try:
        r = httpx.post(
            f"{API}/api/auth/register",
            json={"email": SIGNUP_EMAIL, "password": f"Smoke!{uuid.uuid4().hex[:8]}", "name": "Smoke Test"},
            headers={"Origin": APP_ORIGIN},
            timeout=90,
        )
        check("signup", r.status_code in (200, 201), str(r.status_code))
        print("    -> check the inbox: sender should be hello@intro-connect.com, branded 'Intro Connect'")
    except Exception as e:  # noqa: BLE001
        check("signup", False, repr(e))
else:
    print("[SKIP] signup (set SMOKE_SIGNUP_EMAIL=you+test@yourdomain.com to run)")

passed = sum(1 for _, ok in results if ok)
print(f"\nSUMMARY: {passed}/{len(results)} checks passed")
raise SystemExit(0 if passed == len(results) else 1)
