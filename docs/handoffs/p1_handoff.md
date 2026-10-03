# P1 Handoff (Ishan) - agent + tracing, batch 1

## Entry points
- `from agent.demo_agent import run_agent, to_json`
- `run_agent(task, seed, failure: FailureConfig|None, scenario_id="flight_basic", run_id=None, resume_from: Checkpoint|None, parent_run_id=None, override={"step_id","value"}|None, use_checkpoint_failure=True) -> RunResult`
- `from agent.failure_injection import FailureConfig, inject_failure, INJECTIONS`
- `RunResult = {run, steps[], checkpoints[], graph, ground_truth}` (pydantic, `tracing/schema.py`)
- Samples: `python -m agent.generate_samples` -> `data/sample_traces/` (+ index.json)

## Conventions (propose freezing at the next sync)
- run_id / checkpoint_id: UUID strings. step_id: `step-N` (1-indexed, == step_index).
- Injection names -> error_type: stale_search_result->retrieval_context_failure, incorrect_filtering->model_decision_failure,
  invalid_tool_output->tool_output_failure, calculation_error->state_corruption, wrong_parameter->parameter_failure.
- Propagation: first detecting step = failure with its own error_type; every later step = failure/state_corruption "depends on failed step-N".
- `ground_truth` is a SIDECAR (not on steps). P2 must keep it out of features.
- Checkpoint after every successful step; `context_snapshot` holds task, scenario_id, seed, failure config, versions.
- Resume: steps before the checkpoint are NOT re-recorded (reused); new run gets parent_run_id.

## P2 / P3 / P4
- P2: read data/sample_traces/*.json; label = ground_truth.target_step_id.
- P3: persist RunResult.run/steps/checkpoints; resume via run_agent(resume_from=ckpt, parent_run_id=..., override=...).
- P4: UI-ready JSON = `to_json(result)`; order by step_index; graph in `result.graph`.

## Tests: `pytest -q` -> 13 passed. Suggested commit: `p1: add deterministic agent runner and trace recorder`

## Batch 2 (dataset for P2)
- `python -m agent.generate_dataset --n 600 --seed 1` -> `data/synthetic/runs.jsonl` (1 RunResult JSON per line, with `split`) + `benchmark_cases.json` (matches `benchmark_cases` table columns; `notes` = run_id).
- Scenarios: flight_basic, flight_group, flight_tight_budget. `flight_tight_budget` is HELD OUT entirely (always test) for known-vs-held-out evaluation.
- Other splits by whole run: 70/15/15. ~15% normal runs (no injection).
- Seed now varies budget, prices, seats, and latency (incl. benign 7% timing outliers on any step so latency alone doesn't reveal the label).
- Label for P2: `ground_truth.target_step_id` (sidecar, not a step field). Normal runs have target null.
- Tests: `pytest -q` -> 32 passed (all 3 scenarios x 5 failures x many seeds fail correctly, never crash earlier than origin).
- Suggested commit: `p1: add scenario variation and batch dataset generator`

## Batch 3 - audit fixes (IMPORTANT for P3/P4)
- **Override now wins over an inherited injected failure.** Before, replaying from a checkpoint with default args re-injected the failure and ignored the modification. Now `override` on a step suppresses the injection for that step.
- Override coverage (spec's 3 modification types), `override={"step_id","value"}`:
  - tool result: step-3 `{"results":[...]}`, step-4 `{"candidates":[...]}`, step-5/6/7 merge into output (e.g. `{"available": true}`)
  - parameter: step-2 merges into journey; step-3 `{"from"|"to"|"date": ...}` edits the search query
  - branch/tool choice: step-4 `{"selected_flight_id": "F202"}`
- Resumed runs: only steps AFTER the checkpoint are recorded. `completed_steps` on new checkpoints now includes reused parent steps. P3: derive common prefix from checkpoint.step_index of the parent.
- Removed the literal `stale` marker from step output (was a label leak); stale detection now compares against the mock availability service.
- `Step` validates status/error_type on assignment.
- Checkpoint `context_snapshot` holds the injected failure config (needed so partial replay reproduces the same failure). P2: never read it as a feature; use steps only.
- Known: sanitizer runs in `to_json()`; persisting `RunResult` objects directly skips it (no secrets are ever produced by the mock tools anyway).
- Known: for incorrect_filtering, ~30% of runs crash at the origin step itself (empty candidate list, group scenario). Other failure types always crash after the origin except invalid_tool_output (same step).
- Dataset is very clean/deterministic, so expect near-perfect RandomForest scores; report honestly and show the held-out `flight_tight_budget` split.
- Tests: `pytest -q` -> 42 passed.
