/**
 * Fill {placeholders} in a template string, mirroring backend merge_vars.
 *
 * Unknown placeholders are left visibly intact rather than blanked: a host
 * previewing "{atendee_name}" should SEE the typo, not an invisible hole where
 * a name was supposed to go.
 */
export function mergeVars(text, ctx) {
  if (!text) return "";
  return text.replace(/\{(\w+)\}/g, (m, key) =>
    ctx[key] !== undefined && ctx[key] !== null ? String(ctx[key]) : m
  );
}
