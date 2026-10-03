# Black Box - A Flight Recorder for AI Agents

Welcome to the **Black Box** project repo! This repository contains the source code for our AI-powered debugging system that learns from agent execution traces to identify suspicious or failure-causing steps, provides trace-grounded evidence, supports checkpointed replay, supports alternative execution paths, compares executions, and reports measured evaluation results.

## Clean-Start Setup

1. **Clone the repo:**
   ```bash
   git clone https://github.com/Chirag-Patel123/BNB26_NoSleepClub_Internal_Round.git
   cd BNB26_NoSleepClub_Internal_Round
   ```
2. **Setup Virtual Environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Environment setup:**
   Copy `.env.example` to `.env` and fill in your Supabase credentials:
   ```bash
   cp .env.example .env
   ```
4. **Database Setup:**
   Execute `storage/schema.sql` against your Supabase instance to create the required tables.
5. **Run the API & UI:**
   Start the backend FastAPI server:
   ```bash
   python main.py
   ```
   In a new terminal, start the Streamlit Dashboard:
   ```bash
   streamlit run ui/app.py
   ```

## Roles
- **P1 Ishan**: Agent execution and tracing (`agent/`, `tracing/`)
- **P2 Rudra**: ML diagnosis and evaluation (`ml/`, `data/benchmark/`)
- **P3 Chirag**: Supabase storage and replay (`storage/`, `replay/`)
- **P4 Madhav**: API, UI, Integration, and Demo (`api/`, `ui/`, Docs)
