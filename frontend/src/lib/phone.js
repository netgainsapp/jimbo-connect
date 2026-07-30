/**
 * Phone formatting and validation, mirroring backend/phone.py.
 *
 * The rule is one thing: exactly ten digits, shown as XXX-XXX-XXXX. Anything
 * shorter or longer is refused rather than truncated or padded, because a
 * silently mangled number looks right and only fails when somebody tries to
 * call it.
 *
 * The input formats as you type and caps at ten digits, so a valid number is
 * the path of least resistance and the error is mostly unreachable. The server
 * validates independently; this is the courtesy, not the enforcement.
 */
export const PHONE_ERROR =
  "Enter a 10 digit phone number, for example 303-555-0101.";

const REQUIRED_DIGITS = 10;

export function phoneDigits(value) {
  return String(value ?? "").replace(/\D/g, "");
}

/**
 * Format for display and for typing.
 *
 * Over-length input is deliberately NOT truncated. Cutting it to ten digits
 * turns a pasted "1-303-555-0101" into "130-355-5010": a different number that
 * looks entirely valid. That silent corruption is the exact failure this rule
 * exists to prevent, and it is worse than an error, because nothing looks
 * wrong until somebody dials it. Too many digits are left visible and unformatted
 * so the field reads as wrong and isValidPhone refuses it.
 */
export function formatPhone(value) {
  const d = phoneDigits(value);
  if (d.length > REQUIRED_DIGITS) return d;
  if (d.length <= 3) return d;
  if (d.length <= 6) return `${d.slice(0, 3)}-${d.slice(3)}`;
  return `${d.slice(0, 3)}-${d.slice(3, 6)}-${d.slice(6)}`;
}

/** Blank is fine, phone is optional. A partial number is not. */
export function isValidPhone(value) {
  const d = phoneDigits(value);
  return d.length === 0 || d.length === REQUIRED_DIGITS;
}
