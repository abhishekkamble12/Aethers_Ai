# Saans: winning project document

Oct 8, 2026 · @biilly

## Summary

Saans turns an official bad-air order into an approved, re-planned school day and a public receipt anyone can verify, with no hardware. Tagline: **Reads the order. Re-plans the day. Proves it.**

Track: Air ("school safety on bad days"), Environmental Hacks, Oct 8-11, 2026. Primary user: the school principal in Delhi-NCR. Principle: code decides, the model proposes and drafts, a person approves.

**What makes it unique**

- **Order-first, not sensor-first.** Restrictions come from the circular and the declared stage. Forecast only decides advisory versus allowed inside what the order permits.
- **Re-plan, don't cancel.** A deterministic planner swaps periods, checks teachers, ground, locked periods and forecast error, and falls back to an indoor session so activity minutes are kept. This matches CAQM's Sept 16, 2026 advice to reschedule.
- **Proof.** Every step goes into a hash-chained log. A public Air-Day Receipt page recomputes the chain in the browser.
- **Stage Rehearsal (new).** The principal drags the declared stage from I to IV and watches tomorrow's timetable re-plan instantly, before any order lands. It reuses the same planner, so it costs little to build and is easy to see in a video.
- **The system visibly refuses (new).** A circular with an injected instruction or an invented quote is rejected on screen. It shows where AI stops and code decides.

## Problem and users

On bad-air days the order arrives, but each school must turn it into a working day alone, and nothing records that it did. **How might we make the compliant action the easiest one for a school, and make it provable?**

**Evidence** (from the team brief v6; re-check primary sources before the video)

- GRAP stages by Delhi AQI: I Poor 201-300, II Very Poor 301-400, III Severe 401-450, IV Severe Plus above 450.
- Nov 21, 2025: Delhi schools were ordered to halt outdoor activities after a Supreme Court directive.
- Dec 2025: CAQM wrote to the chief secretaries of Delhi, Haryana, Rajasthan and UP that some schools still held outdoor sports despite earlier directions.
- Dec 13, 2025: after CAQM invoked Stage IV, Delhi's Directorate of Education ordered classes up to IX and XI to run hybrid. School action follows DoE circulars, not only CAQM orders.
- Sept 16, 2026: CAQM advised schools to avoid outdoor sports in Nov-Dec 2026 and to find alternate ways to reschedule or provide opportunities. This supports "re-plan, don't cancel" in the authorities' own words.
- To verify: a weak source reports a revised GRAP on Sept 29, 2026, and current-season directions per stage are not confirmed. Rules are therefore versioned data, never hard-coded.

Limit to state on screen: the CAQM letter shows non-compliance occurred. It does not show how widespread it is or why. Do not quote a rate.

**Four failures** (each is a hypothesis to confirm on the user call)

| Failure | What goes wrong today | Saans answer |
| --- | --- | --- |
| Interpretation | Someone matches the latest circular to today's forecast, informally, early in the morning | Rule engine labels every period allowed, advisory, restricted or banned, with the rule ID and quote |
| Follow-through | Cancelling PT leaves a class and teacher without a plan and removes physical activity | Swap planner, then an indoor session as fallback |
| Communication | Teachers and parents get forwards and calls | Drafted notices, Hindi and English, WhatsApp click-to-share, acknowledgement link |
| Proof | Nothing records when, on what basis, or who was told | Hash-chained log and a public receipt |

**Who it serves**

| Person | Need | Pain |
| --- | --- | --- |
| Principal (primary user) | A defensible decision and a record | Interpreting directives under time pressure |
| PE and class teachers | A clear plan for the changed period | Improvising at short notice |
| Parents | A timely, understandable notice | Inconsistent information |
| Authorities | Evidence of compliance | No school-level visibility |
| Site supervisors (second profile) | Re-plan outdoor tasks, record exposure decisions | The same interpretation burden |

