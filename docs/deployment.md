# LeadFlow AI Deployment Guide

LeadFlow AI is designed to run in two practical modes:

- Local development with SQLite for a fast backend-only setup.
- Docker development with PostgreSQL, FastAPI, and Streamlit running together.

The default AI provider is `mock`, which generates deterministic local email drafts and does not call an external API.

## 1. Local development

Create a local environment file:

```bash
cp .env.example .env
```

For simple local development, keep SQLite enabled:

```env
DATABASE_URL=sqlite:///./leadflow.db
AI_PROVIDER=mock
```

Install backend dependencies:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In a second terminal, run the frontend:

```bash
cd frontend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
BACKEND_API_URL=http://localhost:8000 streamlit run app/main.py --server.port 8501
```

Open:

- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Frontend: `http://localhost:8501`

## 2. Docker development

Create a Docker environment file:

```bash
cp .env.example .env
```

For Docker, PostgreSQL is used through `DOCKER_DATABASE_URL`:

```env
POSTGRES_USER=leadflow
POSTGRES_PASSWORD=replace-this-postgres-password
POSTGRES_DB=leadflow
DOCKER_DATABASE_URL=postgresql+psycopg://leadflow:replace-this-postgres-password@postgres:5432/leadflow
```

Replace the placeholder passwords and `SECRET_KEY` before sharing or deploying the project.
Docker Compose requires these values so the stack does not quietly start with hidden default
secrets.

Start the application:

```bash
docker compose up --build
```

Open:

- FastAPI backend: `http://localhost:8000`
- Streamlit frontend: `http://localhost:8501`
- PostgreSQL: `localhost:5432`

Stop the application:

```bash
docker compose down
```

Remove PostgreSQL and pgAdmin volumes when you want a clean database:

```bash
docker compose down -v
```

Run pgAdmin when you need a database UI:

```bash
docker compose --profile tools up pgadmin
```

Open pgAdmin at `http://localhost:5050`.

Inside pgAdmin, connect to PostgreSQL with:

- Host: `postgres`
- Port: `5432`
- Database: `leadflow`
- Username: the value of `POSTGRES_USER`
- Password: the value of `POSTGRES_PASSWORD`

## 3. Environment variables

Core variables:

| Variable | Purpose | Typical local value |
| --- | --- | --- |
| `APP_NAME` | Display name for the API | `LeadFlow AI API` |
| `ENVIRONMENT` | Runtime environment label | `development` |
| `LOG_LEVEL` | Backend logging level | `INFO` |
| `SECRET_KEY` | JWT signing secret | Use a long random value |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime | `60` |
| `DATABASE_URL` | Backend database URL for local runs | `sqlite:///./leadflow.db` |
| `DOCKER_DATABASE_URL` | Backend database URL inside Docker | PostgreSQL URL using host `postgres` |
| `UPLOAD_DIR` | Uploaded import storage | `../uploads` locally, `/app/uploads` in Docker |
| `EXPORT_DIR` | Exported file storage | `../exports` locally, `/app/exports` in Docker |
| `MAX_UPLOAD_SIZE_MB` | Upload size limit | `10` |
| `BACKEND_API_URL` | Frontend API URL for local frontend runs | `http://localhost:8000` |
| `FRONTEND_BACKEND_API_URL` | Frontend API URL used by Docker Compose | `http://backend:8000` |
| `AI_PROVIDER` | AI provider selection | `mock` |
| `OPENAI_API_KEY` | OpenAI API key when using OpenAI | empty by default |
| `GEMINI_API_KEY` | Gemini API key when using Gemini | empty by default |

Do not commit real secrets. Keep real production values in the deployment platform secret manager or on the server as protected environment variables.

## 4. Database migrations

LeadFlow AI uses Alembic for database migrations.

Run migrations locally:

```bash
cd backend
alembic upgrade head
```

Create a new migration after model changes:

```bash
cd backend
alembic revision --autogenerate -m "Describe the schema change"
```

Rollback one migration:

```bash
cd backend
alembic downgrade -1
```

In Docker, the backend startup script runs this command before starting FastAPI:

