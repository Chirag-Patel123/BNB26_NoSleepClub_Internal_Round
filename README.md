# Black Box - A Flight Recorder for AI Agents (NoSleepClub)
Observe -> Diagnose -> Explain -> Replay -> Modify -> Compare -> Evaluate.

## Clean-start setup
1. `python -m venv .venv && .venv\Scripts\activate`
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in Supabase values.
4. Run `storage/schema.sql` in the Supabase SQL editor.
5. `pytest -q`
6. API: `uvicorn api.main:app --reload`  |  UI: `streamlit run ui/app.py`

## Layout
agent/ + tracing/ (P1) | ml/ (P2) | storage/ + replay/ (P3) | api/ + ui/ + docs/ (P4). See CONTRACTS.md.
