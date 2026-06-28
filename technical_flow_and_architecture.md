# Technical Architecture & Data Flow

This document outlines the technical architecture, data flow, and development lifecycle for the AI Productivity Assistant. It is intended for software engineers to understand how the system is constructed, how data moves across layers, and how to implement new features.

## 1. System Architecture Overview

The system follows a modern decoupled architecture:
*   **Frontend**: React Single-Page Application (SPA) built with Vite.
*   **Backend API**: Python FastAPI application acting as the central orchestrator.
*   **Database**: Relational Database via SQLAlchemy (SQLite for local dev, Supabase PostgreSQL for production).
*   **AI Engine**: LangGraph orchestration with Google GenAI SDK (`gemini-3.5-flash`).
*   **Asynchronous Workers**: Celery with Redis as the message broker for background jobs (like reminders).

## 2. Directory Structure & Responsibilities

### Backend (`backend/app/`)
*   `main.py`: The entry point. Initializes FastAPI, sets up CORS, connects DB (`Base.metadata.create_all`), and mounts all routers.
*   `routers/`: Presentation layer. Defines HTTP endpoints (e.g., `routers/tasks.py` for `/api/tasks`). They handle request validation via Pydantic schemas and delegate logic to services.
*   `services/`: Business logic layer. Keeps routers thin. Contains engines for complex operations (e.g., `focus_service.py`, `priority_engine.py`).
*   `models/`: Data Access layer. SQLAlchemy ORM classes (`User`, `Commitment`, `Task`, `FocusSession`).
*   `schemas/`: Data Transfer Objects (DTOs). Pydantic models for request/response validation.
*   `ai/`: The AI orchestration layer.
    *   `graph/`: LangGraph state graphs (`nodes.py`, `router.py`, `state.py`).
    *   `agents/`: Specific agent logic (`commitment_agent.py`, `planner_agent.py`).

### Frontend (`src/`)
*   `App.jsx`: Main React router and authentication gatekeeper.
*   `services/api.js`: Axios/Fetch wrappers for API communication. Handles auth tokens.
*   `pages/`: Top-level route components (`Dashboard.jsx`, `Focus.jsx`).
*   `components/`: Reusable UI elements (`Layout.jsx`, `TaskItem.jsx`).

## 3. Deep Dive: How Data Flows

Let's trace the exact data flow for key features.

### Flow A: AI Task Breakdown (The AI Pipeline)
When a user asks the AI to break down a large commitment into tasks:

1.  **Frontend**: User clicks "Plan with AI" on a Commitment. React calls `POST /api/ai/plan` with the `commitment_id` in the payload.
2.  **API Router (`routers/ai.py`)**: Receives the request. Extracts the user ID from the JWT token via dependency injection.
3.  **Context Gathering (`services/context_service.py`)**: The router calls `ContextService` to fetch relevant user state from the database (e.g., existing tasks, past focus sessions). This ensures the LLM generates a grounded and personalized plan.
4.  **AI Orchestration (`ai/graph/router.py`)**: 
    *   The router passes the context and the user prompt into the **LangGraph** orchestration graph.
    *   The graph transitions through nodes (e.g., `PlannerAgent`).
    *   The `PlannerAgent` uses `services/llm_client.py` to communicate with the Google GenAI API (`gemini-3.5-flash`), submitting the enriched prompt.
5.  **Output Parsing (`services/parser.py`)**: The raw text output from the LLM is passed through a Pydantic parser. This critical step ensures the AI's response matches the strictly expected JSON structure (a list of tasks) rather than conversational text.
6.  **Database Persistence (`routers/tasks.py` via service calls)**: The structured subtasks are written to the database using SQLAlchemy (`app.models.task.Task`).
7.  **Response**: The router returns the newly created tasks as serialized JSON to the frontend.
8.  **UI Update**: React receives the HTTP 200 response, updates its local React state, and triggers a re-render to display the newly generated tasks under the Commitment.

### Flow B: Focus Session Tracking (Stateful Updates)
1.  **Frontend**: User starts a Pomodoro timer in `Focus.jsx`.
2.  **API Router**: React sends `POST /api/focus/start`.
3.  **Backend**: `routers/focus.py` validates the request, creates a new `FocusSession` record in the database with `start_time = now()` and `status = 'active'`, and returns the session ID.
4.  **Completion**: When the timer ends, the frontend sends `POST /api/focus/{session_id}/complete`.
5.  **Service Logic (`services/focus_service.py`)**: The backend retrieves the session, calculates the total duration, marks the session complete, and commits the transaction. It may also queue a `Celery` task to analyze productivity patterns asynchronously.

## 4. How to Build a New Feature (End-to-End Guide)

If you need to build a new feature (e.g., "Project Tags"), follow this step-by-step lifecycle:

**Step 1: Database Model (`models/`)**
*   Create a new SQLAlchemy model (e.g., `models/tag.py`).
*   Define columns (`id`, `name`) and relationships (e.g., a many-to-many relationship between `Task` and `Tag`).
*   Generate an Alembic migration (if using migrations) or restart the app to let `Base.metadata.create_all` construct the table in local SQLite.

**Step 2: Pydantic Schemas (`schemas/`)**
*   Create validation schemas in `schemas/tag.py`.
*   Standard pattern requires three schemas: 
    *   `TagBase` (shared fields like `name`).
    *   `TagCreate` (for POST requests, inherits from `TagBase`).
    *   `TagResponse` (for returning data, includes `id` and `model_config = ConfigDict(from_attributes=True)`).

**Step 3: Business Logic (`services/`)**
*   (Optional but recommended) Create `services/tag_service.py` to abstract complex logic away from the router, such as tag deduplication or usage counting.

**Step 4: API Router (`routers/`)**
*   Create `routers/tags.py`.
*   Define the FastAPI endpoints: `@router.get("/")`, `@router.post("/")`.
*   Inject the database session (`db: Session = Depends(get_db)`) and current user (`current_user = Depends(get_current_user)`).
*   Use SQLAlchemy to query or insert data, returning the Pydantic schemas.

**Step 5: Router Mounting (`main.py`)**
*   Import your new router: `from app.routers import tags`.
*   Mount it to the main application: `app.include_router(tags.router, prefix="/api/tags", tags=["Tags"])`.

**Step 6: Frontend Integration (`src/services/api.js`)**
*   Add functions like `createTag(tagData)` and `fetchTags()` to your HTTP service wrapper, ensuring the JWT token is attached to the headers.

**Step 7: Frontend UI (`src/components/` & `src/pages/`)**
*   Create React components to display and input tags.
*   Use hooks like `useEffect` to load tags on mount and update local state when a new tag is successfully saved via the API.

## 5. Security & Authentication Data Flow
*   **Method**: JWT (JSON Web Tokens).
*   **Login Flow**: User submits credentials to `POST /api/auth/login`. The backend verifies the password hash. If valid, it generates a JWT containing the `user_id` and an expiration time, signed with a secret key (`python-jose`).
*   **Protection Flow**: Every protected endpoint relies on the `Depends(get_current_user)` dependency injection. This function intercepts the request, reads the `Authorization: Bearer <token>` header, decodes the JWT, verifies the signature, and fetches the user from the database. If any step fails, it throws a `401 Unauthorized` exception before the router logic ever executes.
