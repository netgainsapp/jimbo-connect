/**
 * Pure state logic for the claim page (/claim/:token). Kept out of the JSX so
 * node --test can cover it; the page only renders what these return.
 */

const DEAD_LINK_STATUSES = new Set([404, 410]);
const GENERIC_FAILURE = "Something went wrong. Please try again.";
const INVALID_EMAIL = "Enter a valid email address.";
const INVALID_STATUS = 422;
// The 409 the server sends when the email belongs to an account that is not
// the one signed in. The other 409 codes (plan_limit, just_claimed) get no
// log in link, because logging in does not fix them.
const ACCOUNT_EXISTS = "account_exists";
// Deliberately loose: one @, something before it, a dot in the domain, no
// spaces. The server's EmailStr is the real check.
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** Map GET /api/claim/:token to the view the page shows. */
export function viewFor(response) {
  const state = response?.state;
  if (!response?.event) return { view: "dead" };
  if (state === "needs_email") {
    return { view: "form", event: response.event, host: response.host };
  }
  if (state === "ok") {
    return { view: "ready", event: response.event, host: response.host };
  }
  return { view: "dead" };
}

/** A failed claim call: 404 and 410 mean the link is dead, 422 is a bad
 *  email, anything else is a message the host can act on. `login` is true
 *  only when logging in is the fix. */
export function failureView(err) {
  if (DEAD_LINK_STATUSES.has(err?.status)) return { view: "dead" };
  if (err?.status === INVALID_STATUS) {
    return { view: "error", message: INVALID_EMAIL, login: false };
  }
  return {
    view: "error",
    message: err?.message || GENERIC_FAILURE,
    login: err?.code === ACCOUNT_EXISTS,
  };
}

export function isValidEmail(value) {
  return typeof value === "string" && EMAIL_PATTERN.test(value.trim());
}

/** The POST body: nothing for a ready claim, the email (and a name when one
 *  was typed) for a pending host. */
export function claimBody(form) {
  const email = (form?.email || "").trim().toLowerCase();
  if (!email) return {};
  const name = (form?.name || "").trim();
  return name ? { email, name } : { email };
}

/** After the attendee list step: ask for a photo only when there is none. */
export function nextStepAfterImport(user) {
  return user?.profile?.photo_url ? "done" : "photo";
}