Related work: I found tools that stop at the alert (sensors, dashboards, threshold notifications) and none that re-plans the timetable, handles follow-through and keeps a verifiable record. The search was not exhaustive, so say "I found none", not "none exist".

## Judging map

Each of the five event criteria has a named piece of evidence, and the two weakest ones (usability and the video) get the most design attention here.

| Criterion | What judges ask | Saans evidence | Risk and fix |
| --- | --- | --- | --- |
| Idea and impact | A real problem? What changes for people? A small problem solved well | One bounded problem: turning a circular into a safe school day. Cited CAQM and DoE record. PE minutes preserved. One real principal quote | Judges may say it only reduces exposure. Answer: it protects children on days the air is bad and keeps their activity. Get the quote today |
| Built on AWS | Is AWS in the project? | Deployed on AWS: Scheduler, Step Functions, Lambda, DynamoDB, SQS, Bedrock, Textract, S3 and CloudFront, CloudWatch. Open source: SAM CLI and Strands Agents SDK | Bedrock and Textract access can block you. Request access today; static fallbacks exist |
| Design and usability | Could someone outside the team use it? | One Brief screen with one primary action, load-demo-school button, sample CSV, Hindi and English, readable on a phone, Stage Rehearsal slider | Onboarding is heavy. Pre-load a demo school; watch one outsider try it |
| Execution | Does it work? One feature that runs beats five | One end-to-end run plus three failure drills and an eval table | Scope. P2 items are cut unless P0 and P1 are green |
| Demo video | What it does, who it is for, where AWS fits, in 3 minutes | Three beats, user named aloud, AWS console on screen | Overstuffing. Three beats only |

**Likely judge questions**

- *Where is AI actually needed?* Circular-to-Rules turns unstructured PDFs into validated rules. The model proposes, code validates, a human approves.
- *Why not just alerts?* Alerts stop at information. The school still has to re-plan, communicate and prove. Saans does all three.
- *What if the forecast is wrong?* The swap must also pass a pessimistic forecast, and a morning re-check can produce a revised proposal.
- *Why trust the record?* Hash chain plus a public verify page. We say tamper-evident, not tamper-proof.
- *Is it production-ready?* Production-shaped (infrastructure as code, least privilege, idempotency, observability, tests). Not ready: DLT and WhatsApp registration, DPDP review and a real pilot remain.

## Product walkthrough and usability

A principal who has never seen Saans should reach a decision in under 60 seconds: open the Brief, read the before-and-after grid, tap Approve. Everything else is secondary.

**Screens** (one primary action each)

| Screen | Content | Primary action |
| --- | --- | --- |
| Today's Brief | Before-and-after grid per class, a plain-language reason with numbers, forecast chart, Plan A and Plan B | Approve |
| Stage Rehearsal | A slider for the declared stage (I to IV) that re-plans tomorrow's timetable instantly, so the principal sees what each order would change | Save as Standing Order draft (P2) or close |
| Rules | Active ruleset, circular upload, rule-diff with the source quote highlighted | Approve ruleset |
| Receipts | Decision list with audit trail and a QR code that opens the public verify page | Open receipt |
| Import | CSV timetable upload with row-level validation messages; a Load demo school button | Import |

**Usability rules**

- One primary action per screen, plain words, Hindi and English strings, usable on a phone.
- A sample CSV and a pre-loaded demo school, so a judge can try it without setup.
- Every banned or restricted label shows its rule ID and the circular quote behind it.
- Replay days wear a visible "Replay scenario" banner.
- Before Sunday, have one person outside the team run the flow cold and fix what confuses them.

**What the principal receives** (example, Telegram)

> Stage III declared. Forecast PM2.5 peaks 10:00-13:00. 7B PT (P2) can move to P5 (permitted, lower exposure). 8A PT: no safe swap, indoor session proposed. \[Approve A\] \[Approve B\] \[Reject\]

Teachers get the new schedule and any indoor plan. Parents get a short Hindi or English notice with an acknowledgement link. Each class teacher gets a WhatsApp click-to-share link for the parent group. It needs one manual tap and no WhatsApp Business API, which matches how schools already work, and the video says so.

