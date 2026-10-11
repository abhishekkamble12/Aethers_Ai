# Saans — Winning Frontend Design Doc (v2)

Oct 11, 2026 · @SASA · v2 checked against the deployed API and this repo at 09:30 IST

## 0. Read this first

**Time.** Submission is assumed at 16:00 IST today (from `impleme_work.md`), which leaves about six hours.
Sections 1 to 9 describe the full design. Section 10 gives the six-hour build order and lists what is cut. If the
two disagree, follow section 10.

**Every backend fact in this doc was checked against the live stack** (`https://367bcz1ry5.execute-api.us-east-1.amazonaws.com/Prod`).
Where v1 assumed something the API does not do, v2 says so and gives the fix.

### What changed from v1

| v1 said | Reality | v2 fix |
| --- | --- | --- |
| The approve screen shows a plan summary and a countdown | The only public approval call is `POST /approve/{shortId}`. No public call returns the plan or the expiry for a link | Approve inside `/today`, which reads `/decisions` through the admin proxy. The standalone `/approve` page is cut |
| "Send for approval" in the demo | No HTTP endpoint starts a run. Only the Trigger Lambda does | Add one backend endpoint, `POST /runs` (admin key), before building `/today`. See section 2 |
| Separate "link used" and "link expired" screens | The API returns one `410 approval_link_invalid` for unknown, used and expired links, on purpose | One honest state for all three |
| One Approve button and "Not now" | Actions are `APPROVE_PLAN_A`, `APPROVE_PLAN_B` and `REJECT` | Approve and Reject buttons. Doing nothing leads to escalation |
| Drag the slider from II to IV to show the timetable move | For the demo school, Stages I and II give the same plan, and so do III and IV. The plan only changes between II and III | The demo moment is II to III. The haze carries the I/II and III/IV steps |
| Locked periods show a lock icon in the demo | The demo timetable has no locked periods | Keep the lock state in the component; do not promise it in the demo |
| Provenance chip "Bedrock Nova Lite" | This AWS account is on the Free plan, so Bedrock cannot be called. Every notice is the labelled static template | Chip shows the real `model_id` or `template_id` from the audit row |
| Not mentioned | The backend now records notice provenance and modelled exposure averted, and `/verify` can check a pasted notice | These are now the closing beat of the demo (sections 6E and 10) |
| Saffron Approve button, teal text, Stage I chip | White on saffron is 2.6:1, teal text on paper is 4.3:1 and the Stage I chip is 1.95:1. All three fail WCAG | Contrast rules in section 4 |
| Tailwind config, Zod, visx, new `lib/verify.ts` | Tailwind v4 (CSS `@theme`, no config file), Recharts, Framer Motion, TanStack Query and `lib/crypto.ts` are already installed, and `lib/crypto.ts` is tested against the real chain | Use what is installed |
| No hosting plan | Judges need a URL | Deploy the skeleton in the first hour (section 10) |
| CORS risk, test early | Checked: the API returns `Access-Control-Allow-Origin: *` on all routes, including preflight | Call public endpoints straight from the browser |

## 1. Thesis: make the invisible backend visible in 90 seconds

A judge should be able to drag a slider, watch a school day re-plan itself, approve it as the principal, verify the
hash chain in their own browser, and then paste a WhatsApp notice and see it proven genuine, all in 90 seconds.
The backend already does all of this. The frontend's only job is to make it **visible, live and memorable**.

### The five invisible things to make tangible

1. **The re-plan.** Drag a GRAP stage slider and watch periods move or turn into indoor sessions. PE minutes kept
   and modelled exposure cut update live.
2. **The reasoning.** Click any affected period to see its `decision_trace`: the order, the nominal and
   pessimistic forecast, every candidate slot with why it was rejected, and the room chosen.
3. **The human in the loop.** A real run waits for a real click. If nobody answers, the vice-principal is asked;
   if still nobody answers, the run fails safe and nothing is sent.
4. **The proof.** The SHA-256 chain is shown as linked blocks that the browser re-verifies. A tamper button breaks it.
5. **The AI's words are on the record.** A parent pastes the notice they received. The browser hashes it and finds
   the exact row that recorded it, and which model or template wrote it. Changing one character breaks the match.
   No other entry will have this. It is the closing beat.

