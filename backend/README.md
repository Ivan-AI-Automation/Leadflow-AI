# LeadFlow AI Backend

This is the FastAPI backend for LeadFlow AI.

The backend owns authentication, lead import processing, data validation, deterministic scoring, email draft management, dashboard metrics, and export generation.

## Main Responsibilities

- Register and authenticate users.
- Protect user data with JWT-based current-user dependencies.
- Accept CSV, XLSX, and XLS lead imports.
- Store import metadata and uploaded files.
- Load and clean spreadsheet data with pandas.
- Process imports into normalized Lead records.
- Detect missing contact information.
- Score leads with a deterministic Follow-up Priority Score.
- Track lead status and lead activity.
- Generate email drafts through an AI provider abstraction.
- Manage draft approval, rewrite, archive, and delete workflows.
- Export approved drafts to CSV or Excel.
- Serve dashboard summary metrics and chart-ready JSON.

## Backend Structure

```text
backend/
├── alembic/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       └── router.py
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   └── services/
│       ├── ai/
│       └── export/
├── scripts/
├── tests/
├── Dockerfile
├── alembic.ini
├── pyproject.toml
└── README.md
```

## Important Modules

- `app/main.py` creates the FastAPI app.
- `app/core/config.py` loads settings from environment variables.
- `app/core/errors.py` centralizes API error responses.
- `app/core/security.py` handles password hashing and JWT tokens.
- `app/db/session.py` creates SQLAlchemy sessions.
- `app/models/` contains SQLAlchemy models.
- `app/schemas/` contains Pydantic request and response schemas.
- `app/repositories/` contains database access helpers.
- `app/services/` contains business logic.
- `app/services/ai/` contains the mock, OpenAI, and Gemini providers.
- `app/services/export/` contains CSV and Excel export helpers.

## Run Locally

From the project root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ./backend
```

Create `.env` from the root example:

```bash
cp .env.example .env
```

For local SQLite development:

```env
DATABASE_URL=sqlite:///./leadflow.db
AI_PROVIDER=mock
```

Run migrations:

```bash
cd backend
alembic upgrade head
```

Start the backend:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or from the project root:

```bash
make backend
```

## Run With Docker

From the project root:

```bash
cp .env.example .env
docker compose up --build backend postgres
```

The backend container runs:

```bash
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Backend URL:

```text
http://localhost:8000
```

API docs:

```text
http://localhost:8000/docs
```

## Database

The backend supports two practical database modes.

SQLite for simple local development:

```env
DATABASE_URL=sqlite:///./leadflow.db
```

PostgreSQL for Docker development:

```env
DOCKER_DATABASE_URL=postgresql+psycopg://leadflow:replace-this-postgres-password@postgres:5432/leadflow
```

Inside Docker, the PostgreSQL host is `postgres`. From your host machine, PostgreSQL is available on `localhost:5432`.

## Migrations

Run all migrations:

```bash
alembic upgrade head
```

Create a migration after model changes:

```bash
alembic revision --autogenerate -m "Describe the schema change"
```

Rollback one migration:

```bash
alembic downgrade -1
```

## Tests and Quality

Run tests:

```bash
make test
```

Run tests with coverage:

```bash
make test-cov
```

Run Ruff:

```bash
make lint
```

Run mypy:

```bash
make type-check
```

The test suite focuses on business-critical behavior: authentication, imports, cleaning, scoring, lead workflows, dashboard data, AI mock generation, draft approval, and exports.

## API Groups

- `auth`: registration, login, current user.
- `imports`: upload, list, view, delete.
- `import_processing`: convert uploaded files into leads.
- `leads`: CRUD, filters, status tracking, activity.
- `scoring`: single-lead, import, and user-wide scoring.
- `dashboard`: summary metrics and chart-ready data.
- `email_drafts`: generation, bulk generation, approval, rewrite, archive.
- `exports`: CSV and Excel export plus download.
- `health`: service health check.

## AI Providers

Default local provider:

```env
AI_PROVIDER=mock
```

OpenAI:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key
```

Gemini:

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
```

The AI provider receives only lead-level context needed to draft an email. It does not receive raw uploaded spreadsheets or unrelated leads.

## Notes for Reviewers

This backend is intentionally not over-abstracted. Services hold business rules, repositories hold
database operations, and schemas keep API contracts separate from SQLAlchemy models.

The scoring engine is deterministic because lead priority is a business decision that should be
inspectable. AI is used for wording, not for deciding which leads matter.
