# StudyFlow

A personal commitments planner built with React, TypeScript, Flask, and PostgreSQL.

## Features
- Login with demo accounts
- Create, edit, and delete commitments
- Mark commitments as complete
- Filter by upcoming and completed items
- Keep each user's commitments private

## Tech Stack
- Frontend: React, TypeScript, Vite
- Backend: Python, Flask
- Database: PostgreSQL
- Local development: Docker Compose

## Run Locally
1. Create a `.env` file with the required `SECRET_KEY`.
2. Start the services:

   ```bash
   docker compose up --build -d
   ```

3. Apply the database migration and seed the demo accounts if setting up a fresh database.
4. Open http://localhost:5173.

## Demo Accounts
Both accounts use the password `studentplanner123`.

- `adina@test.com`
- `sarah@test.com`

**Note:** Demo credentials are for local development only.