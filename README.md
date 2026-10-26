# StudyFlow

StudyFlow is a personal commitments planner built to help users organize assignments, work, events, and personal tasks in one place.

## Features

- Login with demo accounts
- Add, edit, and delete commitments
- Mark commitments as complete
- Organize commitments by date and type
- Optional start time, end time, and description
- User-specific data protected by backend authentication

## Tech Stack

- **Frontend:** React, TypeScript, Vite
- **Backend:** Python, Flask
- **Database:** PostgreSQL
- **Development:** Docker Compose

## Run Locally

1. Make sure Docker Desktop is running.
2. From the project root, run:

   ```bash
   docker compose up --build -d
   ```

3. Apply the database migration:

   ```bash
   docker compose exec db psql -U studyflow -d studyflow -v ON_ERROR_STOP=1 -f /migrations/001_initial_schema.sql
   ```

4. Create the demo accounts:

   ```bash
   docker compose exec backend python seed.py
   ```

5. Open **http://localhost:5173** in your browser.

## Demo Accounts

For local development only:

| Email | Password |
|---|---|
| adina@test.com | studentplanner123 |
| sarah@test.com | studentplanner123 |

## Deployment

StudyFlow is configured for deployment using Render. See the deployment environment variables and database migration steps before deploying.

