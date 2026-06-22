import { Bookmark, BookmarkCheck, MessageCircle, Star } from "lucide-react";

/* ──────────────────────────────────────────────────────────────────────
   Each marquee feature gets a row — eyebrow, title, paragraph, and
   a real mini-UI preview (not an icon). Rows alternate sides so the
   page reads like a magazine spread, not a SaaS template.
   ────────────────────────────────────────────────────────────────────── */

const MARQUEE = [
  {
    eyebrow: "01 · Directory",
    title: "A private room, after the room.",
    body: "Every event you host turns into a searchable directory of who came. Photos, bios, role, company, contact info, what they're looking for. Mobile-first, and permanent on paid plans.",
    preview: <DirectoryPreview />,
  },
  {
    eyebrow: "02 · Notes",
    title: "Remember the conversation. Not just the name.",
    body: '"Lives in Boulder, building robotics, wants intro to Diego." Private notes attached to any saved contact, visible only to the person who wrote them.',
    preview: <NotesPreview />,
  },
  {
    eyebrow: "03 · Messages",
    title: "Reach anyone without losing their email.",
    body: "Direct messaging built in, scoped to people you shared a room with. No mass-blast tools. No spam. The thread lives in the directory.",
    preview: <MessagesPreview />,
  },
  {
    eyebrow: "04 · Sponsors",
    title: "Drop a URL. Get a sponsor tile.",
    body: "Paste a sponsor's website and we pull their headline, image, and description automatically. No uploading logos, no copy-writing. Click-through analytics included.",
    preview: <SponsorPreview />,
  },
];

const ALSO = [
  ["Save anyone, anytime", "One tap and they're saved to your contacts."],
  ["Custom personal tags", '"Warm lead," "investor," "Q3 follow-up." Each user builds their own.'],
  ["Editable email templates", "Save the date, day-of, post-event. Eight templates."],
  [".ics calendar invites", 'One-click "Add to calendar" in every invitation email.'],
  ["Custom post-event surveys", "Six question types. Charts. Per-event."],
  ["Clone any event", "Recurring monthly dinner? Duplicate in one click."],
  ["CSV import from anywhere", "Eventbrite, Meetup, your spreadsheet."],
  ["Custom branding per event", "Your logo, your color, your name."],
];