### How judges score a frontend

| Criterion | What judges look for | Saans answer |
| --- | --- | --- |
| Visual identity | Memorable in 2 seconds, not a template | Civic-editorial look with a haze tied to the GRAP stage |
| Clarity | Understandable without a pitch | Hero is the live slider: "Bad air. Better day." |
| Real, not mocked | Wired to a live backend | Slider calls `POST /rehearse`; status chip reads `/health`; a live run is approved on stage |
| Completeness | Edge states, mobile, errors | Fail-safe, invalid link, run ended, offline snapshot |
| Craft | Motion, type, microcopy | Shared-layout timetable moves, Devanagari set properly, plain voice |
| Trust | Honest claims | "Modelled, not measured" and "static template" shown where they apply |

### Two hard rules

- **Do not copy CampusEvac's neo-brutalism.** Saans has its own identity (section 3).
- **No screen runs on mock data.** Delete `app/api/{health,notifications,rehearse,schedule,verify}` and
  `lib/mockData.ts` in the first hour. The only offline data is a labelled snapshot of real responses (section 7).

## 2. The backend contract (verified)

### What each endpoint really gives you

| Endpoint | Access | What it returns that the UI uses |
| --- | --- | --- |
| `POST /rehearse` body `{"stage":"III","forecast_source":"replay","date":"YYYY-MM-DD"}` | Public, no side effects | `classified_periods`: all 48 cells (6 classes × 8 periods) with `start`, `end`, `subject`, `teacher_code`, `venue`, `is_outdoor`, `label`, `reason`, `pm25`. `plan_a`: moves (`from_period`, `to_period`, `exposure_before`, `exposure_after`, `reason`). `plan_b`: indoor sessions with `venue_choice` (chosen room, alternatives, modelled indoor PM2.5, `why`). `decision_trace`: per affected period, with nominal and pessimistic forecast, `candidates[]` with `verdict` and `reasons`, and `outcome`. Plus `pe_minutes`, `exposure_reduction_pct`, `exposure_averted_modelled` and `forecast` |
| `GET /forecast?hours=48` / `?source=replay` | Public | Hourly PM2.5, thresholds (advisory 90, restricted 120, and stricter limits for sensitive classes), `first_crossing`, `source`, `label`, `cache` |
| `GET /health` | Public | `status`, declared stage, forecast source, `bedrock.usable` (currently `false`), audit `head_hash` and `chain_valid` |
| `GET /decisions?tenant=demo&date=…` | Admin key | The decision and plan, plus `approval: {role, expires_at (epoch seconds), approve_url, actions}` while one is pending |
| `POST /approve/{shortId}` body `{"action": …}` | Single-use link | `200` approved. `400 invalid_action`. `410 approval_link_invalid` (unknown, used or expired; deliberately not told apart). `409` the run has already ended. `5xx` is transient and the link stays usable, so retry |
| `GET /watch` | Admin key | Contingency drafts for the next two school days |
| `GET /receipts/{id}` | Public | `blocks[]` with `payloadJson` and the server's verdict. `PLAN_GENERATED` carries `exposure_averted_modelled`. `NOTICES_DRAFTED` carries `notices[]` with `model_id`, `template_id`, `prompt_sha256`, `text_sha256`, and `facts_given_to_writer` |
| `GET /verify/{id}` | Public | The standalone verifier page, including "Check a notice you received". Its script is the reference implementation |

### Demo-school numbers (replay forecast, from `/rehearse`)

| Stage | Moved to a cleaner slot | Replaced indoors | PE kept | Exposure cut (modelled) | Exposure averted (modelled) |
| --- | :---: | :---: | :---: | :---: | :---: |
| I or II | 1 (7A PE, P2 → P8) | 5 | 240 of 240 | 95% | 53,180 µg/m³·min |
| III or IV | 0 | 6 | 240 of 240 | 100% | 51,380 µg/m³·min |

Show **exposure cut %** next to the slider, because it rises with the stage and reads correctly. Show **exposure
averted** on the receipt and in the trace summary. Next to the slider it would look wrong, because it falls slightly
from II to III: indoor air still carries some PM2.5, while 7A's moved slot at Stage II was cleaner outdoors.

### Backend work the frontend depends on (do it first)

