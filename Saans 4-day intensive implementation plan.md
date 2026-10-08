# Saans: 4-day intensive implementation plan

Oct 8, 2026 · @biilly

## Ground rules and shared contracts

Four people, four days, one rule: every day ends with a deployed, recorded, working slice, and anything that is not will be cut. Assumed working hours are Thu 10:45 to 23:30, Fri and Sat 08:00 to 24:00, and Sun 08:00 until submitted. Move the blocks if your hours differ.

**Owners**

| Owner | Name it in chat | Owns |
| --- | --- | --- |
| A | Platform | SAM, Step Functions, EventBridge, SQS and DLQ, IAM, hash chain, CloudWatch, drills |
| B | Planner | Rules engine, planner, tests, CSV import, Stage Rehearsal, replay |
| C | AI | Circular-to-Rules, drafting, gold set, eval table |
| D | Product | Telegram, WhatsApp relay, dashboard, verify page, user calls, README, blog, video |

**Working rules**

- Standup at 09:00 and 21:00 for 10 minutes: what shipped, what is blocked, what is cut. The 21:00 standup checks the day's gate.
- Trunk-based git: small commits to `main` behind a passing unit test; no long branches. Commit history must sit inside the event window.
- One shared SAM stack in one region. Only A merges infrastructure changes; others send a pull request or a snippet.
- Definition of done for any feature: unit tests pass, deployed in AWS, visible in the dashboard or logs, and a screen clip saved to `docs/clips/`. A feature that misses one stays out of the video.
- Record a clip the moment something works. The final video is assembled from clips.
- Keep a running "what fought back" log (D) for the blog.

**Shared contracts** (freeze on paper in the first hour; change only by announcing in chat)

```json
{
  "ClassifiedPeriod": { "class": "7B", "period": "P2", "start": "09:20", "end": "10:00", "label": "banned", "reason": "Stage III order", "rule_ids": ["r-017"] },
  "Plan": { "decision_id": "T1#2026-10-12#MORN", "plan_a": [], "plan_b": [], "exposure_before": 0, "exposure_after": 0, "ruleset_version": "2026-10-08-r1" },
  "Decision": { "decision_id": "", "status": "pending", "approvals": [], "notices": [], "audit_head": "" },
  "AuditRow": { "seq": 0, "prev_hash": "", "hash": "", "actor_role": "", "event": "", "payload_digest": "", "ts": "" }
}
```

The values above are illustrative placeholders, not measured data. Timetable CSV columns: class, day, period, start, end, subject, teacher\_code, venue, outdoor, locked.

**Repository layout:** `infra/` (SAM), `services/rules`, `services/planner`, `services/circular`, `services/workflow`, `services/notify`, `services/audit`, `web/`, `data/gold`, `data/demo`, `tests/`, `docs/`.

## Day 1, Thu Oct 8: foundations

**Gate at 21:00:** a scheduled run in AWS outputs a valid Plan A or Plan B for a replay day, and the 10 planner tests pass. Everything else today supports that sentence.

| Time | A: Platform | B: Planner | C: AI | D: Product |
| --- | --- | --- | --- | --- |
| 10:45-11:45 | Create repo and SAM skeleton; deploy one hello Lambda to prove the pipeline; pick one region; request Bedrock model access; test one Textract call; set a budget alarm | Write fixtures: sample timetable CSV (6 classes, 8 periods, Mon-Fri), a replay forecast for a Stage III day, and ruleset v1 by hand from one real circular | Finish collecting 8-10 real circulars; write the extraction JSON schema file; label rules for the first three | BotFather: create the Telegram bot and token; call one principal or teacher and record the quote; scaffold `web/` |
| 11:45-13:30 | DynamoDB single table and GSI1 in SAM; one least-privilege IAM role per function; EventBridge Scheduler rule for one demo tenant | Write the 10 planner tests (red); build `classify()` with the order-then-forecast hierarchy | Textract on one circular (text layer first, then a scan); extraction prompt v0 with Bedrock tool use and the schema | Static Brief page with fake data: before-and-after grid, reason line, Approve button; CSV upload form stub |
| 13:30-14:15 | Lunch and a 10-minute sync: contracts still hold? |  |  |  |
| 14:15-17:00 | Ingest Lambda (forecast from the replay fixture, grid-cell cache stub); ruleset loader from `RULESET#` | Planner v1: hard-constraint filter, nominal and pessimistic scoring, Plan B activity bank by class band; get all 10 tests green | Validators: schema, verbatim quote, value sanity; run extraction on 3 gold circulars and log every failure | Telegram message with \[Approve A\] \[Approve B\] \[Reject\] from a local script; design the webhook and short-ID scheme |
| 17:00-17:30 | Break |  |  |  |
| 17:30-21:00 | Wire Scheduler to ingest, rules and planner Lambdas; the run writes a `Decision` item to DynamoDB; check CloudWatch logs | CSV loader with row-level errors; expose `plan()` as a Lambda; add edge tests (locked period, busy teacher, ground clash) | Hostile circular fixtures (hidden instruction, invented quote); conflict-detection stub against the active ruleset | Point the Brief page at a stub `GET /decisions` returning the real Plan from DynamoDB; first usability notes |
| 21:00-21:15 | Gate standup |  |  |  |
| 21:15-23:30 | Fix what the gate exposed; commit; record a clip of the scheduled run | Record a clip of the plan output; write tomorrow's tests | Write the failure log from today's extraction runs | Clip of the grid; log what fought back; send the first blog notes |

