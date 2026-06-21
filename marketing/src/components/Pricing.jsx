import { ArrowRight, Check } from "lucide-react";

const STARTER = {
  name: "Starter",
  price: "$99",
  period: "/month",
  blurb: "For solo hosts running a handful of events a year.",
  cta: "Start free trial",
  href: "https://jimbo.frontrangedev.co/register",
  features: [
    "Up to 6 events per year",
    "Up to 200 attendees per event",
    "Full directory + saved contacts",
    "In-app DMs",
    "Custom branding (logo, color, name)",
    "Email invitations via your domain",
  ],
};

const PRO = {
  name: "Pro",
  price: "$249",
  period: "/month",
  blurb: "For hosts running events most weeks.",
  cta: "Start free trial",
  href: "https://jimbo.frontrangedev.co/register",
  features: [
    "Unlimited events",
    "Unlimited attendees",
    "Custom subdomain (yours.introconnect.com)",
    "Editable email templates",
    "Post-event surveys with analytics",
    "Sponsor tile auto-generation",
    "Calendar (.ics) invites",
    "Recurring event cloning",
    "Priority support",
  ],
};

const ENTERPRISE = {
  name: "Enterprise",
  price: "Contact",
  blurb: "For organizations running events across multiple hosts.",
  cta: "Schedule a call",
  href: "mailto:hello@frontrangedev.co?subject=Intro%20Connect%20Enterprise",
  features: [
    "Multiple host accounts",
    "SSO via Google or Microsoft",
    "Custom integrations (Meetup, CRMs)",
    "Dedicated support",
    "On-premise deploy option",
    "Custom contracts and SLAs",
  ],
};

export default function Pricing() {
  return (
    <section id="pricing" className="py-24 sm:py-32">
      <div className="container-prose">
        <div className="max-w-3xl">
          <div className="eyebrow">Pricing</div>
          <h2 className="mt-4 text-4xl sm:text-5xl font-extrabold text-ink leading-[1.05] tracking-tight">
            Free for guests.{" "}
            <span className="text-primary">Fair for hosts.</span>
          </h2>
          <p className="mt-4 text-lg text-stone leading-relaxed">
            Attendees never pay. Hosts pay so the platform exists and the
            directory stays private. No ads, no tracking, no data sale —
            written into the terms.
          </p>
        </div>

        {/* Three columns — Pro is the centerpiece, dark and dominant.
            Starter and Enterprise flank it as quieter outline tiers. */}
        <div className="mt-16 grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          <SideTier tier={STARTER} />
          <CenterTier tier={PRO} />
          <SideTier tier={ENTERPRISE} />
        </div>

        <p className="mt-10 text-center text-xs text-stone tracking-wide">
          14-day free trial. No credit card required. Cancel anytime.
        </p>
      </div>
    </section>
  );
}

function SideTier({ tier }) {
  return (
    <div className="lg:col-span-4 border-t-4 border-stone/20 pt-6">
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-2xl font-extrabold text-ink tracking-tight">
          {tier.name}
        </h3>
        <div className="text-right">
          <div className="text-2xl font-extrabold text-ink tracking-tight">
            {tier.price}
          </div>
          {tier.period && (
            <div className="text-[11px] text-stone font-semibold">
              {tier.period}
            </div>
          )}
        </div>
      </div>
      <p className="mt-2 text-[14px] text-stone">{tier.blurb}</p>

      <a
        href={tier.href}
        target={tier.href.startsWith("http") ? "_blank" : undefined}
        rel="noopener"
        className="mt-5 inline-flex items-center gap-1.5 text-[14px] font-bold text-primary hover:underline"
      >
        {tier.cta} <ArrowRight className="w-3.5 h-3.5" />
      </a>

      <ul className="mt-6 space-y-2 text-[13px]">
        {tier.features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-stone">
            <Check
              className="w-3.5 h-3.5 text-primary shrink-0 mt-1"
              strokeWidth={3}
            />
            <span>{f}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function CenterTier({ tier }) {
  return (
    <div className="lg:col-span-4 relative">
      <div
        className="absolute -inset-3 rounded-card -z-10 opacity-90"
        style={{
          background:
            "radial-gradient(60% 80% at 50% 0%, rgba(37,99,235,0.18) 0%, transparent 70%)",
        }}
      />
      <div className="relative bg-ink text-white rounded-card p-8 shadow-lift overflow-hidden">
        <div
          className="absolute inset-0 opacity-30 -z-0"
          style={{
            background:
              "radial-gradient(50% 50% at 30% 0%, #2563EB 0%, transparent 60%)",
          }}
        />
        <div className="relative">
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase tracking-[0.22em] font-extrabold text-wash">
              Most popular
            </span>
            <span className="h-px flex-1 bg-white/15" />
          </div>
          <h3 className="mt-4 text-3xl font-extrabold tracking-tight">
            {tier.name}
          </h3>
          <p className="mt-1 text-[14px] text-white/70">{tier.blurb}</p>

          <div className="mt-5 flex items-baseline gap-1">
            <span className="text-5xl font-extrabold tracking-tight">
              {tier.price}
            </span>
            <span className="text-sm text-white/70 font-semibold">
              {tier.period}
            </span>
          </div>

          <a
            href={tier.href}
            target="_blank"
            rel="noopener"
            className="mt-6 inline-flex items-center justify-center w-full gap-2 px-7 py-3 rounded-pill bg-white text-ink font-bold hover:bg-cream transition"
          >
            {tier.cta} <ArrowRight className="w-4 h-4" />
          </a>

          <ul className="mt-7 space-y-2.5 text-[14px]">
            {tier.features.map((f) => (
              <li key={f} className="flex items-start gap-2 text-white/85">
                <Check
                  className="w-4 h-4 text-wash shrink-0 mt-0.5"
                  strokeWidth={3}
                />
                <span>{f}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