```bash
alembic upgrade head
```

Disable automatic migrations only when you want to run them manually:

```env
RUN_MIGRATIONS=false
```

Then run:

```bash
docker compose run --rm backend alembic upgrade head
```

## 5. Running tests

Run the backend test suite:

```bash
make test
```

Run tests with coverage:

```bash
make test-cov
```

Run linting:

```bash
make lint
```

Run type checking:

```bash
make type-check
```

Run the main quality check:

```bash
make quality
```

The tests use an isolated test database and do not require Docker.

## 6. Deployment options

### Render

Use two web services and one managed PostgreSQL database:

1. Create a PostgreSQL database.
2. Create a backend web service from `backend/Dockerfile`.
3. Set `DATABASE_URL` to the Render PostgreSQL internal connection string.
4. Set `SECRET_KEY`, `AI_PROVIDER`, and provider API keys as environment variables.
5. Create a frontend web service from `frontend/Dockerfile`.
6. Set `BACKEND_API_URL` to the public backend URL.

Render can run Dockerfiles directly, which keeps the setup close to local Docker development.

### Railway

Use one PostgreSQL service and two app services:

1. Add a PostgreSQL plugin.
2. Deploy the backend from the `backend` directory.
3. Deploy the frontend from the `frontend` directory.
4. Set the backend `DATABASE_URL` to Railway PostgreSQL.
5. Set the frontend `BACKEND_API_URL` to the backend public URL.

Railway is convenient for quick portfolio demos because it handles networking and database provisioning with little setup.

### Fly.io

Use Fly apps plus managed or external PostgreSQL:

1. Create one Fly app for the backend.
2. Create one Fly app for the frontend.
3. Use Fly Postgres or an external PostgreSQL provider.
4. Store secrets with `fly secrets set`.
5. Expose backend port `8000` and frontend port `8501`.

Fly.io is a good option when you want more control over regions and container behavior.

### VPS

Use Docker Compose on a small Linux server:

1. Install Docker and Docker Compose.
2. Copy the project to the server.
3. Create `.env` from `.env.example`.
4. Replace all placeholder secrets.
5. Run `docker compose up -d --build`.
6. Put Nginx, Caddy, or Traefik in front of the backend and frontend.
7. Enable HTTPS with Let's Encrypt.

For a portfolio project, a VPS is useful because it demonstrates practical operational knowledge.

## 7. Common issues

### The backend cannot connect to PostgreSQL

Check that the Docker database URL uses host `postgres`, not `localhost`:

```env
DOCKER_DATABASE_URL=postgresql+psycopg://leadflow:password@postgres:5432/leadflow
```

Inside Docker, `localhost` means the backend container itself.

### The frontend cannot reach the backend

When Streamlit runs locally outside Docker, use the backend URL from your machine:

```env
BACKEND_API_URL=http://localhost:8000
```

When Streamlit runs inside Docker Compose, use the backend service name:

```env
FRONTEND_BACKEND_API_URL=http://backend:8000
```

For deployed environments, set it to the public backend URL.

### Tables are missing

Run migrations:

```bash
cd backend
alembic upgrade head
```

Or in Docker:

```bash
docker compose run --rm backend alembic upgrade head
```

### Uploaded files or exports are missing after restart

Docker Compose mounts these host folders:

- `uploads`
- `exports`

Make sure the folders exist and the container has permission to write to them.

### Port already in use

Change the host ports in `.env`:

```env
BACKEND_PORT=8001
FRONTEND_PORT=8502
POSTGRES_PORT=5433
```

The container ports stay the same.

### JWT tokens fail after restart

Do not change `SECRET_KEY` between runs unless you are fine with invalidating existing tokens.

## 8. How to switch between MockAIProvider and real AI providers

Use the mock provider for local development:

```env
AI_PROVIDER=mock
```

Use OpenAI:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key
```

Use Gemini:

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
```

The AI provider is used only to generate and rewrite email drafts. Lead scoring stays deterministic and does not use AI.

If a real provider is selected without its API key, the backend returns a clear provider configuration error instead of silently falling back to mock output.
