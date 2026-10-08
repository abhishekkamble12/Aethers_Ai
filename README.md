# 💨 Saans (साँस) — Day 1 Build & Gate Verification

> **Reads the order. Re-plans the day. Proves it.**  
> Track: Air ("School safety on bad days"), Environmental Hacks (Oct 8–11, 2026).

---

## 🎯 Day 1 Gate Status: **GREEN**

**Target:** *A scheduled run in AWS outputs a valid Plan A or Plan B for a replay day, and the 10 planner tests pass.*

---

## 📂 Repository Architecture

```
d:\Aethers_Ai\
├── data/
│   ├── demo/
│   │   ├── forecast_stage3_sample.json   # SAFAR-IITM Stage III replay forecast (P1-P8)
│   │   ├── ruleset_v1.json               # Delhi Stage III ruleset with exact CAQM quotes
│   │   └── timetable_sample.csv          # 6 classes × 8 periods with PE slots & locked rooms
│   └── gold/
│       ├── circular_real_caqm.txt        # Verbatim Delhi DoE/CAQM Stage III circular
│       ├── hostile_instruction.txt       # Prompt injection attack circular fixture
│       ├── hostile_invented_quote.json   # Hallucinated quote candidate fixture
│       └── ruleset_schema.json           # JSON Schema for extracted rules
├── infra/
│   └── template.yaml                     # AWS SAM template (DynamoDB Single-Table, EventBridge, Lambdas)
├── services/
│   ├── rules/
│   │   └── rules_engine.py               # Order-first, forecast-second classification engine
│   ├── planner/
│   │   ├── csv_loader.py                 # Timetable CSV loader with row-level validation
│   │   ├── planner.py                    # Deterministic Swap Planner + Plan B Fallback bank
│   │   └── handler.py                    # Lambda handlers for EventBridge & Rehearsal API
│   ├── circular/
│   │   └── validator.py                  # Quote substring checker & hostile refusal logic
│   └── audit/
│       └── hash_chain.py                 # Tamper-evident SHA256 audit log engine
├── tests/
│   ├── test_planner.py                   # 10 mandatory planner tests
│   ├── test_audit.py                     # Hash chain integrity & tamper-detection tests
│   └── test_circular_validator.py        # Real circular approval & hostile refusal tests
├── web/
│   ├── index.html                        # Today's Brief, Stage Rehearsal slider & Receipt
│   ├── styles.css                        # Glassmorphism dark mode aesthetic
│   └── app.js                            # Client-side Rehearsal & in-browser WebCrypto verifier
├── run_all_tests.py                      # Unified test runner
└── verify_day1_pipeline.py               # Full end-to-end pipeline demonstration script
```

---

## 🧪 The 10 Mandatory Planner Tests

Defined in [`tests/test_planner.py`](file:///d:/Aethers_Ai/tests/test_planner.py):

| # | Test Name | Constraint / Behavior Verified |
|---|-----------|--------------------------------|
| 1 | `test_01_valid_swap_exists_and_chosen` | Valid swap to a clean period with available teacher and ground is selected. |
| 2 | `test_02_best_partner_teacher_busy_next_chosen` | When the optimal slot has a teacher clash, the next best conflict-free slot is picked. |
| 3 | `test_03_ground_double_booked_rejected` | Double-booking grounds is rejected; falls back to Plan B indoor session. |
| 4 | `test_04_outdoor_sports_banned_for_day_so_plan_b` | Under Stage III ban, all outdoor sports fall back to Plan B; preserves 100% of PE minutes. |
| 5 | `test_05_locked_period_never_moved` | Locked periods (exams/labs) are strictly immutable. |
| 6 | `test_06_two_proposals_conflict_revalidates_and_resolves` | Multi-class competition for the same slot is reconciled without double-booking. |
| 7 | `test_07_all_periods_allowed_no_change` | Clean forecast produces `confirmed_no_change` with zero churn. |
| 8 | `test_08_fine_nominally_but_fails_pessimistic_rejected` | Periods that exceed threshold under the $+20\%$ pessimistic forecast ($\delta=0.20$) are rejected. |
| 9 | `test_09_stage_ban_never_relaxed_by_low_pm25` | Stage-level legal bans cannot be relaxed by local low PM2.5 readings. |
| 10 | `test_10_ruleset_for_another_jurisdiction_rejected` | A ruleset from another jurisdiction (e.g., Maharashtra) fails closed. |

---

## 🚀 Running the Tests & Verification

### 1. Run all Unit Tests:
```bash
python run_all_tests.py
```

### 2. Run End-to-End Local Pipeline Demo:
```bash
python verify_day1_pipeline.py
```

### 3. Open Web UI Dashboard:
Open [`web/index.html`](file:///d:/Aethers_Ai/web/index.html) in any browser to interact with:
- The **Stage Rehearsal Slider** (drag from Stage I to IV to watch the timetable recalculate in real time).
- The **Before & After Timetable Grid** with reason lines and rule IDs.
- In-browser **SubtleCrypto SHA-256 Hash Chain Verification**.
