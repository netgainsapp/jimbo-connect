import { ArrowRight, CalendarDays, FileText, Layers } from "lucide-react";

const POINTS = [
  { icon: CalendarDays, label: "Multi day events group themselves by date" },
  { icon: FileText, label: "Downloads as a real Word file you can still edit" },
  { icon: Layers, label: "Drag sessions into the order you want" },
];

/** A miniature of the document the tool produces. Showing the output is the
 *  pitch: it is the thing the organizer actually wants. */
function AgendaPreview() {
  return (
    <div className="relative">
      <div
        aria-hidden="true"
        className="absolute -inset-4 rounded-card bg-primary/20 blur-2xl"
      />
      <div className="relative rounded-card bg-white shadow-lift p-6 sm:p-7 rotate-[-1.2deg]">
        <div className="flex justify-center">
          <div className="h-8 w-8 rounded-full bg-primary/15" />
        </div>
        <div className="mt-3 text-center">
          <div className="text-[15px] font-extrabold tracking-tight text-ink">
            Denver Founders Dinner
          </div>
          <div className="mt-0.5 text-[9px] text-stone">
            Saturday, August 1 · The Loft
          </div>
        </div>

        <div className="mt-5 text-[9px] font-extrabold uppercase tracking-[0.16em] text-primary">
          Saturday, August 1
        </div>
        <div className="mt-1.5 border-t border-line">
          {[
            ["5:30 PM", "Doors open and welcome drinks", "Rooftop terrace"],
            ["6:15 PM", "Opening remarks", "Scott Weiss · Main room"],
            ["6:45 PM", "Dinner, seated by table theme", "Main room"],
          ].map(([time, title, meta]) => (
            <div key={title} className="flex gap-3 border-b border-line py-2">
              <div className="w-14 shrink-0 text-[9px] font-bold text-ink/70">
                {time}
              </div>
              <div className="min-w-0">
                <div className="text-[10px] font-bold leading-tight text-ink">
                  {title}
                </div>
                <div className="text-[9px] leading-tight text-stone">{meta}</div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 text-center text-[7px] uppercase tracking-[0.18em] text-stone">
          Agenda created with Intro Connect
        </div>
      </div>
    </div>
  );
}

export default function AgendaTool() {
  return (
    <section id="agenda-tool" className="bg-ink text-white">
      <div className="container-prose py-20 sm:py-24">
        <div className="grid grid-cols-1 md:grid-cols-12 items-center gap-12 md:gap-16">
          <div className="md:col-span-7">
            <span className="inline-flex items-center rounded-pill bg-white/10 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.16em] text-wash">
              Free tool · No account needed
            </span>

            <h2 className="mt-5 text-4xl sm:text-5xl font-extrabold tracking-tight leading-[1.05]">
              Build your event agenda.
              <span className="block text-wash">Free, and yours to keep.</span>
            </h2>

            <p className="mt-5 max-w-xl text-lg leading-relaxed text-white/70">
              Stop fighting tab stops in a word processor. Add your sessions,
              drag them into order, and download an agenda that looks like
              someone designed it. No sign up, no payment, nothing to install.
            </p>

            <ul className="mt-7 space-y-3">
              {POINTS.map(({ icon: Icon, label }) => (
                <li key={label} className="flex items-center gap-3 text-white/85">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-pill bg-white/10">
                    <Icon className="h-3.5 w-3.5 text-wash" />
                  </span>
                  <span className="text-[15px]">{label}</span>
                </li>
              ))}
            </ul>

            <div className="mt-9 flex flex-wrap items-center gap-4">
              <a
                href="/agenda"
                className="inline-flex items-center justify-center gap-2 rounded-pill bg-white px-6 py-3 text-[15px] font-bold text-ink transition hover:bg-wash"
              >
                Build an agenda free <ArrowRight className="h-4 w-4" />
              </a>
              <span className="text-sm text-white/50">
                Takes about five minutes.
              </span>
            </div>
          </div>

          <div className="md:col-span-5">
            <AgendaPreview />
          </div>
        </div>
      </div>
    </section>
  );
}
