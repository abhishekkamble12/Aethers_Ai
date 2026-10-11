# Contributing to Saans (साँस)

Thank you for your interest in contributing to **Saans**! We welcome contributions to help protect school children from hazardous air pollution across Delhi-NCR.

---

## Development Setup

### Prerequisites
- **Python 3.10+** (Python 3.12 recommended)
- **Node.js 20+** and **npm**
- **AWS CLI** and **AWS SAM CLI** (for cloud deployment)

### 1. Clone & Setup Backend
```bash
git clone https://github.com/abhishekkamble12/Aethers_Ai.git
cd Aethers_Ai

python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt -r requirements-dev.txt
```

### 2. Run the Full Test Suite
Before making any code changes, ensure all 272 automated tests pass:
```bash
python run_all_tests.py
```
*(AWS services, Bedrock, and external APIs are mocked using `moto` and custom deterministic test doubles, requiring no AWS credentials).*

### 3. Setup Frontend
```bash
npm install
npm run dev       # Starts Next.js development server at http://localhost:3000
npm run build     # Validates production build with Turbopack
```

---

## Extending the System

### 1. Adding Statutory Rulesets
Official CAQM and DoE orders are defined in JSON:
- Default starting ruleset: `data/demo/ruleset_v1.json`
- Rules require statutory citations (`source`, `quote`, `rule_id`, `min_stage`, `actions`).
- To test ruleset validation against real circulars:
  ```bash
  python -m unittest tests.test_circular_validator
  ```

### 2. Adding School Profiles & Venues
- Timetable definitions: `data/demo/timetable_sample.csv`
- Class profiles & sensitive student counts: `data/demo/timetable_sample.csv`
- Indoor venues and ventilation factors: `data/demo/venues.json`
- Replay forecast scenarios: `data/demo/forecast_stage3_sample.json`

### 3. Adding AWS Lambda Services
All backend services reside under `services/`:
```
services/
  admin/       Demo seeding and reset endpoints
  audit/       SHA-256 hash chain and S3 Object Lock anchor
  circular/    Bedrock extraction, strict validator, diff engine
  common/      HTTP utilities, Bedrock Converse client, fallbacks
  forecast/    Open-Meteo CAMS forecast client and 48h watch
  health/      System health and dependency diagnostic probes
  notify/      Bilingual notice generator, output whitelist checker
  planner/     Deterministic constraint planner and stage simulator
  rules/       Order-first statutory period classifier
  workflow/    Step Functions triggers, task tokens, decision brief
```

When adding or modifying Lambda handlers:
1. Ensure the handler is declared in `infra/template.yaml`.
2. Run `python -m unittest tests.test_lambda_bundle` to verify bundle packaging.

---

## Coding Standards & Invariants

All pull requests must respect the core project invariants:
1. **Order First, Forecast Second:** Statutory circular bans can never be overridden by a clean forecast.
2. **Re-Plan, Don't Cancel:** The planner must prioritize rescheduling before proposing indoor fallbacks.
3. **Model Proposes, Code Decides:** AI proposals must always be vetted by deterministic code checks (verbatim quote match, number whitelist, Devanagari script integrity).
4. **Zero Hallucination:** Notices can only contain numbers derived directly from the verified plan fact sheet.
5. **No PII:** Never store individual student names, medical histories, or parent phone numbers.

---

## Submitting Pull Requests

1. Fork the repository and create your branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Commit your changes with clear, descriptive commit messages:
   ```bash
   git commit -m "feat: add support for Haryana NCR school schedules"
   ```
3. Ensure the test suite and frontend build pass with 100% success:
   ```bash
   python run_all_tests.py
   npm run lint
   npm run build
   ```
4. Push to your fork and submit a Pull Request to `main`.

---

## License

By contributing to Saans, you agree that your contributions will be licensed under the [MIT License](LICENSE).
