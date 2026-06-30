# AI Productivity Assistant

An end-to-end full-stack, AI-powered productivity and time management application designed to help users capture commitments, prioritize tasks, execute deep work sessions, and receive dynamic, personalized interventions using LLMs.

## 🚀 Key Features (End-to-End Application)

### 1. AI Superpowers & Orchestration
- **Smart Extraction:** Paste raw text (e.g., emails, messages) and let the LLM automatically extract structured commitment data (type, title, due date, amount).
- **AI Task Planning:** Generates step-by-step task breakdowns for larger commitments using LangGraph orchestration.
- **Intervention Engine:** Delivers dynamic, context-aware reminders based on user psychology and root causes (e.g., time crunch, procrastination, low motivation). Styles include Deadline, Achievement, Consequence, and Streak.
- **Recovery Plans:** AI generates actionable recovery steps when tasks fall behind or become high-risk.

### 2. Task & Commitment Management
- **Commitments Tracking:** High-level tracking for Bills, Interviews, Assignments, and Events.
- **Daily & Weekly Planning:** Granular task management allowing users to set daily highlights and weekly objectives.
- **Backlog & Review:** Systematic approach to moving tasks between the backlog and active execution, alongside weekly review rituals.

### 3. Deep Work & Focus
- **Focus Timer:** Built-in Pomodoro, Flowtime, and Deep Work timers integrated directly into the application.
- **Distraction Tracking:** Logs sessions and tracks interruptions to help improve deep work endurance over time.

### 4. Analytics & Insights
- **Productivity Dashboard:** Visualizes completion rates, focus hours, and overall productivity trends using interactive charts.
- **Contextual Reminders:** Smart reminders pushed based on deadlines and user interaction history.

---

## 🛠️ Technology Stack

### Frontend
- **Framework:** React 19 (via Vite)
- **Routing:** React Router v7
- **Styling:** Vanilla CSS (Custom Design System + Dark Mode)
- **Data Visualization:** Chart.js & React-Chartjs-2
- **Icons:** Lucide React

### Backend
- **Framework:** FastAPI (Python)
- **Database:** Supabase (PostgreSQL)
- **ORM:** SQLAlchemy with Pydantic for validation
- **AI & LLM:** NVIDIA NIM API, OpenAI SDK, Google GenAI, LangGraph (Workflow orchestration)
- **Background Tasks:** Celery + Redis
- **Authentication:** Google OAuth + Supabase Auth

---

## 🏗️ Backend Development Process (What We Have Built)

The backend is built as a robust, scalable FastAPI application utilizing a layered architecture:

### 1. Architecture & Modular Design
- **Entry Point (`main.py`):** Handles startup events, verifies database connectivity (fail-fast mechanism), auto-creates idempotent DB tables, and mounts all application routers.
- **Domain-Driven Routers:** Endpoints are strictly organized by domain: `auth`, `commitments`, `tasks`, `daily_plans`, `weekly_plans`, `focus`, `analytics`, and `ai`.
- **Services Layer:** Abstracted business logic out of routers. Services include `llm_service`, `intervention_engine`, `priority_engine`, `risk_engine`, and `context_service`.

### 2. Database & ORM
- **PostgreSQL via Supabase:** Utilizes `SQLAlchemy` for ORM mapping (`user`, `commitment`, `task`, `focus_session`, `reminder`, etc.).
- **Pydantic Schemas:** Strict request/response validation ensuring data integrity across the API.

### 3. AI Engineering & Workflow
- **LangGraph Integration (`ai_graph`):** We built a state-machine based AI orchestration layer. Endpoints like `/api/ai/extract`, `/plan`, `/recover`, and `/chat` invoke the `ai_graph` with specific user states and context.
- **LLM Clients:** Integrated `NVIDIA NIM` (using OpenAI-compatible SDK) for fast, structured JSON extraction and natural language planning. Fallback heuristic engines are in place if the API is unavailable.
- **Intelligent Engines:** 
  - *Intervention Engine:* Maps task status and user profiles to personalized reminder styles.
  - *Priority & Risk Engines:* Analyzes task deadlines, estimated effort, and historical data to flag high-risk commitments.

### 4. Background Processing
- **Celery & Redis:** Configured for asynchronous task execution and beat scheduling (e.g., sending out scheduled reminders or aggregating daily analytics).

---

## 🎨 Frontend Development Process (What We Have Built)

The frontend is a fast, responsive Single Page Application (SPA) focusing on a clean, distraction-free user experience.

### 1. State Management & Routing
- **React Context:** Used for global state management (`AuthContext` for user sessions and `StatsContext` for global application stats).
- **React Router:** Protected routes wrapping the application. If not authenticated, users are redirected to the Login page.

### 2. UI/UX & Pages
- **Layout Component:** A persistent shell housing the navigation sidebar, global top bar, and the main content outlet.
- **Core Pages:**
  - `Dashboard`: High-level overview of today's progress and active commitments.
  - `Today`: Focuses entirely on the daily plan and active tasks.
  - `Commitments`: Detailed list and modal views of high-level objectives.
  - `Focus`: Dedicated Pomodoro/Deep Work timer page.
  - `Analytics`: Chart.js driven visual reports on productivity.
  - `Weekly Planning / Review`: Interface for setting up the week's goals and reviewing past performance.

### 3. Styling Approach
- **Vanilla CSS:** We completely bypassed heavy utility frameworks like Tailwind in favor of strict, modular Vanilla CSS (`index.css`, `App.css`, `Today.css`, etc.).
- **CSS Variables:** Built a comprehensive design system utilizing CSS variables for colors, typography, spacing, and seamless Dark Mode integration.

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- Supabase Account (for PostgreSQL & Auth)
- Redis (if running background workers locally)

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Environment Setup
cp .env.example .env
# Fill in your SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, NVIDIA_API_KEY, etc.

# Start FastAPI Server
uvicorn app.main:app --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install

# Environment Setup
# Create a .env file based on the backend connections
# VITE_API_BASE_URL=http://localhost:8000
# VITE_SUPABASE_URL=...

# Start Vite Dev Server
npm run dev
```

### 3. Background Workers (Optional but Recommended)
In a separate terminal (ensure Redis is running):
```bash
cd backend
source venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info
```

---

## 📖 API Documentation

Once the backend is running, FastAPI auto-generates interactive API documentation:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

These endpoints provide complete visibility into the schemas and required payloads for all standard operations and AI functionalities.
