import { Bookmark, BookmarkCheck, ArrowRight, Check } from "lucide-react";

const STEPS = [
  {
    n: "01",
    kicker: "Bring your guest list",
    title: "Paste names. Walk away.",
    body:
      "Drop in a CSV from Eventbrite, Meetup, or the spreadsheet you've been keeping. We create accounts, send everyone their login link, and attach a calendar invite. Setup is done before your coffee is.",
    visual: <PasteVisual />,
  },
  {
    n: "02",
    kicker: "The night of",
    title: "Your room becomes a directory.",
    body:
      "Attendees log in and see who else is there: name, role, company, what they're looking for. They save the people they meet with one tap. Notes, intros, and follow-ups, all in one place.",
    visual: <DirectoryVisual />,
  },
  {
    n: "03",
    kicker: "Six months later",
    title: "Connections compound.",
    body:
      "They can still find that designer. Message that investor. Intro a friend. The host (you) stays in everyone's network. Not as a stranger on LinkedIn, but as the reason any of this exists.",
    visual: <CompoundVisual />,
  },
];

export default function HowItWorks() {
  return (
    <section id="how" className="py-24 sm:py-32 bg-cream border-y border-line">
      <div className="container-prose">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 max-w-4xl">
          <div>
            <div className="eyebrow">How it works</div>
            <h2 className="mt-4 text-4xl sm:text-5xl font-extrabold text-ink leading-[1.05] tracking-tight">
              Three steps. <span className="text-primary">Five minutes</span>{" "}
              of setup.
            </h2>
          </div>
          <p className="text-stone text-[15px] max-w-sm">
            No onboarding calls. No implementation specialists. You will
            understand the product before you finish this page.
          </p>
        </div>

        <div className="mt-14 divide-y divide-line border-y border-line bg-white rounded-card overflow-hidden">
          {STEPS.map((s) => (
            <Step key={s.n} {...s} />
          ))}
        </div>
      </div>
    </section>
  );
}

function Step({ n, kicker, title, body, visual }) {
  return (
    <div className="grid grid-cols-12 gap-4 sm:gap-8 items-center py-10 sm:py-14 px-5 sm:px-8">
      {/* Big serif number */}
      <div className="col-span-12 sm:col-span-2 flex sm:block items-baseline gap-3">
        <div
          className="text-7xl sm:text-8xl font-extrabold text-primary leading-none tracking-tighter"
          style={{
            fontFeatureSettings: '"lnum" 1',
          }}
        >
          {n}
        </div>
        <div className="sm:hidden text-[11px] uppercase tracking-[0.2em] text-stone font-bold">
          {kicker}
        </div>
      </div>

      {/* Copy */}
      <div className="col-span-12 sm:col-span-6">
        <div className="hidden sm:block text-[11px] uppercase tracking-[0.2em] text-stone font-bold mb-2">
          {kicker}
        </div>
        <h3 className="text-2xl sm:text-3xl font-extrabold text-ink leading-[1.1] tracking-tight">
          {title}
        </h3>
        <p className="mt-3 text-[15px] sm:text-[16px] text-stone leading-relaxed">
          {body}
        </p>
      </div>

      {/* Mini visual */}
      <div className="col-span-12 sm:col-span-4">{visual}</div>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────────
   Step-specific mini visuals
   ────────────────────────────────────────────────────────────────────── */

function PasteVisual() {
  const rows = [
    ["ava@trailheadlabs.com", "Ava Reynolds", "Founder"],
    ["ben@summitrobotics.com", "Ben Carter", "VP Eng"],
    ["cara@aspenstudio.com", "Cara Liu", "Designer"],
    ["diego@rangecap.vc", "Diego Martinez", "Partner"],
  ];
  return (
    <div className="card bg-white p-3">
      <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-stone mb-2 px-1">
        guests.csv
      </div>
      <div className="font-mono text-[10px] leading-relaxed">
        <div className="flex gap-2 text-stone border-b border-line pb-1.5 mb-1.5">
          <span className="flex-1">email</span>
          <span className="flex-1">name</span>
          <span className="w-16">role</span>
        </div>
        {rows.map((r) => (
          <div key={r[0]} className="flex gap-2 text-ink py-0.5">
            <span className="flex-1 truncate">{r[0]}</span>
            <span className="flex-1 truncate">{r[1]}</span>
            <span className="w-16 truncate">{r[2]}</span>
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-center justify-end gap-1 text-[11px] text-primary font-bold tracking-wide">
        Import 4 guests <ArrowRight className="w-3.5 h-3.5" />
      </div>
    </div>
  );
}

function DirectoryVisual() {
  const people = [
    { name: "Ava Reynolds", role: "Trailhead Labs", img: "/images/avatars/avatar-4.jpg", saved: true },
    { name: "Ben Carter", role: "Summit Robotics", img: "/images/avatars/avatar-3.jpg", saved: false },
    { name: "Cara Liu", role: "Aspen Studio", img: "/images/avatars/avatar-5.jpg", saved: true },
  ];
  return (
    <div className="card bg-white p-3">
      <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-stone mb-2 px-1">
        24 attendees · live now
      </div>
      <div className="space-y-1.5">
        {people.map((p) => (
          <div
            key={p.name}
            className="flex items-center justify-between gap-2 border border-line rounded-card p-2"
          >
            <div className="flex items-center gap-2 min-w-0">
              <img
                src={p.img}
                alt={p.name}
                loading="lazy"
                className="w-7 h-7 rounded-full object-cover"
              />
              <div className="min-w-0">
                <div className="text-[12px] font-bold text-ink truncate">
                  {p.name}
                </div>
                <div className="text-[9px] text-stone truncate">{p.role}</div>
              </div>
            </div>
            {p.saved ? (
              <BookmarkCheck className="w-4 h-4 text-primary fill-primary shrink-0" />
            ) : (
              <Bookmark className="w-4 h-4 text-stone shrink-0" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function CompoundVisual() {
  // Three "events" stacked, attendees from earlier events showing up in later ones
  return (
    <div className="card bg-white p-4">
      <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-stone mb-3">
        Network over time
      </div>
      <div className="space-y-2.5">
        <Cohort label="Jan · Founders Dinner" count={24} marks={1} primary />
        <Cohort
          label="Apr · Sponsor Mixer"
          count={38}
          marks={2}
          callout="+14 returning"
        />
        <Cohort
          label="Jun · This week"
          count={51}
          marks={3}
          callout="+22 returning"
        />
      </div>
      <div className="mt-3 pt-3 border-t border-line flex items-center gap-2 text-[11px]">
        <Check className="w-3.5 h-3.5 text-primary" strokeWidth={3} />
        <span className="text-ink font-semibold">
          113 unique people in your network
        </span>
      </div>
    </div>
  );
}

function Cohort({ label, count, marks, callout, primary }) {
  return (
    <div className="flex items-center gap-2">
      <div className="text-[10px] text-stone font-bold w-32 truncate">
        {label}
      </div>
      <div className="flex-1 h-1.5 bg-cream rounded-pill overflow-hidden">
        <div
          className="h-full bg-primary rounded-pill"
          style={{ width: `${(count / 60) * 100}%`, opacity: 0.4 + marks * 0.2 }}
        />
      </div>
      <div className="text-[10px] font-bold text-ink w-7 text-right">
        {count}
      </div>
      {callout && (
        <div className="text-[9px] uppercase tracking-[0.15em] font-bold text-primary">
          {callout}
        </div>
      )}
    </div>
  );
}
