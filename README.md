# AI Productivity Assistant

Full-stack: FastAPI + Vanilla JS + Supabase + NVIDIA NIM

## Project Structure
```
backend/          FastAPI Python API
  app/
    main.py           Entry point, router mounting, lifespan
    config.py         All env vars (pydantic-settings)
    database.py       SQLAlchemy engine + Supabase client
    models/           ORM models (user, commitment, task, focus_session, reminder)
    schemas/          Pydantic request/response schemas
    routers/          API route handlers (auth, commitments, tasks, focus, reminders, analytics)
    services/         Business logic (llm, priority, risk, root_cause, graph, intervention, focus)
    workers/          Celery tasks + beat scheduler
  migrations/       SQL schema (run in Supabase SQL Editor)
  requirements.txt
  .env.example      Copy to .env and fill in keys
  Dockerfile
  docker-compose.yml

frontend/         Single-page app (no framework)
  index.html        All UI: login, dashboard, focus timer, analytics, modals
  assets/
    style.css       Full design system + dark mode
    api.js          All API calls
    app.js          Dashboard, commitment list, detail modal
    focus.js        Pomodoro/Flowtime/DeepWork timer
    analytics.js    Chart.js analytics
```

## Quick Start

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Fill in keys
uvicorn app.main:app --reload
```

### Database (Supabase)
Run `backend/migrations/init_schema.sql` in Supabase SQL Editor.

### Frontend
```bash
cd frontend
python -m http.server 5500
# Open http://localhost:5500 and click "Try Demo"
```

### Background Workers (optional)
```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info
```

API Docs: http://localhost:8000/docs