1. **`POST /runs` (admin key), about 1 hour with tests.** It starts a run for the demo school with the replay
   forecast and returns the decision ID and receipt ID. Runs are refused as duplicates per school, date and session,
   so pick the next date that has no decision yet. Without this endpoint, the "a person decides" moment needs
   someone at a CLI.
2. **Run one fresh decision before the demo.** The rows in the chain today were written before provenance shipped,
   so they have no `model_id` or `text_sha256`. Run one decision and approve it, then run another and leave it
   unanswered, which gives a `FAILSAFE_TIMEOUT_NO_BROADCAST` receipt. Keep both receipt IDs.
3. **Cut first if short of time:** a public `GET /approve/{shortId}` (counts-only summary plus `expires_at`), which
   would bring back the standalone mobile approve page.

**Approval timing.** The principal has 60 seconds, then the vice-principal has 60 seconds, then the run fails safe.
A live approval on stage must happen within 60 seconds of pressing Start. Show escalation and fail-safe through the
prepared fail-safe receipt; never wait two minutes live.

## 3. Aesthetic direction: "Civic editorial meets air instrument"

A government circular redesigned by a good newspaper, with a live sensor reading running through it. It fits the
story (official orders, trust, two languages, breath) and looks unlike any neo-brutalist, glassmorphic or
purple-gradient entry.

- **Editorial serif headlines**, a warm newsprint background, hairline rules and ruled tables.
- **Instrument details:** mono numerals, gauge ticks, small-caps labels.
- **Bilingual parity:** Hindi is a first-class voice, never a footnote.
- **Restraint:** flat colour, hairlines, almost no shadows. Motion carries the energy.

### Three signature devices

| Device | What it is | Where |
| --- | --- | --- |
| **The haze** | Grain plus gradient whose density and tint follow the stage. Clear at I, thick amber-grey at IV | Landing, forecast strip |
| **The breath ring** | A pulsing circle, 4 s in and 4 s out | Loader, approval countdown, logo mark |
| **The ink stamp** | APPROVED, VERIFIED, CHAIN BROKEN, FAIL-SAFE, GENUINE | Approval, receipt, notice check |

### The haze, done safely

- One fixed `pointer-events: none` layer: an SVG `feTurbulence` noise plus a CSS gradient, driven by one variable,
  `--haze` (I = 0.1, II = 0.35, III = 0.7, IV = 0.95), eased over 600 ms.
- **The haze sits behind content, never over text.** Cards and the timetable use an opaque `--paper` surface above
  the layer, so text contrast does not change with the stage. The haze shows in the margins, the hero band and
  between cards. Indoor cells stay crisp because they are part of the content.
- Under `prefers-reduced-motion`, set the level with no transition.

## 4. Design tokens

Define tokens once, in `app/globals.css` under Tailwind v4's `@theme`; there is no `tailwind.config` file. No
component hardcodes a colour, size or duration. **Every colour has one job.**

### Colour roles

| Token | Hex | Job |
| --- | --- | --- |
| `--paper` | #F6F1E7 | Page background |
| `--paper-2` | #EDE6D6 | Cards, table stripes |
| `--ink` | #14181F | Text, rules |
| `--ink-soft` | #4A5160 | Secondary text (7.1:1 on paper) |
| `--haze` | #B8B1A2 | Smog tint, decoration only (1.9:1, never for text or borders that carry meaning) |
| `--breath` | #12806F | Fills for clean, indoor, approved |
| `--breath-ink` | #0A4F45 | Teal text and links on paper |
| `--seal` | #2B3F8F | Proof: hash chain, receipts, focus ring (8.4:1) |
| `--saffron` | #E88A1A | A person must act: Approve, Share |
| `--danger` | #B3261E | Chain broken, errors. Always with an icon and the word "broken" or "error" |

### GRAP stage scale (CPCB AQI palette)

| Stage | Token | Hex | Chip text |
| --- | --- | --- | --- |
| I | `--aqi-poor` | #F29C33 | `--ink` |
| II | `--aqi-vpoor` | #E0443C | `--ink` |
| III | `--aqi-severe` | #A3207B | white |
| IV | `--aqi-severe2` | #6B1030 | white |

Every stage chip carries the numeral, the label and a 1 px `--ink` border, because the Stage I fill is only 1.95:1
against paper.

