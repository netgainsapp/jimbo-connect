import { useEffect, useState } from "react";
import { Check } from "lucide-react";
import { billingApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";

const PLANS = [
  {
    id: "free",
    name: "Free",
    price: 0,
    tagline: "Try hosting with a single event.",
    features: [
      "Host 1 event",
      "Unlimited attendees per event",
      "Attendee directory and messaging",
      "Email invites with join links",
    ],
  },
  {
    id: "starter",
    name: "Starter",
    price: 39,
    tagline: "For hosts who run events all year.",
    features: [
      "Host up to 10 events",
      "Unlimited attendees per event",
      "Attendee directory and messaging",
      "Email invites with join links",
    ],
  },
  {
    id: "pro",
    name: "Pro",
    price: 99,
    tagline: "For organizations with a full calendar.",
    recommended: true,
    features: [
      "Host unlimited events",
      "Your logo and color on event pages and guest emails",
      "Unlimited attendees per event",
      "Attendee directory and messaging",
      "Email invites with join links",
    ],
  },
];

// Which paid plans count as an upgrade from the current one.
const UPGRADES_FROM = { free: ["starter", "pro"], starter: ["pro"], pro: [] };

export default function Upgrade() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyPlan, setBusyPlan] = useState(null);
  const toast = useToast();

  useEffect(() => {
    billingApi
      .status()
      .then(setStatus)
      .catch(() => setStatus(null))
      .finally(() => setLoading(false));
  }, []);

  const currentPlan = status?.plan || "free";
  const upgradable = UPGRADES_FROM[currentPlan] || [];

  const startCheckout = async (plan) => {
    setBusyPlan(plan);
    try {
      const { url } = await billingApi.checkout(plan);
      window.location.href = url;
    } catch (err) {
      toast.show(
        err.status === 503
          ? "Billing is not switched on yet. Check back soon."
          : err.message,
        "error"
      );
      setBusyPlan(null);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold text-text-primary">Plans</h1>
        <p className="text-sm text-text-secondary mt-1">
          Every plan includes the full attendee experience. Paid plans lift how
          many events you can host.
        </p>
      </div>

      {loading ? (
        <div className="text-text-muted text-center">Loading…</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-start">
          {PLANS.map((p) => {
            const isCurrent = p.id === currentPlan;
            const canUpgrade = upgradable.includes(p.id);
            return (
              <div
                key={p.id}
                className={`card p-6 flex flex-col gap-4 ${
                  p.recommended ? "border-primary sm:-mt-2 sm:pb-8" : ""
                }`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-bold text-text-primary">
                      {p.name}
                    </div>
                    {p.recommended && (
                      <span className="pill bg-primary/10 text-primary">
                        Recommended
                      </span>
                    )}
                    {isCurrent && !p.recommended && (
                      <span className="pill">Current plan</span>
                    )}
                  </div>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="text-3xl font-bold text-text-primary tabular-nums">
                      ${p.price}
                    </span>
                    <span className="text-sm text-text-muted">per month</span>
                  </div>
                  <p className="text-sm text-text-secondary mt-1">{p.tagline}</p>
                </div>

                <ul className="flex flex-col gap-2">
                  {p.features.map((f) => (
                    <li
                      key={f}
                      className="flex items-start gap-2 text-sm text-text-secondary"
                    >
                      <Check className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                </ul>

                <div className="mt-auto pt-2">
                  {isCurrent ? (
                    <button className="btn-outline w-full" disabled>
                      {p.recommended ? "Your current plan" : "Current plan"}
                    </button>
                  ) : canUpgrade ? (
                    <button
                      onClick={() => startCheckout(p.id)}
                      className={`${p.recommended ? "btn-primary" : "btn-outline"} w-full`}
                      disabled={busyPlan !== null}
                    >
                      {busyPlan === p.id
                        ? "Opening checkout…"
                        : `Upgrade to ${p.name}`}
                    </button>
                  ) : (
                    <button className="btn-ghost w-full" disabled>
                      Included in your plan
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <p className="text-xs text-text-muted text-center mt-8">
        Payments are handled securely by Stripe. You can cancel anytime and your
        plan stays active through the period you paid for.
      </p>
    </div>
  );
}