**Tentative then confirmed.** The evening run sends a heads-up. The morning run re-fetches the forecast. If no label changes, the plan is confirmed. If any period's label changes, the system creates a revised proposal that needs approval. Periods near a threshold are flagged.

## Architecture on AWS

&#91;embedded content: architecture · 3 planes on AWS\]

Three planes share one AWS deployment: a control plane that owns state and waiting, an AI and document plane that only proposes, and an evidence plane that stores and proves.

**One decision, end to end**

1. EventBridge Scheduler fires per tenant in the evening (tentative) and the morning (confirm). The decision key is tenant, date and session.
2. Lambda loads the grid-cell forecast, the timetable, the active ruleset version and the declared stage.
3. The rules engine labels every period, and the planner builds Plan A or Plan B.
4. If nothing changed, the run closes. Otherwise Step Functions sends the brief and waits with `waitForTaskToken`. No answer escalates to the vice-principal, then fails safe with no broadcast.
5. After approval, Bedrock drafts notices (static template as fallback) and SQS delivers them, retrying and then dead-lettering.
6. Acknowledgements are collected, every step is appended to the audit chain, and the morning run confirms the plan or proposes a revision.

**Open-source tooling.** The build uses SAM CLI (infrastructure as code) and the Strands Agents SDK (the extraction agent). Both are on the event's open-source list, so prize eligibility holds even if a deployment problem appears. Powertools for AWS Lambda adds structured logs and idempotency; it is AWS open source but not on the event's list. LocalStack is the local fallback for testing if account access stalls.

**Region.** Pick one region today and test Bedrock model access and Textract there. The brief flags both as unverified, and approval for model access can take time.

## AI design

The model does two bounded jobs, extracting candidate rules from a circular and drafting notices. It never edits a timetable, sets a permission, sends a message or activates a rule. Each job is one typed request with a code check after it, not a free-running agent.

**Job 1: Circular-to-Rules**

1. Upload the PDF to a versioned S3 bucket with issuer, issue date and jurisdiction metadata. Store a content hash.
2. Extract text. Use the text layer when present; use Textract for scans. Textract quality and availability in the Mumbai region is still to verify; the fallback is text-layer-only for digital PDFs.
3. Chunk by section and send only relevant chunks.
4. A Strands agent calls Bedrock with a strict JSON schema. The agent's tools are limited to three: read the chunk, read the active ruleset, submit candidate rules. It has no write, send or approve tool.
5. Code validates every candidate: schema, enumerated values (stages, class bands), date ranges, jurisdiction, and that `source_quote` is a verbatim substring of the extracted text. A quote that does not match rejects the rule.
6. Code checks conflicts against the active ruleset and builds a diff of added, changed and removed rules, each with its quote and page.
7. An admin reviews and approves. Only then is a new immutable, hashed ruleset version created. Rollback selects a prior approved version.

**The refusal moment.** The gold set includes two hostile circulars: one with an instruction hidden in the text, and one where the model's quote is invented. The video shows both rejected on screen. Circular text is treated as untrusted input; the model's instructions come only from the system side.

**Extraction prompt rules.** Use only the text provided. One JSON object per rule. Every rule carries an exact quote. Unstated fields are null. Return an empty list when no rule applies. The code, not the model, checks the quotes.

**Job 2: notice drafting**

- Input: approved plan fields only, plus audience, language and channel.
- Output: a short draft in a constrained schema. Every fact must map to a plan field. No new permissions and no AQI claims.
- A static template is the fallback if Bedrock fails, times out or is denied. The audit row records that the fallback was used. A safety notice never fails because a model failed.

**Model risk.** Bedrock model and region access (Amazon Nova) is still to verify. Request it today. If it is blocked, the pipeline runs on pre-extracted rules and static templates, and the writeup says so.

## Rules engine and planner