### Contrast rules (measured)

| Pair | Ratio | Rule |
| --- | :---: | --- |
| White on saffron | 2.6 | **Not allowed.** The Approve button uses `--ink` text on saffron (6.9:1) |
| White on Stage I | 2.2 | Not allowed. Use ink text |
| `--breath` text on paper | 4.3 | Not allowed for body text. Use `--breath-ink`. `--breath` is for fills and large text only |
| White on `--breath` | 4.8 | OK |
| White on Stage III | 6.9 | OK |

### Dark "control room" theme

Cut for submission (section 10). If built later, use background `#0E1116`, raised surface `#171C24`, text `#ECE7DA`,
teal `#2BB39C` and saffron `#F2A33A`, switched with `data-theme`.

### Typography

Load with `next/font/google`, which self-hosts and subsets the files.

| Role | Latin | Devanagari | Use |
| --- | --- | --- | --- |
| Display | Fraunces 600 | Tiro Devanagari Hindi | Hero, section titles, the साँस mark |
| UI and body | Inter | Noto Sans Devanagari | Body 17 to 18 px, labels 13 to 14 px |
| Data | JetBrains Mono | Latin digits | Hashes, IDs, times, PM2.5, traces |

- Scale: 13, 15, 17, 20, 28, 40, 64, 96 px. Hero `clamp(3rem, 9vw, 7rem)`.
- Devanagari line-height 1.6 or more. Check conjuncts and matras on the real strings early.
- Labels are small caps with 0.08em tracking. Live numbers use `font-variant-numeric: tabular-nums`.

### Shape, spacing, motion

- Spacing 4, 8, 12, 16, 24, 32, 48, 72, 120. Radius 4 px on cards and 999 px on chips. Hairline borders at 20% ink;
  2 px ink for the one selected item. No shadows except one paper-fold `0 1px 0 rgba(20,24,31,.12)`.
- Motion: `--ease-out` cubic-bezier(.2,.8,.2,1), `--ease-inout` cubic-bezier(.65,0,.35,1), 120 / 240 / 600 ms, and
  an 8 s breath cycle.

## 5. Routes for submission

Four routes. The rest of v1's routes become sections of these, or wait until after submission.

| Route | Contains | Backend |
| --- | --- | --- |
| `/` | Hero, stage slider, timetable, counters, trace drawer, 48 h forecast strip, three proof cards, "How it works" section | `/rehearse`, `/forecast`, `/health` |
| `/today` | Principal's brief: Start a run (demo), pending approval with countdown, Approve and Reject, then notices in a phone frame (EN/HI) | `/runs`, `/decisions`, `/approve`, `/watch` through server proxies |
| `/receipt/[id]` | Hash chain, verify, tamper, notice check, provenance, exposure averted, server verdict, QR | `/receipts/{id}` |
| `/privacy` | Keep the existing page | static |

**Existing routes:** redirect `/verification/[receiptId]` to `/receipt/[id]`. Delete `/dashboard`, `/city-board`
and `/conditions`, or redirect them to `/`. Delete `hooks/useWebSocket.ts` and `components/real-time/*`, because
the backend has no WebSocket and a fake live feed is exactly what judges probe.

### Global shell

- **Header:** साँस wordmark with the breath ring, nav (Today, Receipt), EN / हिन्दी toggle, and an IST clock.
- **Status chip** from `/health`: "LIVE · us-east-1 · chain fde77f…" in `--seal`. It turns amber with "REPLAY" when
  the forecast fell back, and grey with "SNAPSHOT" when offline (section 7). Poll every 60 s.
- **Footer:** "Modelled, not measured. Tamper-evident, not tamper-proof." The DPDP review is not yet done, which
  the footer says. Also the source circular link and the MIT licence.
- The ticker strip is cut; its lines become the three proof cards.

## 6. Screens

Build in this order: A, E, D. A and E are the showstoppers.

### A. Landing (`/`)

- **Headline** "Bad air. Better day." in Fraunces, with "ख़राब हवा। बेहतर दिन।" under it, then one line: "Saans
  reads the GRAP order, re-plans the school day, and proves it."
- **Slider:** four stops (I to IV), each with its stage colour, numeral and label. Keyboard arrows, ARIA slider
  role, `aria-valuetext="Stage III, severe"`. The stage is kept in the URL (`/?stage=3`).