export default function Features() {
  return (
    <section id="features" className="py-24 sm:py-32">
      <div className="container-prose">
        <div className="max-w-2xl">
          <div className="eyebrow">Features</div>
          <h2 className="mt-4 text-4xl sm:text-5xl font-extrabold text-ink leading-[1.05] tracking-tight">
            Built for the way{" "}
            <span className="text-primary">hosts actually work</span>.
          </h2>
          <p className="mt-4 text-lg text-stone leading-relaxed">
            Not another CRM. Not another email tool. The minimum amount of
            software it takes to turn a guest list into a network that lasts.
          </p>
        </div>

        <div className="mt-16 divide-y divide-line border-y border-line">
          {MARQUEE.map((f, i) => (
            <FeatureRow key={f.eyebrow} {...f} flipped={i % 2 === 1} />
          ))}
        </div>

        <div className="mt-20">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-stone mb-6">
            And also
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-5">
            {ALSO.map(([title, body]) => (
              <div key={title} className="border-l-2 border-primary/30 pl-4">
                <div className="font-extrabold text-ink text-[15px] leading-tight tracking-tight">
                  {title}
                </div>
                <div className="text-[13px] text-stone mt-1 leading-relaxed">
                  {body}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function FeatureRow({ eyebrow, title, body, preview, flipped }) {
  return (
    <div className="py-12 sm:py-16 grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
      <div
        className={`lg:col-span-5 ${
          flipped ? "lg:order-2 lg:col-start-8" : ""
        }`}
      >
        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-primary">
          {eyebrow}
        </div>
        <h3 className="mt-3 text-3xl sm:text-4xl font-extrabold text-ink leading-[1.1] tracking-tight">
          {title}
        </h3>
        <p className="mt-4 text-[17px] text-stone leading-relaxed">{body}</p>
      </div>
      <div
        className={`lg:col-span-6 ${
          flipped ? "lg:order-1 lg:col-start-1" : "lg:col-start-7"
        }`}
      >
        {preview}
      </div>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────────
   Mini UI previews — small fragments of the real product, rendered in
   the brand palette. Each one is a 3-second glance, not a screenshot.
   ────────────────────────────────────────────────────────────────────── */

function PreviewFrame({ children }) {
  return (
    <div className="card p-4 bg-cream/40">
      <div className="bg-white border border-line rounded-card p-3">
        {children}
      </div>
    </div>
  );
}

function DirectoryPreview() {
  const people = [
    { name: "Ava Reynolds", role: "Founder · Trailhead Labs", saved: true },
    { name: "Ben Carter", role: "VP Eng · Summit Robotics", saved: false },
    { name: "Cara Liu", role: "Designer · Aspen Studio", saved: true },
    { name: "Diego Martinez", role: "Partner · Range Capital", saved: false },
  ];
  return (
    <PreviewFrame>
      <div className="flex items-center justify-between mb-3">
        <div className="text-sm font-extrabold text-ink tracking-tight">
          Denver Founders Dinner
        </div>
        <div className="text-[10px] text-stone font-semibold">24 attendees</div>
      </div>
      <div className="space-y-2">
        {people.map((p) => (
          <div
            key={p.name}
            className="flex items-center justify-between gap-2 border border-line rounded-card p-2.5"
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-7 h-7 rounded-full bg-wash text-primary text-[10px] font-bold flex items-center justify-center">
                {p.name.split(" ").map((s) => s[0]).join("")}
              </div>
              <div className="min-w-0">
                <div className="text-[13px] font-bold text-ink truncate">
                  {p.name}
                </div>
                <div className="text-[10px] text-stone truncate">{p.role}</div>
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
    </PreviewFrame>
  );
}

function NotesPreview() {
  return (
    <div className="grid grid-cols-2 gap-3">
      <div
        className="relative p-4 rounded-card text-ink"
        style={{
          background:
            "linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%)",
          fontFamily: "Georgia, serif",
          transform: "rotate(-1.5deg)",
        }}
      >
        <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-amber-700 mb-1.5">
          Cara Liu
        </div>
        <p className="text-[13px] leading-snug italic">
          "Designs for outdoor brands. Mentioned a Patagonia project ending in
          Q3, circle back then re: brand work for us."
        </p>
        <div className="text-[10px] text-amber-700/70 mt-2 font-semibold">
          Saved at Denver Founders Dinner · Jun 15
        </div>
      </div>
      <div
        className="relative p-4 rounded-card text-ink"
        style={{
          background:
            "linear-gradient(135deg, #DBEAFE 0%, #BFDBFE 100%)",
          fontFamily: "Georgia, serif",
          transform: "rotate(1.5deg)",
        }}
      >
        <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-blue-700 mb-1.5">
          Diego Martinez
        </div>
        <p className="text-[13px] leading-snug italic">
          "Range Capital seed/series A · Outdoor & mountain west · Wants intro
          to anyone in robotics."
        </p>
        <div className="text-[10px] text-blue-700/70 mt-2 font-semibold">
          Visible only to me
        </div>
      </div>
    </div>
  );
}

function MessagesPreview() {
  return (
    <PreviewFrame>
      <div className="flex items-center gap-2 pb-3 mb-3 border-b border-line">
        <div className="w-8 h-8 rounded-full bg-wash text-primary text-[11px] font-bold flex items-center justify-center">
          AR
        </div>
        <div>
          <div className="text-sm font-bold text-ink">Ava Reynolds</div>
          <div className="text-[10px] text-stone">Founder · Trailhead Labs</div>
        </div>
      </div>
      <div className="space-y-2">
        <Bubble side="left">
          Loved the founder dinner Thursday. Wanted to follow up on what you
          mentioned about open-source distribution.
        </Bubble>
        <Bubble side="right">
          Same! Free Thursday for coffee? I'm in RiNo most mornings.
        </Bubble>
        <Bubble side="left">Thursday 9am at Crema. Calendar invite incoming.</Bubble>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <div className="flex-1 border border-line rounded-pill px-3 py-1.5 text-xs text-stone">
          Reply…
        </div>
        <div className="w-8 h-8 rounded-pill bg-primary text-white flex items-center justify-center">
          <MessageCircle className="w-3.5 h-3.5" />
        </div>
      </div>
    </PreviewFrame>
  );
}

function Bubble({ side, children }) {
  const right = side === "right";
  return (
    <div className={`flex ${right ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] text-[12px] leading-snug px-3 py-2 rounded-card ${
          right
            ? "bg-primary text-white rounded-br-sm"
            : "bg-cream text-ink rounded-bl-sm"
        }`}
      >
        {children}
      </div>
    </div>
  );
}

function SponsorPreview() {
  return (
    <div className="grid grid-cols-5 gap-3 items-center">
      <div className="col-span-2 border border-line rounded-card p-3 bg-white">
        <div className="text-[10px] text-stone font-semibold">paste URL</div>
        <div className="mt-1.5 font-mono text-[11px] text-ink truncate border-b border-line pb-1.5">
          https://trailheadlabs.com
        </div>
        <div className="mt-3 text-[10px] text-primary font-bold tracking-[0.15em] uppercase">
          → Generate tile
        </div>
      </div>
      <div className="col-span-3 card overflow-hidden">
        <div
          className="aspect-[16/9]"
          style={{
            background:
              "linear-gradient(135deg, #134E4A 0%, #2563EB 100%)",
          }}
        >
          <div className="h-full flex items-center justify-center text-white font-extrabold tracking-tight text-lg">
            Trailhead Labs
          </div>
        </div>
        <div className="p-3">
          <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-stone">
            Sponsor
          </div>
          <div className="text-sm font-extrabold text-ink mt-0.5">
            Developer tools for outdoor brands
          </div>
          <div className="text-[11px] text-stone mt-1 line-clamp-2">
            Open-source distribution and embedded checkout for outdoor and
            adventure DTC.
          </div>
        </div>
      </div>
    </div>
  );
}
