import { useState, useEffect } from "react";

// Three distinct logo directions. View at http://localhost:3001/#logos
//
// Direction A — Stamped Wordmark (FRDC house style)
//   Same brand grammar as Front Range Dev Co. All-caps, heavy weight,
//   horizontal flank lines around the secondary word. Most "hand-stamped"
//   feel; least app-store-friendly as a tiny favicon.
//
// Direction B — Two Rings + Sans Wordmark
//   Distinctive mark: two interlocking circles. Universally reads as
//   "connection." Pairs with a clean modern sans wordmark. Strong icon,
//   slightly more SaaS-y feel.
//
// Direction C — Topographic + Serif
//   Concentric arcs that read as Colorado contour lines AND ripples from
//   a stone dropped in water — the network spreading out from one event.
//   Editorial serif wordmark for warmth. Most distinctive overall;
//   warmest, least typical.

export default function LogoExplorations() {
  return (
    <div className="min-h-screen bg-[#FAF8F4] text-[#0a0c10] font-sans">
      <header className="border-b border-[#E4E0D8] py-4">
        <div className="max-w-5xl mx-auto px-6 flex items-center justify-between">
          <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#6B7280]">
            Logo explorations · pick your favorite
          </div>
          <a
            href="/"
            className="text-xs uppercase tracking-[0.2em] font-bold text-[#0a0c10] hover:underline"
          >
            ← back to live site
          </a>
        </div>
      </header>

      <DirectionA />
      <DirectionB />
      <DirectionC />

      <footer className="py-12 text-center text-xs text-[#6B7280]">
        Once you pick — A, B, or C — I'll rebuild the whole marketing site +
        the app to match.
      </footer>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────────
   Direction A — STAMPED WORDMARK (FRDC house style)
   ────────────────────────────────────────────────────────────────────── */
function DirectionA() {
  return (
    <section className="py-16 border-b border-[#E4E0D8]">
      <div className="max-w-5xl mx-auto px-6">
        <Label letter="A" name="Stamped Wordmark" />
        <p className="text-[#3D4454] max-w-2xl mb-10">
          Same brand grammar as <i>FRONT RANGE / DEV CO.</i> — all caps, heavy
          black weight, horizontal flank lines around the secondary word. Feels
          like a typeset stamp, not a software logo. Best for a hosts-only
          audience that values craft over flash.
        </p>

        {/* Big wordmark */}
        <div className="bg-white border border-[#E4E0D8] rounded p-16 flex items-center justify-center">
          <WordmarkA size="lg" />
        </div>

        {/* In nav context */}
        <div className="mt-6 bg-white border border-[#E4E0D8] rounded">
          <FakeNav>
            <WordmarkA size="sm" />
          </FakeNav>
        </div>

        {/* Favicon / tight version */}
        <div className="mt-6 flex items-center gap-4">
          <div className="text-xs uppercase tracking-[0.15em] text-[#6B7280] font-bold w-24">
            Favicon
          </div>
          <div className="w-16 h-16 bg-[#0a0c10] text-white flex items-center justify-center font-black text-2xl tracking-tighter">
            J·C
          </div>
          <div className="w-16 h-16 bg-white border-2 border-[#0a0c10] text-[#0a0c10] flex items-center justify-center font-black text-2xl tracking-tighter">
            J·C
          </div>
        </div>
      </div>
    </section>
  );
}

function WordmarkA({ size = "lg" }) {
  const big = size === "lg";
  return (
    <div className="text-center text-[#0a0c10] leading-none select-none">
      <div
        className={`font-black tracking-[0.04em] ${
          big ? "text-6xl" : "text-xl"
        }`}
      >
        JIMBO
      </div>
      <div
        className={`flex items-center justify-center gap-2 font-bold tracking-[0.3em] mt-1 ${
          big ? "text-sm" : "text-[8px]"
        }`}
      >
        <span
          className="bg-current"
          style={{ height: "1px", width: big ? "32px" : "12px" }}
        />
        CONNECT
        <span
          className="bg-current"
          style={{ height: "1px", width: big ? "32px" : "12px" }}
        />
      </div>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────────
   Direction B — TWO RINGS + SANS
   ────────────────────────────────────────────────────────────────────── */
function DirectionB() {
  const accent = "#2E5266"; // muted slate-teal, warmer than LinkedIn blue
  return (
    <section className="py-16 border-b border-[#E4E0D8]">
      <div className="max-w-5xl mx-auto px-6">
        <Label letter="B" name="Two Rings" />
        <p className="text-[#3D4454] max-w-2xl mb-10">
          Two interlocking circles — reads as <i>connection</i> at a glance.
          Pairs with a clean modern sans wordmark. The icon stands alone in
          tight spaces (favicon, app icon, social avatars). More icon-driven
          than A, easier to brand merch with.
        </p>

        <div className="bg-white border border-[#E4E0D8] rounded p-16 flex items-center justify-center gap-6">
          <RingsMark size={96} color={accent} />
          <WordmarkB color={accent} size="lg" />
        </div>

        <div className="mt-6 bg-white border border-[#E4E0D8] rounded">
          <FakeNav>
            <div className="flex items-center gap-2">
              <RingsMark size={28} color={accent} />
              <WordmarkB color={accent} size="sm" />
            </div>
          </FakeNav>
        </div>

        <div className="mt-6 flex items-center gap-4">
          <div className="text-xs uppercase tracking-[0.15em] text-[#6B7280] font-bold w-24">
            Favicon
          </div>
          <div
            className="w-16 h-16 rounded-lg flex items-center justify-center"
            style={{ background: accent }}
          >
            <RingsMark size={36} color="white" />
          </div>
          <div className="w-16 h-16 rounded-lg bg-white border border-[#E4E0D8] flex items-center justify-center">
            <RingsMark size={36} color={accent} />
          </div>
        </div>
      </div>
    </section>
  );
}

function RingsMark({ size = 48, color = "#2E5266" }) {
  const r = size * 0.32;
  const offset = size * 0.18;
  const cx1 = size / 2 - offset;
  const cx2 = size / 2 + offset;
  const cy = size / 2;
  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      fill="none"
      stroke={color}
      strokeWidth={size * 0.06}
    >
      <circle cx={cx1} cy={cy} r={r} />
      <circle cx={cx2} cy={cy} r={r} />
    </svg>
  );
}

function WordmarkB({ size = "lg", color = "#2E5266" }) {
  const big = size === "lg";
  return (
    <div
      className={`font-black tracking-tight leading-none select-none ${
        big ? "text-5xl" : "text-lg"
      }`}
      style={{ color }}
    >
      Jimbo<span className="font-light">·</span>Connect
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────────
   Direction C — TOPOGRAPHIC + SERIF
   ────────────────────────────────────────────────────────────────────── */
function DirectionC() {
  const accent = "#A8593E"; // ochre / sunset
  return (
    <section className="py-16">
      <div className="max-w-5xl mx-auto px-6">
        <Label letter="C" name="Topographic + Serif" />
        <p className="text-[#3D4454] max-w-2xl mb-10">
          Concentric arcs — reads as both Colorado contour lines AND ripples
          from a stone dropped in water. The network spreading out from one
          event. Paired with an editorial serif for warmth and a sense of
          permanence. Least like other SaaS sites. Most distinctly{" "}
          <i>yours</i>.
        </p>

        <div className="bg-white border border-[#E4E0D8] rounded p-16 flex items-center justify-center gap-8">
          <TopoMark size={96} color={accent} />
          <WordmarkC color={accent} size="lg" />
        </div>

        <div className="mt-6 bg-white border border-[#E4E0D8] rounded">
          <FakeNav>
            <div className="flex items-center gap-2.5">
              <TopoMark size={28} color={accent} />
              <WordmarkC color={accent} size="sm" />
            </div>
          </FakeNav>
        </div>

        <div className="mt-6 flex items-center gap-4">
          <div className="text-xs uppercase tracking-[0.15em] text-[#6B7280] font-bold w-24">
            Favicon
          </div>
          <div
            className="w-16 h-16 rounded-lg flex items-center justify-center"
            style={{ background: accent }}
          >
            <TopoMark size={36} color="white" />
          </div>
          <div className="w-16 h-16 rounded-lg bg-white border border-[#E4E0D8] flex items-center justify-center">
            <TopoMark size={36} color={accent} />
          </div>
        </div>
      </div>
    </section>
  );
}

function TopoMark({ size = 48, color = "#A8593E" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
      <path
        d="M4 38 Q24 24 44 38"
        stroke={color}
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <path
        d="M8 32 Q24 20 40 32"
        stroke={color}
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <path
        d="M12 26 Q24 16 36 26"
        stroke={color}
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <path
        d="M16 20 Q24 13 32 20"
        stroke={color}
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <circle cx="24" cy="14" r="2.5" fill={color} />
    </svg>
  );
}

function WordmarkC({ size = "lg", color = "#A8593E" }) {
  const big = size === "lg";
  return (
    <div
      className={`leading-none select-none ${big ? "text-5xl" : "text-lg"}`}
      style={{
        color,
        fontFamily: 'Georgia, "Times New Roman", Tiempos, serif',
        fontWeight: 700,
        letterSpacing: "-0.02em",
      }}
    >
      Jimbo <span style={{ fontStyle: "italic", fontWeight: 400 }}>Connect</span>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────────
   Shared bits
   ────────────────────────────────────────────────────────────────────── */
function Label({ letter, name }) {
  return (
    <div className="flex items-baseline gap-3 mb-4">
      <div className="text-7xl font-black text-[#0a0c10] leading-none">
        {letter}
      </div>
      <div>
        <div className="text-2xl font-bold text-[#0a0c10] leading-tight">
          {name}
        </div>
        <div className="text-xs uppercase tracking-[0.15em] text-[#6B7280] font-bold">
          Direction {letter}
        </div>
      </div>
    </div>
  );
}

function FakeNav({ children }) {
  return (
    <div className="px-5 h-12 flex items-center justify-between border-b border-[#E4E0D8]">
      {children}
      <div className="flex items-center gap-4 text-xs font-bold text-[#3D4454]">
        <span>Features</span>
        <span>Pricing</span>
        <span>FAQ</span>
      </div>
    </div>
  );
}
