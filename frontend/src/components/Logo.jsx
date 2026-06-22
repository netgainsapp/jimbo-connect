/**
 * Intro Connect mark — two stylized figures interlocking through the negative
 * space between their bodies. Shared across the app nav and auth screens.
 *
 * variant:
 *   "primary"  — brand blue + deep navy, for light surfaces
 *   "reversed" — light blue + white, for dark surfaces
 *   "mono"     — single ink (one figure solid, one at 45%), one-color contexts
 */
const PALETTE = {
  primary: { a: "#2563EB", b: "#0D1B2A", bOpacity: 1 },
  reversed: { a: "#4F8DF7", b: "#FFFFFF", bOpacity: 1 },
  mono: { a: "currentColor", b: "currentColor", bOpacity: 0.45 },
};

export function Mark({ size = 32, variant = "primary", className = "" }) {
  const p = PALETTE[variant] || PALETTE.primary;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className={className}
    >
      <g fill={p.a}>
        <circle cx="18" cy="14" r="7" />
        <path d="M8 28 a4 4 0 0 1 4 -4 h12 a4 4 0 0 1 4 4 v6 h-6 v8 h6 v6 a4 4 0 0 1 -4 4 h-12 a4 4 0 0 1 -4 -4 z" />
      </g>
      <g fill={p.b} opacity={p.bOpacity}>
        <circle cx="46" cy="14" r="7" />
        <path d="M56 28 a4 4 0 0 0 -4 -4 h-12 a4 4 0 0 0 -4 4 v6 h6 v8 h-6 v6 a4 4 0 0 0 4 4 h12 a4 4 0 0 0 4 -4 z" />
      </g>
    </svg>
  );
}