- **On change:** debounce 150 ms, cancel the previous request, and call `POST /rehearse` for tomorrow with the
  replay forecast. Keep the old plan visible while loading, with the breath ring in the corner. Never blank.
- **Timetable:** a 6 × 8 grid from `classified_periods`. Outdoor PE starts amber. Use Framer Motion `layoutId`
  keyed on class plus subject plus original period, so 7A's PE block visibly **slides from P2 to P8** at Stage II
  and **slides back and turns into a teal "Hall A" indoor block** at Stage III. That one cell is the demo.
- **Same-plan note.** When moving I↔II or III↔IV, the plan does not change, and a small note says so: "Same plan
  as Stage II for this school. The order bans outdoor PE from Stage III." This turns a possible "nothing happened?"
  into proof that the system follows the order.
- **Counters** (tabular mono, count-up): Moved, Replaced indoors, PE minutes kept (of 240), PE minutes lost, and
  Exposure cut. Each carries a "modelled" tag where it applies.
- **Badges:** forecast source (REPLAY for the scenario) and "Rehearsal: nothing is sent".
- **Trace drawer** opens when a judge clicks any amber, moved or teal cell. It is a right-side drawer, and a bottom
  sheet on mobile. Steps come straight from `decision_trace`:
  1. **The order:** `label` and `reason`, with the rule ID and quote when present.
  2. **Forecast:** nominal PM2.5 against the limit for this class. If the class has stricter limits, show the
     "stricter limit" badge, with no counts.
  3. **Pessimistic (+20%):** the pessimistic value against the same limit.
  4. **Candidates:** each other slot with its verdict and reasons. This is where clashes and forecast failures show.
  5. **Result:** "Moved to P8", or "Indoors in Hall A: modelled 108 vs 360 µg/m³ outdoors", with the alternatives
     ranked by modelled indoor PM2.5 and the "assumption, not measured" note.

  Every step has an icon plus text. Escape closes the drawer and focus returns to the cell.
- **Forecast strip:** 48 h of PM2.5 from `/forecast`, in Recharts or hand-built SVG. It shows the advisory and
  restricted bands, the first-crossing marker labelled directly, and a faint +20% line. Source chip:
  "CAMS via Open-Meteo, one grid point, modelled", with REPLAY when it applies.
- **Below the fold:** three proof cards (Order first · A person decides · Anyone can verify), each a single
  sentence with a link into `/today` or a receipt. Then "How it works": a small architecture diagram drawn in the
  site's style, a two-column Measured vs Modelled panel, and the known limitations from the README.

### E. Receipt (`/receipt/[id]`): the showstopper

Reuse `lib/crypto.ts` (`verifyAuditChain`), which `tests/test_receipts.py` already runs against the real chain.
Port the notice-check logic from `services/audit/verify_page.html`.

- **Blocks:** sequence, event, role, time, short hash and previous hash, joined by connector lines. Rows for this
  decision are highlighted.
- **Verify in your browser:** blocks light up in `--seal` one at a time (80 ms apart), then a VERIFIED stamp lands.
  The server verdict from `/receipts` sits beside it. If the two disagree, show both.
- **Tamper:** make the role on any row editable. Changing it turns that block and every later block red in a
  cascade (60 ms each), and the stamp becomes CHAIN BROKEN. A Reset button restores the chain.
- **Check a notice you received:** a text box. On input, hash the text (exact, trimmed, CRLF→LF, NFC) and match it
  against `notices[].text_sha256` in `NOTICES_DRAFTED`. On a match, a GENUINE stamp lands with "English parents
  notice, row #4, written by static template static:english:parents_plan_b". On no match: "This exact text is not
  in the school's log." Changing one character must flip it. Keep the copy honest: if the chain itself is broken,
  the match is shown with a warning, never as GENUINE.
- **Provenance panel** for `NOTICES_DRAFTED`: per notice, the language, audience, writer (`model_id` or
  `template_id`), and the prompt and text hashes. When `fallback_used` is true, say "Static template (labelled
  fallback)". Never imply a model wrote it.
- **Exposure averted:** "51,380 µg/m³·min of modelled PM2.5 exposure averted", read from `PLAN_GENERATED`, with the
  basis sentence underneath.