**Done today means**

- A scheduled invocation, not a manual one, produced a Plan A or Plan B and stored it.
- Ten planner tests pass in CI or locally on every commit.
- Bedrock and Textract access are confirmed, or the fallback is chosen.
- At least one real circular has produced text; one has produced candidate rules.
- A real principal or teacher quote is on file, or the call is booked.

**If behind**

- Bedrock access not granted by 13:00: C continues with Textract and local validators using a recorded model response, A tries a second region, and the writeup states the fallback.
- Planner tests not green by 17:00: B drops Plan B variety and ships one activity per class band; the swap logic comes first.
- Scheduler wiring not working by 21:00: invoke the state input by hand, but keep the Lambda chain. The gate then moves to 11:00 Friday and nothing else starts until it passes.

## Day 2, Fri Oct 9: the real loop

**Gate at 21:00:** one end-to-end run (schedule, brief, Telegram approval, notices, audit row) and one real circular producing a rule-diff with quotes. This is the gate that decides the demo; if it is missed, the fallback is a static versioned ruleset JSON and no second profile or City Board.

| Time | A: Platform | B: Planner | C: AI | D: Product |
| --- | --- | --- | --- | --- |
| 08:00-09:00 | Standup; review yesterday's clip; list today's cuts | Fix any failing test from Thursday | Review the failure log; pick the 3 worst extraction errors to fix first | Review the Brief page with one outsider if available |
| 09:00-12:30 | Step Functions Standard state machine: LoadContext, EvaluateRules, Plan, NoChange, RequestApproval with `waitForTaskToken`, Escalate, FailSafe; approval timeout read from an environment value (60 seconds for the demo) | Make `Plan` return Plan A, Plan B and exposure before and after in the agreed shape; add whole-day revalidation across classes | Pipeline v1: S3 upload event, text layer or Textract, chunk by section, Strands agent with three tools calling Bedrock, validators | Webhook Lambda: check the secret-token header and the chat-ID allowlist; short random IDs for task tokens stored in DynamoDB; `POST /approve/{shortId}` |
| 12:30-13:15 | Lunch |  |  |  |
| 13:15-17:00 | Hash-chain append with `TransactWriteItems` (put `AUD#seq` not-exists, conditional update of `AUDHEAD`) and a concurrency test; audit rows for every state transition | PE minutes preserved calculation from the timetable; teacher schedule generator (new timetable per teacher) | Candidate-rule diff data: added, changed, removed, each with quote and page; ruleset version creation on approval with a content hash, immutable | Brief page on real data: before-and-after grid, reason line with rule ID, forecast chart, Approve buttons; rule-diff screen with the quote highlighted |
| 17:00-17:30 | Midpoint check: can an approval resume a paused execution? If not, stop all else |  |  |  |
| 17:30-21:00 | Draft and Broadcast states: SQS queue, deliver Lambda, retry then DLQ; `CollectAcks`; `AuditClose` | Notice payloads for teachers and parents; static templates in English; hand strings to D for Hindi | Drafting Lambda: Bedrock call with a Catch to the static template; audit flag when the fallback is used | Telegram delivery to teachers; `GET /ack/{shortId}`; connect the Brief page to the live approval; first full dry run with all four people |
| 21:00-21:15 | Gate standup |  |  |  |
| 21:15-24:00 | Fix the dry-run failures; record the end-to-end clip | Edge tests for the planner under the real state machine | Run the pipeline on all gold circulars and save raw output for the eval table | Clip of the Brief, approval and notice; write blog notes |

**Done today means**

- A real Telegram tap resumes a waiting Step Functions execution, and a timeout escalates to the vice-principal, then fails safe with no broadcast.
- The audit log has one row per transition with a valid chain.
- A real circular produces a candidate ruleset and a diff in which every rule carries a verbatim quote.
- An invented quote and a hostile circular are rejected by code.
- Drafting works with Bedrock and falls back to a template when Bedrock is denied.

