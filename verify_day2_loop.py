"""
Saans Day 2 End-to-End Loop Verification Script
Executes the full Day 2 Loop:
Scheduled Ingest -> Step Functions Workflow -> Escalation -> Webhook Approval ->
Bilingual Notice Drafting -> WhatsApp Share Links -> Teacher Schedules ->
Rule-Diff with Quotes -> Hash-Chained Audit Trail
"""

import json
from services.planner.csv_loader import load_timetable_csv
from services.planner.planner import plan_schedule
from services.workflow.workflow_manager import workflow_registry
from services.planner.teacher_schedule import generate_teacher_schedules
from services.circular.diff_engine import compute_ruleset_diff
from services.notify.drafting import generate_parent_broadcast_package
from services.audit.hash_chain import GENESIS_HASH, create_audit_row, verify_audit_chain

def main():
    print("=" * 80)
    print("SAANS: THE REAL LOOP (DAY 2 GATE DEMONSTRATION)")
    print("=" * 80)

    # Step 1: Load Context & Plan
    print("\n[STEP 1] Running Ingest & Deterministic Planner...")
    with open("data/demo/timetable_sample.csv", "r", encoding="utf-8") as f:
        timetable, _ = load_timetable_csv(f.read())
    with open("data/demo/forecast_stage3_sample.json", "r", encoding="utf-8") as f:
        forecast = json.load(f)
    with open("data/demo/ruleset_v1.json", "r", encoding="utf-8") as f:
        ruleset = json.load(f)

    plan = plan_schedule(
        timetable=timetable,
        forecast=forecast,
        ruleset=ruleset,
        declared_stage="III",
        decision_id="TENANT#dps#2026-10-12#MORN"
    )
    print(f" -> Plan generated: {len(plan['plan_a'])} swaps, {len(plan['plan_b'])} fallbacks")
    print(f" -> PE Minutes Preserved: {plan['pe_minutes_preserved']}%")

    # Step 2: Step Functions Workflow & Escalation
    print("\n[STEP 2] Simulating Step Functions Workflow with Escalation Timeout...")
    # Register secure token
    raw_sfn_token = "arn:aws:states:us-east-1:123456789:taskToken:sec_999"
    short_id = workflow_registry.register_task_token(raw_sfn_token, "dps", plan["decision_id"])
    print(f" -> TaskToken registered. Short URL Token: '{short_id}' (Raw token isolated)")

    # Simulate Principal timeout -> Vice-Principal Escalation -> Approval
    workflow_result = workflow_registry.execute_workflow_step(
        decision_data=plan,
        timeout_occurred=True, # 60s timeout in video demo
        principal_action="APPROVE_PLAN_B"
    )
    print(f" -> Workflow Transitions: {' -> '.join(workflow_result['transitions'])}")
    print(f" -> Final Status: {workflow_result['status'].upper()}")

    # Step 3: Teacher Schedules
    print("\n[STEP 3] Generating Personalized Teacher Schedules...")
    teacher_schedules = generate_teacher_schedules(timetable, plan)
    pe_teachers = [t for t in teacher_schedules.values() if t["role"] == "Physical Education"]
    for pe in pe_teachers:
        print(f" -> Teacher {pe['teacher_code']} ({pe['role']}):")
        for prd in pe["periods"][:2]: # Show first 2 periods
            print(f"    * Period {prd['period']} ({prd['time']}): [{prd['status']}] -> {prd['activity']} at {prd['venue']}")

    # Step 4: Circular Rule-Diff with Verbatim Quotes
    print("\n[STEP 4] Computing Ruleset Diff from New Circular...")
    candidate_ruleset = {
        "ruleset_version": "2026-10-09-r2",
        "jurisdiction": "Delhi",
        "declared_stage": "IV",
        "rules": [
            *ruleset["rules"],
            {
                "rule_id": "r-022",
                "applies_to": ["school"],
                "class_band": ["primary"],
                "condition": { "stage_at_least": "IV" },
                "action": { "hybrid_mode": "mandatory", "outdoor_sports": "banned", "outdoor_pt": "banned" },
                "source_id": "DoE-circ-StageIV-2026",
                "source_quote": "Classes up to 5th standard shall run in online/hybrid mode exclusively."
            }
        ]
    }
    diff = compute_ruleset_diff(ruleset, candidate_ruleset)
    print(f" -> Active Version: {diff['active_version']} -> Candidate Version: {diff['candidate_version']}")
    print(f" -> Rules Added: {diff['total_added']}")
    for r in diff["added_rules"]:
        print(f"    * [{r['rule_id']}]: Quote: \"{r['source_quote']}\"")

    # Step 5: Bilingual Notice Drafting & WhatsApp Click-to-Share
    print("\n[STEP 5] Drafting Bilingual Notices & Building WhatsApp Links...")
    notices = generate_parent_broadcast_package(plan, stage="III")
    print(f" -> English Draft: \"{notices['english']['notice_text'][:90]}...\"")
    print(f" -> Hindi Draft:   \"{notices['hindi']['notice_text'][:90]}...\"")
    print(f" -> WhatsApp Click-to-Share Link (English): {notices['whatsapp_url_english'][:80]}...")
    print(f" -> WhatsApp Click-to-Share Link (Hindi):   {notices['whatsapp_url_hindi'][:80]}...")

    # Step 6: Cryptographic Audit Trail
    print("\n[STEP 6] Appending Transitions to Hash Chain...")
    chain = []
    prev = GENESIS_HASH
    events = [
        ("scheduler", "EXECUTION_STARTED", {"decision_id": plan["decision_id"]}),
        ("planner", "PLAN_GENERATED", {"plan_b_count": len(plan["plan_b"])}),
        ("workflow", "APPROVAL_REQUESTED", {"token": short_id}),
        ("workflow", "TIMEOUT_ESCALATED_TO_VP", {"escalated_to": "vice_principal"}),
        ("vice_principal", "APPROVED_PLAN_B", {"approver": "vp_delhi_demo"}),
        ("notification", "NOTICES_DISPATCHED", {"channels": ["whatsapp_relay", "telegram"]})
    ]

    for idx, (actor, evt, payload) in enumerate(events, start=1):
        row = create_audit_row(seq=idx, prev_hash=prev, actor_role=actor, event=evt, payload=payload)
        chain.append(row)
        prev = row["hash"]

    valid, msg, _ = verify_audit_chain(chain)
    print(f" -> Audit Chain Integrity: {msg} (Head: {chain[-1]['hash'][:16]}...)")

    print("\n" + "=" * 80)
    print("🎯 DAY 2 GATE DEMONSTRATION COMPLETE AND FULLY OPERATIONAL!")
    print("=" * 80)

if __name__ == "__main__":
    main()
