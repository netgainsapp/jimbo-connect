export default function SocialProof() {
  return (
    <section className="border-y border-line bg-cream">
      <div className="container-prose py-14">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 md:gap-12 items-center">
          <div className="md:col-span-5">
            <div className="overflow-hidden rounded-card border border-line shadow-lift">
              <img
                src="/images/AdobeStock_118993437.jpeg"
                alt="Guests networking with drinks at a business event"
                width="900"
                height="600"
                loading="lazy"
                className="w-full object-cover aspect-[4/3]"
              />
            </div>
          </div>

          <figure className="md:col-span-7">
            <blockquote
              className="text-xl sm:text-2xl text-ink leading-snug tracking-tight"
              style={{
                fontFamily: 'Georgia, "Times New Roman", serif',
                fontStyle: "italic",
                fontWeight: 500,
              }}
            >
              "I run a monthly banking and business networking night. We used to
              lose the room by the next morning. Now everyone who comes can still
              find each other months later, and I'm the one who put them
              together. It paid for itself after the first event."
            </blockquote>
            <figcaption className="mt-5 text-[12px] uppercase tracking-[0.2em] font-bold text-stone">
              Jim Hall <span className="text-primary">·</span> Host, Banking
              Business networking event
            </figcaption>
          </figure>
        </div>

        <div className="mt-12 text-[10px] uppercase tracking-[0.22em] text-stone font-bold text-center mb-5">
          Built for hosts who run rooms like these
        </div>
        <div className="flex flex-wrap items-center justify-center gap-x-10 gap-y-3 text-stone">
          {[
            "Founder Dinners",
            "Chamber Mixers",
            "VC Office Hours",
            "Cohort Reunions",
            "Industry Roundtables",
          ].map((s) => (
            <span
              key={s}
              className="font-bold text-base sm:text-lg tracking-tight text-ink/70"
            >
              {s}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