**If behind**

- Pipeline not producing a diff by 17:00: C stops extraction work and loads a static versioned ruleset JSON; C then helps D with the rule-diff screen using pre-extracted data and the demo says so.
- Midpoint check fails: A and B pair on the approval callback until it works; D keeps the Brief on stubbed approval.
- Hindi strings not ready: ship English notices and mark Hindi as next.

## Day 3, Sat Oct 10: proof, drills and freeze

**Gate at 21:00 and feature freeze:** the verify page recomputes the chain, all three failure drills pass and are recorded, the eval table is measured, and the repository is tagged `v1-freeze`. At 18:00 there is a checkpoint: if the drills are not passing, everything except drills, README and video stops.

| Time | A: Platform | B: Planner | C: AI | D: Product |
| --- | --- | --- | --- | --- |
| 08:00-09:00 | Standup; confirm Friday's end-to-end still runs after overnight changes | Same | Same | Same |
| 09:00-12:30 | CloudWatch dashboard (decisions per hour, approval latency, escalations, DLQ depth, fallback usage, Bedrock errors) and alarms on DLQ depth and Step Functions failures; drill 1: deny Bedrock with an IAM policy and show the template fallback | `POST /rehearse?stage=` that returns the plan for a hypothetical stage with no side effects; replay mode with the "Replay scenario" banner | Eval run on all gold circulars: rule precision, rule recall, quote-validity rate; fix the prompt on the worst cases; run both hostile cases | Public verify page: fetch rows, recompute the hash chain with SubtleCrypto, show valid or broken; receipt QR; WhatsApp click-to-share link per class |
| 12:30-13:15 | Lunch |  |  |  |
| 13:15-17:00 | Drill 2: fire the trigger twice and show one execution and no duplicate messages; drill 3: simulate a Telegram 5xx so SQS retries, the message reaches the DLQ, the alarm fires and the dashboard shows "undelivered" | Stage Rehearsal slider data contract with D; tune the pessimistic delta on the replay set; second profile `outdoor_crew` as config only, time-boxed to 90 minutes | Per-group accuracy (school versus crew) if the crew profile exists; test the Textract scan path; write the eval table into `README.md` | Stage Rehearsal slider on the Brief page; Hindi and English strings; usability test with one outsider; fix the top three confusions |
| 17:00-18:00 | Checkpoint at 18:00: drills passing? |  |  |  |
| 18:00-21:00 | Security pass: no wildcard IAM, webhook checks, cross-tenant read denied, receipts show safe fields only; AWS budget and cost check | README sections: planner, sample data, how to run the tests | README sections: AI pipeline, validators, eval table with limits | Architecture diagram export, README top, blog draft, video storyboard against the demo script |
| 21:00-21:15 | Gate standup and feature freeze; tag `v1-freeze` |  |  |  |
| 21:15-24:00 | Record clips: each drill, console views (Step Functions execution, DynamoDB audit rows, SQS DLQ, CloudWatch alarm) | Clip: Stage Rehearsal and Plan A versus Plan B | Clip: rule-diff, refusal moment, eval table | Clip: Brief, verify page, QR, WhatsApp link |

**P2 items, only if the 18:00 checkpoint is green:** 1,000 synthetic tenants (A; cut at 21:00 if not measured), City Board (D), Standing Order (B and A). Anything not finished at 21:00 is dropped, not carried into Sunday.

**Done today means**

- All three drills have a clip showing cause, system behaviour and the dashboard state.
- The eval table contains only measured numbers, with the size of the gold set printed beside it.
- The verify page shows "broken" when one stored row is edited, and "valid" when it is not. Record both.
- An outsider completed the approval flow without help.

**If behind**

- Drills failing at 18:00: A and B take drill 3 together; D drops the WhatsApp link polish; C writes the README.
- Crew profile needs code: drop it and keep it as a roadmap line.
- Eval set smaller than hoped: publish the real size and say it is a hackathon start, not proof of production reliability.

## Day 4, Sun Oct 11: ship

**Gate: the submission is in by 16:00 and the video opens in a signed-out browser.** The final cutoff time is not published, so 16:00 leaves a safety margin; check the live event page at 08:00 for the real deadline and move this earlier if it says so. No new features today, and no infrastructure deploys after 12:00 except fixes.

