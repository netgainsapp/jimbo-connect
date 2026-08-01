# Founding host offer (DECIDED 2026-08-01: Starter $199, Pro $699, first year)

The closer for warm replies. Zero paying customers means the first ten matter
more as proof than as revenue: testimonials, a case study, and named logos are
worth more than full price right now. The offer trades a discount for exactly
those things.

## The offer (decided)

**Founding Host: the Starter annual plan for $199 for the first year.**
Normally $390. Limited to the first 20 hosts, then it is gone for good.

**Founding Host Pro: the Pro annual plan for $699 for the first year.**
Normally $990. Same cap, same conditions. For the host who already runs more
than three events a year, or wants their own logo and color on everything.

What a founding host gets:
- Starter for a year at $199 (3 events, 250 attendees each, everything
  included, guests never pay), or Pro for a year at $699 (unlimited events,
  2,000 attendees each, plus their own branding).
- A direct line to the team while the product is young. Feature requests from
  founding hosts get read first.
- Their event featured on the site and blog if they want the attention, with
  their say over every word.

What we ask in return, stated plainly in the offer email:
- Honest feedback after their first event.
- A quotable sentence if, and only if, they are genuinely happy.

## Decision box (Scott)

- [x] Starter price: **$199** (Scott, 2026-08-01; the $290 proposal is superseded)
- [x] Cap of 20 stands.
- [x] Pro founding tier: **YES, $699** first year (Scott, 2026-08-01; the $790
      proposal is superseded)

### Stripe mechanics (do this at go-live)

Checkout already passes `allow_promotion_codes` (shipped 2026-08-01), so the
hosted page shows a code field the moment codes exist. Two coupons are needed,
because a fixed amount off cannot produce two different target prices:

| Plan | Normal | Founding | Coupon | Promotion code |
| --- | --- | --- | --- | --- |
| Starter annual | $390 | **$199** | $191 amount off | `FOUNDINGHOST` |
| Pro annual | $990 | **$699** | $291 amount off | `FOUNDINGPRO` |

Both: duration **once** (renewals bill at the full price), max redemptions 20.

⚠️ **Restrict each coupon to its own product** (`applies_to` in Stripe). An
unrestricted $291 off would let someone put the Pro code on the Starter plan
and pay $99. This is the one setting that turns a discount into a hole.

⚠️ The cap is **per code**: Stripe counts each one separately, so 20 and 20 is
up to 40 founding hosts, not 20 total. If 20 total is the real intent, split
the caps (e.g. 15 Starter / 5 Pro) or plan to close one code by hand.

Until the codes exist, every public surface says "reply to claim" rather than
naming a code, so nothing breaks in the meantime.

## The offer email (send on a warm reply, not cold)

**Subject:** founding host

Hi {first_name},

Glad this landed. Since you would be one of our first hosts, here is the
arrangement we are offering exactly 20 people and then never again:

The Starter annual plan for $199 for your first year, instead of $390. Three
events, 250 attendees each, every feature, and your guests never pay anything.
In return we want your honest feedback after your first event, and if you are
genuinely happy, a sentence we can quote.

If you run more than three events a year, or you want your own logo and color
on the event pages and guest emails, Pro is $699 for the first year instead of
$990, on the same terms.

You would also have a direct line to the team while we are young, which is
worth more than the discount.

If that works, the code FOUNDINGHOST at checkout takes care of it (FOUNDINGPRO
for Pro), and I can have {event_name} set up from your guest list the same day.

The Intro Connect team

## Rules

- Never lead cold outreach with the discount. The product is the pitch; the
  founding arrangement is the close.
- The cap is real. When 20 are claimed, the page and the code both end. A
  scarcity claim that quietly renews would be exactly the kind of copy this
  company cuts.
- Track founding hosts by name in the tracker; their feedback debt is the
  point of the discount.
