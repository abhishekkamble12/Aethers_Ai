# Contributing to Saans

## Set up

```bash
git clone https://github.com/abhishekkamble12/Aethers_Ai.git
cd Aethers_Ai

# Backend (Python 3.10+; Lambda runs 3.12)
python -m venv .venv
.venv/Scripts/activate            # Windows. On macOS or Linux: source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Front end (Node 20.9+)
npm install
```

## Check your change

```bash
python run_all_tests.py           # every test; AWS, Bedrock, the fallback model and Twilio are faked
npm run lint
npm run build
```

CI runs the same three on every push and pull request. Keep them green.

## Where things go

| To change | Edit |
| :--- | :--- |
| What a GRAP stage stops or allows | `data/demo/ruleset_v1.json` (a new ruleset from a circular goes through `services/circular/`, which validates it and asks for approval) |
| Rooms and grounds the planner can use | `data/demo/venues.json`, with indoor air factors in `data/demo/indoor_air.json` |
| Classes with sensitive students | `data/demo/class_profiles.json` and `data/demo/sensitivity_policy.json` |
| Planning logic | `services/planner/` and `services/rules/` |
| Notice wording and checks | `services/notify/` |
| Front-end pages | `app/`, with shared parts in `components/` and `lib/` |

### Adding a Lambda handler

1. Write the handler in the relevant package under `services/`.
2. Declare it in `infra/template.yaml` (`Handler: services.<package>.<module>.<function>`).
3. Run the tests. `tests/test_lambda_bundle.py` builds the deploy bundle and imports every handler the template
   declares, so a missing import fails here instead of on AWS.
4. Deploy with `python scripts/deploy.py` (see the README's "Deploy to AWS").

## Rules the code keeps

- The model proposes, code checks, a person approves. Model output never reaches a plan or a parent without a check
  in code.
- Every decision is appended to the hash-chained audit log. Do not edit or delete audit rows.
- No child-level data and no real phone numbers in code, fixtures or the audit chain.
- Never commit secrets. Keys live in git-ignored `infra/.env`, `infra/deploy.secrets` and `.env.local`.
