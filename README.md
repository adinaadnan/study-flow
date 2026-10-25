# Studyflow

Studyflow is a personal commitments planner. The current backend includes
PostgreSQL schema migrations and session-based demo-account authentication.

## Prerequisites

- Docker Desktop with Docker Compose
- Node.js 18 or newer and npm, if running the frontend outside Docker
- Python 3.10 or newer, if running the backend outside Docker
- `psql`, if applying migrations to a locally installed PostgreSQL instance

## Docker development setup

Create a `.env` file in the project root with the PostgreSQL settings below and
a newly generated secret. Generate a secret with:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Example `.env` (replace the secret placeholder with the generated value):

```dotenv
POSTGRES_DB=studyflow
POSTGRES_USER=studyflow
POSTGRES_PASSWORD=studyflow_dev_only
SECRET_KEY=replace-with-generated-secret
SESSION_COOKIE_SECURE=false
```

Do not commit `.env`, use the example database password in production, or set
`SESSION_COOKIE_SECURE=false` outside local HTTP development.

From the project root, run these commands in order. The migration is deliberate:
starting Flask or Compose does not apply it.

```powershell
docker compose up -d db
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /migrations/001_initial_schema.sql'
docker compose run --build --rm backend flask --app app seed-demo-users
docker compose up --build
```

Apply each migration once to each database, in version order. Do not rerun the
initial migration on a database where its tables already exist. The seed command
is repeatable: it creates missing demo accounts and does not change existing
passwords.

The demo accounts are `adina@test.com` and `sarah@test.com`; both use
`studentplanner123`.

- Frontend: <http://localhost:5173>
- Backend health endpoint: <http://localhost:5000/health> (application health only)
- PostgreSQL: `localhost:5432`

Stop foreground services with `Ctrl+C`; run `docker compose down` to remove the
containers. The PostgreSQL data volume is retained. Use `docker compose down -v`
only if you intentionally want to delete local database data.

## Run the backend and database locally

Start a local PostgreSQL server. In PowerShell, create a development database
role and database (these credentials are only for local development):

```powershell
psql -U postgres -d postgres
```

At the `psql` prompt, run:

```sql
CREATE ROLE studyflow WITH LOGIN PASSWORD 'studyflow_dev_only';
CREATE DATABASE studyflow OWNER studyflow;
\q
```

From the project root, set these environment variables in PowerShell. Use a
newly generated secret instead of the placeholder:

```powershell
$env:DATABASE_URL = "postgresql://studyflow:studyflow_dev_only@localhost:5432/studyflow"
$env:SECRET_KEY = "paste-a-newly-generated-secret-here"
$env:SESSION_COOKIE_SECURE = "false"
```

Create a virtual environment and install backend dependencies:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

From `backend/`, apply the migration, seed accounts, then start Flask:

```powershell
psql "$env:DATABASE_URL" -f ..\database\migrations\001_initial_schema.sql
python -m flask --app app seed-demo-users
python -m flask --app app run --debug
```

For a local frontend, use a separate terminal:

```powershell
cd frontend
npm install
```

Set the API proxy target for a locally running frontend and backend, then start Vite:

```powershell
$env:VITE_API_PROXY_TARGET = "http://localhost:5000"
npm run dev
```

When using Docker Compose, Vite proxies API requests to the Compose `backend`
service automatically. For deployment, configure the frontend host to forward
`/api/*` requests to the Flask service on the same origin; session cookies rely
on this same-origin arrangement.

## Backend checks

These unit tests use mocks and do not need a running PostgreSQL server:

```powershell
cd backend
python -m pytest
```

For Docker-based verification, start the services with the setup commands above,
then check `/health` and the login endpoints. `/health` does not verify database
connectivity.

Frontend production build:

```powershell
cd frontend
npm install
npm run build
```

# study-flow