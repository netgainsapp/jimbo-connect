/**
 * Safe handling of a ?next= redirect target.
 *
 * `next` arrives in a URL, so it is attacker controllable: a link like
 * /register?next=https://evil.example is a classic open redirect, and it is
 * more convincing than usual here because the victim genuinely did just sign
 * in on the real site. Only same-site absolute paths are honoured.
 *
 * Rejected on purpose:
 *   https://evil.example      absolute URL, different origin
 *   //evil.example            protocol relative, browsers treat as absolute
 *   /\evil.example            backslash, normalised to // by some parsers
 *   javascript:alert(1)       scheme
 *   events                    relative, ambiguous against the current path
 */
export function safeNext(value, fallback = "/events") {
  if (typeof value !== "string" || !value) return fallback;
  const path = value.trim();
  if (!path.startsWith("/")) return fallback;
  // A second leading slash (or backslash) makes it protocol relative.
  if (path.length > 1 && (path[1] === "/" || path[1] === "\\")) return fallback;
  if (path.includes("\\")) return fallback;
  return path;
}