The rules engine and planner are plain, deterministic code: the same versioned inputs always give the same labels and the same plan, and a jurisdiction mismatch fails closed.

**Decision hierarchy**

1. Orders first. The declared stage plus circular rules decide banned or restricted. Saans takes the stage as input; it never computes or announces one.
2. Forecast second. Inside what orders permit, configured PM2.5 bands decide advisory versus allowed. Advisory thresholds (90 and 120 in the sample) are product defaults, not official limits.
3. Humans last. Approval is required before anything is sent, except under a Standing Order (P2).

CPCB 24-hour PM2.5 bands for reference (re-check at cpcb.nic.in): 0-30, 31-60, 61-90, 91-120, 121-250, above 250 ug/m3.

**Ruleset record** (versioned, immutable once approved)

```json
{
  "ruleset_version": "2026-10-08-r1",
  "jurisdiction": "Delhi",
  "declared_stage": "III",
  "rules": [{
    "rule_id": "r-017",
    "applies_to": ["school"],
    "class_band": ["primary", "middle", "secondary"],
    "condition": { "stage_at_least": "III" },
    "action": { "outdoor_sports": "banned", "outdoor_pt": "banned" },
    "effective_from": "2025-12-13",
    "source_id": "DoE-circular-xyz",
    "source_quote": "<verbatim sentence from the circular>"
  }],
  "advisory_pm25": { "advisory_at": 90, "restricted_at": 120 }
}
```

**Swap planner.** For each outdoor period that is not allowed, try every same-day period of the same class. A swap is valid only if all hard constraints pass.

- Both periods are in the same class and day; the partner is unlocked and indoor-capable.
- Both teachers are free in the new slots; the ground is not double-booked.
- The target period is permitted under the nominal and the pessimistic forecast.
- Modelled exposure strictly decreases.

Soft preferences: fewest moves, at most N moved periods per class, no move across lunch, largest exposure reduction. If no swap qualifies, or outdoor sports are banned for the day, Plan B uses a static indoor activity bank matched to class band and duration (reading, chess, carom, crafts, indoor movement). The model may personalise wording; the bank is the fallback. After choosing moves, the planner re-validates the whole day for teacher and ground conflicts across classes.

```latex
E_{nominal} = \sum_i m_i \, p_i \qquad E_{pessimistic} = \sum_i m_i \, p_i \, (1 + \delta) \qquad score = (E_{before} - E_{after}) - move\_penalty
```

Here m is outdoor minutes in a period, p is that period's forecast PM2.5, and delta = 0.20 is a design target to tune on replay data. Exposure is a modelled comparison, not a medical measure. Label it a modelled estimate and show the inputs.

**Stage Rehearsal.** The same planner runs for any stage, so the Brief can show what Stage I, II, III and IV would each change before an order lands. It is one Lambda call per slider position, or a client-side run of the same logic on the demo data, and it makes the engine visible in seconds.

**Tests to write first**

1. A valid swap exists and is chosen.
2. The best partner's teacher is busy, so the next best is chosen.
3. The ground is double-booked, so the swap is rejected.
4. Outdoor sports banned for the day, so Plan B.
5. A locked period is never moved.
6. Two proposals conflict, so the planner re-validates and resolves.
7. All periods allowed, so no change.
8. Fine nominally but fails the pessimistic check, so rejected.
9. A stage-level ban is never relaxed by low PM2.5.
10. A ruleset for another jurisdiction is rejected.

## Data model, APIs and audit chain

One DynamoDB table holds everything, keyed by tenant, and no record contains a child's name or identifier.

**Single-table keys**

