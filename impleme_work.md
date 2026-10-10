# impleme_work.md: Implementation plan for the final features

Written Sat Oct 10, 20:25 IST, on branch `hackwin/backend` (head `86c59b8`). The stack `saans` is live in us-east-1.
It builds on `hack_win.md`. That file records what is already done and verified. This file is what we build next, in what order, and how we prove each piece.

**Assumed timeline:** submit Sun Oct 11 by 16:00 IST, so the **feature freeze is Sun 12:00**. If the event page gives a different cutoff, move the freeze to deadline minus 4 h and drop items from the bottom of section 2.

---

## 1. Decisions (what we build, change and cut)

| # | Proposed feature | Decision | Why |
|---|---|---|---|
| F1 | Bedrock policy translation (read the circular, extract rules, plain-language notices) | **BUILD if the AWS account is upgraded tonight** (time-box 3 h + 1 h for notices). Otherwise cut and call it roadmap. | It completes "reads the order → re-plans the day → proves it" and gives us the refusal moment. It's blocked today: the account is on the Free plan with a Nova quota of 0. |
| F2 | Forecasting with ML (SageMaker) to predict GRAP III 24–48 h ahead | **CHANGE to "Forecast Watch"** (1.5 h) | No training data or validation time, and it contradicts "orders decide, Saans never declares a stage". The real 5-day CAMS forecast we already ingest gives the same early warning honestly. |
| F3 | 48-hour forecast chart data | **BUILD `GET /forecast`** (45 min) | The chart needs real hourly data and our real thresholds. **No "AQI = 400" line on a PM2.5 chart** (different units). |
| F4 | Parent "Health ROI" message | **CHANGE to one honest sentence** (30 min) | "140 µg of PM2.5 avoided" is scientifically wrong (µg/m³ is a concentration). Use the modelled room-versus-outdoor difference, labelled as modelled. |
| F5 | Parent portal with per-child clean-air minutes | **CUT** | It needs child-level data, which breaks our counts-only privacy design and runs into DPDP rules for children's data. Low value for its cost. |
| F6 | "Blockchain" / "CAQM hash chain" wording | **CUT the wording** | It's a SHA-256 hash chain, not a blockchain, and CAQM publishes no hashes. Say "tamper-evident hash chain". |
| F7 | Principal Command Center (UI) | **Frontend team builds it against the existing API.** The backend only adds F3. | `GET /decisions` and `GET /receipts/{id}` already return everything else (section 8). |
| F8 | Demo script and README section | **BUILD** (1.5 h) | Required for demo readiness. |

**One rule for everything below:** a feature that is not deployed, tested and visible in an API response or the AWS console stays out of the video and the README.

---

## 2. Order of work and time boxes

| Order | Item | Owner | Time | Depends on | Cut trigger |
|---|---|---|---|---|---|
| 0 | **Decision: upgrade AWS to the Paid plan (yes/no)** | Abhishek | 5 min | none | No answer by 21:00 means treat it as "no" |
| 1 | F3 `GET /forecast` | Backend (Claude) | 45 min | none | none |
| 2 | F2 Forecast Watch | Backend | 1.5 h | 1 | Not passing tests by 23:30: ship without the scheduled rule (manual endpoint only) |
| 3 | F4 Honest parent sentence | Backend | 30 min | none | none |
| 4a | F1-a Bedrock spike re-run + fix the notice drafting call | Backend | 45 min | 0 = yes | Quota still 0 after 30 min: stop F1, go to 5 |
| 4b | F1-b Circular → rules extraction with the refusal moment | Backend | 3 h hard | 4a | Not working end to end by Sun 10:00: switch to the labelled cached run (section 6.8) |
| 5 | F8 Demo script and README section | Backend | 1.5 h | 1–4 | none, required |
| 6 | Command Center wired to the real API | Frontend team | ~5 h, in parallel | 1 (contract in section 8) | Sun 11:00: freeze the UI at whatever is real |
| 7 | One real principal or teacher quote | Any teammate | tonight | none | Sun 09:00: no quote means no claims about how schools behave |
| 8 | Video recording | All | Sun 12:00–14:30 | 5, 6 | none |

**Tonight (20:30–01:00):** 0 → 1 → 2 → 3, and 4a if upgraded.
**Sun 08:00–12:00:** 4b (if upgraded) → 5 → reseed → freeze.

