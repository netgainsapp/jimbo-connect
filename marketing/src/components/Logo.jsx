/**
 * Intro Connect mark — two stylized figures interlocking through the negative
 * space between their bodies. Inline SVG so it scales cleanly and travels with
 * the code. To swap in an official export, drop an SVG at /public/logo.svg.
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

export function Mark({ size = 40, variant = "primary", primary, deep }) {
  const p = PALETTE[variant] || PALETTE.primary;
  const aFill = primary || p.a;
  const bFill = deep || p.b;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <g fill={aFill}>
        <circle cx="18" cy="14" r="7" />
        <path d="M8 28 a4 4 0 0 1 4 -4 h12 a4 4 0 0 1 4 4 v6 h-6 v8 h6 v6 a4 4 0 0 1 -4 4 h-12 a4 4 0 0 1 -4 -4 z" />
      </g>
      <g fill={bFill} opacity={p.bOpacity}>
        <circle cx="46" cy="14" r="7" />
        <path d="M56 28 a4 4 0 0 0 -4 -4 h-12 a4 4 0 0 0 -4 4 v6 h6 v8 h-6 v6 a4 4 0 0 0 4 4 h12 a4 4 0 0 0 4 -4 z" />
      </g>
    </svg>
  );
}

export function Lockup({ size = "lg", variant = "primary", monochrome = false }) {
  const isLarge = size === "lg";
  const markSize = isLarge ? 56 : 32;
  const v = monochrome ? "mono" : variant;
  const reversed = v === "reversed";
  const wordColor = reversed ? "#FFFFFF" : v === "mono" ? "currentColor" : "#0D1B2A";
  const connectColor = reversed ? "#C9D6E5" : null;
  const taglineColor = reversed ? "#7FB0FF" : "#2563EB";
  return (
    <div className="inline-flex items-center gap-3">
      <Mark size={markSize} variant={v} />
      <div className="leading-none">
        <div
          className={`font-extrabold tracking-tight ${isLarge ? "text-3xl" : "text-lg"}`}
          style={{ color: wordColor }}
        >
          Intro{" "}
          <span className="font-medium" style={connectColor ? { color: connectColor } : undefined}>
            Connect
          </span>
        </div>
        {isLarge && (
          <div
            className="text-[10px] uppercase tracking-[0.22em] font-bold mt-2"
            style={{ color: taglineColor }}
          >
            Better events. Stronger connections.
          </div>
        )}
      </div>
    </div>
  );
}
