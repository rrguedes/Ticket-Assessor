---
name: Ticket Triage App
description: FastAPI + PostgreSQL ticket triage system; Python 3.11; not registered as a Replit artifact.
---

## Key facts

- Lives in `ticket-triage/` — a standalone Python package, NOT a pnpm artifact.
- Workflow name: **"Ticket Triage App"** — `cd ticket-triage && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- Port 8000 (supported by Replit proxy).
- DB tables created at startup via `Base.metadata.create_all(bind=engine)` — no migration tool.
- Python packages installed via `installLanguagePackages` callback (not pip directly — `pip` is not on PATH).

**Why:** FastAPI/Python stack requested by user; existing workspace is Node.js so a separate directory was used rather than an artifact template.

**How to apply:** To restart the app use `WorkflowsRestart({ name: "Ticket Triage App" })`. To run tests: `cd ticket-triage && python3 -m pytest tests/ -v`.
