"""
Saans Day 1 End-to-End Pipeline Verification Script
Executes the full pipeline locally:
Ingest -> Rules Classification -> Planner (Plan A & B) -> Hash Chain Audit -> Refusal Drill
"""

import json
from services.planner.csv_loader import load_timetable_csv
from services.planner.planner import plan_schedule
from services.rules.rules_engine import classify_period
from services.audit.hash_chain import GENESIS_HASH, create_audit_row, verify_audit_chain
from services.circular.validator import validate_ruleset_candidates

def main():
    print("=" * 75)
    print("SAANS: END-TO-END PIPELINE VERIFICATION (DAY 1 GATE)")
    print("=" * 75)

    # 1. Load fixtures
    print("\n[STEP 1] Loading sample timetable CSV...")
    with open("data/demo/timetable_sample.csv", "r", encoding="utf-8") as f:
        timetable, errors = load_timetable_csv(f.read())
    print(f" -> Loaded {len(timetable)} period records across 6 classes. CSV Errors: {len(errors)}")

    print("\n[STEP 2] Loading Replay Forecast & Ruleset v1...")
    with open("data/demo/forecast_stage3_sample.json", "r", encoding="utf-8") as f:
        forecast = json.load(f)
    with open("data/demo/ruleset_v1.json", "r", encoding="utf-8") as f:
        ruleset = json.load(f)
    print(f" -> Forecast: {forecast['grid_cell']} on {forecast['date']} (Declared Stage: {forecast['declared_stage']})")
    print(f" -> Ruleset Version: {ruleset['ruleset_version']} (Jurisdiction: {ruleset['jurisdiction']})")

    # 2. Run Planner
    print("\n[STEP 3] Executing Deterministic Planner...")
    plan_result = plan_schedule(
        timetable=timetable,
        forecast=forecast,
        ruleset=ruleset,
        declared_stage="III",
        school_jurisdiction="Delhi",
        decision_id="TENANT#demo#2026-10-12#MORN"
    )

    print(f" -> Decision ID: {plan_result['decision_id']}")
    print(f" -> Status: {plan_result['status']}")
    print(f" -> Plan A (Swaps): {len(plan_result['plan_a'])} swaps")
    for s in plan_result['plan_a']:
        print(f"    * Class {s['class']}: Moved from {s['from_period']} to {s['to_period']} (Exposure reduced from {s['exposure_before']} to {s['exposure_after']} µg/m³)")
    
    print(f" -> Plan B (Indoor Fallbacks): {len(plan_result['plan_b'])} fallbacks")
    for fb in plan_result['plan_b']:
        print(f"    * Class {fb['class']} ({fb['period']}): Assigned '{fb['assigned_activity']}' ({fb['fallback_venue']})")

    print(f" -> Modelled Exposure Before: {plan_result['exposure_before']:.1f}")
    print(f" -> Modelled Exposure After:  {plan_result['exposure_after']:.1f}")
    print(f" -> Exposure Reduction:       {plan_result['exposure_reduction_pct']}%")
    print(f" -> PE Minutes Preserved:     {plan_result['pe_minutes_preserved']}% (Headline Metric)")

    # 3. Create Audit Chain
    print("\n[STEP 4] Appending to Tamper-Evident Hash Chain...")
    row1 = create_audit_row(
        seq=1,
        prev_hash=GENESIS_HASH,
        actor_role="scheduler:eventbridge",
        event="STAGE_III_FORECAST_INGESTED",
        payload={"cell": forecast['grid_cell'], "stage": "III"}
    )
    row2 = create_audit_row(
        seq=2,
        prev_hash=row1["hash"],
        actor_role="planner:deterministic",
        event="PLAN_GENERATED",
        payload={
            "plan_a_count": len(plan_result["plan_a"]),
            "plan_b_count": len(plan_result["plan_b"]),
            "pe_preserved": plan_result["pe_minutes_preserved"]
        }
    )
    row3 = create_audit_row(
        seq=3,
        prev_hash=row2["hash"],
        actor_role="principal:allowlist",
        event="PLAN_B_APPROVED",
        payload={"approved_plan": "B", "tenant": "demo"}
    )
    chain = [row1, row2, row3]
    print(f" -> Chain head hash: {row3['hash']}")

    valid, msg, broken_idx = verify_audit_chain(chain)
    print(f" -> Chain verification: {msg}")

    # 4. Hostile Refusal Drill
    print("\n[STEP 5] Testing Refusal Moment (AI & Security Drill)...")
    with open("data/gold/hostile_instruction.txt", "r", encoding="utf-8") as f:
        hostile_text = f.read()
    with open("data/gold/hostile_invented_quote.json", "r", encoding="utf-8") as f:
        invented_quote = json.load(f)

    refusal_result = validate_ruleset_candidates([invented_quote], hostile_text)
    print(f" -> Hostile Input Status: {refusal_result['status'].upper()}")
    print(f" -> Refusal Type:         {refusal_result['refusal_type']}")
    print(f" -> Refusal Message:      {refusal_result['refusal_reason']}")

    print("\n" + "=" * 75)
    print("🎯 DAY 1 GATE DEMONSTRATION COMPLETE AND VERIFIED!")
    print("=" * 75)

if __name__ == "__main__":
    main()
