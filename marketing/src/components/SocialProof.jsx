export default function SocialProof() {
  return (
    <section className="border-y border-line bg-cream">
      <div className="container-prose py-10">
        <div className="text-[10px] uppercase tracking-[0.22em] text-stone font-bold text-center mb-5">
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