| Entity | PK | SK |
| --- | --- | --- |
| Tenant metadata | TENANT#{id} | META |
| Timetable (versioned) | TENANT#{id} | TT#{version} |
| Decision | TENANT#{id} | DEC#{date}#{EVE or MORN} |
| Audit row | TENANT#{id} | AUD#{seq, zero-padded} |
| Audit head pointer | TENANT#{id} | AUDHEAD |
| Acknowledgement | TENANT#{id} | ACK#{decision}#{recipient\_hmac} |
| Standing Order (P2) | TENANT#{id} | SO#{id} |
| Ruleset | RULESET#{version} | META |
| Circular | CIRC#{id} | META |
| Forecast cache (TTL) | GRID#{cell}#{date} | FCST |

GSI1 (status and date) serves dashboard lists. Recipient identifiers in acknowledgements use a keyed HMAC with a secret held in SSM, not a plain hash, because phone numbers are easy to reverse from an unkeyed hash.

**Idempotency.** `decision_id = tenant#date#session` is also the Step Functions execution name, so a duplicate trigger cannot start a second run. Notification writes are conditional puts keyed by decision and recipient.

**Hash-chained audit log**

```latex
hash_n = SHA256( hash_{n-1} \,\|\, canonical\_json(row_n) )
```

- Append with one DynamoDB `TransactWriteItems`: put `AUD#seq` with a not-exists condition and update `AUDHEAD` with the condition `head.seq == n-1`. This enforces strict order under concurrency.
- A row holds timestamp, actor role (never a name), event type, ruleset version, forecast snapshot ID, decision ID and a payload digest.
- The public verify page shows non-sensitive fields only, and the browser recomputes the chain with SubtleCrypto. A QR code on each receipt opens it, so a notice-board printout links to proof.
- Say precisely: tamper-evident, not tamper-proof. Stretch: anchor the daily head hash in an S3 object with Object Lock.

**API surface**

| Endpoint | Purpose | Who |
| --- | --- | --- |
| POST /circulars | Presigned upload URL, start the pipeline | Admin |
| GET /rulesets, /rulesets/{v}, /rulesets/{v}/diff | Read rulesets and the diff against the active one | Staff or reviewer |
| POST /rulesets/{v}/approve | Activate an approved version | Authorised approver |
| POST /timetables/import | CSV import with row-level errors | School admin |
| GET /decisions?date= | Today's brief and plan | Tenant staff |
| POST /rehearse?stage= | Plan for a hypothetical stage, no side effects | Tenant staff |
| POST /approve/{shortId} | Approve Plan A or B, or reject | Allowlisted approver |
| POST /callbacks/telegram | Webhook, secret-token header checked | Telegram |
| GET /ack/{shortId} | Parent acknowledgement | Parent |
| GET /receipts/{id} | Privacy-filtered verifiable receipt | Public, opaque ID |

Object shapes to agree on paper today: ClassifiedPeriod, Plan, Decision, AuditRow. Timetable CSV columns: class, day, period, start, end, subject, teacher\_code, venue, outdoor, locked.

## Reliability, security and privacy

When anything fails, Saans keeps the approved rule state, flags an operator and never sends an unapproved broadcast.

**Failure behaviour and drills**

| Failure | Expected behaviour | Drill in the video |
| --- | --- | --- |
| Model timeout or denial | Static template used, fallback logged in the audit row, rules and planner continue | Deny Bedrock access |
| Duplicate scheduler event | Same decision key blocks a second run and duplicate messages | Fire the trigger twice |
| Channel failure | SQS retries, then the dead-letter queue, an alarm fires, the dashboard shows "undelivered" | Simulate a Telegram 5xx |
| Approver does not answer | Escalate to the vice-principal; on final timeout flag the admin and do not broadcast | Shortened \~60 second timeout in the main flow |
| Forecast unavailable | Mark stale; do not silently substitute; route for a human decision | Optional |
| Bad quote or rule conflict | Block activation and show the validation errors | The refusal moment |

**Security and privacy**