---

## 3. F3: `GET /forecast` (data for the forecast chart)

**Why:** the chart must show real hourly PM2.5 and *our* limits. The judges' question it answers: "which forecast value was used?"

### 3.1 API
`GET /forecast?tenant=demo&hours=48&source=live|replay` (public; no secrets, no per-class counts)

```json
{
  "source": "live",
  "label": "live forecast",
  "model": "CAMS via Open-Meteo Air Quality API",
  "generated_at": "2026-10-10T15:00:00+00:00",
  "fallback_reason": null,
  "unit": "µg/m³ (PM2.5, hourly mean)",
  "hours": [{"time": "2026-10-11T00:00+05:30", "pm25": 51.7, "school_hours": false}],
  "thresholds": [
    {"name": "advisory",   "value": 90,  "basis": "ruleset 2026-10-08-r1 (product default, not an official limit)"},
    {"name": "restricted", "value": 120, "basis": "ruleset 2026-10-08-r1"},
    {"name": "stricter limit for classes with sensitive students", "values": [96.0, 108.0, 114.0], "basis": "policy"}
  ],
  "first_crossing": {"threshold": "restricted", "time": null},
  "declared_stage": {"stage": "III", "label": "REPLAY SCENARIO"},
  "note": "Saans never declares a GRAP stage; thresholds decide advisory/restricted only within what the order allows."
}
```

### 3.2 Implementation
- `services/forecast/ingest.py`
  - `fetch_hourly(school, start_date, end_date, fetch=None) -> list[{time, pm25}]`. It uses the same API call as `get_forecast` with a date range, and raises on gaps.
  - Refactor `get_forecast` to call `fetch_hourly`, so both features share one code path.
  - Cache: `PK=GRID#{cell}#H48#{yyyy-mm-ddThh}`, `SK=FCST`, TTL 2 days, reused for 1 h.
  - Fallback: if the fetch fails, use the replay periods expanded to hours with `source: replay` and a `fallback_reason`. Never empty, never silent.
- `services/forecast/handler.py: forecast_handler` (`@guarded`)
  - Validate: `hours` is in 1..120 and `source` is in `live|replay`.
  - Thresholds come from the active ruleset and `sensitivity_policy.json` applied to `class_profiles.json`. Publish **only the distinct threshold values**, never class names with counts.
  - `school_hours` is true where the hour overlaps a timetable period.
  - `first_crossing` is the first hour at or above each threshold.
- `infra/template.yaml`: add `ForecastFunction` with `GET /forecast` and `DynamoDBCrudPolicy` (for the cache).

### 3.3 Tests (`tests/test_forecast_api.py`)
1. Live stub of 48 hourly values: shape, unit, `school_hours` flags, `first_crossing` correct.
2. Fetch failure gives `source: replay` plus a reason, and status 200.
3. Bad `hours` or `source` gives a 400 JSON error.
4. The response contains no `sensitive_count` and no class names next to the stricter limits.
5. Cache hit within 1 h; refetch after.

### 3.4 Verify on AWS
`curl "$API/forecast?hours=48"` returns `source: live` with 48 hours. Then `curl "$API/forecast?source=replay"` returns the replay label.

**Done when:** deployed, tests pass, and both curls are recorded in `hack_win.md`.

---

## 4. F2: Forecast Watch (early warning without ML)

**Why:** judges like proactive systems. This gives the principal 1–2 days' notice when the *forecast* (not an order) is heading past our limits. It drafts a **contingency plan** that is clearly **not active**, and the principal can promote it to a real run.

**What it must never do:**
- Declare or imply a GRAP stage.
- Notify parents.
- Start an approval.
- Count as a decision.

