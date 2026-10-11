# Changelog

## [0.1.0] - 2026-10-11

First submitted version.

### Added

- Deterministic planner that re-plans the school day for GRAP Stages I–IV: no teacher or venue double-booking, indoor
  sessions placed in the cleanest free room, and stricter limits for classes with sensitive students.
- Live Open-Meteo (CAMS) forecast mapped onto periods, with a labelled replay fallback, a forecast chart API and a
  forecast watch for early warning.
- Step Functions approval workflow: the principal approves through a single-use, role-bound link, with escalation and
  fail-safe outcomes, and idempotent runs started by schedule or `POST /runs`.
- SHA-256 hash-chained audit log in DynamoDB, public receipts, and a verifier that recomputes the chain in the browser.
- Bilingual (English and Hindi) notices drafted by Bedrock, with a labelled fallback model, a static template, and a
  code check of every number in the output. Notice provenance is recorded in the audit chain.
- Circular reader: Bedrock extracts candidate rules from a CAQM or DoE order, a strict validator checks them, and a
  person approves the ruleset diff.
- Demo WhatsApp delivery through Meta's Cloud API or Twilio.
- Next.js front end on live data: Rehearse (3D school and live re-plan), Today (the principal's brief) and Receipt.
- One-command deploy (`scripts/deploy.py`), demo seed and reset, `GET /health`, and Amplify Hosting for the front end.
- 265 tests.
