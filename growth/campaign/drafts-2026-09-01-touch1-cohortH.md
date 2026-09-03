# Cohort H, touch 1 drafts, sourced 2026-09-01 (second run of the day)

**Honest count: 20 vetted and send ready, not 25.** Seven more organisations
produced a name-verified published address but NO confirmed recurring
networking series, so they are parked as verify-first and were not drafted.

**NOT LOADED INTO GMAIL.** The Claude in Chrome extension was disconnected on
this run, as it was on the 5:44 AM run and on 2026-08-28. These twenty exist as
copy only. They join cohorts E, F and G in the unloaded queue.

## Method

Same method that produced cohort G, run against a fresh domain set:
1. Homepage link discovery across 124 uncontacted chamber domains, following
   only links matching young professionals, staff, team, leadership or about.
2. Address extraction from the discovered pages: `mailto:` hrefs, plain text
   addresses, and Cloudflare `data-cfemail` attributes decoded by XOR.
3. **Name consistency check, enforced in code, per the Waco rule from cohort G.**
   Every accepted address has a local part consistent with the person's own
   name: first plus surname, first.last, first initial plus surname, first plus
   surname initial, or a bare first name. Adjacency on a staff page proves
   nothing. The check rejected, among others, `inverness@citruscountychamber.com`
   sitting beside the words "Inverness Send" on the Citrus County page.
4. Generic aliases were dropped automatically: info, contact, hello, events,
   membership, marketing, admin, office, media and similar.
5. **Recurring event verification, run as a separate pass.** Each surviving
   organisation's events and calendar pages were fetched and scanned for a named
   recurring networking series. Ribbon cuttings were treated as noise, not as a
   series, because a ribbon cutting is not a room where attendees are meant to
   meet each other. Organisations with no named series were dropped to
   verify-first rather than drafted against a guess.

Yield: 124 domains probed, 21 dead or unreachable, 46 domains produced at least
one name-verified published address, 27 organisations reached the one-contact
selection stage, 20 cleared the recurring-event bar.

Nothing constructed. One contact per organisation. All filtered against the
tracker's contacted and do_not_contact lists.

## The 20, send ready

Scores are cadence / reachability / room fit, per the tracker's rubric.

| # | Person | Role | Organisation | Address | Recurring event | Score |
|---|---|---|---|---|---|---|
| 1 | Leah Case | Member Engagement Director | JAX Chamber, Jacksonville FL | leah.case@jaxchamber.com | Coffee and Commerce | 9 |
| 2 | Amber Heinlein | Senior Events and Program Manager | Sacramento Metro Chamber CA | aheinlein@metrochamber.org | Coffee Connect | 9 |
| 3 | Amanda Campbell | Strategic Events Manager | MetroHartford Alliance CT | acampbell@metrohartford.com | HYPE | 9 |
| 4 | Carla Hartwig | Events and Programs Specialist | Odessa Chamber TX | carlah@odessachamber.com | Business After Hours Mixers | 9 |
| 5 | Laura Wagner | Director of Programs and Events | St. Cloud Area Chamber MN | lwagner@stcloudareachamber.com | Business After Hours | 9 |
| 6 | Yebin Han | Partner Events and Experience Manager | Catawba County Chamber NC | yhan@catawbachamber.org | First Friday Morning Brew | 8 |
| 7 | Jessica Huffman | Talent Development and Events Director | Champaign County Chamber IL | jessicah@champaigncounty.org | Chamber First Friday Coffee | 8 |
| 8 | Jenny Tucker | Director of Programming | Grand Junction Area Chamber CO | jenny@gjchamber.org | Young Professionals Network | 8 |
| 9 | Katie Johnsen | Events Coordinator | Greater Reading Chamber Alliance PA | kjohnsen@greaterreading.org | New Member Mixer | 8 |
| 10 | Anne Thuma | VP, Programs and Development | Hampton Roads Chamber VA | athuma@hrchamber.com | Monster Mega Mixer | 8 |
| 11 | Mercedies Ramstead | Director of Events | Lynchburg Regional Business Alliance VA | mramstead@lynchburgregion.org | Young Professionals events | 8 |
| 12 | Jennifer Shattuck | VP of Membership | Norman Chamber OK | jennifer@normanchamber.com | Business After Hours | 8 |
| 13 | Hyrum Rappleye | Events and Marketing Coordinator | Ogden-Weber Chamber UT | hyrum@ogdenweberchamber.com | Business After Hours | 8 |
| 14 | Evan Gray | Director of Programs | Palm Springs Chamber CA | egray@pschamber.org | Chamber Mixers | 8 |
| 15 | Kim Calvert | EVP, Membership | Youngstown Warren Regional Chamber OH | kim@regionalchamber.com | Good Morning, Trumbull | 8 |
| 16 | Lyn Fusco | Director of Membership Experience | Roanoke Regional Chamber VA | lfusco@roanokechamber.org | Good Morning, VBR | 8 |
| 17 | Grace Ostaff | Programs and Events | Scottsdale Chamber AZ | gostaff@scottsdalechamber.com | Business and Breakfast | 8 |
| 18 | Jessica Holden | Business Engagement | Springfield Area Chamber MO | jessica@springfieldchamber.com | Good Morning, Springfield | 8 |
| 19 | Ditra Miller | Director of Member Engagement | Greater Winston-Salem Chamber NC | dmiller@winstonsalem.com | Wake Up Winston | 8 |
| 20 | Alejandra Gonzalez | Events Coordinator | Greater Boca Raton Chamber FL | agonzalez@bocachamber.com | LEADS Groups | 7 |

