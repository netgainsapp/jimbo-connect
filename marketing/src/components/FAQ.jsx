import { useState } from "react";
import { Plus, Minus } from "lucide-react";

const FAQS = [
  {
    q: "Is it really free for attendees?",
    a: "Yes, forever. Attendees never pay, never see ads, never get tracked or marketed to. Hosts pay so the platform can exist. That's the deal.",
  },
  {
    q: "How is this different from LinkedIn?",
    a: "LinkedIn is a public network where you accumulate strangers. Intro Connect is a private directory scoped to people you actually shared a room with. Different problem, different shape.",
  },
  {
    q: "What stops attendees from spamming each other?",
    a: "Directories are scoped to single events, so only people who came to your dinner see each other. Anyone can mute or hide their profile. No mass-message tools.",
  },
  {
    q: "Can I import my guest list from Meetup or Eventbrite?",
    a: "CSV import works today (paste from anywhere). Native Meetup and Eventbrite integrations are on the roadmap for Q3 2026.",
  },
  {
    q: "Who owns the data?",
    a: "Hosts own their event data. Attendees own their profiles and can delete their account anytime. We don't sell data, ever. It's written into our terms.",
  },
  {
    q: "What happens to the directory if I cancel?",
    a: "Your past events stay live for 60 days so attendees can still access them. After that, the data is exported to you as a CSV and the directories are taken offline.",
  },
  {
    q: "Can I bring my own domain?",
    a: "On Pro and Enterprise, yes. Use your-name.com or app.your-name.com, and we handle the SSL and DNS guidance.",
  },
  {
    q: "Do you have an iPhone or Android app?",
    a: "Not yet. The web app is fully mobile-optimized, so add it to your home screen and it behaves like a native app. Native apps are on the roadmap once we have 50+ paying hosts.",
  },
];

export default function FAQ() {
  const [open, setOpen] = useState(0);
  return (
    <section id="faq" className="py-24 sm:py-32 bg-cream border-y border-line">
      <div className="container-prose">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
          <div className="lg:col-span-4">
            <div className="lg:sticky lg:top-24">
              <div className="eyebrow">FAQ</div>
              <h2 className="mt-4 text-4xl sm:text-5xl font-extrabold text-ink leading-[1.05] tracking-tight">
                Things people ask before signing up.
              </h2>
              <p className="mt-4 text-stone text-[15px] leading-relaxed">
                Don't see your question?{" "}
                <a
                  href="mailto:hello@frontrangedev.co"
                  className="text-primary font-bold hover:underline"
                >
                  Email us.
                </a>{" "}
                We answer everything ourselves.
              </p>
            </div>
          </div>

          <div className="lg:col-span-8 divide-y divide-line border-t border-line">
            {FAQS.map((f, i) => {
              const isOpen = open === i;
              return (
                <div key={f.q}>
                  <button
                    onClick={() => setOpen(isOpen ? -1 : i)}
                    aria-expanded={isOpen}
                    aria-controls={`faq-answer-${i}`}
                    className="w-full py-6 text-left flex items-start justify-between gap-6 group"
                  >
                    <div className="flex items-start gap-4 min-w-0">
                      <span
                        className="text-[11px] font-mono font-bold text-primary mt-1 shrink-0"
                        style={{ fontFeatureSettings: '"tnum" 1' }}
                      >
                        Q.{String(i + 1).padStart(2, "0")}
                      </span>
                      <span className="text-lg sm:text-xl font-extrabold text-ink tracking-tight group-hover:text-primary transition leading-tight">
                        {f.q}
                      </span>
                    </div>
                    <div className="shrink-0 mt-1.5">
                      {isOpen ? (
                        <Minus className="w-4 h-4 text-primary" />
                      ) : (
                        <Plus className="w-4 h-4 text-stone" />
                      )}
                    </div>
                  </button>
                  {isOpen && (
                    <div id={`faq-answer-${i}`} className="pb-6 pl-12 pr-2 -mt-2">
                      <p className="text-[15px] text-stone leading-relaxed">
                        {f.a}
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
