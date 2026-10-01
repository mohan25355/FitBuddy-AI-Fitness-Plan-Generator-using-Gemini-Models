# FitBuddy

FitBuddy is a FastAPI and Gemini-powered fitness planning app that generates a structured 7-day workout plan, a nutrition/recovery tip, and versioned follow-up plans based on user feedback.

## Features

- Personalized 7-day workout generation
- Goal and intensity-based planning
- Gemini-powered nutrition and recovery guidance
- Feedback-based plan adaptation with preserved history
- Versioned workout plans and feedback records
- Protected admin dashboard
- Server-rendered responsive UI with Jinja2
- SQLite-backed persistence with SQLAlchemy
- FastAPI API documentation at `/docs`

## Architecture

- `app/main.py` wires the FastAPI app, routes, error handling, and templates
- `app/db/` contains SQLAlchemy models and repository helpers
- `app/services/` contains Gemini orchestration and plan logic
- `app/schemas/` contains Pydantic validation models
- `app/templates/` and `app/static/` contain the server-rendered UI

## Tech Stack

- FastAPI
- SQLAlchemy
- SQLite
- Jinja2
- Google Gemini Python SDK (`google-genai`)
- Pydantic v2
- Uvicorn

## Project Structure

```text
app/
  api/
  core/
  db/
  schemas/
  services/
  static/
  templates/
tests/
run.py
requirements.txt
.env.example
```

## Environment Setup

1. Create a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and set the values.

Required variables:

- `GEMINI_API_KEY`
- `GEMINI_WORKOUT_MODEL`
- `GEMINI_FAST_MODEL`
- `DATABASE_URL`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD_HASH`
- `SECRET_KEY`

## Gemini API Setup

- Use the current `google-genai` SDK.
- Set `GEMINI_API_KEY` in `.env`.
- Set model names with environment variables so the code does not hardcode Gemini models.
- The verified local configuration in this workspace uses `gemini-flash-lite-latest` for both workout generation and fast nutrition or recovery responses.

## Database Setup

- SQLite is the default database for local development.
- The database URL is read from `DATABASE_URL`.
- The app creates tables on startup.

## Run Locally

```bash
python run.py
```

Or with Uvicorn:

```bash
uvicorn run:app --host 0.0.0.0 --port 8000
```

## Testing

```bash
pytest
```

Tests mock the AI behavior and verify validation, duplicate user IDs, persistence, plan versioning, and admin auth.

## API Documentation

- OpenAPI docs: `/docs`
- ReDoc: `/redoc`
- Health check: `/health`
- Workout generation: `/api/workouts/generate`
- Feedback adaptation: `/api/workouts/{id}/adapt`
- User lookup: `/api/users/{user_id}`
- User history: `/api/users/{user_id}/history`

## Deployment

- Set `DATABASE_URL` to a PostgreSQL connection string when ready.
- Keep `GEMINI_API_KEY` and admin credentials in environment variables.
- Run with Uvicorn or Gunicorn-compatible process managers.

## Security Notes

- Secrets are read from the environment.
- Gemini calls happen server-side only.
- Admin login is server-side and protected with a password hash.
- Forms use CSRF tokens.
- Validation blocks malformed user input before Gemini sees it.

## Troubleshooting

- If Gemini calls fail, confirm the API key and model names are set.
- If the admin dashboard is inaccessible, confirm `ADMIN_PASSWORD_HASH` is populated.
- If SQLite permissions fail, verify the working directory is writable.

## run command
.\.venv\Scripts\Activate.ps1

python run.py