- QR code to this page, a print stylesheet, and the footnote "Tamper-evident, not tamper-proof. The chain shows
  any edit, but we operate the database."

### D. Today and approval (`/today`)

- **Start a run (demo)** button, shown with a "Demo mode" chip. It calls `POST /runs` through the server proxy,
  then polls `/decisions` every 2 s until an approval is pending, which takes about 5 to 10 s.
- **Pending card:** date, session and stage chip. A three-number summary (moved, replaced indoors, PE kept). A
  countdown ring computed from `expires_at`, whose last 10 s pulse faster. A **saffron Approve this plan** button
  with ink text, at least 56 px tall. A quieter **Reject** button. And the line "If you do nothing, the
  vice-principal is asked in 60 seconds."
- **Which action Approve sends:** both approve actions take the same notify path, and the choice is recorded in the
  audit chain. Send `APPROVE_PLAN_A` when the plan has moves and `APPROVE_PLAN_B` when it is indoor-only. Reject
  sends `REJECT`, which gives a `REJECTED_NO_BROADCAST` receipt, a good second demo.
- **After clicking:** disable the button and show the breath ring. On `200`, the APPROVED stamp lands, followed by a
  link to the receipt.
- **Responses:** `410` "This approval link is no longer valid: it was used, expired or never existed." `409` "This
  run has already ended. Nothing more can be approved." `5xx` "Could not reach the workflow. Your link is still
  valid. Try again."
- **Stepper** above the card: Planned → Principal asked → (60 s) → Vice-principal asked → Approved or Fail-safe.
  The active node breathes and completed nodes are stamped, with roles only, never names. Link "See a fail-safe
  run" to the prepared fail-safe receipt.
- **Notices:** after approval, a phone frame with an EN / हिन्दी toggle, teacher and parent tabs, a saffron Share on
  WhatsApp button (ink text), and the line "Nothing is pushed to phones." Under it, a provenance chip and "Paste
  this into the receipt to check it", which leads into the closing beat.
- **Watch:** contingency drafts from `/watch` as two small cards labelled "Draft, not active".

## 7. Data layer

- **`lib/api.ts`** is one typed client. TanStack Query is already installed. Zod is optional; if it is skipped,
  hand-written type guards on the fields actually used are enough.
- **Public endpoints** are called from the browser. CORS is confirmed.
- **Admin endpoints** (`/decisions`, `/watch`, `/runs`) go through route handlers under `app/api/admin/*`. These read
  `SAANS_ADMIN_KEY` from the server environment and forward the `x-saans-admin-key` header. The key is never in
  the repo or the browser bundle. Check this with a search of the built `.next/static` folder for the key.
- **The demo proxy is reachable without login, which is deliberate.** It exposes only "start a demo run" and "read
  the demo school's brief", and the Demo mode chip says so on screen. Rate-limit `/api/admin/runs` to one call
  every 30 s.
- **Fallback ladder:** live, then `source=replay` (labelled REPLAY), then **snapshot**.
  `scripts/snapshot_frontend.py` saves real `/rehearse` responses for all four stages, plus `/forecast` replay,
  `/health` and both receipts, into `public/snapshot/*.json`. The UI uses them only after a fetch fails and labels
  the page "SNAPSHOT · captured 11 Oct 13:40". The receipt still verifies offline, because the hashing runs in the
  browser.
- **Privacy:** counts only, roles only. The public rehearsal already removes per-class sensitive counts.

## 8. Microcopy

The voice is calm, plain and accountable, like a good public notice. Buttons are verbs. Every estimate is labelled
"modelled", "rehearsal", "draft" or "snapshot". Never say "AI-powered". Have a native speaker review every Hindi
string before the demo; the Hindi below is a draft.

