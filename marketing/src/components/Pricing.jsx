import { ArrowRight, Check } from "lucide-react";

const REGISTER = "https://jimbo.frontrangedev.co/register";

const TIERS = [
  {
    name: "Free",
    price: "$0",
    period: "to start",
    blurb: "Try it with your next event.",
    cta: "Start free",
    href: REGISTER,
    features: [
      "1 active event",
      "Up to 50 attendees",
      "Searchable directory + profiles",
      "Save contacts and private notes",
      "In-app messaging",
      "Directory live for 30 days",
    ],
  },
  {
    name: "Starter",
    price: "$39",
    period: "/month",
    annual: "$390 billed yearly",
    blurb: "For hosts who outgrew the free plan and want a permanent directory.",
    cta: "Choose Starter",
    href: REGISTER,
    features: [
      "Up to 3 active events",
      "Up to 250 attendees per event",
      "Permanent directory, never expires",
      "Attendee to attendee messaging",
      "Host announcements",
      "CSV export",
      "Remove Intro Connect branding",
    ],
  },
  {
    name: "Pro",
    price: "$99",
    period: "/month",
    annual: "$990 billed yearly",
    blurb: "For hosts who want their events to build a lasting network.",
    cta: "Choose Pro",
    href: REGISTER,
    highlighted: true,
    features: [
      "Everything in Starter",
      "Unlimited events",
      "Up to 2,000 attendees per event",
      "Cross-event network: all your events, one directory",
      "Your own custom domain",
      "Post-event surveys with analytics",
      "Sponsor tiles and calendar invites",
      "CSV import from any tool",
      "Priority support",
    ],
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "let's talk",
    blurb: "For teams running events across multiple hosts.",
    cta: "Schedule a call",
    href: "mailto:hello@frontrangedev.co?subject=Intro%20Connect%20Enterprise",
    features: [
      "Multiple host accounts",
      "SSO via Google or Microsoft",
      "White-label",
      "Custom integrations and CRMs",
      "Dedicated support",
      "Custom contracts and SLAs",
    ],
  },
];

export default function Pricing() {
  return (
    <section id="pricing" className="py-24 sm:py-32">
      <div className="container-prose">
        <div className="max-w-3xl">
          <div className="eyebrow">Pricing</div>
          <h2 className="mt-4 text-4xl sm:text-5xl font-extrabold text-ink leading-[1.05] tracking-tight">
            Free for guests.{" "}
            <span className="text-primary">Free to start for hosts.</span>
          </h2>
          <p className="mt-4 text-lg text-stone leading-relaxed">
            Attendees never pay, ever. Hosts start free and pay only when they
            need more events, bigger rooms, or their own brand on it. No ads, no
            tracking, no data sale. It's written into the terms.
          </p>
        </div>

        <div className="mt-16 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 items-stretch">
          {TIERS.map((tier) => (
            <PricingCard key={tier.name} tier={tier} />
          ))}
        </div>

        <div className="mt-6 rounded-card border border-stone/20 bg-cream/60 px-6 py-5 flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-6">
          <div className="flex-1">
            <div className="font-extrabold text-ink">
              Only host a few times a year?
            </div>
            <p className="text-[14px] text-stone mt-0.5">
              Skip the subscription. Pay $149 per event for the full Pro feature
              set, with the directory live for 12 months.
            </p>
          </div>
          <a
            href={REGISTER}
            target="_blank"
            rel="noopener"
            className="inline-flex items-center gap-1.5 text-[14px] font-bold text-primary hover:underline shrink-0"
          >
            Get one event for $149 <ArrowRight className="w-3.5 h-3.5" />
          </a>
        </div>

        <p className="mt-8 text-center text-xs text-stone tracking-wide">
          Free plan, no credit card. Upgrade when you're ready.
        </p>
      </div>
    </section>
  );
}

function PricingCard({ tier }) {
  const hot = tier.highlighted;
  const cardClass = hot
    ? "bg-ink text-white shadow-lift"
    : "bg-white border border-stone/15";
  const checkClass = hot ? "text-wash" : "text-primary";
  const blurbClass = hot ? "text-white/70" : "text-stone";
  const periodClass = hot ? "text-white/70" : "text-stone";
  const featureClass = hot ? "text-white/85" : "text-stone";

  return (
    <div
      className={`relative flex flex-col rounded-card p-7 ${cardClass}`}
    >
      {hot && (
        <span className="absolute top-0 right-6 -translate-y-1/2 rounded-pill bg-primary text-white text-[10px] uppercase tracking-[0.18em] font-extrabold px-3 py-1">
          Most popular
        </span>
      )}

      <h3 className="text-2xl font-extrabold tracking-tight">{tier.name}</h3>
      <p className={`mt-1 text-[14px] ${blurbClass}`}>{tier.blurb}</p>

      <div className="mt-5 flex items-baseline gap-1">
        <span className="text-4xl font-extrabold tracking-tight">
          {tier.price}
        </span>
        {tier.period && (
          <span className={`text-sm font-semibold ${periodClass}`}>
            {tier.period}
          </span>
        )}
      </div>
      <div className={`mt-1 text-[11px] font-semibold ${periodClass} h-4`}>
        {tier.annual || ""}
      </div>

      <a
        href={tier.href}
        target={tier.href.startsWith("http") ? "_blank" : undefined}
        rel="noopener"
        className={`mt-5 inline-flex items-center justify-center w-full gap-2 px-5 py-2.5 rounded-pill font-bold transition ${
          hot
            ? "bg-white text-ink hover:bg-cream"
            : "border border-stone/30 text-ink hover:border-primary hover:text-primary"
        }`}
      >
        {tier.cta} <ArrowRight className="w-4 h-4" />
      </a>

      <ul className="mt-6 space-y-2 text-[13px]">
        {tier.features.map((f) => (
          <li key={f} className={`flex items-start gap-2 ${featureClass}`}>
            <Check
              className={`w-3.5 h-3.5 shrink-0 mt-0.5 ${checkClass}`}
              strokeWidth={3}
            />
            <span>{f}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
