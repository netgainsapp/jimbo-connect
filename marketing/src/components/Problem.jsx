export default function Problem() {
  return (
    <section className="py-24 sm:py-32 relative overflow-hidden">
      <div className="container-prose grid grid-cols-1 md:grid-cols-12 gap-10 md:gap-16">
        <div className="md:col-span-5">
          <div className="md:sticky md:top-24">
            <div className="eyebrow">The problem</div>
            <h2 className="mt-4 text-4xl sm:text-5xl font-extrabold text-ink leading-[1.05] tracking-tight">
              Every event you run is{" "}
              <span className="text-primary">two events</span>.
            </h2>
            <p className="mt-5 text-lg text-stone leading-relaxed">
              <span className="font-extrabold text-ink">
                The one that happens that night
              </span>{" "}
              — and{" "}
              <span className="font-extrabold text-ink">
                the one that should happen for the next six months
              </span>{" "}
              between the people you brought together.
            </p>
            <p className="mt-4 text-lg text-stone leading-relaxed">
              But the second event almost never happens. Business cards get
              lost. LinkedIn requests sit unanswered. The room you carefully
              assembled evaporates by Monday morning.
            </p>
            <p className="mt-5 text-lg font-extrabold text-ink leading-tight">
              Intro Connect fixes that.
            </p>
          </div>
        </div>

        <div className="md:col-span-7">
          <div className="divide-y divide-line border-y border-line">
            <PullQuote
              text="I left dinner with 12 great conversations. By Friday I couldn't remember half the names."
              who="Every attendee"
              where="At every event ever"
            />
            <PullQuote
              text="My LinkedIn is full of strangers I once talked to for ten minutes."
              who="Also every attendee"
              where="Mostly hoping you'll log in"
            />
            <PullQuote
              text="I spend hours putting these dinners together. After everyone leaves, the value I created basically disappears."
              who="Hosts"
              where="The reason this exists"
            />
          </div>
        </div>
      </div>
    </section>
  );
}

function PullQuote({ text, who, where }) {
  return (
    <figure className="py-8 sm:py-10 relative">
      {/* Hanging serif quotation mark */}
      <span
        aria-hidden="true"
        className="absolute -left-2 sm:-left-4 -top-2 text-7xl sm:text-8xl text-primary/15 leading-none select-none"
        style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
      >
        &ldquo;
      </span>
      <blockquote className="relative pl-10 sm:pl-14">
        <p
          className="text-xl sm:text-2xl text-ink leading-[1.35] tracking-tight"
          style={{
            fontFamily: 'Georgia, "Times New Roman", serif',
            fontStyle: "italic",
            fontWeight: 500,
          }}
        >
          {text}
        </p>
        <figcaption className="mt-4 flex items-baseline gap-3 text-[11px] uppercase tracking-[0.22em] font-bold">
          <span className="text-ink">— {who}</span>
          <span className="h-px flex-1 bg-line max-w-[60px]" />
          <span className="text-stone normal-case tracking-normal font-semibold">
            {where}
          </span>
        </figcaption>
      </blockquote>
    </figure>
  );
}
