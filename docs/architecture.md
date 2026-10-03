# Black Box Architecture

## Overview
Black Box is a tracing, diagnosis, and replay engine for AI agent workflows. It observes execution, analyzes the trace graph for anomalies, and allows counterfactual execution to definitively prove the root cause of an agent failure.

## System Components

1. **Agent & Trace Engine (P1)**
   - Executes the 7-step canonical agent workflow.
   - Traces every step, recording state before/after, dependencies, tools called, and outputs.
   - Pydantic models validate the trace schema.

2. **ML Diagnosis (P2)**
   - Consumes the trace graph.
   - Uses a transparent rules baseline and a `RandomForestClassifier` to score the suspicion level of each step.
   - Extracts actual trace facts as human-readable evidence (e.g., "invalid output", "retry count = 2").

3. **Storage & Replay (P3)**
   - Persists runs, steps, and checkpoints in a Supabase PostgreSQL database.
   - Resumes execution from arbitrary historical checkpoints.
   - Runs counterfactuals (e.g., swapping a tool response) and saves them as child runs.
   - Generates trace comparison metrics (changed steps, rerun savings).

4. **API & UI (P4)**
   - FastAPI provides a stateless interface over the trace and replay engines.
   - Streamlit UI offers a judge-friendly visualization of the entire loop: Dashboard -> Investigation -> Replay -> Comparison -> Evaluation.

## Data Flow
`Agent -> Trace Recorder -> Supabase -> FastAPI -> ML Diagnosis -> Streamlit UI`