Note on row 20: Boca Raton scores cadence 3 and reachability 3, but its only
confirmed recurring series is its LEADS Groups, which run under 20 people. Room
fit is therefore 1 and the total is 7. It clears the bar but it is the weakest
row in the cohort, and the copy leads with the chamber's wider event calendar
rather than with a small referral group.

## Parked, verify first, NOT drafted

Each has a name-verified published address but no recurring networking series
was confirmed from its own calendar. Do not draft until someone confirms the
series by hand.

- Christina Gunter, Director Member Value and Engagement, ChamberRVA VA, christina.gunter@chamberrva.com
- Andy Wood, Chief Membership Officer, Greater Fort Myers Chamber FL, andy@fortmyers.org
- Abby Casarella, Event Coordinator, Frederick County Chamber MD, acasarella@frederickchamber.org
- Rachel Reed, Director of Finance and Membership, Greater Binghamton Chamber NY, rreed@greaterbinghamtonchamber.com
- Alexis Schroeder, Program Manager, Sheboygan County Chamber WI, alexis@sheboygan.org
- Stacy Cole, Member Engagement, Greater Wausau Chamber WI, scole@wausauchamber.com
- Taryn Hartle, Membership Director, Williamsport Lycoming Chamber PA, thartle@williamsport.org

---

# The copy

Template 1, personalized. No em dashes, no en dashes, no emoji. Signature is
"Scott Weiss" then "Founder, Intro Connect" on the next line.

---

## 1. Leah Case, JAX Chamber

**To:** leah.case@jaxchamber.com
**Subject:** what members remember after Coffee and Commerce

Hi Leah,

Your members join the JAX Chamber to meet people. Then Coffee and Commerce
ends, the name tags go in the bin, and most of those conversations never turn
into anything. When renewal time comes, "I met someone interesting once" is a
hard memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. Worth a look before the next
Coffee and Commerce? https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect

---

## 2. Amber Heinlein, Sacramento Metro Chamber

**To:** aheinlein@metrochamber.org
**Subject:** what members remember after Coffee Connect

Hi Amber,

Your members join the Metro Chamber to meet people. Then Coffee Connect ends,
the name tags go in the bin, and most of those conversations never turn into
anything. When renewal time comes, "I met someone interesting once" is a hard
memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. Worth a look before the next
Coffee Connect or Metro EDGE mixer? https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect

---

## 3. Amanda Campbell, MetroHartford Alliance

**To:** acampbell@metrohartford.com
**Subject:** what members remember after a HYPE event

Hi Amanda,

People come to HYPE to meet other young professionals in Hartford. Then the
event ends, the name tags go in the bin, and most of those conversations never
turn into anything. When renewal time comes, "I met someone interesting once"
is a hard memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. Worth a look before the next
HYPE night? https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect

