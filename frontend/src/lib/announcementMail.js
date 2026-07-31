/**
 * Build the "open this in my own mail client" link for a host announcement.
 *
 * Announcements are in-app by decision. When a host also wants the notice to
 * land in inboxes, they send it themselves rather than the platform sending it
 * for them: hello@intro-connect.com is the transactional sender for password
 * resets and invitations, and an announcement blast from that address risks the
 * deliverability of both.
 *
 * The whole reason this is its own module is the ceiling. A mailto: URL has a
 * hard length limit in every mail client, lowest in Outlook on Windows, and a
 * guest list passes it long before it reaches even the Starter cap of 250. The
 * tempting behaviour is to fill the link up to the limit and stop. That would
 * email some attendees and silently not others, with nothing on screen saying
 * so, which is precisely the failure the CSV importer had. So: past the ceiling
 * this returns no link at all, and the caller offers the address list to copy
 * instead. Refusing loudly beats half-sending quietly.
 */

/**
 * Practical ceiling for a mailto: URL.
 *
 * Outlook on Windows is the binding constraint at roughly 2048 characters for
 * the whole URL; Chrome and the Windows shell handler sit near the same mark.
 * 1900 leaves headroom for the client appending its own parameters rather than
 * discovering the limit by having a link fail silently at the shell boundary.
 */
export const MAILTO_SAFE_LENGTH = 1900;

function normalizeEmails(emails) {
  const seen = new Set();
  const out = [];
  for (const raw of emails || []) {
    const value = String(raw ?? "").trim();
    if (value === "") continue;
    const key = value.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(value);
  }
  return out;
}

/**
 * @returns {{href: string|null, bcc: string, recipientCount: number,
 *            tooLong: boolean, length: number}}
 *   `href` is null when the link would exceed what a mail client accepts. It is
 *   null rather than truncated so that a caller cannot use it by mistake; the
 *   restriction is structural instead of a rule someone has to remember.
 *   `bcc` always holds every address, so the copy-to-clipboard path stays
 *   complete even when the link is unusable.
 */
export function buildAnnouncementMailto({ subject = "", body = "", emails = [] } = {}) {
  const recipients = normalizeEmails(emails);
  const bcc = recipients.join(",");

  const params = [];
  // Omitted entirely when empty: a trailing `bcc=` makes some clients open a
  // compose window with a blank recipient chip that has to be deleted by hand.
  if (bcc) params.push(`bcc=${encodeURIComponent(bcc)}`);
  if (subject) params.push(`subject=${encodeURIComponent(subject)}`);
  if (body) params.push(`body=${encodeURIComponent(body)}`);

  const href = `mailto:?${params.join("&")}`;
  const tooLong = href.length > MAILTO_SAFE_LENGTH;

  return {
    href: tooLong ? null : href,
    bcc,
    recipientCount: recipients.length,
    tooLong,
    length: href.length,
  };
}
