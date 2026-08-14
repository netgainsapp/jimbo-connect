/**
 * Turn the invite endpoint's summary into the one line a host sees.
 *
 * The rule this exists to enforce: a send where no mail left must never read
 * like a send that worked. The endpoint returns `invited` (how many were
 * attempted) alongside `sent`, and reporting the former as success is how a
 * completely failed blast came back as "Invited 40 guests".
 *
 * Only `sent` means mail actually left. Anything short of that is surfaced as
 * an error, because the host's next action differs: a clean send is done, a
 * failed one needs retrying, and retrying now works because a failed address
 * is no longer stamped as invited. See backend/invites.py.
 */

// Resend echoes request fragments back in some errors, so a reason is not
// guaranteed to be short or meaningful.
const MAX_REASON = 60;

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

/** The reason that accounts for the most failures, if it says anything useful. */
function topReason(failures) {
  const entries = Object.entries(failures || {});
  if (entries.length === 0) return "";
  const [reason] = entries.sort((a, b) => b[1] - a[1])[0];
  const text = String(reason || "").trim();
  if (!text || text === "unknown" || text === "other") return "";
  return text.length > MAX_REASON ? `${text.slice(0, MAX_REASON - 1)}…` : text;
}

export function inviteOutcome(res) {
  const r = res || {};
  if (r.skipped === "email_not_configured") {
    return { type: "error", message: "Email is not set up yet, so no invites were sent." };
  }

  const attempted = r.invited ?? 0;
  const sent = r.sent ?? 0;
  // `failed` is derived rather than trusted, so a response from an older API
  // that predates the field still produces a truthful line.
  const failed = r.failed ?? Math.max(0, attempted - sent);
  const skippedRecent = r.skipped_recent ?? 0;

  if (attempted === 0) {
    return {
      type: "success",
      message:
        skippedRecent > 0
          ? `Everyone on that list was already invited in the last 24 hours.`
          : "There was no one new to invite.",
    };
  }

  if (failed === 0) {
    const tail =
      skippedRecent > 0
        ? ` ${plural(skippedRecent, "guest")} were already invited recently.`
        : "";
    return { type: "success", message: `Invited ${plural(sent, "guest")}.${tail}` };
  }

  const reason = topReason(r.failures);
  const because = reason ? ` (${reason})` : "";

  if (sent === 0) {
    const who = attempted === 1 ? "that guest" : `any of the ${attempted} guests`;
    return {
      type: "error",
      message: `Could not email ${who}${because}. Nothing was recorded, so you can try again.`,
    };
  }

  return {
    type: "error",
    message: `Invited ${sent} of ${attempted} guests. ${plural(
      failed,
      "message"
    )} could not be sent${because}.`,
  };
}
