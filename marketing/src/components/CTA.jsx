import { ArrowRight } from "lucide-react";

export default function CTA() {
  return (
    <section
      className="py-24 sm:py-32 text-white relative overflow-hidden"
      style={{ background: "linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)" }}
    >
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(60% 60% at 82% 0%, rgba(255,255,255,0.14) 0%, transparent 60%)",
        }}
      />
      <div className="container-prose text-center max-w-2xl relative">
        <div className="text-[10px] uppercase tracking-[0.22em] font-extrabold text-white/75">
          No long-term contract. No credit card.
        </div>
        <h2 className="mt-5 text-4xl sm:text-5xl font-extrabold leading-[1.05] tracking-tight">
          Turn your next guest list into a network.
        </h2>
        <p className="mt-5 text-lg text-white/85 leading-relaxed">
          Start on the free plan today. Set up your first event in five minutes.
          If your attendees don't use it, walk away.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <a
            href="https://jimbo.frontrangedev.co/register"
            target="_blank"
            rel="noopener"
            className="inline-flex items-center gap-2 px-7 py-3 rounded-pill bg-white text-ink font-bold hover:bg-cream transition shadow-lift"
          >
            Start for free <ArrowRight className="w-4 h-4" />
          </a>
          <a
            href="mailto:hello@frontrangedev.co?subject=Intro%20Connect%20demo"
            className="inline-flex items-center gap-2 px-7 py-3 rounded-pill border border-white/30 text-white font-bold hover:bg-white/10 transition"
          >
            Schedule a 15-min demo
          </a>
        </div>
      </div>
    </section>
  );
}
