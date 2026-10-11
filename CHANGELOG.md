# Changelog

All notable changes to the **Saans (साँस)** project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-10-11

### Added
- **Deterministic Schedule Planner:** Constraint-satisfaction engine resolving venue, teacher, and academic period conflicts while keeping 100% of planned physical activity minutes.
- **Order-First Rules Engine:** Categorizes timetable periods against statutory CAQM/DoE GRAP Stage I–IV mandates before evaluating PM2.5 forecasts.
- **AWS Serverless Cloud Backend:** Complete AWS SAM template (`infra/template.yaml`) deploying Step Functions Standard workflow, 16 Lambda micro-services, DynamoDB single-table, and Amazon API Gateway.
- **Cryptographic Audit Ledger:** SHA-256 tamper-evident hash chain with optimistic locking and nightly anchoring to **Amazon S3 with Object Lock (COMPLIANCE mode, 365-day retention)**.
- **In-Browser Public Verifier:** Self-contained client-side verification engine powered by the W3C Web Crypto API (`/verify/{id}`).
- **AI Safety & Zero-Hallucination Guardrails:** Amazon Bedrock Nova Lite integration via Converse API with prompt injection defense, verbatim quote validation, and strict notice digit whitelisting.
- **Multi-Tier Model Failover:** Transparent, auditable failover from Amazon Bedrock $\rightarrow$ Groq-hosted Llama-3 $\rightarrow$ Static bilingual template.
- **Bilingual Notification Generator:** English and Hindi notice drafting with Devanagari Unicode script enforcement and WhatsApp dispatch integration (Meta WhatsApp Cloud API / Twilio).
- **Human-in-the-Loop Workflow:** Step Functions `waitForTaskToken` integration with 60-second principal approval timer, role-bound nonces, and automated fail-safe shutdown.
- **48-Hour Forecast Watch:** Scheduled EventBridge evaluator (16:30 IST) generating proactive contingency drafts for upcoming school days.
- **Interactive Next.js 16 Web Application:** Turbopack-powered frontend featuring real-time GRAP Stage I–IV rehearsal slider, 3D Three.js school venue visualization, principal's brief, and public receipt viewer.
- **Full Automated Test Suite:** 272 passing unit, integration, and security tests across all services and state machine paths (`python run_all_tests.py`).
- **AWS Amplify Hosting Configuration:** `amplify.yml` deploying the Next.js frontend with SSR support, paired with the CloudFormation API backend.
