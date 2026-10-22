# Event leads: what Scott does

This is the order to switch the event lead engine on. Do the steps one at a
time and stop at any step that does not match what it says you will see. The
reference for how everything works is the Event Leads section of
`JIMBO_CONNECT_DOCS.md`, and the fixes for common problems are in
`docs/RUNBOOK.md`.

## Steps

1. Open the Render dashboard, pick the `jimbo-connect-api` service, and set
   three environment variables: `EVENT_LEADS_INGEST_KEY` (make up a long random
   value), `SIGNAL_SCOUT_URL` (the base address of Signal Scout) and
   `SIGNAL_SCOUT_API_KEY` (Signal Scout's `CRON_SECRET`). If you want Linked
   Helper to report results by itself, also set `LINKED_HELPER_WEBHOOK_SECRET`
   to another long random value. Save and wait for the service to redeploy.
   Then put the same ingest key in the weekly sourcing job's settings on your PC.

2. Install Linked Helper on your PC, choose the Standard plan (about $15 a
   month, it includes CSV export and outgoing webhooks), and log in with your
   LinkedIn account.

3. Create the Linked Helper campaign. Use these steps in this order: visit the
   profile, send an invite with a note, send a message after the invite is
   accepted, stop the campaign for that person if they reply. Set the daily
   caps to 20 invites and 20 messages. In the Event Leads page, use Download
   queue in the LinkedIn queue card to get the file of approved leads, and load
   it into the campaign. To get results back, point the campaign's outgoing
   webhook at
   `{API_PUBLIC_URL}/api/admin/event-leads/linkedin-webhook?secret=...`
   where `{API_PUBLIC_URL}` is `https://jimbo-connect-api-rdkp.onrender.com` and
   the secret is your `LINKED_HELPER_WEBHOOK_SECRET`. If you would rather not
   use the webhook, plan to export the campaign results from Linked Helper and
   use Upload results in the same card.

4. Run the weekly sourcing job once by hand while you watch. Open
   `/admin/event-leads` and check that rows appear and that the run count in the
   KPI strip went up. If the page is empty, check that the key in the job matches
   `EVENT_LEADS_INGEST_KEY` exactly.

5. Approve one A-tier lead that has an email. Open its drawer and confirm three
   things: the claim link is shown, the event was created with the right name and
   date, and the Signal Scout outcome shows no red "Outreach failed" line. If
   there is an error, follow "Approve shows an outreach error" in the runbook
   before approving anything else.

6. The next morning, after the 07:00 UTC tick, open the same lead's drawer and
   read the Funnel section. It should show when the email was sent and, if the
   host looked, when it was opened. Also open the Actions tab on GitHub, find the
   latest run of "Event leads status poll" and check that it is green and its
   reply has an empty `errors` list.

7. When that host claims the event, confirm it shows under their account (the
   lead's funnel gets a claimed time) and that the attendee mail they send goes
   out in their name, with their photo and name at the top and Intro Connect
   only in the footer.

8. Only after a few batches reviewed by hand, consider setting the auto approve
   minimum score in the Auto approve card on the page. Start high. Leave it blank
   to keep auto approve off.

## What never happens automatically

- Intro Connect itself never sends mail to a prospect host. Signal Scout does
  that, and only after a lead is approved.
- No LinkedIn action is ever taken for an attendee. A guest sees a button and
  sends their own connection.
- Auto approve ships off. Nothing is approved until you approve it or you set a
  minimum score.
- An imported guest gets no mail from the platform beyond the host's invite, the
  two reminders (they go out no later than the day before the event) and the one email
  that tells them a message is waiting.