---

## 4. Carla Hartwig, Odessa Chamber

**To:** carlah@odessachamber.com
**Subject:** what members remember after Business After Hours

Hi Carla,

Your members join the Odessa Chamber to meet people. Then Business After Hours
ends, the name tags go in the bin, and most of those conversations never turn
into anything. When renewal time comes, "I met someone interesting once" is a
hard memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. Worth a look before the next
Business After Hours or Coffee and Connections? https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect

---

## 5. Laura Wagner, St. Cloud Area Chamber

**To:** lwagner@stcloudareachamber.com
**Subject:** what members remember after Business After Hours

Hi Laura,

Your members join the St. Cloud Area Chamber to meet people. Then Business
After Hours ends, the name tags go in the bin, and most of those conversations
never turn into anything. When renewal time comes, "I met someone interesting
once" is a hard memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. Worth a look before the next
Business After Hours or NEXT gathering? https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect

---

## 6. Yebin Han, Catawba County Chamber

**To:** yhan@catawbachamber.org
**Subject:** what members remember after First Friday Morning Brew

Hi Yebin,

Your members join the Catawba County Chamber to meet people. Then First Friday
Morning Brew ends, the name tags go in the bin, and most of those conversations
never turn into anything. When renewal time comes, "I met someone interesting
once" is a hard memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. Worth a look before the next
Morning Brew or Hickory Young Professionals night? https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect

---

## 7. Jessica Huffman, Champaign County Chamber

**To:** jessicah@champaigncounty.org
**Subject:** what members remember after First Friday Coffee

Hi Jessica,

Your members join the Champaign County Chamber to meet people. Then First
Friday Coffee ends, the name tags go in the bin, and most of those
conversations never turn into anything. When renewal time comes, "I met someone
interesting once" is a hard memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. Worth a look before the next
First Friday Coffee or YPRG event? https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect

---

## 8. Jenny Tucker, Grand Junction Area Chamber

**To:** jenny@gjchamber.org
**Subject:** what members remember after a Young Professionals Network event

Hi Jenny,

People come to the Young Professionals Network to meet other people on the
Western Slope. Then the event ends, the name tags go in the bin, and most of
those conversations never turn into anything. When renewal time comes, "I met
someone interesting once" is a hard memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. Worth a look before the next
YPN event? https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect

---

## 9. Katie Johnsen, Greater Reading Chamber Alliance

**To:** kjohnsen@greaterreading.org
**Subject:** what members remember after the New Member Mixer

Hi Katie,

Your members join the Greater Reading Chamber Alliance to meet people. Then the
New Member Mixer ends, the name tags go in the bin, and most of those
conversations never turn into anything. When renewal time comes, "I met someone
interesting once" is a hard memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. A new member mixer is probably
the single best place to test it. https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect

---

## 10. Anne Thuma, Hampton Roads Chamber

**To:** athuma@hrchamber.com
**Subject:** what members remember after the Mega Mixer

Hi Anne,

Your members join the Hampton Roads Chamber to meet people. Then the Mega Mixer
ends, the name tags go in the bin, and most of those conversations never turn
into anything. When renewal time comes, "I met someone interesting once" is a
hard memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. Worth a look before the next
mixer or Young Professionals night? https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect

---

## 11. Mercedies Ramstead, Lynchburg Regional Business Alliance

**To:** mramstead@lynchburgregion.org
**Subject:** what members remember after a Young Professionals night

Hi Mercedies,

Your members join the Alliance to meet people. Then the Young Professionals
event ends, the name tags go in the bin, and most of those conversations never
turn into anything. When renewal time comes, "I met someone interesting once"
is a hard memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. Worth a look before your next
one? https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect

---

## 12. Jennifer Shattuck, Norman Chamber

**To:** jennifer@normanchamber.com
**Subject:** what members remember after Business After Hours

Hi Jennifer,

Your members join the Norman Chamber to meet people. Then Business After Hours
ends, the name tags go in the bin, and most of those conversations never turn
into anything. When renewal time comes, "I met someone interesting once" is a
hard memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. Worth a look before the next
Thursday After Hours? https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect

