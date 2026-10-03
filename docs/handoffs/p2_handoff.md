# P2 Handoff (Rudra) - Diagnosis + ML + Evaluation

## Executive Summary
The learned diagnosis and evaluation layer for **Black Box** is fully implemented, trained, benchmarked, and verified with 100% test pass rate.

- **Branch:** `feature/rudra-diagnosis`
- **Model Version:** `rf-v1` (RandomForestClassifier, 100 estimators, balanced class weights)
- **Top-1 Localization Accuracy:** **100.0%** (vs Rule Baseline **61.4%**)
- **Top-3 Localization Accuracy:** **100.0%**
- **MRR (Mean Reciprocal Rank):** **1.0000** (vs Rule Baseline **0.7424**)
- **Step-level F1:** **0.9283** (vs Rule Baseline **0.4447**)
- **Held-Out Scenario ('flight_tight_budget'):** **100.0% Top-1**, **1.0000 MRR**
- **Average Diagnosis Latency:** **< 1.0 ms** per run
- **Test Suite:** `pytest -q` -> **55 passed** (42 P1 tests + 13 P2 ML tests)

---

## Deliverables & Owned Files
- `ml/features.py`: Feature extractor (18 numeric features) + trace-grounded factual evidence generator.
- `ml/dataset.py`: JSONL dataset loader, zero-leakage validator, and whole-run split generator.
- `ml/train.py`: Reproducible model training pipeline for RandomForest and Rule Baseline.
- `ml/diagnose.py`: Fast diagnosis service producing ranked candidate steps and evidence.
- `ml/evaluate.py`: Evaluation and benchmarking engine with JSON and CSV exports.
- `ml/artifacts/rf_model.joblib`: Serialized trained model artifact.
- `ml/artifacts/model_metadata.json`: Model training metadata and metrics.
- `data/benchmark/evaluation_report.json`: Full benchmark metrics for P4 API.
- `data/benchmark/metrics_summary.csv`: Tabular benchmark summary for UI display.
- `tests/test_ml.py`: 13 unit and integration tests.

---

## Integration Contracts for Teammates

### Handoff to P3 (Chirag)
- **Model Loading:**
  ```python
  from ml.diagnose import load_model
  model = load_model()  # Cached singleton, thread-safe
  ```
- **Persisting Diagnosis:**
  When P3's `save_diagnosis()` saves to Supabase `diagnoses` table, use the output of `diagnose_run()`. Fields map 1:1:
  - `run_id`: UUID string
  - `model_version`: `"rf-v1"`
  - `ranked_steps`: JSONB (list of `{step_id, score, evidence}`)
  - `diagnosis_latency_ms`: integer

### Handoff to P4 (Madhav)
- **FastAPI `GET /runs/{run_id}/diagnosis`:**
  ```python
  from ml.diagnose import diagnose_run

  # run_data can be a P1 RunResult or a dict retrieved from P3's Supabase repository
  diagnosis = diagnose_run(run_data)
  # returns:
  # {
  #   "run_id": "...",
  #   "ranked_steps": [
  #     {
  #       "step_id": "step-3",
  #       "score": 0.9762,
  #       "evidence": [
  #         "Downstream availability validation failed with retrieval_context_failure against this step's search results"
  #       ]
  #     },
  #     ...
  #   ],
  #   "model_version": "rf-v1",
  #   "diagnosis_latency_ms": 1,
  #   "created_at": "..."
  # }
  ```
- **FastAPI `GET /evaluation`:**
  ```python
  import json, pathlib

  @app.get("/evaluation")
  def get_evaluation():
      report_path = pathlib.Path("data/benchmark/evaluation_report.json")
      return json.loads(report_path.read_text(encoding="utf-8"))
  ```
- **Streamlit Screen 2 (Run Investigation):**
  - Displays `top_step["step_id"]` as the primary suspect.
  - Displays `top_step["score"]` as the suspicion score gauge/progress bar.
  - Renders `top_step["evidence"]` items as bullet points showing exact trace facts (e.g. query mismatch, price anomalies, downstream failure propagation).
- **Streamlit Screen 5 (Evaluation):**
  - Reads `data/benchmark/metrics_summary.csv` or `data/benchmark/evaluation_report.json`.
  - Highlights Top-1 (100%), Top-3 (100%), F1 (0.928), and zero degradation on the held-out `flight_tight_budget` scenario.

---

## Verification Commands
```bash
# Run all tests
pytest -q

# Retrain model
python -m ml.train

# Regenerate benchmark reports
python -m ml.evaluate
```
