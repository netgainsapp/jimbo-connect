/**
 * Turn the attendee-import summary into the one line a host sees.
 *
 * Two different things happen during a roster import and only one of them was
 * ever reported: guests get added to the event, and brand new accounts get an
 * invitation email. The old copy counted the rows the browser uploaded and
 * called them "invited", which is wrong twice over. It counts rows the server
 * may have skipped, and an address that already has an account is never
 * emailed at all, by design.
 *
 * So "added" and "emailed" are stated separately, and a failed send is never
 * folded into a success. See backend/attendee_import.py.
 */

const MAX_REASON = 60;

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

function topReason(failures) {
  const entries = Object.entries(failures || {});
  if (entries.length === 0) return "";
  const [reason] = entries.sort((a, b) => b[1] - a[1])[0];
  const text = String(reason || "").trim();
  if (!text || text === "unknown" || text === "other") return "";
  return text.length > MAX_REASON ? `${text.slice(0, MAX_REASON - 1)}…` : text;
}

export function importOutcome(res) {
  const r = res || {};
  const added = r.added_to_event ?? r.created ?? 0;
  const emailed = r.emailed ?? 0;
  const failures = r.email_failures || {};
  const failed = Object.values(failures).reduce((a, b) => a + b, 0);

  const addedPart = `${plural(added, "guest")} added`;

  if (failed > 0) {
    const reason = topReason(failures);
    const because = reason ? ` (${reason})` : "";
    const emailedPart = emailed > 0 ? `${emailed} emailed, ` : "";
    return {
      type: "error",
      message: `${addedPart}. ${emailedPart}${plural(
        failed,
        "invitation"
      )} could not be sent${because}.`,
    };
  }

  if (emailed > 0) {
    return { type: "success", message: `${addedPart}, ${emailed} emailed.` };
  }

  return { type: "success", message: `${addedPart}. No invitation emails were sent.` };
}