| Where | English | Hindi (draft) |
| --- | --- | --- |
| Hero | Bad air. Better day. | ख़राब हवा। बेहतर दिन। |
| Subline | Saans reads the GRAP order, re-plans the school day, and proves it. | साँस GRAP आदेश पढ़ता है, स्कूल का दिन दोबारा बनाता है, और उसका प्रमाण देता है। |
| Slider | Drag to see tomorrow at each GRAP stage | हर GRAP चरण पर कल का दिन देखने के लिए खींचें |
| Same plan | Same plan as Stage II for this school. The order bans outdoor PE from Stage III. | इस स्कूल के लिए योजना चरण II जैसी ही है। आदेश चरण III से बाहरी PE पर रोक लगाता है। |
| Rehearsal | Rehearsal: nothing is sent | अभ्यास: कुछ भी भेजा नहीं जाता |
| Start run | Start tonight's run (demo) | आज रात का रन शुरू करें (डेमो) |
| Approve | Approve this plan | इस योजना को मंज़ूर करें |
| Reject | Reject | अस्वीकार करें |
| Waiting | Waiting for the principal. 60 seconds left. | प्रधानाचार्य के उत्तर की प्रतीक्षा। 60 सेकंड शेष। |
| Do nothing | If you do nothing, the vice-principal is asked in 60 seconds. | यदि आप कुछ नहीं करते, तो 60 सेकंड में उप-प्रधानाचार्य से पूछा जाएगा। |
| Fail-safe | Nothing was sent. That is the safe answer. | कुछ भी नहीं भेजा गया। यही सुरक्षित उत्तर है। |
| Link invalid (410) | This approval link is no longer valid: it was used, expired or never existed. | यह लिंक अब मान्य नहीं है: इसका उपयोग हो चुका है, यह समाप्त हो गया है, या कभी था ही नहीं। |
| Run ended (409) | This run has already ended. Nothing more can be approved. | यह रन समाप्त हो चुका है। अब कुछ भी मंज़ूर नहीं किया जा सकता। |
| Verify | Verify in your browser | अपने ब्राउज़र में जाँचें |
| Verified | Verified. Every hash matches. | सत्यापित। हर हैश मेल खाता है। |
| Tamper hint | Change any character and watch the chain break. | कोई भी अक्षर बदलें और श्रृंखला टूटते देखें। |
| Notice check | Paste the WhatsApp notice you received | आपको मिली WhatsApp सूचना यहाँ चिपकाएँ |
| Genuine | Genuine. This exact notice is in the school's record. | असली। यही सूचना स्कूल के रिकॉर्ड में दर्ज है। |
| Not found | This exact text is not in the school's log. | यह सटीक पाठ स्कूल के रिकॉर्ड में नहीं है। |
| Provenance | Written by the static template (labelled fallback) | स्थिर टेम्पलेट द्वारा लिखा गया (लेबल किया गया विकल्प) |
| Snapshot | Offline: showing a saved copy of real responses from 13:40. | ऑफ़लाइन: 13:40 पर सहेजे गए वास्तविक उत्तर दिखाए जा रहे हैं। |
| Footer | Modelled, not measured. Tamper-evident, not tamper-proof. | अनुमानित, मापा हुआ नहीं। छेड़छाड़ दिखाई देती है, रोकी नहीं जाती। |

## 9. States and accessibility

| Screen | Loading | Empty | Error | Special |
| --- | --- | --- | --- | --- |
| Landing | Breath ring over the old plan | n/a | Replay, then snapshot, each labelled | Same-plan note |
| `/today` | Skeleton card | "No decisions waiting. Tomorrow's plan appears at 19:30." | Retry; keep the last good data | Run started but not yet pending: "Planning…" |
| Approval | Button disabled with ring | n/a | 410, 409 and 5xx copy (section 8) | APPROVED stamp, REJECTED stamp |
| Receipt | Blocks fade in | "No audit rows yet" | Server and browser disagree: show both | VERIFIED, CHAIN BROKEN, GENUINE, not found |

- Contrast as in section 4, and the focus ring is 2 px `--seal` everywhere.
- Never colour alone: numeral, icon and text for every stage and status.
- Keyboard path: slider arrows, Tab through cells, Enter opens the drawer, Escape closes it.
- ARIA live region announces "Stage III: 0 moved, 6 replaced indoors, 240 of 240 PE minutes kept."
- `lang="hi"` on Hindi spans. Honour `prefers-reduced-motion` with one global switch.
- Touch targets at least 44 px; Approve at least 56 px.
- Projector check: 17 px body text minimum, tested on a 1280 px screen at low brightness.

## 10. Six-hour plan, demo script and checklist

### Build order (09:45 to 16:00 IST)

