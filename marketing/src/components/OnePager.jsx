import { useState } from "react";
import { ArrowRight, CheckCircle2, FileText } from "lucide-react";

const API_BASE =
  import.meta.env.VITE_API_URL || "https://jimbo-connect-api-rdkp.onrender.com";

export default function OnePager() {
  const [email, setEmail] = useState("");
  const [hp, setHp] = useState("");
  const [status, setStatus] = useState("idle"); // idle | sending | sent | error
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    if (status === "sending") return;
    setStatus("sending");
    setError("");
    try {
      const r = await fetch(`${API_BASE}/api/one-pager`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, website: hp }),
      });
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(
          body.detail || "Something went wrong. Please try again in a minute."
        );
      }
      setStatus("sent");
    } catch (err) {
      setStatus("error");
      setError(err.message);
    }
  }

  return (
    <section id="one-pager" className="py-20 sm:py-24 bg-cream/60">
      <div className="container-prose">
        <div className="relative overflow-hidden rounded-[28px] bg-ink text-white shadow-lift">
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background:
                "radial-gradient(55% 70% at 85% 10%, rgba(37,99,235,0.35) 0%, transparent 60%)",
            }}
          />
          <div className="relative grid grid-cols-1 lg:grid-cols-12 gap-10 items-center p-8 sm:p-12 lg:p-14">
            <div className="lg:col-span-7">
              <div className="inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.22em] font-extrabold text-[#7AA7F7]">
                <FileText className="w-3.5 h-3.5" /> The one pager
              </div>
              <h2 className="mt-4 text-4xl sm:text-5xl font-extrabold leading-[1.05] tracking-tight">
                The whole pitch, on one page.
              </h2>
              <p className="mt-5 text-lg text-white/80 leading-relaxed max-w-xl">
                Built to forward to a board, a boss, or a co host. We will email
                it to you, along with the founding host special: your first year
                of Starter for $199 instead of $390, for the first 20 hosts.
              </p>

              {status === "sent" ? (
                <div
                  className="mt-8 flex items-start gap-3 bg-white/10 border border-white/15 rounded-card p-5 max-w-xl"
                  role="status"
                >
                  <CheckCircle2 className="w-6 h-6 text-[#7AA7F7] shrink-0 mt-0.5" />
                  <div>
                    <div className="font-bold">Sent. Check your inbox.</div>
                    <div className="text-sm text-white/70 mt-1">
                      The founding host special is inside.{" "}
                      <a
                        href="/intro-connect-one-pager.pdf"
                        target="_blank"
                        rel="noopener"
                        className="underline text-white hover:text-[#7AA7F7] transition"
                      >
                        Or open the one pager directly
                      </a>
                      .
                    </div>
                  </div>
                </div>
              ) : (
                <form
                  onSubmit={submit}
                  className="mt-8 max-w-xl"
                  aria-label="Get the one pager by email"
                >
                  <div className="flex flex-col sm:flex-row gap-3">
                    <label htmlFor="one-pager-email" className="sr-only">
                      Work email
                    </label>
                    <input
                      id="one-pager-email"
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@yourorganization.com"
                      className="flex-1 rounded-pill bg-white text-ink placeholder-stone px-6 py-3 font-semibold outline-none focus:ring-2 focus:ring-[#7AA7F7]"
                    />
                    {/* Honeypot: humans never see it, bots fill it. */}
                    <input
                      type="text"
                      value={hp}
                      onChange={(e) => setHp(e.target.value)}
                      name="website"
                      tabIndex={-1}
                      autoComplete="off"
                      aria-hidden="true"
                      className="absolute -left-[9999px] w-px h-px opacity-0"
                    />
                    <button
                      type="submit"
                      disabled={status === "sending"}
                      className="inline-flex items-center justify-center gap-2 px-7 py-3 rounded-pill bg-primary text-white font-bold hover:bg-[#1D4ED8] transition shadow-lift disabled:opacity-60"
                    >
                      {status === "sending" ? "Sending" : "Email me the one pager"}
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                  <div aria-live="polite">
                    {status === "error" && (
                      <p className="mt-3 text-sm text-red-300">{error}</p>
                    )}
                  </div>
                  <p className="mt-3 text-xs text-white/60 tracking-wide">
                    One email with the PDF, from a real address you can reply
                    to. No spam.
                  </p>
                </form>
              )}
            </div>

            <div className="lg:col-span-5">
              <a
                href="/intro-connect-one-pager.pdf"
                target="_blank"
                rel="noopener"
                className="block max-w-[340px] mx-auto rotate-2 hover:rotate-0 transition-transform duration-300"
                aria-label="Open the one pager PDF"
              >
                <img
                  src="/images/one-pager-preview.png"
                  alt="The Intro Connect one pager"
                  width="1632"
                  height="2112"
                  loading="lazy"
                  className="w-full h-auto rounded-xl border border-white/15 shadow-lift"
                />
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