| Time | Who | Task |
| --- | --- | --- |
| 08:00-08:30 | All | Standup; read the live event page and rules for the cutoff; confirm the submission form fields |
| 08:30-09:00 | A | Smoke test of the deployed stack end to end; run the demo-school reset so the recording starts clean |
| 08:30-10:30 | D with B and C | Final README: problem, architecture diagram, AWS table, tests, eval table, limitations, AI tools used. B writes the planner part, C writes the AI part |
| 08:30-10:30 | A | Infrastructure notes: how to deploy and tear down with SAM, region, cost check, secrets handling |
| 10:30-12:30 | D leads, all support | Record the video in two takes against the script; capture the console clips again if any are stale |
| 12:30-13:15 | All | Lunch |
| 13:15-14:30 | D | Edit, trim to 2:50 or less, add captions and the "Replay scenario" label; upload where it opens without sign-in |
| 13:15-14:30 | C | Blog on AWS Builder Center: problem, build, where AWS fits, what fought back, measured results, limitations; link the repo and video |
| 13:15-14:30 | A and B | Secret scan of the repository history; rotate the Telegram token after submission; make the repo public; confirm commit history sits inside the event window |
| 14:30-15:30 | All | Review pass: one person watches the video signed out on another device; one person follows the README from a clean clone; fix typos and broken links only |
| 15:30-16:00 | D | Submit: repository, video, writeup, blog link; save the confirmation |
| 16:00 onward | All | Do not change the repository, the video or the blog. If the form allows edits before the cutoff, change only a broken link |

**Recording checklist**

- Say the user aloud in the first 25 seconds: a school principal in Delhi-NCR on a bad-air day.
- Keep three beats: reads the order, re-plans the day, proves it. Then show where AWS fits.
- Show the "Replay scenario" label on screen during the replay.
- Show the AWS console: a Step Functions execution, DynamoDB audit rows, the SQS dead-letter queue and the CloudWatch alarm.
- Hide tokens, keys and account IDs. Check the clips frame by frame for secrets.
- Say the limits in one line: modelled forecast, WhatsApp needs a manual tap, no real pilot yet.

**Submission checklist**

- [ ] Public repository with commit history inside the event window
- [ ] Demo video of 2-3 minutes that opens without sign-in and shows AWS
- [ ] Short writeup: the problem, the build, where AWS fits, limitations
- [ ] Blog on AWS Builder Center linked in the submission
- [ ] Every member registered individually and student status verified
- [ ] One submission per team
- [ ] No secrets in the repository or the video
- [ ] Submitted by 16:00, or earlier if the deadline says so

## Handoffs and gate checks

Most schedule slips on a four-person team come from waiting on another owner's piece, so each handoff below has a deadline and a form. Hand over a stub first, then the real thing.

**Handoffs**

| From | To | What | Stub by | Real by |
| --- | --- | --- | --- | --- |
| C | A, B | Ruleset JSON schema and one hand-made ruleset v1 | Thu 11:45 | Fri 13:15 |
| B | A | `plan()` signature and the `Plan` shape | Thu 14:15 | Fri 12:30 |
| A | D | `GET /decisions` and `POST /approve/{shortId}` | Thu 17:30 | Fri 13:15 |
| C | D | Rule-diff data shape with quote and page | Thu 21:00 | Fri 17:00 |
| A | all | Audit append function and the audit row shape | Thu 17:30 | Fri 17:00 |
| D | B, C | Notice string keys for English and Hindi | Fri 13:15 | Fri 17:30 |
| B | D | `POST /rehearse?stage=` contract for the Stage Rehearsal slider | Fri 21:00 | Sat 13:15 |

A blocked handoff is raised in chat immediately, not at the next standup. If the real handoff is late, the receiver keeps working on the stub and the demo uses the stub only if the real one misses the gate.

**How each gate is verified.** Someone who did not build the piece runs the check, so the work is not grading itself.

| Gate | Check | Evidence saved |
| --- | --- | --- |
| Thu 21:00 | Look at CloudWatch for a scheduled invocation (not a manual one); open the `Decision` item in DynamoDB; run the 10 planner tests | Log link, item screenshot, test output |
| Fri 21:00 | Tap Approve in Telegram and watch the waiting execution resume; let one execution time out and see Escalate then FailSafe; upload a real circular and read the diff; submit a hostile circular and see it rejected | Clip, execution link, diff screenshot |
| Sat 21:00 | Edit one audit row by hand and confirm the verify page reports broken; run all three drills; read the eval table against the raw outputs | Two verify clips, three drill clips, raw eval output |
| Sun 16:00 | Open the video link in a private window on another device; follow the README from a clean clone; confirm the blog link works | Submission confirmation |

**If the whole plan slips by half a day,** keep the gates and move the cuts: drop P2 first, then the second profile, then Stage Rehearsal, then the WhatsApp link polish. Never drop the end-to-end loop, the rule-diff with quotes, the audit chain with its verify page, or the failure drills.