- The Telegram webhook checks a secret-token header, and only allowlisted chat IDs can approve.
- Workflow task tokens never leave the server. Callbacks carry a short random expiring ID.
- Dashboard access uses signed, expiring magic links sent to allowlisted chats. Cognito is out of scope.
- API Gateway throttling and one least-privilege IAM role per Lambda, with no wildcard resources. The bot token sits in SSM Parameter Store as a SecureString.
- The model's credentials have no write access to tenant records, rulesets, approvals or delivery.
- Data minimisation: class-level timetable, teacher codes instead of names, no child-level records, parent contact only as an opt-in chat ID or keyed hash, with TTLs on caches and acknowledgements.
- Treat uploaded PDFs as untrusted: isolate document text, limit tools, require quotes and validate output.
- Legal and privacy review for India's DPDP Act obligations on children's data is required before any real deployment. This is stated as a limitation, not claimed as done.

## Evaluation, metrics and honest claims

Every number shown to judges is one of three kinds, and the kind is printed beside it: measured, modelled or design target. No number is shown that has not been produced by a run.

**Extraction evaluation (the judge-facing table).** Collect 8-10 real CAQM and Delhi DoE circulars today and hand-label the expected rules in `data/gold/`. Add the two hostile cases (hidden instruction, invented quote). Report rule precision, rule recall, quote-validity rate and per-group accuracy (school versus crew) in the README, and show it on screen. Eight to ten circulars is a hackathon start, not proof of production reliability, and the README says so.

| Metric | Kind | How it is produced |
| --- | --- | --- |
| Time from trigger to principal brief | Measured | Timestamps in the audit log |
| Principal response time, escalation used | Measured | Approval rows |
| Messages delivered, failures, DLQ count | Measured | SQS and CloudWatch counters |
| Static-fallback usage when the model fails | Measured | Audit flag |
| Periods rescheduled, replaced, unchanged | Measured | Planner output on the timetable |
| PE minutes preserved (retained or replaced within the day, over originally scheduled) | Measured | Timetable arithmetic |
| Circular-to-Rules precision, recall, quote validity | Measured | Gold set |
| 1,000-tenant run time and failures (P2) | Measured | Synthetic run, only if done |
| PM2.5-weighted outdoor minutes avoided per class | Modelled estimate | Formula and inputs shown |
| Child-hours moved indoors | Modelled estimate | Formula and inputs shown |
| Notice delivered within 5 minutes of approval | Design target | Label as a target until measured |

**The one number to remember.** "PE minutes preserved" is the headline: it shows the school kept children active without sending them into bad air. It is computed from the timetable, so it is measured, and the PM2.5 exposure figure sits beside it as a modelled estimate.

**Claims to avoid**

- Do not say Saans solves Delhi's air problem. Say: schools first, a pilot-ready engine, and a second profile showing the engine generalises.
- The forecast is modelled, not a station reading. Label every replay day as a replay.
- Do not state a cost per school or scale performance before it is measured.
- Do not state a count of Delhi schools unless it comes from an official source (DoE or UDISE+).
- A cleaner window reduces exposure; it does not make unsafe air safe. Stage rules override the planner.

## Build plan

The plan is gate-driven: ship P0 first, add P1 only while P0 stays green, and treat P2 as optional. If the clock has already started, do the first-hour tasks below before any feature work.

**Priorities**

| Priority | Build | Exit evidence |
| --- | --- | --- |
| P0 core | Rules engine with versioned rulesets, planner with the 10 tests, CSV timetable import, Step Functions approval with escalation, templated notices, hash-chained audit and receipt, one AWS-deployed path | One scheduled or replayed end-to-end run with approval, delivery and a verified receipt |
| P1 differentiators | Circular-to-Rules with quote validation and diff, the refusal moment, robust (pessimistic) swap, Stage Rehearsal, WhatsApp click-to-share, public verify page with QR, polished before-and-after grid | Eval table, model-off drill, no unsupported rule activated |
| P2 only if P0 and P1 are green | Standing Order (Cedar), second outdoor-crew profile as config only, City Board, morning re-check lifecycle, 1,000 synthetic tenants | Measured results on clearly labelled synthetic data |

&#91;embedded content: build roadmap · 4 days, 4 gates\]

