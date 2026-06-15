# VeriSynth — Synthetic Data Engine (MVP)

> Generate useful fake data that keeps the patterns, removes the people, and documents the risk.

This is the MVP vertical slice of the VeriSynth product plan:
**CSV upload → profiling & PII detection → synthetic generation → privacy/utility safety scoring → evidence-based safety report**.

The safety angle is intentionally *evidence-based*. The report does not just
say "AI says it's safe" — it reports measured findings (duplicate rows,
nearest-neighbour similarity, PII leakage, distribution & correlation
fidelity), the kind of quantitative evidence a HIPAA Expert Determination or
NIST differential-privacy framing expects.

## Architecture

```
Synthetic Data Engine/
  apps/
    api/                 FastAPI + SQLite backend (the engine)
      app/
        main.py          app + CORS + router wiring
        config.py        env-driven settings
        database.py      SQLAlchemy engine/session
        models.py        projects, datasets, synthetic_runs, safety_reports
        schemas.py       Pydantic request/response models
        routers/         projects, datasets, runs
        services/
          profiler.py    column typing + PII/sensitive-field detection
          generator.py   statistical synthesis (Faker + copula sampling)
          safety.py      privacy + utility scoring
          report.py      deterministic report (+ optional OpenAI narrative)
      requirements.txt
      .env.example
    web/                 Next.js 14 + Tailwind frontend
      app/               dashboard, new project, project workspace
      lib/api.ts         typed API client
      components/ui.tsx  score rings, badges, checks
  storage/               SQLite db + uploads + generated CSVs (gitignored)
  sample_data/           example CSV to try the flow
```

## Privacy-by-design with OpenAI

OpenAI is **optional**. With no key, a deterministic local engine writes the
report. If `OPENAI_API_KEY` is set, only the **schema + aggregate statistics**
are sent to the model to write a narrative summary — never raw rows.

## Quick start (Windows / PowerShell)

### 1. Backend

```powershell
cd "apps\api"
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env   # optional: add OPENAI_API_KEY
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

API runs at http://127.0.0.1:8000 (interactive docs at `/docs`).

### 2. Frontend

```powershell
cd "apps\web"
npm install
npm run dev
```

App runs at http://localhost:3000 and proxies `/api/*` to the backend.

### 3. Try it

1. Create a project.
2. Upload `sample_data/patient_appointments.csv`.
3. Review the profiler's PII/risk findings.
4. Generate synthetic rows, preview them, download the CSV.
5. Run the safety scan and read the evidence-based report; approve or reject.

## Roadmap (from the product plan)

- Excel/JSON intake, scenario/edge-case generator
- GAN-based & differential-privacy generation modes
- Multi-table relational + time-series synthesis
- Auth + RBAC, audit logs, Postgres/Redis/Celery, S3 storage
- Industry template library, database connectors, API access
