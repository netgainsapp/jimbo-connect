/**
 * Pure logic for the message email's sign in page (/magic/:token). The page
 * signs in only when the guest presses its button, never on load, so a link
 * scanner opening the email cannot spend the single use token.
 */
import { safeNext } from "./nextPath.js";

const INBOX = "/messages";

/** Where to go after signing in: the `next` the email named when it is a
 *  same-site path, else the inbox. */
export function magicDestination(next) {
  return safeNext(next, INBOX);
}
