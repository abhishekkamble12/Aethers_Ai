# 💨 Saans (साँस) — Air-Safety School Day Planner & Verifier

> **Reads the order. Re-plans the day. Proves it.**  
> Track: Air ("School safety on bad days"), Environmental Hacks (Oct 8–11, 2026).

---

## 🎯 Hackathon Gates Status

| Milestone | Gate Requirement | Status |
| :--- | :--- | :---: |
| **Day 1: Foundations** | Scheduled run outputs valid Plan A/B + 10 planner tests pass | ✅ **PASSED (16/16 tests green)** |
| **Day 2: The Real Loop** | Step Functions approval loop with escalation + Rule-diff with verbatim quotes + Bilingual WhatsApp notices | ✅ **PASSED (23/23 tests green)** |

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
│   │   ├── teacher_schedule.py           # Personalized indoor/swap rosters for teachers
│   │   └── handler.py                    # Lambda handlers for EventBridge & Rehearsal API
│   ├── circular/
│   │   ├── validator.py                  # Quote substring checker & hostile refusal logic
│   │   └── diff_engine.py                # Active vs Candidate ruleset diff with quote citations
│   ├── workflow/
│   │   ├── state_machine.json            # Step Functions ASL with waitForTaskToken & escalation
│   │   ├── workflow_manager.py           # Token registry isolating raw task tokens
│   │   └── handler.py                    # Approval webhook handler with allowlist checks
│   ├── notify/
│   │   ├── drafting.py                   # Bilingual notice drafting & WhatsApp click-to-share links
│   │   └── handler.py                    # Lambda notification dispatcher
│   └── audit/
│       ├── hash_chain.py                 # Tamper-evident SHA256 audit log engine
│       └── handler.py                    # Public receipt verification API handler
├── tests/
│   ├── test_planner.py                   # 10 mandatory planner tests
│   ├── test_audit.py                     # Hash chain integrity & tamper-detection tests
│   ├── test_circular_validator.py        # Real circular approval & hostile refusal tests
│   └── test_day2_loop.py                 # Day 2: Workflow escalation, teacher schedules, diff engine, WhatsApp
├── web/
│   ├── index.html                        # Today's Brief, Stage Rehearsal slider, Rule-Diff, Receipts
│   ├── styles.css                        # Glassmorphism dark mode aesthetic
│   └── app.js                            # Client-side Rehearsal & in-browser WebCrypto verifier
├── run_all_tests.py                      # Unified test runner (all 23 tests)
├── verify_day1_pipeline.py               # Day 1 pipeline demonstration script
└── verify_day2_loop.py                   # Day 2 complete loop demonstration script
```

---

## 🧪 All Automated Tests

Run the complete test suite:
```bash
python run_all_tests.py
```

The suite covers **23 automated tests**:
1. **Planner Tests (10 tests)**: Valid swaps, busy teacher fallback, ground double-booking rejection, Stage III outdoor ban (Plan B fallback), locked period protection, multi-class collision resolution, clean air zero-churn, $+20\%$ pessimistic forecast rejection ($\delta=0.20$), Stage ban priority over clean air, and jurisdiction mismatch failure.
2. **Audit & Cryptographic Chain (3 tests)**: Valid sequence verification, tamper-evidence detection, and broken link detection.
3. **Circular Extraction & Refusal (3 tests)**: Verbatim quote substring validation, hallucinated quote rejection, and prompt injection refusal (*"SYSTEM OVERRIDE"*).
4. **Day 2 Loop Suite (7 tests)**: Direct approval transition, 60s timeout escalation to Vice-Principal, final timeout fail-safe with zero broadcast, secure one-time token resolution, teacher schedule generator with indoor venue mapping, ruleset diff computation with quote citations, bilingual notice drafting, and static fallback resiliency.

---

## 🚀 Execution & Verification Commands

### Run Day 2 End-to-End Loop Demonstration:
```bash
python verify_day2_loop.py
```

### Run All Unit Tests:
```bash
python run_all_tests.py
```

### Interactive Dashboard:
Open [`web/index.html`](file:///d:/Aethers_Ai/web/index.html) in your browser:
- **Stage Rehearsal Slider**: Drag between Stage I and Stage IV to watch schedules re-plan in real time.
- **Rule-Diff Screen**: Inspect candidate rules with verbatim circular quotes highlighted.
- **Teacher Rosters & 1-Tap WhatsApp Buttons**: Pre-formatted bilingual parent notices ready for WhatsApp share.
- **Air-Day Cryptographic Receipt**: Live in-browser SHA-256 chain verification using the WebCrypto API.
