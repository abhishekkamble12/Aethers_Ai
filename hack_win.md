# hack_win.md: Backend audit and win plan for Saans

Audited Sat Oct 10, 2026, 16:00 IST. Scope: backend only (`services/`, `infra/`, `data/`, `tests/`, the root `verify_*.py` scripts). Measured against the event's judging criteria (idea and impact, built on AWS, design and usability, execution, demo video) and the spec in `Saans winning project document.md`, which this file calls "the spec".

**How this was checked:** I read every backend file. I ran the suite: `.venv/Scripts/python.exe run_all_tests.py` gives 40 tests, all passing, but the script crashes after the run on Windows (see M8). I also ran the planner directly on the demo data at all four stages and on two hand-built edge cases.

**Assumptions:**
- The SAM stack has never been deployed successfully. There is no `samconfig.toml` or `.aws-sam/`, and the packaging bug in M1 makes every Lambda fail on import.
- The deadline is Sun Oct 11. The exact cutoff isn't published, so the target is **submit by 16:00 Sunday**.
- The team has 4 people with the A/B/C/D roles from the spec.

---

## 0. Live on AWS (Sat Oct 10, 17:50 IST)

> **Deployed:** stack `saans` in **us-east-1** (profile `Abhi`, an IAM user, not root), 33 resources. API: `https://367bcz1ry5.execute-api.us-east-1.amazonaws.com/Prod/`. The region changed from ap-south-1 because us-east-1 has Nova on demand and the billing metrics.
> **First real run:**
> - Trigger → execution `TENANT_demo_2026-10-12_MORN` **SUCCEEDED** (LoadContext → RequestPrincipalApproval → UsePrincipalAnswer → DraftAndDispatchNotices → AuditCloseApproved).
> - `GET /decisions` showed `AWAITING_PRINCIPAL` with the approval link. `POST /approve` (Plan B) returned 200; replaying the link returned 410.
> - `GET /receipts/0iILY1AMCHHG`: 5 rows, server verdict valid. `GET /verify/...` returned 200 HTML.
> - A second trigger returned `duplicate_suppressed` (existing SUCCEEDED). Bad stage gave a 400 JSON error. `/decisions` without the key gave 401.
> - The audit chain on AWS shows every notice as `STATIC_TEMPLATE_FALLBACK, fallback_used: true` (Bedrock unavailable), the forecast as `is_replay: true`, and stricter limits for 3 classes.
> - **Status upgrade:** M1, M2a, M2b, M3a and M3b are now **DONE (deployed and verified on AWS)**.
>
> **Final Features Deployed & Verified (Sun Oct 11, 00:35 IST):**
> - **F3 (Hourly Forecast Chart API - `GET /forecast`):** Deployed to AWS (`ForecastFunction`). Returns 48h CAMS forecast with product thresholds, advisory/restricted crossing detection, and DynamoDB hourly cache (`PK=GRID#...#H48`, `SK=FCST`). Validated live via `curl`.
> - **F2 (Forecast Watch & `GET /watch`):** Deployed to AWS (`WatchFunction` EventBridge cron daily 16:30 IST + `WatchApiFunction` `GET /watch`). Evaluates next 2 school days, drafts contingency plans, stores `WATCH#{date}` with TTL, appends `CONTINGENCY_DRAFTED` hash-chain audit row on new `act` risk, and requires `x-saans-admin-key`. Validated live with 2 evaluated watches.
> - **F4 (Honest Parent Sentence): PARTIAL until redeployed.** `services/notify/drafting.py` computes `indoor_air_reduction_pct_modelled` (works) and `classes_with_stricter_limits`. The second one was always 0 on the deployed stack because it read a top-level `sensitivity` key the planner never returns, so the teacher sentence never appeared. Fixed locally on Oct 11 (counts distinct classes in `decision_trace[].sensitivity`, 3 on the demo data) with regression tests in `tests/test_review_regressions.py`. Mark DONE after the next deploy shows the sentence in a live NOTICES_DRAFTED run.
> - **Test Suite Gate:** full suite passing (`run_all_tests.py`). Count at the Oct 11 review fixes: 193.
>
> **Review fixes (Sun Oct 11, local, tested):**
> - `scripts/test_live_api.py` no longer hardcodes the admin key. It reads `SAANS_ADMIN_KEY`, `ADMIN_API_KEY` or `infra/deploy.secrets`. The key never reached a commit. **Rotate it after the event anyway.**
> - F2 watch `plan_summary` was always zeros (read `problematic_periods`, `plan_a_swaps`, `plan_b_fallbacks`, which the planner doesn't return). Now reads `classified_periods`, `plan_a`, `plan_b`.
> - The hand-built replay scenario was labelled `SAFAR-IITM-Ensemble`. It is now labelled as an illustrative scenario, not a model forecast.
> - `GET /watch` promote hint pointed at `POST /workflow/trigger`, which doesn't exist. It now gives the Trigger Lambda name (`TRIGGER_FUNCTION_NAME`) and one valid payload per `act` date.
>
> **Bedrock spike: BLOCKED.** All Nova models return `ValidationException: Operation not allowed`. Cause: the account is on the AWS **Free plan** (`accountPlanType: FREE`, $149.61 credits), and the Nova Lite on-demand quota is **0** tokens and 0 requests per minute. The fix is the owner's decision: upgrade to the Paid plan (credits carry over). Until then X1 and M4 can't produce real model output, and notices use the labelled static fallback.
> **Billing safety:** an existing "My Zero-Spend Budget" emails on any spend. AWS/Billing metrics aren't available yet, so no separate CloudWatch billing alarm was added.

## 1. Verdict

| Criterion | Score | Evidence |
|---|---|---|
| **Impact** | **6/10** | The problem is real and well framed: a real DoE circular in `data/gold/circular_real_caqm.txt`, the spec's CAQM and DoE timeline, and an order-first hierarchy in `rules_engine.py`. But the backend does not deliver the outcome end to end. No decision is persisted past one row, no notice reaches anyone, and the approval loop cannot run on AWS. The impact numbers in the README ("400,000 children protected") come from `tenant_scale_sim.py`, which hardcodes them. |
| **Execution** | **3/10** | The pure functions work and are tested (40/40). Every deployed path is broken: Lambda packaging (M1); the state machine is not in the template, and its `LoadContext` expects a shape the planner doesn't return (M2); approval tokens live in process memory (M2); the receipt API returns a hardcoded chain (M3). All three "drills" are in-process simulations with fake ARNs (`drills_simulator.py:131`). The planner has a confirmed teacher double-booking bug (M6). |
| **Design** | **5/10** | The principles are excellent: code decides and the model proposes, stage bans are never relaxed by a clean forecast, single-table keys, idempotency by decision ID. The implementation doesn't follow them. Approver identity is read from the request body (`workflow/handler.py:51`). The Telegram secret check never fires behind API Gateway (`:34`). The audit "chain" is always `seq=1` from genesis and is overwritten on each run (`planner/handler.py:423`). There's no IAM for Bedrock, no CORS, and `/notifications/dispatch` is public and unthrottled. |
| **Innovation** | **6/10, could reach 8** | Quote-verified rule extraction, "re-plan, don't cancel", and public hash-chain receipts are genuinely uncommon among AQI projects. But the AI half **does not exist**. Nothing calls a model to extract rules: `eval_runner.py:261-303` hand-writes the "extracted" rules. The "refusal" is a 5-string blocklist (`validator.py:15`). Make it real and this becomes the most memorable part of the project. |

**Summary:** Saans has the best *idea* and the best *spec* most judges will see this round, and a clean, deterministic, well-tested core (`rules_engine.py`, `planner.py`, `hash_chain.py`, `validator.py`). But under a code review it is mostly a **local simulation presented as a deployed AWS system**:
- No model reads a circular.
- No Step Functions execution can run.
- The receipt proves a hardcoded 3-row chain.
- The drills simulate their own failures.
- The headline metric, "PE minutes preserved 100%", is true by construction.
- The UI's Stage Rehearsal calls a TypeScript mock (`app/api/rehearse/route.ts`), not the Python planner.
- The demo script (`docs/DEMO_VIDEO_SCRIPT.md`, Beat 1) narrates "Bedrock and Strands Agents" processing the circular, which is not implemented. The rules say features that only appear in the writeup or narration don't count.

The fix is not a rewrite. It is about 10 targeted changes that make **one real decision run on AWS end to end**: plan, then approval, then a drafted notice, then a persisted chain, then a verifiable receipt. Add a real Bedrock extraction with the refusal moment, and keep every number honest. Do that and this is a strong contender for the Air track.

### Idea positioning: strong idea, one exposed flank

The idea is good enough to win. It acts rather than displays, it has a named user (a Delhi-NCR principal), it's grounded in real GRAP and DoE process, and it has three hooks. The idea is not the main risk. The risk is the question a judge will ask once they see the Stage III plan:

> *"On a bad-air day every outdoor period just becomes an indoor session. A principal can do that with one WhatsApp message. Why do I need this?"*

Our own run proves the premise: at Stage III and IV the planner makes **0 swaps and 6 Plan B fallbacks**. Swaps only happen when the order permits outdoor activity and the forecast decides (Stage I–II). Four positioning fixes, each tracked as a task below:

| # | Fix | Where it lands | Owner |
|---|---|---|---|
| P1 | **Reframe the pitch around interpretation and proof, not timetable maths.** The value is that the circular becomes a compliant, approved, communicated and provable plan in under 60 s. The evidence is CAQM's Dec 2025 letter that schools *still* held outdoor sports, so the problem is follow-through and accountability. The planner supports that story; it isn't the headline. | README top, writeup, video 0:00–0:25 narration | D |
| P2 | **Show two days, not one.** Day 1 is a **Stage II replay** where the forecast drives a real swap (PE moved to a cleaner afternoon slot, with the explanation from U2). Day 2 is **Stage III**, where the order forces Plan B with an active indoor session and the rule quote. The current `forecast_stage3_sample.json` has Severe-level PM2.5 (210–395) and is the wrong fixture for a Stage II day. Add `data/demo/forecast_stage2_sample.json` with a realistic profile: a morning peak above `restricted_at` (120) and afternoon periods below `advisory_at` (90) under the pessimistic +20%. Verify that the planner produces at least 2 swaps on it and add that as a test. | `data/demo/`, `tests/test_planner.py`, video 1:00–1:55 | B |
| P3 | **Get one real quote from a principal, PE teacher or class teacher**, today. Ask: *"When the GRAP circular arrives, how do you find out, what do you do with PT that day, and who checks?"* One sentence in the video and README turns "we assume schools struggle" into evidence. If nobody is reachable by Sun 09:00, drop all claims about how schools behave and cite only the CAQM letter. | video 0:00–0:25, README Problem section | D |
| P4 | **Scope claims honestly.** Say "Delhi-NCR schools on GRAP days, mostly Nov–Jan", the time-boxed problem it is. Don't say "solves Delhi's air" or "protects 400,000 children". Say the engine is rule-driven data, so other states' orders are new rulesets, not new code. That's true of `rules_engine.py`, and it's the scale story. | README, writeup | D |

---

## 2. Must-fix (blocks winning), in priority order

### M1. Lambda packaging: nothing imports on AWS (≈45 min, owner A)
> **Status: PARTIAL (code done; not yet deployed).** Evidence: `python -m unittest tests.test_lambda_bundle` builds `infra/.lambda_src` and imports all 5 template handlers with only the bundle on `sys.path` (the old layout raises `ModuleNotFoundError: No module named 'services'`). Every handler was also invoked from the bundle alone and returned 200 (approval's 410 is M2). Full suite: 43/43 OK. **Not done:** `sam build`/`sam deploy` (SAM CLI isn't installed on this machine, and deploying needs your go-ahead). Change from the plan: the build script is Python (`scripts/build_lambda.py`), not bash, so it runs on Windows.
- **Problem:** `infra/template.yaml` sets `CodeUri: ../services/planner/` (and similar), but every handler imports `services.<pkg>...` and `planner/handler.py:_get_demo_fixtures` reads `data/demo/*`. Neither is inside the zipped folder, so you get `ImportModuleError` on cold start for all 5 functions.
- **Fix:**
  1. Add `scripts/build_lambda.sh`. It deletes and recreates `infra/.lambda_src/`, copies `services/` and `data/demo/` and `data/gold/` into it, and writes an empty `requirements.txt` (boto3 is in the runtime). Add `infra/.lambda_src/` to `.gitignore`.
  2. In `template.yaml`, put `CodeUri: .lambda_src/` in `Globals.Function` and use fully qualified handlers, for example `Handler: services.planner.handler.lambda_handler`, `services.workflow.handler.approval_handler`, and so on.
  3. Add `Globals: Api: Cors: {AllowOrigin: "'*'", AllowHeaders: "'Content-Type'", AllowMethods: "'GET,POST,OPTIONS'"}`. Today a browser POST with JSON fails the preflight.
  4. Exit test: `sam build && sam deploy --guided` (region ap-south-1), then `curl -X POST $API/rehearse -d '{"stage":"III"}'` returns a plan.

### M2. Make the approval workflow real (≈4 h, owners A and D)
> **M2a status: PARTIAL (code done and tested locally; not deployed).** Evidence: `python -m unittest tests.test_approval_flow` passes 19/19 against moto DynamoDB (single-use links, expiry, role from token not body, 409 when the window closed, 502 that keeps the link usable, no internals leaked). A local chain run (plan → RequestApproval → GET /decisions → POST /approve → replay gives 410) passes. `sam validate --lint` and `sam build` succeed; the template has 29 resources, including `AWS::StepFunctions::StateMachine`. Full suite 62/62. Moto caught a real bug before deploy: `consumed` is a DynamoDB reserved word. **Pending:** deploy and a real execution (needs the AWS profile).
> **Also pulled forward from M7:** approver identity comes from the token, and there's no default action. **Removed:** the Telegram check that never ran behind API Gateway and the hardcoded chat-ID allowlist (X1 adds `/callbacks/telegram` properly). **Interim:** `AuditFunction` only logs (`persisted: false`) until M3.
> **M2b status: PARTIAL (code done and tested locally; not deployed).**
> - **Escalation path:** both answers are normalised into `$.final_approval` by Pass states. Evidence: on the M2a definition, "principal timeout, VP approves B" fails with `States.Runtime: path $.approval_result not found`; on the new one it ends in `AuditCloseApproved`.
> - **Fail-safe outcomes are separate:** `REJECTED_NO_BROADCAST` (with role), `FAILSAFE_TIMEOUT_NO_BROADCAST`, `WORKFLOW_ERROR_NO_BROADCAST` (catches errors in the approval and notify steps). Transient Lambda errors are retried.
> - **Idempotency:** `TriggerFunction` (now owns the schedule) names each execution after the decision ID and looks it up first, because StartExecution returns success for a running duplicate. Moto test: 2 triggers give 1 execution, and the second reports `duplicate_suppressed`.
> - **Tests:** `tests/test_workflow_paths.py` passes 14/14 (8 paths through an ASL interpreter, plus trigger tests). Full suite 76/76. `sam build` OK, 31 resources.
> - **Pending:** a real execution on AWS (needs the profile).
The state machine in `services/workflow/state_machine.json` is not deployed (there's no `AWS::Serverless::StateMachine` in the template) and would fail if it were.
- **Add to `template.yaml`:**
  - `SaansWorkflow: Type: AWS::Serverless::StateMachine` with `DefinitionUri: ../services/workflow/state_machine.json`.
  - `DefinitionSubstitutions` for `IngestPlannerFunctionArn`, `RequestApprovalFunctionArn`, `NotificationFunctionArn` and `AuditFunctionArn`.
  - `Policies: [LambdaInvokePolicy x4]`.
  - Replace the `Schedule` event on `IngestPlannerFunction` with a `Schedule` event on the **state machine**, so the scheduler starts the workflow rather than a bare Lambda.
- **`planner/handler.py:lambda_handler`:**
  - Return a plain dict `{"decision": plan_result, "audit_head": ...}` when invoked by Step Functions (that is, `"httpMethod" not in event`).
  - Keep the API Gateway envelope only for HTTP calls. Right now `ResultSelector "$.Payload.decision"` fails with `States.Runtime`, because the payload is `{"statusCode","headers","body":"<string>"}`.
- **Split approval into two functions:**
  - **New `RequestApprovalFunction`** (`services/workflow/request.py`), invoked with `$$.Task.Token`. It generates `short_id = secrets.token_urlsafe(6)` and writes `PK=TOKEN#{short_id}, SK=META, task_token, decision_id, tenant_id, role ("principal" or "vice_principal" from the `escalation` flag), ttl=now+600` to DynamoDB. It returns nothing; the brief link is `GET /decisions/{decision_id}`. Telegram is optional, see the cut list.
  - **`ApprovalFunction` (`workflow/handler.py`)** reads `TOKEN#{shortId}` from **DynamoDB** with a conditional `UpdateItem SET consumed=true IF consumed=false AND ttl > now`. Today it reads `workflow_registry`, an in-memory dict that is empty in every fresh Lambda container, so every real call returns 410.
- **State machine JSON:**
  - The `DraftAndDispatchNotices` payload uses `"approval.$": "$.approval_result"`, which doesn't exist on the escalation path, so the run errors. Add a `Pass` state in each branch that normalises to `$.final_approval`.
  - Give `FailSafeNoBroadcast` a distinct `event` for "rejected" versus "timed out". Today a rejection is logged as `FAILSAFE_TIMEOUT_NO_BROADCAST`.
  - Make the approval timeout `${ApprovalTimeoutSeconds}` (60 for the demo).
- **Idempotency (this is also drill 2, done for real):** start executions with `name = decision_id` with `#` replaced by `_`. A second start with the same name returns `ExecutionAlreadyExists`. Show that in the console.

### M3. Make the audit chain an actual chain (≈2.5 h, owner D)
> **M3a status: PARTIAL (code done and tested locally; not deployed).**
> - **Store:** `services/audit/store.py:append_audit` does one `TransactWriteItems`: `AUD#n` if not exists, `AUDHEAD` only if `seq = n-1`, and an optional `AUDKEY#` so retries can't log twice. On conflict it re-reads the head and retries.
> - **Wired in:** planner (`PLAN_GENERATED`, which records the stage, ruleset version and SHA-256, the forecast snapshot with `is_replay`, and plan/timetable digests), `APPROVAL_REQUESTED`, `APPROVAL_RECEIVED` (role from the token), `NOTICES_DRAFTED` (per notice: `model_used`, `fallback_used`, text SHA-256), and the 5 terminal workflow events. The always-row-1 genesis write and the M2a log-only stub are gone.
> - **The verifier now also re-checks each stored payload against its digest.** Before, an edited payload passed verification.
> - **Evidence:** `test_audit_store` 9/9 (a real 4-thread race with 7 retried conflicts gives a gapless chain of 20; editing a row is detected at its seq; editing a payload is detected; history can't be overwritten). `test_audit_wiring` 6/6 (real handlers driven through `state_machine.json` write a 5-row chain that verifies, short IDs and task tokens never enter it, and a retried audit doesn't double-log). Full suite 91/91; `sam build` OK.
> - **Limitation to state honestly:** someone with write access who rewrites *every* row from some point onward, recomputing the hashes, isn't detectable from the chain alone. Publishing the head hash on each notice and receipt (the QR) is what pins it. Moto's `transact_write_items` isn't thread-safe, so the race test serialises each transaction to stand in for DynamoDB's atomicity.
> **M3b status: PARTIAL (code done and tested locally; not deployed).**
> - **Receipts:** an opaque 12-character receipt ID is issued per decision at planning time. `GET /receipts/{id}` returns the tenant's real chain from DynamoDB in the frontend's `AuditBlock` shape, plus `payloadJson` (the exact bytes the digest covers), the rows for this decision, the head hash and the server's verdict. `DEMO_CHAIN` is deleted. Guessable `tenant#date` IDs are rejected (400), unknown IDs get 404.
> - **New `GET /verify/{id}`:** a standalone page served by the API with a strict CSP. It recomputes every row hash and payload digest in the browser (no fake fallback without WebCrypto) and has a labelled "simulate tampering (local copy only)" button.
> - **Hash input** now uses the browser verifier's field names (`actor, eventType, payloadDigest, sequence, timestamp`), so the existing frontend `lib/crypto.ts` verifies real rows unchanged.
> - **Evidence:** `test_receipts` passes 7/7, including running the **unchanged** `lib/crypto.ts verifyAuditChain` and the page's own `<script>` under Node against a backend-written chain (valid; editing row 3 is detected at #3). There's a new contract test that LoadContext only selects fields the planner returns. Full suite 99/99; `sam build` OK; 34 resources.
> - **Frontend status (not changed, it's your call):** the Next verification page still verifies the mock `auditChain` from the Zustand store, and `web/verify.html` uses an incompatible pipe-joined hash over an in-page array. The real demo uses `GET /verify/{id}`. Wiring the Next page needs a fetch of `${NEXT_PUBLIC_API_URL}/receipts/${id}` passing `blocks` to the existing `verifyAuditChain`, and removing its non-cryptographic fallback hash in `lib/crypto.ts`.
- **Problem:** `planner/handler.py:423` always creates `seq=1, prev_hash=GENESIS` and `put_item`s `AUD#000001`, so every run overwrites it. `audit/handler.py:116` serves a hardcoded `DEMO_CHAIN`. The "Proves it" beat currently proves nothing.
- **Fix:**
  1. Add `services/audit/store.py: append_audit(table, tenant_id, actor_role, event, payload)`:
     - Read `AUDHEAD` (seq, hash). Build the row with `create_audit_row(seq+1, head_hash, ...)`.
     - Write with `TransactWriteItems`: a `Put` of `AUD#{seq:06d}` with `attribute_not_exists(SK)`, plus an `Update` of `AUDHEAD` with `ConditionExpression seq = :prev` (create it with `attribute_not_exists` for the first row).
     - On `TransactionCanceledException`, retry 3 times. This is exactly what the spec describes, and it is not implemented.
  2. Add `AuditFunction` (`services/audit/handler.py:audit_append_handler`) for the state machine's `${AuditFunctionArn}` states.
  3. Call `append_audit` from the planner (`PLAN_GENERATED`, with the payload digest of the full plan), the approval handler (`APPROVED_PLAN_A/B` with role, never a name), notify (`NOTICE_DRAFTED`, with `model_used` and `fallback_used`, which the spec requires and is missing today) and fail-safe.
  4. `receipt_handler`: `Query PK=TENANT#{t}, begins_with(SK,"AUD#")` and return only the fields used in the hash (already PII-free). Delete `DEMO_CHAIN`.
  5. Point `web/verify.html` (or `app/api/verify/[receiptId]`) at `GET /receipts/{id}` so the browser recomputes the **DynamoDB** chain.
  6. Add a test, `tests/test_audit_store.py`, using a fake table (dict plus condition checks) that covers concurrent appends and tamper detection.

### M4. "Reads the order" must be real, or must come out of the video (≈4 h, owner C)
- **Problem:** No model call extracts rules (grep for `bedrock` in `services/circular` returns nothing). `eval_runner.py` hand-writes `school_rules` and then scores them against the validator. `precision` and `recall` use the **identical formula** (`eval_runner.py:344-345`), and `per_group_accuracy` is a hardcoded 100.0 (`:369`). It also accepts `r-019`, whose quote ("Morning assemblies… indoors") does not support its action (`outdoor_sports: banned`), and `r-018` (a hybrid-mode quote, but the action is an outdoor-sports ban). A judge reading `eval_table.json` will see "100%" everywhere on one circular and stop trusting every other number.
- **Fix:**
  1. Add `services/circular/extractor.py: extract_candidate_rules(text) -> list[dict]`.
     - Use `bedrock-runtime.converse` (not `invoke_model`) with a system prompt containing the rules from the spec's "Extraction prompt rules", and the circular inside `<document>` tags as untrusted data.
     - Use tool-use or JSON output matching `data/gold/ruleset_schema.json`.
     - Model: Nova Lite. In ap-south-1 it likely needs the `apac.` inference-profile ID, so verify in the console. Grant `bedrock:InvokeModel` and `bedrock:Converse` in the template.
     - Optional, and worth it for the "AWS open source" box: wrap this in a **Strands Agents** `Agent` with exactly 3 tools (`read_chunk`, `read_active_ruleset`, `submit_candidate_rules`). That matches the spec, and your commit `e309b0e` already says "strands agent". If time is short, do the plain `converse` call and **remove Strands from the video and README**.
  2. In `validator.py`, add a **support check**: an action key must be justified by its quote. `outdoor_sports`/`outdoor_pt` require `sport|physical education|PT|outdoor` in the quote, and `hybrid_mode` requires `hybrid|online`. Unsupported action keys are rejected with `"REFUSED (Action not supported by quote)"`. That gives the video a third refusal, from **the model over-reaching**, which is far more convincing than a keyword blocklist.
  3. Keep `INJECTION_PATTERNS` as a signal, but make the real defence the structure: the model has no write tools, every rule needs a verbatim quote, and the support check is in code. A rephrased injection ("Kindly disregard the earlier guidance…") passes the blocklist today. Say so, and show that the quote and support checks still stop it.
  4. Rewrite `eval_runner.py`:
     - Run the extractor on every gold circular and match the output to **hand-labelled** `data/gold/labels/*.json` by `(action key, stage, quote)`.
     - precision = matched / extracted, recall = matched / labelled.
     - Print `n` beside every metric. Record raw model output in `data/gold/runs/` so the numbers are reproducible.
     - Add at least 3 more real circulars (CAQM Stage IV direction, DoE Dec 2025 hybrid order, DoE Nov 2025 outdoor halt) if they can be fetched as text. Otherwise publish `n=1` and say so.
  5. Rename `circular_real_caqm.txt` to `doe_circular_40_2025.txt`, since it is a DoE circular, and **diff it against the real PDF** at edudel.nic.in (listed in the spec). If any sentence was paraphrased, the "verbatim quote" claim is false at the source.
  6. **If the extractor isn't working by Sunday 09:00:** cut "reads the order" to "validates a ruleset": show the validator rejecting the two hostile fixtures, and change the narration to "rules are hand-entered from the circular and validated by code; model extraction is next".

### M5. Make every number honest (≈1.5 h, owner B)
> **Status: DONE locally (tested; deploys with the rest).**
> - **PE minutes:** `pe_minutes` is measured per decision (scheduled / unchanged / moved_to_cleaner_slot / replaced_indoor_active / lost). `pe_minutes_preserved` is now the share kept *physically active*. The indoor bank holds only physical sessions (chess, carrom and lectures removed); a seated item counts as lost. PE detection uses exact subject names ("Speech", "Optics" no longer count).
> - **Notices:** they state only plan facts (`facts`). The Bedrock prompt no longer asserts "100% preserved". The fake `saans.delhi.gov.in` ack and roster links are replaced by our own `{PUBLIC_BASE_URL}/verify/{receipt_id}`, with no link if either is missing. The date comes from the decision instead of a hardcoded default.
> - **Removed:** `tenant_scale_sim.py` and the "400,000 children" / "Mathematically proven" README claims.
> - **Eval** now says it measures the validator only (n=1 circular, 3 hand-entered rules) and reports the gap it finds: 2/3 accepted rules have a quote that doesn't support the action.
> - **Also done (from M7):** the public `/notifications/dispatch` route is removed. That also broke a CloudFormation dependency cycle; the approval role now references the state machine by its fixed name.
> - **Evidence:** `test_honest_numbers` 11/11; full suite 121/121; `sam validate --lint` and `sam build` OK.
> - **Frontend still contains `saans.delhi.gov.in`** in `app/privacy/page.tsx`, `components/real-time/NotificationCenter.tsx`, `components/verification/ReceiptDisplay.tsx`, `web/index.html` and `web/verify.html`. That's for the frontend owner to remove before recording.
- **`planner.py:326-348`, `pe_minutes_preserved`:** unaffected + swapped + fallback always equals the original, so it is 100% by construction at every stage. It also counts "Sports Nutrition & Recovery Lecture" and "Sports Psychology Audio-Visual Session" (`DEFAULT_INDOOR_ACTIVITIES`) as preserved activity.
  - Replace it with three measured fields: `pe_minutes_outdoor_retained` (swapped into a safe slot), `pe_minutes_active_indoor` (Plan B activities tagged `active: true`) and `pe_minutes_lost`.
  - Remove the lecture items from the bank, or tag them `active: false`.
  - The headline becomes "**X of Y PE minutes kept active**". It's still strong, and it's true.
- **`planner.py:150-155`, `original_pe_minutes`:** this uses substring matches for `"pe"` and `"pt"`. `"Speech"`, `"Optics"` and `"Experiment Lab"` all count as PE (verified). Use the `outdoor` flag plus an exact subject set `{"physical education","pe","pt","games","sports"}`.
- **`notify/drafting.py:290`:** the Bedrock prompt hardcodes `"100% of physical education minutes have been preserved"`. Pass the real field. The spec says every fact must map to a plan field.
- **`notify/drafting.py:350,392`:** `ack_base_url="https://saans.delhi.gov.in/ack"`. This is a **government domain you don't own**, and it goes into WhatsApp messages. Replace it with your own API Gateway or CloudFront URL from an env var `PUBLIC_BASE_URL`. Implement `GET /ack/{shortId}` (it writes `ACK#{decision}#{hmac}`) or drop the ack link.
- **`services/drills/tenant_scale_sim.py`:** delete it, or rename it `key_partition_demo.py` and strip `total_delhi_students_protected` and `total_student_exposure_hours_avoided`. Those are `count × 400` and `160 × 400`, invented constants. Remove "400,000 children protected" and "Mathematically Proven Correctness" from README lines 21, 31, 35 and 219. The spec's own "Claims to avoid" section forbids both.
- **`data/gold/eval_table.json`:** regenerate it from M4. Never hand-edit it.

### M6. Planner correctness (≈2 h, owner B)
> **Status: DONE locally (tested; deploys with the rest).**
> - **Double-booking:** each candidate swap is simulated on a copy of the day (subject, teacher, venue and outdoor actually move) and rejected if it creates any clash the input didn't already have. The stale index is gone. Audit repro: OLD swaps leave `T_M` in X and Y at P1; NEW picks the next valid slot and the final day has 0 clashes.
> - **Whole-day revalidation** fails closed (reverts the latest swaps to Plan B, reported in `revalidation`).
> - **Day:** the handler plans the weekday of the date; Sunday gives `confirmed_no_change` with "No classes scheduled on Sunday."
> - **Rules:** they bind only the `class_band` and `applies_to` they name.
> - **Demo CSV:** 3 input clashes fixed (T_CS1 P7, T_LIB1 P8, Ground_A P2). Remaining input clashes are reported in `input_conflicts`.
> - **Explainability (core of U2, pulled forward):** `decision_trace` gives each intervention's rule IDs and quote, the forecast used, and every candidate period with `chosen`/`rejected` and the exact reasons.
> - **Evidence:** `tests/test_planner_m6.py` 11/11; the 13 original planner tests still pass unchanged; full suite 110/110; `sam build` OK.
- **Confirmed bug, teacher double-booking after swaps:**
  - `planner.py:291-294` updates the index for the PE teacher only. The **indoor partner's teacher** moves into the original period, but `teacher_index` is never updated.
  - Repro: class X has PE at P1 and Math (T_M) at P2; class Y has PE at P1 and Math (T_M) at P5. The planner swaps both, so T_M teaches X and Y at P1.
  - Fix: after a swap, set `teacher_index[(indoor_teacher, orig_prd_id)] = cls_id` and clear `(indoor_teacher, target_prd_id)`. Store `{cls}` sets instead of a single class string, so input clashes aren't overwritten silently. Add the repro as test 11.
- **Whole-day revalidation** (spec test 6) is not implemented. Add `validate_day(final_grid) -> list[conflict]` at the end of `plan_schedule`. Fail closed: if there's a conflict, undo the last swap and use Plan B for that period.
- **Day is ignored:**
  - Indexes key on `(teacher, period)` and lookups on `(class, period)`. A Mon–Fri CSV (which `csv_loader` accepts) produces cross-day swaps (verified: 5 swaps and 7 fallbacks on a two-day copy of the demo).
  - Fix: add a `day` parameter to `plan_schedule`, filter `timetable` to that day first, and derive the day from `date` in the handler.
- **Input clashes:** the demo CSV itself double-books `T_CS1` at P7 (7A and 8A) and `T_LIB1` at P8 (6A and 10A). Add a teacher clash check to `csv_loader.load_timetable_csv` that returns row-level warnings, and fix the CSV.
- **Unused fields:** `rules_engine.classify_period` ignores `class_band` and `applies_to`. A primary-only rule (`r-018`) applies to class 10A. Filter by `get_class_band(class)` before matching.

### M7. Approval authorisation (≈45 min, owner D)
- **`workflow/handler.py:51`:** `approver_id = body.get("approver_id", "principal_delhi_demo")`. Anyone can approve as the principal by omitting the field. Derive the role from the token record (`role` from M2), never from the body.
- **`:50`:** the default `action="APPROVE_PLAN_A"`. Require an explicit action and return 400 otherwise.
- **`:34`:** `if "update_id" in event` never fires behind API Gateway, because Telegram's `update_id` sits in `event["body"]`. The test (`test_security_isolation.py:33`) puts it at the top level, so it passes. Parse the body first, or put the Telegram webhook on its own route, `/callbacks/telegram`, that always checks the header.
- **`:61`:** with no `shortId`, the handler returns `200 "success"` and does nothing. Return 400.
- **`template.yaml:127`:** `/notifications/dispatch` is a public, unauthenticated route that invokes Bedrock, which is a cost-abuse vector. Remove the `Api` event, since only the state machine needs it, and add `MethodSettings` throttling on the API.

### M8. One-command test run (5 min, owner A)
> **Status: DONE.** `run_all_tests.py` reconfigures stdout/stderr to UTF-8. Under `PYTHONIOENCODING=cp1252` it now prints `ALL 131 TESTS PASSED` and exits 0 (it used to crash after the run with exit 1).
- `run_all_tests.py:28` prints `✅`, which crashes on Windows cp1252 **after** the tests pass, so the exit code is 1. Add `sys.stdout.reconfigure(encoding="utf-8")` at the top, or use ASCII.
- `pytest` isn't installed in `.venv`, so either add it to a `requirements-dev.txt` or document `python run_all_tests.py`.

---

## 3. High-impact upgrades (only after M1–M3 are green)

| # | Upgrade | Where | Effort | Judge impact | Risk |
|---|---|---|---|---|---|
| U1 | **Real forecast ingest.** Add `services/forecast/ingest.py`. It fetches the Open-Meteo Air Quality API (`hourly=pm2_5`, CAMS model, free, no key) for the school's lat/lon. It maps hourly values onto periods by start time and computes `pm25_pessimistic = nominal × 1.2`. It caches `GRID#{cell}#{date}/FCST` with a TTL. If the fetch fails or the data is older than 6 h, it **falls back to `data/demo/forecast_stage3_sample.json` with `is_replay=true`** and writes an audit event `FORECAST_FALLBACK_REPLAY`. The handler then uses the cached forecast instead of the fixture. | new file, plus `planner/handler.py:_get_demo_fixtures` | 2.5 h | High: kills "it's all fixtures" | Low. October air may be clean, so keep the replay for the Stage III video beat and show live data in the health check. Confirm the API response shape before building on it. |
| U2 | **Explainable decisions.** For each problematic period, return `candidates: [{period, verdict, reason}]`, where reason is one of `teacher_busy(T_X in 8A)`, `ground_booked(Ground_A by 9A)`, `fails_pessimistic(P6 312 ≥ 120)`, `no_exposure_gain`, `locked`. Collect these at each `continue` in `planner.py:236-263`. | `planner.py` | 1.5 h | High: answers "why did it do that?" in one JSON field, and the UI can show it | Very low |
| U3 | **Make Stage Rehearsal differ at every stage.** Today I and II give identical plans, and so do III and IV (verified). Add rules **from real text only**: Stage IV hybrid for classes up to IX and XI (the DoE Dec 13, 2025 order in the spec) as `class_mode: hybrid`, which marks those classes "online, no PE" in the plan. Optionally, a Stage II "advisory: avoid strenuous" rule if a source supports it. | `data/demo/ruleset_v1.json`, `rules_engine.py` | 1.5 h | Medium-high: the slider is a planned video beat | Medium. Don't invent a quote; if there's no source text, skip it. |
| U4 | **Anchor the head hash in S3 Object Lock.** Add a bucket with `ObjectLockEnabled: true` in governance mode with a 1-day retention. `AuditCloseApproved` writes `anchors/{tenant}/{date}.json = {seq, head_hash}`. The verify page shows "anchor matches head". This turns "tamper-evident against outsiders" into "tamper-evident against us, the operators". | `template.yaml`, `audit/handler.py` | 1.5 h | High: memorable, and only works because of AWS | Low. Use governance mode, not compliance mode, so you can delete it after the hackathon. |
| U5 | **Real drill 1 (model denied).** Remove the `bedrock:InvokeModel` statement from `NotificationFunction` via a parameter `BedrockEnabled=false`, run the workflow, and show the audit row `NOTICE_DRAFTED {fallback_used:true}`. Then delete `drills_simulator.py` drills 1–3 from the video (keep the tests if you like, renamed to say "simulated"). | `template.yaml` | 30 min, after M2 and M3 | Medium: a real failure beats a printed one | Low |
| U6 | **Health endpoint** `GET /health`. It reports DynamoDB reachable, active ruleset version and hash, forecast freshness and replay flag, Bedrock reachable (one cached `converse` ping), and audit head seq and hash. | `services/health/handler.py` | 45 min | Medium: a great 5-second shot | Very low |
| U7 | **Morning re-check diff.** Run the planner at 07:00 with fresh forecast, compare `classified_periods` labels with the evening decision, and start a "revised proposal" execution only if any label changed. | `planner/handler.py` | 2 h | Medium | Medium. Do it only if everything above is done. |

---

### X-factor upgrades (agreed Oct 10, 16:10). Run after M3 in this order: X2 → X3 → X1 → X4

> **X2 status: DONE locally (tested; deploys with the rest).**
> - **Data:** `data/demo/indoor_air.json` holds the infiltration factors per ventilation type (`basis: assumption`, configurable). `venues.json` has 4 indoor venues; class homerooms are added automatically. `class_profiles.json` holds class sizes (counts only).
> - **Choice:** each Plan B session gets `venue_choice`: the outdoor forecast, the chosen venue with its modelled indoor PM2.5 and factor, every alternative with its value or rejection reason (in use / already assigned / too small), and a `why`.
> - **Exposure:** `plan_b_indoor_exposure_modelled` is reported. With no free room, the session is marked "cannot run" and its PE minutes count as lost.
> - **Demo, Stage III:** every class is moved to a room with lower modelled PM2.5. In P2, 7A gets Hall_A (84 vs 280 outdoors) and 7B gets the Gym (140), because the hall is taken.
> - **Evidence:** `tests/test_indoor_air.py` 10/10. It caught a real bug: the outdoor ground was being offered as a "classroom". Full suite 131/131.

> **X3 status: DONE locally (tested; deploys with the rest).**
> - **Data:** `class_profiles.json` adds `sensitive_count` per class (counts only; the loader refuses any other field or a count above class size). `sensitivity_policy.json` holds thresholds × max(floor 0.6, 1 − 0.05 × count), `basis: policy`, capped at 1.0 so it can never loosen a limit. Stage bans from orders are unaffected.
> - **Priority:** sensitive classes choose slots first, and rooms first within a period.
> - **Explained:** the trace says "stricter threshold applied: 4 sensitive students (×0.8: advisory 72.0, restricted 96.0 µg/m³)".
> - **Demo, Stage II:** 6A (4 sensitive) refuses P8 because its pessimistic 114 is over its limit of 96, so it gets the purifier hall, which frees P8 for 7A to keep outdoor PE. Stage III P2: 7B (2 sensitive) gets Hall_A before 7A.
> - **Privacy:** per-class counts appear only in admin responses (the plan behind `GET /decisions`). Public `/rehearse` redacts them, and the public audit chain records only the policy and how many classes got stricter limits.
> - **Evidence:** `tests/test_sensitive_first.py` 9/9; full suite 140/140.

> **X4 status: DONE (deployed and verified on AWS).**
> - **Source:** `services/forecast/ingest.py` fetches Open-Meteo hourly PM2.5 (CAMS) for `data/demo/school.json`, averages it over each period's minutes, computes pessimistic as nominal × 1.2, and caches it in DynamoDB for 6 h.
> - **Fallback:** on any API error, timeout, missing hour, or date beyond the ~5-day horizon, it falls back automatically to the replay forecast, labelled `is_replay` with a `fallback_reason`, and writes a `FORECAST_FALLBACK_REPLAY` audit row.
> - **Defaults:** deployed runs use `live`; local runs and tests use `replay` (no network in tests). Every plan has a `forecast` summary ("live forecast" or "REPLAY SCENARIO …").
> - **On AWS:**
>   - **(A) live, 12 Oct, Stage II:** real values P1 66.7 … P8 50.3 → `confirmed_no_change` (honest: October air is under every limit).
>   - **(B) 30 Nov, Stage III:** fallback row written, then principal timeout → `EscalateToVicePrincipal` → `FailSafeTimeout` (first real escalation run).
>   - **(C) 7 Dec, Stage III, rejected:** fallback reason "HTTP 400: Parameter 'start_date' is out of allowed range…", `FailSafeRejected`, decision status `REJECTED_NO_BROADCAST`; chain of 17 rows verifies.
> - **The live runs exposed two gaps, both fixed:** HTTP error bodies were discarded (the reason read "Bad Request"), and the terminal audit step didn't close the decision (the Brief showed a stale "awaiting"). Terminal events now set `APPROVED_AND_NOTIFIED` / `CLOSED_NO_CHANGE` / `REJECTED_NO_BROADCAST` / `FAILSAFE_TIMEOUT` / `WORKFLOW_ERROR`.
> - **Evidence:** `tests/test_forecast.py` 12/12, plus a final-status test; full suite 153/153.
> - **Demo implication:** a real bad-air day needs the labelled replay (`forecast_source: replay`). Live data is the "real data" proof shot.

These replace U4 (S3 Object Lock is **dropped**; keep only the receipt QR code). Each must run on AWS on camera, or it stays out of the video.

| # | X-factor | Build | Rules | Time-box |
|---|---|---|---|---|
| **X2** | **Indoors isn't automatically safe.** Plan B puts the indoor session in the least-polluted free room. | Venue table `data/demo/venues.json`: `{venue_id, ventilation: sealed\|purifier\|normal\|open, capacity}`. Modelled indoor PM2.5 = outdoor × `infiltration[ventilation]`. The planner picks the lowest-exposure free venue (no venue clash) and returns `venue_choice: {chosen, alternatives[], indoor_pm25_modelled}`. | Infiltration factors live in the ruleset or config, not in code. Every response labels them `"basis": "assumption"` with the factor used. | 2 h |
| **X3** | **Sensitive children first.** Classes with children who have respiratory conditions get stricter limits and first claim on clean slots and rooms. | `data/demo/class_profiles.json`: `{class, sensitive_count}` (**counts only, never names or IDs**). `advisory_at` and `restricted_at` are scaled down for those classes; the planner processes them first. The explanation shows "stricter threshold applied: N sensitive students". | Counts only. The CSV/profile loader rejects any name-like column. | 1 h |
| **X1** | **Just forward the circular.** The principal forwards a circular PDF or photo to a Telegram bot, Bedrock extracts rules, code validates them, and the bot replies with the plan and Approve buttons. | Telegram webhook → S3 → extractor (M4) → validator → diff → reply. Fallback: `POST /circulars` (upload) with **cached, labelled** model output. | **Only if the Bedrock spike passes.** If Telegram plus Bedrock isn't working end to end within 3 h, switch to `POST /circulars` with cached labelled output. Stop there. | 3 h hard |
| **X4** | **Live clean-air window.** | Same as U1: Open-Meteo hourly PM2.5, with an automatic labelled fallback to replay. | Replay is always labelled `is_replay=true`, plus an audit event. | 2.5 h |

**Hard freeze: deadline minus 4 h.** No new features after that, only the demo script, seed data, fallbacks, README and recording.

## 4. Cut list (stop work, remove from video and README)

- **S3 Object Lock anchoring (U4/X5).** Dropped by decision on Oct 10. The receipt QR code stays.
- **`web/verify.html` and `web/app.js` (legacy static pages).** Their hashes can't match the backend (pipe-joined input, in-page fake chain). Don't show them; use `GET /verify/{id}`.

- **`services/drills/tenant_scale_sim.py` and every "1,000 schools / 400,000 children" claim.** The numbers are fabricated constants, and the spec's own rules forbid them.
- **`services/drills/drills_simulator.py` drill 3 (SQS/DLQ/Telegram 5xx).** There's no SQS queue, DLQ, alarm or delivery Lambda in the template. Either build the queue for real (≈2 h, low judge value) or remove SQS/DLQ from the README architecture (lines 107–126) and the video. **Recommendation: remove it.** Notices are delivered as WhatsApp click-to-share links, and saying so honestly is fine.
- **Telegram bot.** Approve through the brief page link (`POST /approve/{shortId}`). It's one channel fewer to break on camera. Keep the webhook secret check (M7) for the security story.
- **`services/planner/standing_order.py`.** It's an in-memory class that isn't wired to anything. It's P2 in your own spec. Keep the test and don't demo it.
- **`data/demo/profile_outdoor_crew.json` and the "crew" eval group.** No code path consumes the profile. Mention it as roadmap in one line.
- **Textract and "OCR noise resilience".** The "Textract" eval case is a hand-typed string with newlines (`eval_runner.py:312`), with no Textract involved. Remove the metric. Digital DoE PDFs have a text layer anyway.
- **`web/city_board.html`, Cedar, Cognito, multi-city.** All are P2 or cut in the spec.
- **`verify_day1_pipeline.py`, `verify_day2_loop.py`, `verify_day3_proof.py`.** They're local rehearsal scripts that print simulated AWS output. Don't show them as proof.
- **Frontend feature work** (out of scope here, but it competes for hours). Freeze UI features. The only frontend work allowed is pointing `lib/api.ts` and `app/api/rehearse/route.ts` at the real `/rehearse` and `/decisions` endpoints. Today `api.ts:9` calls `/api/simulate-stage`, which doesn't exist in the backend, and then falls back to a mock with hardcoded `exposureReductionPct: 84/94`.

---

## 5. Time-boxed plan (Sat 16:00 to Sun 16:00, 4 people)

| Block | A: Platform | B: Planner | C: AI | D: Evidence and API |
|---|---|---|---|---|
| **Sat 16:00–17:00** | M8; M1 build script and template; first `sam deploy` to ap-south-1; budget alarm | M6 teacher-index fix plus test 11 (repro above) | Request or confirm Bedrock Nova access in ap-south-1; one `converse` call from your laptop; collect 2–3 more circular texts | M7 auth fixes plus tests; **P3: message 3–5 principals or teachers now** to book a 10-min call tonight or Sun before 09:00 |
| **17:00–21:00** | M2: state machine in SAM, `RequestApprovalFunction`, DynamoDB tokens, the `Pass` normalisation, execution name = decision ID | M6 day filter, whole-day revalidation, `class_band` filter; M5 PE-minute fields; fix the demo CSV clashes | M4 steps 1–2: extractor plus support check; run it on the DoE circular | M3: `append_audit` with TransactWriteItems, `AuditFunction`, receipts from DynamoDB |
| **21:00 gate** | **One real execution:** start, then plan, then wait, then `curl POST /approve/{shortId}`, then draft, then audit close. Then a second start with the same name fails. | All tests green; plan JSON has the new fields | Extractor output on 1 circular validated; 3 refusals reproduce | `GET /receipts/{id}` returns ≥4 real rows and verify.html says valid |
| **21:00–00:30** | U5 real Bedrock-denied drill; CloudWatch log links ready | **P2: Stage II forecast fixture plus swap test**; U2 explainability; U3 stage-differentiated rules (real text only) | M4 steps 4–5: labelled gold set, honest `eval_table.json` with n | U4 S3 Object Lock anchor; U6 `/health`; point the frontend at the real `/rehearse` |
| **Sun 08:00–09:30** | Smoke test from a clean clone: `scripts/build_lambda.sh && sam build && sam deploy`; then `scripts/seed_demo.py` | U1 forecast ingest **only if** everything above is green; otherwise README planner section | **Cut decision at 09:00:** extractor ships, or narration changes (M4 step 6) | README: delete false claims (M5), add the AWS table with only deployed services; **P1 and P4 reframe of the README top**; **P3 cut decision at 09:00:** quote in, or behaviour claims out |
| **09:30–11:00** | Record console clips: Step Functions graph (approve path plus timeout to escalate), DynamoDB `AUD#` rows, S3 anchor | Clip: rehearsal I to IV with explanations | Clip: real extraction, then diff, then 3 refusals | Clip: verify valid, then edit one row in the console, then verify broken at seq N |
| **11:00–16:00** | Follow the spec's Day 4 plan: video, writeup (list AI tools: Claude Code and any others), blog, secret scan, rotate tokens, make the repo public, **submit by 16:00** | | | |

Rule for the whole plan: no infrastructure deploys after Sun 12:00 except a fix to a broken demo path.

---

## 6. Demo-readiness checklist (backend)

- [ ] **One-command build and deploy:** `scripts/build_lambda.sh && sam build -t infra/template.yaml && sam deploy` works from a clean clone.
- [ ] **One-command tests:** `python run_all_tests.py` exits 0 on Windows.
- [ ] **Seed data:** add `scripts/seed_demo.py`.
  - It writes `TENANT#demo/META` (lat/lon, jurisdiction), `TT#v1` from `data/demo/timetable_sample.csv` (fixed so it has no teacher clashes), and `RULESET#2026-10-08-r1`.
  - It **deletes the `AUD#*`, `AUDHEAD`, `DEC#*` and `TOKEN#*` items for the demo tenant**, so each recording starts at seq 1.
- [ ] **One-command demo run:** add `scripts/demo_run.sh`. It runs `aws stepfunctions start-execution --name demo_<date> ...`, polls `GET /decisions/{id}` for the short ID, approves, then fetches `GET /receipts/{id}` and runs `verify_audit_chain` locally.
- [ ] **Fallback when a live API fails:**
  - Forecast: replay fixture with `is_replay=true`, plus an audit event (U1). The video shows the "Replay scenario" label.
  - Bedrock drafting: static template plus a `fallback_used` audit row (already in `drafting.py`; add the audit write in M3).
  - Bedrock extraction: if the call fails during recording, load `data/gold/runs/<last_good>.json`, **labelled "cached model output from <timestamp>"**.
- [ ] **Health endpoint:** `GET /health` (U6) is green before you hit record.
- [ ] **Secrets:** no tokens in the repo (`git log -p | grep -i token`); `.env` is git-ignored; there's no hardcoded `chat_id` allowlist in code (`workflow/handler.py:15` moves to SSM or env).
- [ ] **Stage II fixture (P2)** produces at least 2 swaps, covered by a test; the Stage III fixture produces Plan B with active sessions only.
- [ ] **Real user quote (P3)** is on file with a name or role and date, or every claim about how schools behave has been removed.
- [ ] **The backend moments to show judges** (four if P2 is ready, otherwise drop moment 2):
  1. **The code refuses the model.** A real DoE circular goes through Bedrock, and the diff shows each rule with its highlighted verbatim quote. Then come three rejections on screen: hidden instruction, invented quote, and the model over-reaching (a quote that doesn't support the action). Caption: *"The model proposes. Code decides."*
  2. **Two days, one engine (P2).** On the Stage II replay, the forecast moves PE to a cleaner slot and shows the rejected candidates and why. On Stage III, the order forces Plan B with an active indoor session and the rule's quote. This answers "why not just WhatsApp the PE teacher?" before anyone asks it.
  3. **A real Step Functions run.** The console graph shows the plan, then a 60 s wait that times out and escalates to the vice-principal, then approval via link, then the notice drafted (with the Bedrock or fallback flag in the audit), and then a second trigger with the same decision ID that is refused (`ExecutionAlreadyExists`).
  4. **Tamper-evident proof.** The public receipt page recomputes the chain from DynamoDB in the browser and shows valid. Edit one `AUD#` row in the DynamoDB console and the page shows broken at seq N. The head hash matches the S3 Object Lock anchor.

---

### Demo readiness status (Sat Oct 10, 18:15 IST)

> **One-command seed/reset: DONE (verified on AWS).**
> - `python scripts/seed_demo.py` clears only the demo school (decisions, audit chain, tokens, receipts, forecast cache), records **Stage II → III (labelled REPLAY SCENARIO)** as audit row **#1**, prints `/health`, and prints the exact next trigger command with a fresh run label. Step Functions keeps execution names for 90 days, so a reset can't reuse one.
> - On AWS it removed 38 + 8 + 1 items, seeded row #1, and the next run used **stage III from the tenant record**. The trigger and the schedule no longer hardcode the stage; an unseeded tenant fails visibly.
> - **Re-run the seed right before each recording.**
>
> **`GET /health`: DONE (verified on AWS).** It reports table (ok, 76 ms), ruleset (version, sha256, 2 rules), declared stage with its source, forecast for tomorrow (**live**, Open-Meteo, cache hit), Bedrock (**not usable: "Operation not allowed"**, so notices use the static template), and audit head (seq, hash, chain valid).
> - Status: `ok`, `degraded` (any labelled fallback, or not seeded), or `down` with HTTP 503 (table unreachable or chain broken). The Bedrock probe is cached for 10 minutes so health checks don't spend money. No secrets or internals in the output.
> - Live it says **degraded**, and the *only* reason is Bedrock (Free plan).
> - **Evidence:** `tests/test_seed_health.py` 13/13; full suite 166/166.
>
> **Still to do for demo readiness:** `scripts/demo.py` (the 3-step path) and the README section.

## 7. Likely judge questions about the backend

**Q: On a Stage III day everything just goes indoors. Why not send one WhatsApp message to the PE teacher?**
A: On Stage III days the hard part isn't the timetable. It's knowing which order applies, to which classes, from when; making sure the replacement keeps children active instead of sitting idle; telling parents in Hindi and English; and being able to prove later that it happened. CAQM wrote to four states in Dec 2025 because schools still held outdoor sports, so a WhatsApp message wasn't enough. On Stage I–II days the forecast decides, and Saans finds a cleaner slot that a person doing this by hand wouldn't compute (show the P2 Stage II swap with its explanation).

**Q: Isn't this only useful a few weeks a year in one city?**
A: Yes, and it's built for exactly that window, when Delhi-NCR schools face it every winter. The rules are versioned data checked against quotes, not code, so another state's order or a heat-action-plan circular is a new ruleset, not a rewrite. We haven't built other regions, and we say so.

**Q: Where does AI actually do something, and what stops it from doing harm?**
A: One bounded job: turning a circular into candidate rules (`services/circular/extractor.py`). The model has no tool that writes, sends or approves. Every rule must carry a quote that is a verbatim substring of the document, and must use only action keys that the quote supports. Both checks are code (`validator.py`), and a person approves the ruleset diff before anything activates. You saw three refusals in the video, including the model over-reaching on a real circular.

**Q: Your eval says 100%. On how many documents?**
A: Answer with the actual `n` from the regenerated `eval_table.json` (for example, "4 real circulars, 11 labelled rules, 2 adversarial"). That is a hackathon start, not production evidence, and the README says so. *Do not walk into this question with today's table: identical precision and recall formulas and hardcoded per-group 100% will sink credibility.*

**Q: What happens if the forecast is wrong?**
A: A swap must pass both the nominal and a pessimistic (+20%) forecast (`planner.py:221-240`). Stage-level bans can never be relaxed by a clean forecast (`rules_engine.py:266`). The morning run re-checks, and if forecast data is stale or unavailable we mark the run as replay, write that to the audit chain, and never substitute silently.

**Q: Why should anyone trust your receipt? You control the database.**
A: Each row hashes the previous row's hash plus its canonical JSON, and appends are conditional transactions on the head pointer, so rows can't be reordered or inserted. The browser recomputes the chain itself. The daily head hash is written to an S3 Object Lock bucket we cannot overwrite during retention. We claim tamper-evident, not tamper-proof.

**Q: What if the principal doesn't answer?**
A: Step Functions `waitForTaskToken` with a timeout escalates to the vice-principal. If they time out too, it fails safe: no broadcast, an audit row, and the admin is flagged. Task tokens never leave the server; approvers get a short, single-use, expiring ID stored in DynamoDB with a conditional consume.

**Q: What if the scheduler fires twice?**
A: The execution name is the decision ID (`tenant#date#session`). Step Functions rejects a duplicate name, which you saw in the console. Notice writes are keyed by decision and recipient.

**Q: Is "PE minutes preserved" just 100% by definition?**
A: Not any more. We report outdoor minutes kept in a safe slot, minutes replaced with active indoor sessions, and minutes lost, all computed from the timetable. *This only holds after M5.*

**Q: Why serverless and not a simple server?**
A: The workload is two bursts a day per school plus a human wait of up to minutes. Step Functions holds the wait for free, without a running process. Lambda and on-demand DynamoDB cost close to zero at idle, and the tenant-partitioned single table scales per school without coordination. Don't quote a cost per school you haven't measured.

**Q: What about children's data and DPDP?**
A: There's no child-level data at all: class-level timetables, teacher codes instead of names, and roles instead of names in the audit. Parent acknowledgements are keyed HMACs, not phone numbers. A DPDP review is required before any real pilot, and it is listed as a limitation.

**Q: What's not production-ready?**
A: Say it plainly: modelled forecast (CAMS via Open-Meteo, not a station reading), manual-tap WhatsApp delivery, a small gold set, no real pilot, no DLT or WhatsApp Business registration, and no DPDP review.