Each day ends in a gate and a recorded clip; Friday's gate is the one that decides whether the demo can open with a real circular.

**First-hour tasks**

- Everyone: AWS Builder Center student verification, an AWS account with credits, and a budget alarm.
- A: install SAM CLI, pick one region, request Bedrock model access, and test one Textract call.
- B: draft the sample timetable CSV (6 classes, 8 periods, Monday to Friday) and a replay forecast table for a Stage III day.
- C: collect 8-10 real circulars (CAQM and Delhi DoE), hand-label the expected rules, and write the two hostile cases.
- D: call one principal or teacher for a real quote, and create the Telegram bot and token.
- Everyone: agree the ClassifiedPeriod, Plan, Decision and AuditRow shapes on paper. If the call shows swaps are rare in practice, lead the demo with Plan B.

**Owners**

| Owner | Owns | Thu Oct 8 | Fri Oct 9 | Sat Oct 10 |
| --- | --- | --- | --- | --- |
| A: Platform | SAM, Step Functions, EventBridge, SQS and DLQ, IAM, hash chain, CloudWatch, drills | SAM template, DynamoDB, scheduler, IAM | State machine with approval, escalation, fail-safe; hash-chain append | SQS and DLQ, alarms, three drills |
| B: Planner | Rules engine, planner, tests, CSV import, Stage Rehearsal, replay | 10 tests, rules, planner v1, CSV loader | Connect to the state machine, whole-day revalidation | Replay mode, Stage Rehearsal, edge cases, optional second profile |
| C: AI | Circular-to-Rules, drafting, gold set, eval table | Schema, prompt, Textract and Bedrock on one circular, validators | Chunking, conflict diff, ruleset versioning, drafting with fallback | Eval table, hostile cases, prompt tuning |
| D: Product | Telegram, WhatsApp relay, dashboard, verify page, user calls, README, blog, video | UI shell, Telegram buttons, user call | Webhook, Brief grid, rule-diff screen | WhatsApp relay, verify page and QR, Hindi and English strings, usability test |

Sunday is shared: README, architecture diagram, limitations, blog, video, submit early.

**Definition of done for any feature:** unit tests pass, it is deployed in AWS, it is visible in the dashboard or logs, and a clip is recorded. A feature that misses one of the four stays out of the video.

**Cut triggers** (decided by the clock, not by feeling)

| If | Then |
| --- | --- |
| Friday gate missed | Circular-to-Rules becomes a static versioned JSON; no second profile, no City Board |
| Bedrock or Textract access blocked | Text-layer-only extraction and static templates; say so honestly |
| Saturday 6 pm and drills not passing | Freeze everything except drills, README and video |
| Second profile needs code | Drop it; mention as roadmap only |
| 1,000-tenant test not done by Saturday 9 pm | Drop it and claim nothing |

## Demo video script (2:50)

The video is the only thing judges see, so it runs three beats that match the tagline (reads the order, re-plans the day, proves it), then shows where AWS fits. The rules ask for 2-3 minutes with AWS visibly used.

| Time | Shot | Criterion it serves |
| --- | --- | --- |
| 0:00-0:25 | Say who it is for out loud: a school principal in Delhi-NCR on a bad-air day. Show the CAQM Sept 16 line and one real quote from the principal call. Problem in one sentence: the order arrives, the school re-plans alone and cannot prove it | Idea and impact |
| 0:25-1:00 | **Reads the order.** Upload a real circular, show the rule-diff with the quote highlighted, approve. Then the refusal moment: a hostile circular and an invented quote are rejected. Flash the eval table | Execution, AI where needed |
| 1:00-1:55 | **Re-plans the day.** Replay banner on screen. Drag Stage Rehearsal from II to III and watch the grid re-plan. Show a Plan A swap and a Plan B indoor session, tap Approve, let the timeout fire once to show escalation, then the teacher schedule, the WhatsApp share link and the audit row. Show PE minutes preserved | Design and usability, execution |
| 1:55-2:20 | **Proves it.** Open the public verify page and recompute the hash in the browser. Show the QR. One failure drill: deny Bedrock and the static notice goes out, flagged in the audit | Execution, trust |
| 2:20-2:50 | **Where AWS fits.** Architecture diagram, then the console: a Step Functions execution, the DynamoDB audit rows, the SQS dead-letter queue and alarm. One line on limits: modelled forecast, WhatsApp needs a manual tap, not yet piloted | Built on AWS |

