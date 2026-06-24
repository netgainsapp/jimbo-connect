import { ArrowRight, Calendar, Users, Bookmark, MessageCircle } from "lucide-react";

export default function Hero() {
  return (
    <section className="relative overflow-hidden">
      {/* Full-bleed networking photo, darkened so the headline stays crisp */}
      <img
        src="/images/networking-mixer.jpg"
        alt=""
        aria-hidden="true"
        width="1920"
        height="1280"
        loading="eager"
        fetchpriority="high"
        decoding="async"
        className="absolute inset-0 w-full h-full object-cover"
      />
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(90deg, rgba(13,27,42,0.93) 0%, rgba(13,27,42,0.80) 38%, rgba(13,27,42,0.52) 100%)",
        }}
      />
      <div className="container-prose pt-16 sm:pt-24 pb-20 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center relative">
        <div className="lg:col-span-7">
          <div className="text-[11px] uppercase tracking-[0.22em] font-extrabold text-wash">
            For event hosts
          </div>
          <h1 className="mt-4 text-5xl sm:text-6xl font-extrabold text-white leading-[1.02] tracking-tight">
            The room shouldn't disappear
            <br />
            <span className="text-[#7AA7F7]">by Monday.</span>
          </h1>
          <p className="mt-6 text-lg sm:text-xl text-white/80 max-w-xl leading-relaxed">
            Intro Connect turns every event you host into a private,
            searchable directory of everyone who came. Real introductions.
            Real follow-up. A network that compounds.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a href="#pricing" className="btn-primary">
              Start for free <ArrowRight className="w-4 h-4" />
            </a>
            <a
              href="#how"
              className="inline-flex items-center gap-2 px-7 py-3 rounded-pill border border-white/30 text-white font-bold hover:bg-white/10 transition"
            >
              See how it works
            </a>
          </div>
          <p className="mt-4 text-xs text-white/70 tracking-wide">
            Free plan · No credit card · Free for guests, forever
          </p>
        </div>

        <div className="lg:col-span-5">
          <MockApp />
        </div>
      </div>
    </section>
  );
}

function MockApp() {
  return (
    <div className="relative">
      <div className="absolute -inset-6 bg-gradient-to-br from-primary/15 via-wash to-transparent rounded-[28px] blur-2xl" />
      <div className="relative card overflow-hidden">
        <div className="border-b border-line h-10 flex items-center px-4 gap-1.5 bg-cream/50">
          <div className="w-2.5 h-2.5 rounded-full bg-red-300" />
          <div className="w-2.5 h-2.5 rounded-full bg-amber-300" />
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-300" />
          <div className="ml-3 text-xs text-stone font-mono">
            app.introconnect.com/events/denver-founders
          </div>
        </div>
        <div className="p-5">
          <div className="text-[10px] uppercase tracking-[0.2em] text-stone font-bold">
            Cohort
          </div>
          <div className="text-xl font-extrabold text-ink mt-1 tracking-tight">
            Denver Founders Dinner
          </div>
          <div className="flex items-center gap-3 text-xs text-stone mt-2">
            <span className="inline-flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5" /> Jun 15, 2026
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5" /> 24 attendees
            </span>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2">
            {[
              { name: "Ava Reynolds", role: "Founder · Trailhead Labs", img: "/images/avatars/avatar-4.jpg", saved: true },
              { name: "Ben Carter", role: "VP Eng · Summit Robotics", img: "/images/avatars/avatar-3.jpg", saved: false },
              { name: "Cara Liu", role: "Designer · Aspen Studio", img: "/images/avatars/avatar-5.jpg", saved: true },
              { name: "Diego Martinez", role: "Partner · Range Capital", img: "/images/avatars/avatar-1.jpg", saved: false },
            ].map((p) => (
              <div
                key={p.name}
                className="border border-line rounded-card p-3 flex items-start justify-between gap-2 bg-white"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <img
                    src={p.img}
                    alt={p.name}
                    loading="lazy"
                    className="w-8 h-8 rounded-full object-cover"
                  />
                  <div className="min-w-0">
                    <div className="text-sm font-bold text-ink truncate">{p.name}</div>
                    <div className="text-[10px] text-stone truncate">{p.role}</div>
                  </div>
                </div>
                <Bookmark
                  className={`w-4 h-4 shrink-0 ${
                    p.saved ? "fill-primary text-primary" : "text-stone"
                  }`}
                />
              </div>
            ))}
          </div>

          <div className="mt-4 flex items-center gap-2 text-xs text-primary font-semibold bg-wash rounded-card p-2">
            <MessageCircle className="w-3.5 h-3.5" />
            2 new messages from your network
          </div>
        </div>
      </div>
    </div>
  );
}
