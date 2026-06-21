/**
 * Intro Connect mark — two stylized figures, primary blue + deep navy,
 * interlocking via negative space. Inline SVG so it scales cleanly and
 * inherits color when needed. To swap in the official asset, drop your
 * SVG export at /public/logo.svg and reference it as an <img />.
 */
export function Mark({ size = 40, primary = "#2563EB", deep = "#0D1B2A" }) {
  // Designed on a 64x64 grid. Two figures, each with a circular head and
  // a rounded-square body. Bodies are notched on the inner side so the
  // negative space between them reads as a chat-bubble / connector.
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      {/* Left figure (primary blue) */}
      <g fill={primary}>
        <circle cx="18" cy="14" r="7" />
        <path d="M8 28 a4 4 0 0 1 4 -4 h12 a4 4 0 0 1 4 4 v6 h-6 v8 h6 v6 a4 4 0 0 1 -4 4 h-12 a4 4 0 0 1 -4 -4 z" />
      </g>
      {/* Right figure (deep navy) */}
      <g fill={deep}>
        <circle cx="46" cy="14" r="7" />
        <path d="M56 28 a4 4 0 0 0 -4 -4 h-12 a4 4 0 0 0 -4 4 v6 h6 v8 h-6 v6 a4 4 0 0 0 4 4 h12 a4 4 0 0 0 4 -4 z" />
      </g>
    </svg>
  );
}

export function Lockup({ size = "lg", monochrome = false }) {
  const isLarge = size === "lg";
  const markSize = isLarge ? 56 : 32;
  const primary = monochrome ? "#0D1B2A" : "#2563EB";
  const deep = "#0D1B2A";
  return (
    <div className="inline-flex items-center gap-3">
      <Mark size={markSize} primary={primary} deep={deep} />
      <div className="leading-none">
        <div
          className={`font-extrabold text-ink tracking-tight ${
            isLarge ? "text-3xl" : "text-lg"
          }`}
        >
          Intro <span className="font-medium">Connect</span>
        </div>
        {isLarge && (
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-primary mt-2">
            Better events. Stronger connections.
          </div>
        )}
      </div>
    </div>
  );
}
