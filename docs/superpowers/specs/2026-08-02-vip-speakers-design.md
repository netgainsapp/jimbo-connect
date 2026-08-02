# VIPs and speakers — featured without being exposed

**Date:** 2026-08-02
**Owner:** Scott
**Author of record:** Claude (brainstormed with owner)
**Status:** DESIGN ONLY. Deliberately not implemented — see §7.

---

## 1. The problem

The model has exactly one kind of person: an attendee in a flat directory where
everyone is equal. That is right for a mixer and wrong the moment an event has a
speaker, a guest of honour, or anyone the host wants the room to notice.

Two things are missing, and they are not the same thing:

1. **Prominence.** A speaker is one card among two hundred identical cards,
   sorted like everyone else. The host has no way to say "this person matters".
2. **Protection.** Inside an event, everyone can message everyone. A named
   speaker who joins the guest list is volunteering their inbox to the whole
   room, and the host cannot offer them any other deal.

## 2. Verified current state (probed 2026-08-02)

| Fact | Where |
| --- | --- |
| Membership is a link row; no person-level roles exist | `event_attendees` |
| The only role distinction anywhere is event ownership | `events.created_by` |
| Sharing an event is sufficient for messaging, full stop | `core._users_connected`, [core.py:657](../../../backend/core.py) |
| A per-event, per-person visibility switch already exists | `discoverable`, [directory.py](../../../backend/directory.py) |
| `discoverable` gates browsing and messaging together, all or nothing | `directory.both_discoverable` |
| Event page order: announcements → agenda → survey → sponsors → attendees | [EventDirectory.jsx](../../../frontend/src/pages/EventDirectory.jsx) |
| Attendees render as a flat 4 column grid of identical cards | `EventDirectory.jsx:379` |
| The sponsors band is a separate section above the grid, 3 columns, larger tiles | `EventDirectory.jsx:339` |
| Agenda items already carry a speaker, as a plain string | `AgendaItem.speaker`, [agenda/schema.py:97](../../../backend/agenda/schema.py) |

Two of these did most of the design work. The `discoverable` flag proves the
per-event per-person switch is the right shape and the right home. The sponsors
band proves the featured-section layout already works on that page.

## 3. Decisions

| # | Decision | Rationale |
| --- | --- | --- |
| D1 | The host sets VIP status, per event, per person | The host knows who the draw is; the platform does not |
| D2 | VIP carries a contactability switch, not just a badge | "Reach" and "showcase" are both real and vary by event, so the host picks per person |
| D3 | The VIP can veto contactability; the host cannot override the veto | An organizer must not be able to volunteer someone else's inbox |
| D4 | The veto is a separate field, not a shared one | Two owners writing one field means one silently clobbers the other |
| D5 | Default is contactable | Optimises for the common case (a speaker who wants to meet the room) and still works when the VIP never logs in |
| D6 | VIP status does not connect to `AgendaItem.speaker` | Matching free text ("Jane Doe") to an account ("Jane D.", different email) is its own problem; plenty of agenda speakers never sign up. Leave a seam, do not build the bridge |
| D7 | Protection is directional and messaging only | Symmetric protection would mute the VIP and hide her profile, which defeats the feature |
| D8 | VIPs appear in the band **and** stay in the main grid | Otherwise they vanish from search, filtering, and the list people expect them in |

## 4. Data model

Three booleans on the `event_attendees` link row, alongside `discoverable`. No
new collection, no change to `users`.

| Field | Written by | Default | Meaning |
| --- | --- | --- | --- |
| `vip` | Host | `false` | Featured and marked at this event |
| `vip_contactable` | Host | `true` | "The room may message this person" |
| `vip_contact_optout` | The VIP | `false` | The VIP's veto |

Effective reachability:

```
reachable = NOT vip  OR  (vip_contactable AND NOT vip_contact_optout)
```

A missing field reads as its default, so every row that exists today is a
non-VIP, reachable exactly as it is now. Nothing changes for anyone until a host
flips a switch.

The flags live on the link row for the same reason `discoverable` does: being a
VIP at your client's conference and being a face in the crowd at a neighbourhood
mixer are different facts about the same person, and should not share a switch.

## 5. The messaging gate

This is the part that is easy to get wrong.

`core._users_connected(a, b)` is **symmetric** today and gates two different
things: whether a message may be sent, and whether one user may read another's
profile. Dropping VIP protection into it as written produces two bugs at once —
the VIP cannot message attendees either, and nobody can open her profile, which
is the entire point of featuring her.

Required behaviour:

| Case | Result |
| --- | --- |
| Attendee → protected VIP, new thread | **Blocked** |
| Protected VIP → attendee | **Allowed.** She reaches out; that is the good outcome |
| Anyone → protected VIP's profile | **Allowed, always.** Visible but not reachable is the feature |
| Either direction, thread already exists | **Allowed.** Flipping a flag must not cut a live conversation |
| Cross-event directory | **Unaffected.** `discoverable` still governs it; VIP is event scoped |

So the profile-read path must keep using the existing symmetric check, and only
the send path consults VIP protection, in one direction. If this ends up
implemented as a single shared predicate, it is wrong.

## 6. Interface

**Event page.** A Speakers band above the attendee grid, built on the sponsors
band's anatomy: its own section, fewer columns, larger cards. It renders only
when the event has at least one VIP, so an ordinary mixer looks exactly as it
does today.

**The card.** A protected VIP shows no message button and a short line saying
messaging is off for this person, rather than a button that fails when pressed.

**Host control.** On the attendee row the host already manages: a VIP toggle,
and when it is on, a contactable toggle. When a VIP has vetoed, the host's
control reads as overridden rather than appearing to still be in effect.

**VIP control.** The veto sits with the person's own per-event settings, next to
the existing directory opt-in, which is where someone already goes to answer
"who can see and reach me at this event".

## 7. Not building this yet

Nobody has asked for it. No host is blocked, and no deal is waiting on it. The
value of this document is that the seam is designed before someone asks under
time pressure — not that the code exists.

Build it when a real host needs it. The design should survive the wait, because
it adds three defaulted booleans to an existing row and one directional check to
an existing gate.

## 8. Explicitly out of scope

Both of these were raised alongside VIPs and neither is solved by this flag.
Bundling them is how one field becomes a roles system.

- **Guest hosts** — people who need permission to post announcements and see the
  guest list. That is an access control change, and much bigger: roles today are
  binary, own or attend.
- **Non attending speakers** — presence without an account. Needs a person who
  is not a user, which nothing in the model supports.

## 9. Testing notes for whoever implements this

The behaviours worth pinning, because they are the ones a naive implementation
gets wrong:

- A protected VIP can still send a message to an attendee.
- An attendee cannot open a new thread with a protected VIP.
- An attendee can still read a protected VIP's profile.
- An existing thread keeps working after protection is switched on.
- A host turning contactability on does not defeat a VIP's veto.
- Rows with none of the new fields behave exactly as they do today.
- Marking someone a VIP at event A does not mark them at event B.
- The cross-event directory is unchanged by any of these flags.