If two people are available, one person does the backend row while the other starts on the frontend.

| Time | Deliverable | Done when |
| --- | --- | --- |
| 09:45 to 10:30 | Delete mocks and fake real-time code. Add tokens and fonts. Header with the live `/health` chip. **Deploy the skeleton** (AWS Amplify Hosting if it builds the installed Next 16; otherwise Vercel) | A public URL shows the live chip |
| 10:00 to 11:15 (backend) | `POST /runs` with tests, deployed. Then run one approved decision and one fail-safe decision | Both receipt IDs saved |
| 10:30 to 12:15 | **A:** slider, timetable with the 7A layout move, counters, haze, trace drawer | Dragging II→III moves the block on live data |
| 12:15 to 13:30 | **E:** receipt with verify cascade, tamper, notice check, provenance, exposure averted | Paste genuine ✓, edit one character ✕ |
| 13:30 to 14:30 | **D:** `/today` with Start, countdown, Approve and Reject, phone-frame notices | A live run approved within 60 s |
| 14:30 to 15:00 | Snapshot script and fallback; forecast strip if time allows | Network off: the page still demos, labelled SNAPSHOT |
| 15:00 to 15:30 | Hindi review, contrast pass, **record the fallback video** | Video saved |
| 15:30 to 16:00 | Buffer, README link to the frontend URL, submit | Submitted |

**Cut, in this order, if late:** forecast strip → Watch cards → stepper animation (keep a static stepper) → QR and
print stylesheet → haze grain (keep the gradient). **Never cut:** the live slider, the receipt verify and tamper,
the notice check, the live approval.

**Out of scope for submission:** dark theme, standalone mobile `/approve`, `/how` as its own route, keyboard
shortcut sheet, Storybook or a `/kit` route, Lighthouse targets, the ticker.

### The 90-second demo

1. **0 to 15 s.** Open `/`. "Delhi schools get a GRAP order at night. Saans re-plans the day." Drag II → III.
   The haze thickens and 7A's PE slides back from P8 into an indoor Hall A block. Counters: moved 1→0, indoor 5→6,
   PE kept 240 of 240, exposure cut 95%→100%, "modelled".
2. **15 to 30 s.** Click 6A P3. The drawer shows the order banning outdoor PE, the forecast of 360 against a stricter
   96 limit, each candidate slot rejected with its reason, and Hall A at a modelled 108 µg/m³.
3. **30 to 55 s.** Open `/today` and press Start. The card appears with a 60 s ring. "A person decides. If nobody
   answers, the vice-principal is asked, then nothing is sent." Approve. The APPROVED stamp lands. Toggle the notice
   to Hindi.
4. **55 to 75 s.** Open the receipt. Verify: the blocks light up and VERIFIED lands. Tamper: change the role and the
   chain goes red from that row down. Reset.
5. **75 to 90 s.** Paste the WhatsApp notice into "Check a notice": GENUINE, with the row and the writer. Delete
   one letter: not found. "Even the notice is on the record. Don't trust us. Verify."

Rehearse with a stopwatch, on a projector and on a phone. If the live run fails, use the prepared receipts and
the snapshot, and say so out loud.

### What to avoid

- CampusEvac's look, or a default dashboard with a purple gradient.
- A chatbot or "AI assistant" panel.
- Any mock data, or any unlabelled fallback.
- Implying Bedrock wrote a notice it did not write.
- Hindi in a fallback font or with cramped line height.
- Waiting two minutes on stage for an escalation.

### Pre-submission checklist

- [ ] No file under `app/api/` returns invented data; mocks and `lib/mockData.ts` are deleted
- [ ] Slider calls live `POST /rehearse`; replay and snapshot fallbacks are labelled
- [ ] Admin key is not in the repo or in `.next/static` (searched)
- [ ] `POST /runs` deployed and tested, and `/api/admin/runs` is rate-limited
- [ ] A fresh approved receipt with provenance, and a fail-safe receipt, both saved
- [ ] Notice check: genuine paste ✓, one-character edit ✕, on the deployed URL
- [ ] Contrast rules from section 4 applied; the Approve button uses ink text
- [ ] Hindi reviewed by a native speaker
- [ ] Tested on a phone and a projector; demo under 90 seconds; fallback video recorded
- [ ] README links the frontend URL