---

## 13. Hyrum Rappleye, Ogden-Weber Chamber

**To:** hyrum@ogdenweberchamber.com
**Subject:** what members remember after Business After Hours

Hi Hyrum,

Your members join the Ogden-Weber Chamber to meet people. Then Business After
Hours ends, the name tags go in the bin, and most of those conversations never
turn into anything. When renewal time comes, "I met someone interesting once"
is a hard memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. Worth a look before the next
Business After Hours? https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect

---

## 14. Evan Gray, Palm Springs Chamber

**To:** egray@pschamber.org
**Subject:** what members remember after a Chamber Mixer

Hi Evan,

Your members join the Palm Springs Chamber to meet people. Then the mixer ends,
the name tags go in the bin, and most of those conversations never turn into
anything. When renewal time comes, "I met someone interesting once" is a hard
memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. Worth a look before your next
mixer? https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect

---

## 15. Kim Calvert, Youngstown Warren Regional Chamber

**To:** kim@regionalchamber.com
**Subject:** what members remember after Good Morning, Trumbull

Hi Kim,

Your members join the Regional Chamber to meet people. Then Good Morning,
Trumbull ends, the name tags go in the bin, and most of those conversations
never turn into anything. When renewal time comes, "I met someone interesting
once" is a hard memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. Worth a look before the next
Good Morning or Mahoning Valley Young Professionals event?
https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect

---

## 16. Lyn Fusco, Roanoke Regional Chamber

**To:** lfusco@roanokechamber.org
**Subject:** what members remember after Good Morning, VBR

Hi Lyn,

Your members join the Roanoke Regional Chamber to meet people. Then Good
Morning, VBR ends, the name tags go in the bin, and most of those conversations
never turn into anything. When renewal time comes, "I met someone interesting
once" is a hard memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. Worth a look before the next
Good Morning, VBR? https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect

---

## 17. Grace Ostaff, Scottsdale Chamber

**To:** gostaff@scottsdalechamber.com
**Subject:** what members remember after Business and Breakfast

Hi Grace,

Your members join the Scottsdale Chamber to meet people. Then Business and
Breakfast ends, the name tags go in the bin, and most of those conversations
never turn into anything. When renewal time comes, "I met someone interesting
once" is a hard memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. Worth a look before the next
Business and Breakfast or Scottsdale Rising event? https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect

---

## 18. Jessica Holden, Springfield Area Chamber

**To:** jessica@springfieldchamber.com
**Subject:** what members remember after Good Morning, Springfield

Hi Jessica,

Your members join the Springfield Area Chamber to meet people. Then Good
Morning, Springfield ends, the name tags go in the bin, and most of those
conversations never turn into anything. When renewal time comes, "I met someone
interesting once" is a hard memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. Worth a look before the next
Good Morning, Springfield? https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect

---

## 19. Ditra Miller, Greater Winston-Salem Chamber

**To:** dmiller@winstonsalem.com
**Subject:** what members remember after Wake Up Winston

Hi Ditra,

Your members join the Greater Winston-Salem Chamber to meet people. Then Wake
Up Winston ends, the name tags go in the bin, and most of those conversations
never turn into anything. When renewal time comes, "I met someone interesting
once" is a hard memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. Worth a look before the next
Wake Up Winston? https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect

---

## 20. Alejandra Gonzalez, Greater Boca Raton Chamber

**To:** agonzalez@bocachamber.com
**Subject:** what members remember after a chamber event

Hi Alejandra,

Your members join the Boca Chamber to meet people. Then the event ends, the
name tags go in the bin, and most of those conversations never turn into
anything. When renewal time comes, "I met someone interesting once" is a hard
memory to bill against.

I built IntroConnect to turn every event into a private member directory
where attendees can find who they met, save contacts, message each other, and
keep those connections alive long after the event.

Guests never pay and never install anything. They join in the browser in about
a minute.

Your first event is free for up to 50 attendees. Worth a look before your next
one? https://intro-connect.com

Feel free to reach out if you have any questions,

Scott Weiss
Founder, Intro Connect