### 4.1 Behaviour
- **Schedule:** EventBridge daily at 16:30 IST (`cron(0 11 * * ? *)`), plus on demand.
- **For each of the next 2 school days** (skip days with no classes):
  1. `get_forecast(date, timetable, "live")` (replay only if requested, labelled).
  2. Run `plan_schedule` with the **currently declared stage from the tenant record** and that forecast, as a rehearsal. No decision item and no approval.
  3. Classify the risk: `none` (no period restricted), `watch` (any period advisory), or `act` (any period restricted, or any class's stricter limit crossed).
  4. Store `PK=TENANT#demo`, `SK=WATCH#{date}` with `{risk, peak_pm25, peak_period, plan_summary (counts only), forecast summary, label: "CONTINGENCY DRAFT: not active until an order or the principal starts the day's run"}`.
  5. If the risk is `act` and it's new or higher than the last watch for that date, append the audit event `CONTINGENCY_DRAFTED` `{date, risk, peak_pm25, source}`, so the early warning becomes provable.

### 4.2 API
- `GET /watch?tenant=demo`: admin key (same header as `/decisions`). Returns the stored watches for the next 2 school days, plus `promote_hint` (the exact trigger payload to start the real run).
- **Promotion reuses the existing trigger**, so there's no new approval path and no new risk.

### 4.3 Implementation
- `services/forecast/watch.py: run_watch(table, today, source="live") -> list[watch]` and `watch_handler(event, ctx)` for the schedule, which logs and never raises on a forecast failure.
- `services/forecast/handler.py: watch_get_handler`, guarded, admin key via the shared `_require_admin`. Move that helper from `decisions.py` into `services/common/auth.py`.
- Template: `WatchFunction` (schedule) and `WatchApiFunction` (`GET /watch`) with DynamoDB CRUD.

### 4.4 Tests (`tests/test_forecast_watch.py`)
1. Clean live data (the real Oct values, ~50–74) gives `risk: none` and no audit row.
2. Replay forecast (the bad day) gives `risk: act`, the label contains "not active", and exactly one `CONTINGENCY_DRAFTED` row. Running it again gives no duplicate row.
3. A class with sensitive students crosses its stricter limit while the base limit isn't crossed: risk is `act` with the reason stated.
4. No-class day (Sunday) is skipped.
5. The watch creates **no** `DEC#` item, **no** `TOKEN#` item and **no** Step Functions execution.
6. `GET /watch` without the key returns 401.

### 4.5 Verify on AWS
1. `aws lambda invoke WatchFunction '{"source":"replay"}'` gives `act` for the next school day, and the audit row appears in `/receipts`.
2. A live invoke gives an honest `none` today (October air).

**Demo line:** "Saans saw the forecast crossing the limits 36 hours ahead and drafted a contingency plan. Nothing went to parents, and nothing changed until the order arrived."

---

## 5. F4: The honest parent sentence

**Why:** parents care about health, but every number must be true and labelled.

### 5.1 The fact
`plan_facts()` in `services/notify/drafting.py` gains:
- `indoor_air_reduction_pct_modelled`: the mean over Plan B sessions of `(outdoor_pm25 - chosen_indoor_pm25) / outdoor_pm25 × 100`, rounded to a whole number. It comes from `venue_choice` (X2). If there is no Plan B, or no venue data, it's `None` and the sentence is left out.
- `classes_with_stricter_limits` is a count only. Mention it in the teacher notice, not the parent one.

### 5.2 The text (static templates; Bedrock gets the same fact)
- **EN:** "Indoor sessions are in rooms with an estimated {pct}% lower PM2.5 than outdoors (modelled from ventilation type, not measured)."
- **HI:** "इनडोर सत्र ऐसे कमरों में होंगे जहाँ बाहर की तुलना में अनुमानित {pct}% कम PM2.5 है (वेंटिलेशन के आधार पर अनुमान, मापा नहीं गया)।"
- **Never:** "µg avoided", "health ROI", "safe air", or any per-child figure.

### 5.3 Tests
Extend `tests/test_honest_numbers.py`:
1. Stage III demo gives a percentage between 60 and 80.
2. The word "modelled" (or "अनुमान") is present.
3. No Plan B means no sentence.
4. No "µg" anywhere in a notice.

---

## 6. F1: Bedrock policy translation (only if upgraded)

### 6.1 Prerequisite (Abhishek, 5 min, owner decision)
- Upgrade the account to the Paid plan in **Billing and Cost Management**. Credits ($149.61) carry over, the Zero-Spend Budget still emails on any charge, and the expected Bedrock cost for the whole demo is **under $0.10**.
- Then tell the backend "upgraded".

### 6.2 Spike re-run (backend, 15 min)
- Re-run the scratchpad spike (`converse`, Nova Lite, the real DoE circular plus the hostile circular).
- **Pass:** the model returns JSON rules, and the validator accepts the true quotes and refuses the hostile and invented ones.
- **Fail:** the quota is still 0 after 30 min. Stop F1 and record "blocked" in `hack_win.md`.

### 6.3 Fix notice drafting (30 min)
- `services/notify/drafting.py:_invoke_bedrock_nova` uses `invoke_model` with a content block `{"type": "text", ...}`, which Nova rejects, so it would *always* silently fall back. Switch to `bedrock-runtime.converse` with `system` + `messages` and `inferenceConfig {maxTokens 300, temperature 0.2}`.
- Template: give `NotificationFunction` `bedrock:InvokeModel` on `foundation-model/amazon.nova-lite-v1:0` only.
- **Keep the guardrails:** the prompt states only `plan_facts`. After generation, a code check rejects the draft (and uses the static fallback, `fallback_used: true`, `fallback_reason`) if it contains a number not in the facts, a URL other than the verify link, or is over 600 characters.
- **Tests:** stub `converse` and check a valid draft is used; a draft with an invented number triggers the fallback with a reason; an exception triggers the fallback.

### 6.4 Circular → rules pipeline (3 h hard)

```
POST /circulars (admin key) ──► presigned S3 PUT (circulars bucket, versioned, private, SSE)
S3 ObjectCreated ──► ExtractFunction
    1. text = PDF text layer (pypdf) or the .txt body; sha256 of the file
    2. injection screen (existing patterns) → recorded as a signal, never a decision
    3. Bedrock converse (Nova Lite, temperature 0, schema prompt from the spike;
       school rules only — ignore vehicles, construction, industry)
    4. validate each candidate in CODE:
         schema/enums · verbatim quote (substring of text) · action supported by quote (NEW)
    5. diff vs active ruleset (diff_engine) + content hash
    6. store CIRC#{id}/META: status, accepted[], rejected[{rule, reasons}], ignored_count, raw model output
    7. audit CIRCULAR_EXTRACTED {circular_sha256, accepted, rejected, refusal_types, model}
GET /circulars/{id} (admin key) ──► diff with highlighted quotes + refusals
```

**Files**
- `services/circular/extractor.py`: `extract_candidates(text, client=None) -> (rules, raw)`. Strict JSON parsing; a non-JSON reply means zero candidates plus a `model_output_invalid` reason.
- `services/circular/validator.py`: add `action_supported_by_quote(rule)` (the same keyword logic already in `eval_runner.unsupported_actions`) as a **rejecting** check with the reason `REFUSED (action not supported by its quote)`.
- `services/circular/handler.py`: `upload_handler` (presign, validate filename, size cap 5 MB, `.pdf`/`.txt` only), `extract_handler` (S3 event), `circular_get_handler`.
- `scripts/build_lambda.py`: write `pypdf==5.1.0` into the bundle's `requirements.txt`. `sam build` installs it.
- `infra/template.yaml`:
  - `CircularsBucket` (versioning, block public access, SSE-S3, lifecycle 30 days).
  - `UploadFunction` (S3 put-object presign on the bucket only).
  - `ExtractFunction` (S3 read on the bucket, `bedrock:InvokeModel` on Nova Lite only, DynamoDB CRUD, timeout 60 s, memory 1024).
  - `CircularGetFunction`.

**Out of scope (cut to fit 3 h):** activating an extracted ruleset (`POST /rulesets/{v}/approve`) so the planner reads it from DynamoDB. The planner keeps the bundled reviewed ruleset. In the video: "extracted rules are reviewed before activation; activation is the next step." That's honest and matches "the model proposes, a person approves".

### 6.5 The refusal moment (the demo beat)
Run three uploads:
1. **The real DoE circular No. 40:** r-017 is accepted with its highlighted quote; the hybrid-mode rule is accepted for `hybrid_mode` only; any outdoor-sports action attached to the assembly or hybrid quotes is **refused: action not supported by its quote**.
2. **The hostile circular ("SYSTEM OVERRIDE…"):** refused.
3. **A circular plus a forged rule with an invented quote:** refused, "quote not found in source".

### 6.6 Evaluation (honest numbers)
- `data/gold/labels/doe_40.json`: hand-labelled expected rules (action, stage, class band, quote).
- `services/circular/eval_runner.py`: run the extractor on each gold circular, store raw outputs in `data/gold/runs/{timestamp}.json`, and compute **precision = matched/extracted** and **recall = matched/labelled**, with *n* printed beside each.
- Add 2–3 more real circular texts only if they can be copied from the official PDFs tonight. Otherwise publish *n = 1* and say so.

### 6.7 Tests
`tests/test_extractor.py`, using a stubbed Bedrock client:
1. JSON parsing, including prose around the JSON.
2. A non-JSON reply gives zero candidates plus a reason.
3. Support check: refuses the assembly-quote ban.
4. An invented quote is refused.
5. The upload handler validates type and size.
6. Extract writes `CIRC#` and the audit row; the audit holds no raw model text, only counts and hashes.

Plus one **live** test, skipped unless `SAANS_LIVE_BEDROCK=1`.

### 6.8 Fallback if Bedrock is flaky while recording
- `GET /circulars/{id}?replay=1` serves the last stored successful run, with `label: "CACHED MODEL OUTPUT from {timestamp}"`.
- It is **never** generated by hand.

### 6.9 Verify on AWS
Upload all three files with curl to the presigned URL, `GET /circulars/{id}` for each, and confirm `CIRCULAR_EXTRACTED` rows appear on `/receipts`. Record it in `hack_win.md`.

---

## 7. F8: Demo script and README section

### 7.1 `scripts/demo.py` (3 steps, ~2 min, uses the deployed API and the `Abhi` profile)
1. **"Reads the order / sees it coming":**
   - Print `/health`.
   - Show `/forecast` (live) vs the replay, then `/watch` → `act` with a contingency draft.
   - If F1 shipped: show the 3 circular uploads with accepted and refused rules.
2. **"Re-plans the day":**
   - Trigger a replay run (stage from the tenant record).
   - Print the decision trace for 6A: the stricter limit and why P8 was refused, then the room choice (Hall_A 108 vs 360 µg/m³ outdoors).
   - Approve via the link, trigger again to show `duplicate_suppressed`, and print the Step Functions path.
3. **"Proves it":** print the receipt rows and the `/verify/{id}` URL to open in the browser, then press "Simulate tampering" on camera.

Flags:
- `--reset` runs `seed_demo.py` first.
- `--escalation` runs a no-answer case: principal timeout, then vice-principal, then fail-safe.

### 7.2 README section ("For judges")
- **Problem in 3 lines** (with the CAQM Dec 2025 non-compliance letter), the user, and one real quote if we have it.
- **Architecture diagram** (Mermaid):

  ```mermaid
  flowchart LR
    TriggerFunction[Trigger] --> SF[Step Functions]
    SF --> LoadContext[LoadContext: forecast + planner]
    LoadContext --> Approve[waitForTaskToken approval]
    Approve --> Notify[Notify]
    Notify --> Audit[Audit]
    LoadContext --- DDB[(DynamoDB)]
    Approve --- DDB
    Audit --- DDB
    Watch[Forecast Watch] --> DDB
    API[API Gateway: /decisions /approve /receipts /verify /health /forecast /watch] --> DDB
  ```

- **AWS services and why:** Step Functions (holds the human wait for free, retries, escalation), Lambda (bursty, twice-daily), DynamoDB (single table, conditional writes, transactions for the audit chain), API Gateway, EventBridge, S3 + Bedrock (only if shipped), CloudFormation/SAM.
- **How to run:**
  - `python run_all_tests.py`
  - `python scripts/build_lambda.py && cd infra && sam build && sam deploy`
  - `python scripts/seed_demo.py`
  - `python scripts/demo.py`
- **3 backend highlights:**
  1. Every decision is explained: rule, quote, forecast value, rejected options, room choice.
  2. A real approval loop with escalation and fail-safe on Step Functions, plus idempotency.
  3. A tamper-evident hash chain verified in the browser.
- **Measured vs modelled vs assumption** table for every number.
- **Limitations:** forecast is modelled (CAMS); October air needs the labelled replay for the bad-day demo; indoor factors are assumptions; manual WhatsApp tap; not piloted; DPDP review needed; AI extraction status (shipped, or roadmap if not upgraded).
- **AI tools used:** Claude Code, and any others the team used (required by the rules).

---

## 8. Frontend contract for the Command Center (handoff to the UI team)

**No new backend is needed except F3.** Point the UI at `https://367bcz1ry5.execute-api.us-east-1.amazonaws.com/Prod`. The admin key goes in `x-saans-admin-key`: keep it in a server-side Next.js env var and **never ship it to the browser**.

| UI element | Source | Fields |
|---|---|---|
| Forecast chart | `GET /forecast?hours=48` | `hours[].pm25`, `thresholds[]`, `school_hours`, `label`. **No AQI line.** |
| Workflow timeline | `GET /receipts/{receipt_id}` | `blocks[]` filtered to `decisionSequences`: `eventType`, `actor`, `timestamp`. Show only events that happened. **No "Circular Parsed"** unless `CIRCULAR_EXTRACTED` exists. |
| Action Hub table | `GET /decisions?tenant=demo&date=…` (server-side) | `plan.plan_b[]` (class, period, `fallback_venue`, `venue_choice.chosen.indoor_pm25_modelled`, `venue_choice.outdoor_pm25_forecast`), `plan.plan_a[]`, `plan.decision_trace[]` for "why" |
| Approve button | `approval.approve_url` | `POST` `{"action": "APPROVE_PLAN_A" | "APPROVE_PLAN_B" | "REJECT"}`. 410 means the link was used or expired; 409 means the window closed. |
| Early-warning banner | `GET /watch` (server-side) | `risk`, `peak_pm25`, `label` ("CONTINGENCY DRAFT: not active") |
| Verify button | link to `/verify/{receipt_id}` | Wording: "Verify the decision record" (not blockchain, not CAQM hash) |
| Status pill | `GET /health` | `status` plus the reason |

**Copy fixes before recording:** remove every `saans.delhi.gov.in`, "blockchain", "400,000", and any hardcoded numbers from `lib/mockData.ts` on screens that are shown.

---

## 9. Cut list (do not build)

- **SageMaker or any trained ML model.** No data or validation time. Replaced by Forecast Watch.
- **Parent portal and per-child tracking.** Privacy and DPDP risk, low value.
- **"Health ROI" numbers in µg.** Scientifically wrong. Replaced by the modelled % sentence.
- **"Blockchain" wording, and "CAQM hash".** Inaccurate.
- **Vehicle, construction and industry rules from circulars.** Not school-relevant. The prompt ignores them; the count is reported.
- **Ruleset activation from extracted rules.** Next step after review, not this weekend.
- **Gemini or any non-AWS LLM.** "Built on AWS" is a criterion; Bedrock or nothing.
- **More drills, SQS/DLQ, Telegram, Textract.** Already on the `hack_win.md` cut list.

---

## 10. Definition of done (every item)

1. Unit tests pass (`python run_all_tests.py` exits 0).
2. `sam validate --lint` and `sam build` pass, and it's deployed to `saans` in us-east-1.
3. Verified with a real call on AWS, with the command and output pasted into `hack_win.md`.
4. Responses never leak stack traces, secrets, approval links on public endpoints, or per-class sensitive counts.
5. Every number shown is labelled *measured*, *modelled* or *assumption*.
6. One commit per item, with a clear message.

---

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Upgrade done but the Bedrock quota is still 0 for a while | 30-min wait limit, then cut F1 (section 6.2) |
| Bedrock flaky while recording | Labelled cached run (section 6.8); notices fall back to static, which is recorded in the audit |
| Open-Meteo down during the demo | Automatic labelled replay already exists; `/health` shows it |
| Real October air is clean, so nothing to show | Bad-day beats use the labelled replay; the live run is shown as the "real data" proof |
| Frontend not wired by the freeze | Record the backend beats from `/verify` (a real page) and the AWS console; drop UI screens that are still mock |
| Running out of time | Drop from the bottom of section 2. Never drop the reseed, demo script or README |
| Secrets on screen | Keep `infra/deploy.secrets` and `.env` closed, mask the account ID, rotate the access key after the event |

---

## 12. Checklist before the freeze (Sun 12:00)

- [ ] F3 `/forecast` live on AWS
- [ ] F2 Forecast Watch live; replay gives `act`, live gives an honest `none`
- [ ] F4 notice sentence live
- [ ] F1 shipped or explicitly cut, and the README says which
- [ ] `scripts/demo.py` runs end to end against AWS
- [ ] README "For judges" section merged
- [ ] `python scripts/seed_demo.py` run right before recording
- [ ] Frontend shows only real data (or mock screens are kept out of the video)
- [ ] One real quote, or behaviour claims removed
- [ ] All tests green; `hack_win.md` updated with AWS evidence