**Rules for recording**

- State on screen that the run is a labelled replay; early-October air may not reach the Poor band.
- Capture every working piece as a clip while building, so the final cut is assembly, not a live recording.
- The video must open in a signed-out browser.
- The second profile (outdoor crew) and the City Board appear only if they are ready, as a 10-second clip, and are never narrated as built if they are not.

## Risks, limits and submission checklist

The biggest risk is scope, so every risk below has a named mitigation and the cut list is decided in advance.

| Risk | Mitigation |
| --- | --- |
| Scope too large for 4 people in 4 days | Gates and cut triggers (Build plan). P2 starts only when P0 and P1 are green |
| Rules block swaps on the worst days | Show one day where Plan A works and one where Plan B applies |
| Real timetables are messy | CSV validation with clear errors; if swaps are rare, lead with Plan B |
| The model misses or invents a rule | Verbatim quote check, schema validation, human approval, never auto-activate |
| Forecast is modelled, not measured | Robust swap, morning re-check, state it plainly |
| Telegram is not a production channel | WhatsApp click-to-share now; SMS or WhatsApp registration later |
| Bedrock or Textract access or region problems | Request access today; static templates and text-layer-only extraction |
| Overclaiming | Evidence tags in every claim; no unmeasured number on video |

**Limitations to publish.** The forecast is modelled. Stage invocation is CAQM's decision. There is no hardware. Effectiveness is not proven by a real pilot. Exposure numbers are estimates. The WhatsApp relay needs a manual tap. The initial ruleset is Delhi-specific. Not production-ready: DLT and WhatsApp registration, DPDP review and a real pilot remain.

**Cut first:** mobile app, IoT sensors, WhatsApp Business API, voice-note approval, multi-hazard features, model training, Cognito, a multi-city onboarding UI, a Hindi Q&A bot. Cut next if time slips: Standing Order, Cedar policy, City Board, 1,000-tenant test, second profile.

**Submission checklist** (from the tour rules in the brief; confirm on the live event page)

- [ ] Public repository with commit history inside the event window and no project code before the clock starts.
- [ ] Demo video of 2-3 minutes, opens without sign-in, AWS visibly shown.
- [ ] Short writeup: the problem, the build, where AWS fits, plus limitations.
- [ ] Blog on AWS Builder Center, linked in the submission.
- [ ] Every member registered individually and student status verified on AWS Builder Center.
- [ ] One submission per team, one team per person.
- [ ] Submitted well before the cutoff. The final cutoff time is not published, and a late submission is not scored.

Prize reference from the brief: each track winner gets Rs 2,00,000 plus $2,000 AWS credits; four runner-ups get $1,000 credits; the top 10 students get fast-track Amazon interviews; the top 5 blogs win AirPods. Prize eligibility needs at least one AWS open-source tool or a deployment on AWS. Verify these on the event page.

**Sources.** The facts above come from the team's brief v6, whose research links were not re-opened for this document, so treat dates and policy statements as items to re-check. Links in the brief that are complete: [Event page and judging criteria](https://www.wemakedevs.org/aws/env), [Tour rules](https://www.wemakedevs.org/aws/rules), [Example DoE circular, Jan 2025](https://edudel.nic.in/upload/upload_2025_26/40_dt_17012025sch.pdf), [CAQM Stage IV measures, Dec 14, 2025](https://newsonair.gov.in/caqm-enforces-grap-iv-measures-as-delhi-ncr-air-quality-worsens/).
