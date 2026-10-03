# ⬛ BLACK BOX — AI Agent Flight Recorder & Diagnostics

> **Autonomous Agent Observability, Failure Localization, and Checkpointed Replay Engine**

Welcome to **Black Box**, a flight recorder and diagnostics platform for autonomous AI agents. Black Box captures every execution step an agent takes, stores rich trace metadata in Supabase PostgreSQL, diagnoses failures using ML and LLM models, and enables checkpointed replay to explore counterfactual fixes without re-running what did not change.

---

## 📋 Table of Contents
1. [Overview & Core Capabilities](#-overview--core-capabilities)
2. [Architecture](#-architecture)
3. [Quick Start & Setup](#-quick-start--setup)
4. [Running the Backend (FastAPI)](#-running-the-backend-fastapi)
5. [Running the Frontend (React + Vite)](#-running-the-frontend-react--vite)
6. [Database Setup (Supabase)](#-database-setup-supabase)
7. [Environment Configuration (`.env`)](#-environment-configuration-env)
8. [Testing & Verification](#-testing--verification)
9. [Deployment (Railway & Vercel)](#-deployment-railway--vercel)
10. [Repository Structure](#-repository-structure)
11. [Roles & Ownership](#-roles--ownership)

---

## 🎯 Overview & Core Capabilities

- **Flight Recording (`tracing/`)**: Deterministic trace logging capturing tool calls, LLM decisions, latency, status, state snapshots, and error taxonomy tags.
- **Trace-Grounded Diagnostics (`ml/`, `agent/`)**: Machine-learning classifiers (Random Forest / Decision Tree) and Groq LLM analysers rank suspicious steps and output natural-language evidence explaining why a step failed.
- **Checkpointed Replay (`replay/`)**: Branch from any past checkpoint, override tool outputs or parameters, and re-execute only subsequent steps while preserving the shared prefix.
- **Comparative Analysis (`replay/compare.py`)**: Diff original and alternative runs side-by-side to verify if counterfactual modifications resolved the failure.
- **Dark-Tech Precision Web UI (`web/`)**: React + Vite dashboard featuring execution graphs, interactive 5-step demo mode, guided tour, trace logs, and evaluation metrics.
- **Live Database Persistence (`storage/`)**: Fully compatible with Supabase PostgreSQL and local SQLite fallback.

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────┐
│               React + Vite Frontend (web/)             │
│   Overview  ·  Logs  ·  Investigate  ·  Replay  · Diff │
└───────────────────────────┬────────────────────────────┘
                            │ REST API (JSON)
┌───────────────────────────▼────────────────────────────┐
│                 FastAPI Backend (api/)                 │
│   /runs  ·  /runs/recent  ·  /runs/{id}  ·  /replay   │
└─────────────┬───────────────────────────┬──────────────┘
              │                           │
┌─────────────▼──────────────┐ ┌──────────▼──────────────┐
│    Diagnostic & Replay     │ │   Storage Layer (storage/)   │
│   • ML Ranker (ml/)        │ │   • SQLAlchemy 2.0 ORM      │
│   • Groq LLM (agent/)      │ │   • Supabase PostgreSQL     │
│   • Replay Engine (replay/)│ │   • SQLite Fallback         │
└────────────────────────────┘ └─────────────────────────┘
```

---

## 🚀 Quick Start & Setup

### 1. Clone the repository
```bash
git clone https://github.com/Chirag-Patel123/BNB26_NoSleepClub_Internal_Round.git
cd BNB26_NoSleepClub_Internal_Round
```

### 2. Python Environment Setup
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Frontend Dependencies
```bash
cd web
npm install
cd ..
```

---

## 🛠️ Running the Backend (FastAPI)

Start the backend server locally:
```bash
uvicorn api.main:app --reload --port 8000
```
- API Base: `http://localhost:8000`
- Interactive API Docs (Swagger): `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health` (returns `{"db": "postgresql"}` or `{"db": "sqlite"}`)

---

## 💻 Running the Frontend (React + Vite)

In a separate terminal:
```bash
cd web
npm run dev
```
Open `http://localhost:5173` in your browser.

To build the production frontend bundle:
```bash
cd web
npm run build
```

---

## 🗄️ Database Setup (Supabase)

1. Open your project on [Supabase](https://supabase.com).
2. Navigate to **SQL Editor** -> **New query**.
3. Copy and run the contents of [`storage/schema.sql`](storage/schema.sql) to set up tables:
   - `runs`, `steps`, `checkpoints`, `diagnoses`, `experiments`, `benchmark_cases`, `model_versions`
4. Copy your database connection string and add it to `.env`:
   ```bash
   SUPABASE_DB_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```

---

## ⚙️ Environment Configuration (`.env`)

Create `.env` in the root directory (never commit this file):
```env
# Database
SUPABASE_DB_URL=postgresql://postgres:your-password@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>

# Backend
API_BASE_URL=http://localhost:8000
USE_MOCK=false

# LLM Diagnostics
GROQ_API_KEY=<your-groq-api-key>
GROQ_MODEL=openai/gpt-oss-120b
```

Frontend environment variables (`web/.env`):
```env
VITE_API_URL=http://localhost:8000
```

---

## 🧪 Testing & Verification

Run the full pytest suite:
```bash
pytest
```
Run API integration tests:
```bash
pytest tests/test_api.py -v
```

---

## ☁️ Deployment (Railway & Vercel)

### Backend Deployment (Railway)
1. Link your GitHub repo to a new Railway project.
2. Railway detects the root [`Procfile`](Procfile):
   ```text
   web: uvicorn api.main:app --host 0.0.0.0 --port $PORT
   ```
3. Set the following environment variables in Railway:
   - `SUPABASE_DB_URL`
   - `GROQ_API_KEY`
   - `RAILWAY_ENVIRONMENT=production`
4. Verify deployment health at `https://<your-railway-url>.up.railway.app/health`.

### Frontend Deployment (Vercel)
1. Import the repository in Vercel with **Root Directory** set to `web`.
2. Framework Preset: **Vite**.
3. Add Environment Variable:
   - `VITE_API_URL`: `https://<your-railway-url>.up.railway.app`
4. Deploy!

---

## 📁 Repository Structure

| Path | Description |
|------|-------------|
| `api/` | FastAPI routes, Pydantic schemas, and application lifecycle. |
| `agent/` | Deterministic demo agent, LLM agent pipelines, tools, and failure injectors. |
| `storage/` | Database engine, SQLAlchemy ORM models, and repositories. |
| `ml/` | Failure diagnosis models, feature extraction, and benchmark evaluators. |
| `replay/` | Counterfactual replay engine and trace comparison diff utilities. |
| `tracing/` | Event schema, recorders, sanitizers, and trace renderers. |
| `web/` | Modern React + Vite frontend application. |
| `data/` | Benchmark reports, sample traces, and synthetic dataset. |
| `tests/` | Pytest suite covering API, agent, ML, and replay modules. |
| `Procfile` | Production entrypoint configuration for Railway / container hosts. |
| `requirements.txt` | Python dependency specifications. |

---

## 👥 Roles & Ownership

- **P1 Ishan**: Agent Execution & Tracing (`agent/`, `tracing/`)
- **P2 Rudra**: ML Diagnosis & Evaluation (`ml/`, `data/benchmark/`)
- **P3 Chirag**: Supabase Storage & Checkpointed Replay (`storage/`, `replay/`)
- **P4 Madhav**: API, Web UI, Integration, and Documentation (`api/`, `web/`)

---

## 📄 License
This project is licensed under the MIT License — see the `LICENSE` file for details.