# P1 Documentation: Agent and Trace Engine

**Project:** Black Box, a flight recorder for AI agents (team NoSleepClub)
**Owner:** P1 Ishan
**Packages:** `agent/`, `tracing/`
**Status:** complete and verified (`python verify_p1.py` gives 14/14, `pytest -q` gives 42 passed)

---

## 1. What P1 provides

P1 produces the raw material that every other component consumes:

| Capability | Where | Consumed by |
|---|---|---|
| A deterministic 7-step mock flight agent | `agent/demo_agent.py` | API (P4), replay (P3) |
| Controlled, reproducible failure injection | `agent/failure_injection.py` | API (P4), dataset (P2) |
| Canonical trace objects (Pydantic) | `tracing/schema.py` | Everyone |
| A database-independent trace recorder | `tracing/recorder.py` | Agent runner |
| Execution graph and dependency helpers | `tracing/graph.py` | UI (P4), ML features (P2) |
| Secret sanitizer | `tracing/sanitizer.py` | `to_json()` |
| Checkpoint creation and resume support | `agent/demo_agent.py` | Replay (P3) |
| Batch dataset generator with a held-out scenario | `agent/generate_dataset.py` | ML (P2) |
| One-call service entry for the API | `agent/service.py` | API (P4) |

P1 does **not** own ML training, Supabase persistence, the replay algorithm, API routes, or the UI.

---

## 2. Quick start

```bash
pip install pydantic pytest python-dotenv    # or: pip install -r requirements.txt
python verify_p1.py                          # all-in-one check, expect 14/14
python -m pytest -q                          # unit tests, expect 42 passed
python -m agent.generate_samples             # writes data/sample_traces/
python -m agent.generate_dataset --n 600 --seed 1   # writes data/synthetic/
```

Run one agent with an injected failure:

```python
from agent.service import start_run

run = start_run("flight_basic", seed=42,
                failure_type="stale_search_result", target_step="step-3")
print(run["run"]["status"])               # failure
print(run["ground_truth"]["target_step_id"])   # step-3  (the real origin)
print([(s["step_id"], s["status"]) for s in run["steps"]])
```

All commands run from the repository root. Python 3.11 or newer is required.

---

## 3. Architecture

```
FailureConfig ──► run_agent() ──► TraceRecorder ──► RunResult
                      │                                │
                      │ (per step)                     ├─ run            (Run)
                      ▼                                ├─ steps[]        (Step)
               agent/tools.py                          ├─ checkpoints[]  (Checkpoint)
               (deterministic mock tools)              ├─ graph          (nodes, edges, order)
                                                       └─ ground_truth   (sidecar, evaluation only)
```

Design rules:

1. **The recorder never touches a database.** It returns in-memory Pydantic objects. P3 persists them.
2. **Everything is deterministic.** The same task, seed, scenario and failure config always produce the same trace (ignoring generated UUIDs and timestamps). Latency is seeded, not measured, so it never depends on the machine.
3. **No hidden random failures.** A failure occurs only when a `FailureConfig` asks for one.
4. **The ground truth is a sidecar.** The injected target lives in `RunResult.ground_truth`, never in step fields, so it cannot leak into ML features.

---

## 4. The canonical scenario

A mock flight-research agent. There is no real booking, no network call, and no financial transaction.

| # | `step_id` | `step_type` | `tool` | What it does | Depends on |
|---|---|---|---|---|---|
| 1 | `step-1` | `understand_request` | `parse_request` | Parses the task text | none |
| 2 | `step-2` | `extract_journey` | `extract_journey` | Extracts route, date, budget, passengers | step-1 |
| 3 | `step-3` | `tool_call` | `search_flights` | Searches the mock flight database | step-2 |
| 4 | `step-4` | `filter` | `filter_flights` | Keeps flights within budget, picks the first | step-3 |
| 5 | `step-5` | `tool_call` | `validate_availability` | Checks the chosen flight against the availability service | step-4 |
| 6 | `step-6` | `compute` | `calculate_price` | Computes base, taxes and total | step-5, step-4 |
| 7 | `step-7` | `finalize` | `prepare_booking_payload` | Builds the mock booking payload | step-6, step-4 |

`parent_step_id` is always the previous step. `dependency_ids` is the data dependency (steps 6 and 7 also depend on step 4).

### Scenarios

| `scenario_id` | Base max price (INR) | Passengers | Notes |
|---|---|---|---|
| `flight_basic` | 6000 | 1 | Default |
| `flight_group` | 7500 | 3 | |
| `flight_tight_budget` | 5500 | 1 | **Held out**: always in the test split |

The seed adds up to +400 to the budget and varies prices, seats left and latency.

---

## 5. Failure injection

```python
from agent.failure_injection import FailureConfig, inject_failure

cfg = inject_failure("invalid_tool_output", target_step=5, seed=42)
# equivalent: FailureConfig(failure_type="invalid_tool_output", target_step="step-5", seed=42)
```

| Injection name | Origin step | What the agent silently does wrong | First visible failure | Recorded `error_type` | Retries |
|---|---|---|---|---|---|
| `stale_search_result` | step-3 | Search prices are lowered by 1800 (stale data) | step-5 | `retrieval_context_failure` | 1 |
| `incorrect_filtering` | step-4 | Filter is inverted (keeps flights over budget) | step-5 (about two thirds of runs) or step-4 (empty list) | `model_decision_failure` | 1 or 0 |
| `invalid_tool_output` | step-5 | Availability returns `null` and `-1` seats | step-5 (the origin itself) | `tool_output_failure` | 2 |
| `calculation_error` | step-6 | Total price is negated, no crash | step-7 | `state_corruption` | 0 |
| `wrong_parameter` | step-3 | Search is sent to the wrong destination, returns nothing | step-4 | `model_decision_failure` | 0 |

**The key product behavior:** for four of the five injections, the origin step looks healthy (`status=success`) and the crash appears later. This is what Black Box must learn to diagnose.

> **Taxonomy note.** `FailureConfig.error_type` gives the taxonomy class of the root cause (for `wrong_parameter` that is `parameter_failure`). The `error_type` written into the trace is whatever the *detecting* step observed. For `wrong_parameter` the detecting step is step-4 ("no candidates after filtering"), so the trace records `model_decision_failure`, and `parameter_failure` never appears on a step. Use `ground_truth` for the true cause.

### Failure propagation rule

1. The first step that detects bad data records `status=failure` with its own `error_type` and message.
2. Every later step records `status=failure`, `error_type=state_corruption`, `error_message="depends on failed step-N"`, with empty output.
3. The run `status` is `failure` if any step failed.

This gives P2 a real "downstream failure count" signal.

---

## 6. Data model

All models are in `tracing/schema.py`.

### 6.1 `Step` (20 fields, frozen by the team contract)

| Field | Type | Notes |
|---|---|---|
| `run_id` | str (UUID) | |
| `step_id` | str | `step-N`, 1-indexed, equals `step_index` |
| `parent_step_id` | str or null | Previous step; null for step-1 |
| `step_index` | int | Ordering key |
| `step_type` | str | See section 4 |
| `input_summary` | dict | Step 1 holds the task; later steps list the state keys read |
| `output_summary` | dict | Tool output. Empty for propagated failures |
| `state_before` | dict | Agent state snapshot before the step |
| `state_after` | dict | Agent state snapshot after the step |
| `tool` | str or null | Mock tool name |
| `model` | str or null | Always null (no LLM in the demo agent) |
| `latency_ms` | int | Seeded, 80 to 140 plus occasional benign outliers of 150 to 400 ms on any step |
| `tokens` | int or null | Always null |
| `status` | enum | See 6.4 |
| `error_type` | enum or null | See 6.5 |
| `error_message` | str or null | |
| `retry_count` | int | |
| `dependency_ids` | list[str] | Data dependencies |
| `checkpoint_id` | str or null | Set when a checkpoint was taken after this step |
| `created_at` | datetime (UTC) | |

`Step` validates `status` and `error_type` on assignment, so a bad value raises immediately.

### 6.2 `Run`

`run_id`, `parent_run_id`, `task`, `scenario_id`, `status`, `agent_version` (`agent-v1`), `environment_version` (`env-v1`), `start_time`, `end_time`, `root_checkpoint_id`.

`parent_run_id` is set only for replayed (child) runs. `root_checkpoint_id` is the first checkpoint of the run.

### 6.3 `Checkpoint`

| Field | Meaning |
|---|---|
| `checkpoint_id` | UUID |
| `run_id`, `step_id`, `step_index` | The step this checkpoint was taken after |
| `state_snapshot` | Full agent state after that step |
| `context_snapshot` | `task`, `scenario_id`, `seed`, `failure` config, `agent_version`, `environment_version` |
| `completed_steps` | All successful steps up to and including this one, including steps reused from a parent run |

A checkpoint is created after **every successful step**. The failing step and the steps after it have none, so the latest usable checkpoint is the one just before the first failure.

### 6.4 Status vocabulary

`running`, `success`, `failure`, `skipped`, `cancelled`. The demo agent emits only `success` and `failure`.

### 6.5 Error taxonomy

`tool_output_failure`, `model_decision_failure`, `state_corruption`, `retrieval_context_failure`, `parameter_failure`, `branching_failure`. The demo agent currently emits the first four; `parameter_failure` and `branching_failure` are reserved by the taxonomy.

### 6.6 `GroundTruth` (sidecar)

`run_id`, `scenario_id`, `seed`, `failure_type`, `target_step_id`. For normal runs, `failure_type` and `target_step_id` are null. **Use it only for labels and evaluation.**

### 6.7 `RunResult`

`{run, steps, checkpoints, graph, ground_truth}`. `to_json(result)` returns a sanitized, JSON-ready dict of the same shape.

### 6.8 Execution graph

```json
{
  "nodes": [{"step_id": "step-1", "step_index": 1, "step_type": "understand_request", "status": "success"}],
  "edges": [{"from": "step-4", "to": "step-5"}],
  "order": ["step-1", "step-2", "step-3", "step-4", "step-5", "step-6", "step-7"]
}
```

Edges follow `dependency_ids`. A normal run has 7 nodes and 8 edges. `tracing.graph.downstream(steps, "step-3")` returns every step that transitively depends on a step.

---

## 7. API reference

### 7.1 `agent.service.start_run`

```text
start_run(scenario_id="flight_basic", seed=42, failure_type=None, target_step=None) -> dict
```

Runs the agent once and returns `to_json(RunResult)`. If `failure_type` is given without `target_step`, the default origin step for that type is used. An unknown `failure_type` raises `ValueError` listing the allowed values. This is the intended entry point for `POST /runs`.

### 7.2 `agent.demo_agent.run_agent`

```text
run_agent(task=DEFAULT_TASK, seed=42, failure=None, scenario_id="flight_basic",
          run_id=None, resume_from=None, parent_run_id=None,
          override=None, use_checkpoint_failure=True) -> RunResult
```

| Parameter | Purpose |
|---|---|
| `failure` | A `FailureConfig`, or `None` for a normal run |
| `run_id` | Force a specific run id (otherwise a UUID is generated) |
| `resume_from` | A `Checkpoint`; execution continues from the step after it |
| `parent_run_id` | Recorded on the new run, for child runs |
| `override` | `{"step_id": "step-N", "value": {...}}`, a counterfactual modification |
| `use_checkpoint_failure` | When resuming, re-apply the failure stored in the checkpoint (default `True`). Set `False` for a clean resume with no injected failure |

### 7.3 `agent.demo_agent.to_json`

`to_json(result) -> dict`. Dumps with `mode="json"` and runs the sanitizer over the result.

### 7.4 `TraceRecorder` (`tracing/recorder.py`)

`start_run`, `start_step`, `complete_step`, `fail_step`, `skip_step`, `add_checkpoint`, `finish_run`, `build_execution_graph`. It is independent of the database and is used internally by `run_agent`.

### 7.5 Sanitizer

`tracing.sanitizer.sanitize(obj)` redacts dictionary values whose key contains `key`, `secret`, `password`, `authorization` or `api`, and redacts strings that look like `sk-...` keys, JWTs, or `postgres://` URLs. The mock tools never produce secrets; the sanitizer is a safety net.

---

## 8. Checkpoint replay and counterfactuals

P3 owns the replay service; P1 guarantees the agent can resume deterministically.

```python
from agent.demo_agent import run_agent
from agent.failure_injection import inject_failure

orig = run_agent(failure=inject_failure("invalid_tool_output", 5))
ckpt = next(c for c in orig.checkpoints if c.step_index == 4)   # checkpoint before the failing step

alt = run_agent(
    resume_from=ckpt,
    parent_run_id=orig.run.run_id,
    override={"step_id": "step-5", "value": {"available": True}},
)
print(orig.run.status, "->", alt.run.status)       # failure -> success
print([s.step_id for s in alt.steps])              # ['step-5', 'step-6', 'step-7']
```

Rules:

- **Resumed runs record only the steps after the checkpoint.** Earlier steps are reused from the parent. P3 should compute the common prefix from the parent's `checkpoint.step_index`.
- **A resumed run gets a new `run_id`.** The original run object is never modified.
- **An override always wins** over an injected failure inherited from the checkpoint, even with default arguments.
- **`completed_steps`** on checkpoints created during a resume include the reused parent steps.

### Supported modifications (the spec's three types)

| Type | `step_id` | `value` | Effect |
|---|---|---|---|
| Tool result | `step-3` | `{"results": [...]}` | Replaces the search results |
| Tool result | `step-4` | `{"candidates": [...]}` | Replaces the filtered candidates |
| Tool result | `step-5`, `step-6`, `step-7` | Any output fields, e.g. `{"available": true}` | Merged into the step output |
| Parameter | `step-2` | Journey fields, e.g. `{"max_price": 7000}` | Merged into the journey |
| Parameter | `step-3` | `{"from"/"to"/"date": ...}` | Edits the search query |
| Branch / tool choice | `step-4` | `{"selected_flight_id": "F202"}` | Picks a different flight |

Example, fixing a wrong parameter by resuming from before step 3:

```python
from agent.demo_agent import run_agent
from agent.failure_injection import inject_failure

orig = run_agent(failure=inject_failure("wrong_parameter", 3))
ckpt = next(c for c in orig.checkpoints if c.step_index == 2)
fixed = run_agent(resume_from=ckpt, override={"step_id": "step-3", "value": {"to": "DEL"}})
print(orig.run.status, "->", fixed.run.status)   # failure -> success
```

---

## 9. Dataset and benchmark for ML (P2)

```bash
python -m agent.generate_dataset --n 600 --seed 1
```

| File | Content |
|---|---|
| `data/synthetic/runs.jsonl` | One `RunResult` JSON per line, plus a `split` field |
| `data/synthetic/benchmark_cases.json` | Rows matching the `benchmark_cases` table. `notes` holds the run id |

How it is built:

- About 15% of runs are normal; the rest are spread across the five failure types.
- Scenario and seed are random but fully determined by `--seed`.
- **Split by whole run.** `flight_tight_budget` always goes to `test` (the held-out scenario); other runs are split about 70/15/15 across train, validation and test.
- Labeling: step label is `1` where `step_id == ground_truth.target_step_id`, otherwise `0`.

Guidance for P2:

- Never use `ground_truth`, `split`, or the checkpoint `context_snapshot.failure` as a feature.
- Informative trace facts include `status`, `error_type`, `retry_count`, output validity, downstream failure count, dependency count, step position and latency deviation.
- The data is clean and deterministic, so expect very high scores. Report them honestly and highlight the held-out scenario.
- Normal runs (target is null) can serve as negatives for every step.

---

## 10. Determinism and reproducibility

- All randomness comes from `random.Random(f"{seed}:{purpose}")`, which is stable across processes, platforms and `PYTHONHASHSEED`.
- Two runs with the same inputs produce identical step data except `run_id`, `checkpoint_id` and `created_at`.
- This is tested across processes with different hash seeds.
- Latency is simulated, so it is identical on every machine.

---

## 11. Files

```
agent/
  demo_agent.py         run_agent(), to_json(), 7-step flow, resume and override logic
  tools.py              deterministic mock tools, SCENARIOS table
  failure_injection.py  FailureConfig, INJECTIONS, inject_failure()
  service.py            start_run() entry point for the API
  state.py              state snapshot helper
  generate_samples.py   writes data/sample_traces/
  generate_dataset.py   writes data/synthetic/
tracing/
  schema.py             Step, Run, Checkpoint, GroundTruth, RunResult
  recorder.py           TraceRecorder
  graph.py              build_execution_graph(), downstream()
  sanitizer.py          sanitize()
tests/test_tracing.py   42 tests
verify_p1.py            one-shot verification (14 checks)
data/sample_traces/     one success trace and five failure traces
docs/handoffs/p1_handoff.md   short handoff note
```

---

## 12. Integration guide

### For P2 (diagnosis and ML)

Load `data/synthetic/runs.jsonl`, derive step-level features from `steps`, and label from `ground_truth.target_step_id`. Use the `split` field. See section 9.

### For P3 (storage and replay)

- Persist `result.run`, `result.steps`, `result.checkpoints` to the `runs`, `steps` and `checkpoints` tables. Field names match the SQL schema.
- Persist in this order: run, steps, checkpoints, final status.
- For replay, load the checkpoint, rebuild a `Checkpoint` object from the row, and call `run_agent(resume_from=..., parent_run_id=..., override=...)`.
- Save the child run as a new run. Never mutate the original.
- Datetimes serialize as ISO-8601 UTC strings; JSON fields map to JSONB.

### For P4 (API and UI)

- `POST /runs` calls `start_run(...)`, then P3's repository to save it, and returns `run_id` and `status`.
- Allowed `failure_type` values: `stale_search_result`, `incorrect_filtering`, `invalid_tool_output`, `calculation_error`, `wrong_parameter`.
- Allowed `scenario_id` values: `flight_basic`, `flight_group`, `flight_tight_budget`.
- Order steps by `step_index`. Draw the timeline from `graph.order` and `graph.edges`.
- Use `status` and `error_type` for coloring. A failed step with `error_message` starting `depends on failed` is a propagated failure, not the first crash.

---

## 13. Testing

| Command | Covers |
|---|---|
| `python verify_p1.py` | 14 end-to-end checks with a PASS/FAIL summary |
| `python -m pytest -q` | 42 unit tests |

The test suite covers:

- step order, dependencies and field names against the contract
- every failure type in every scenario across many seeds (it fails, never before its origin)
- origin versus visible crash separation
- reproducibility, including across processes
- JSON round-trip and sanitizer behavior
- absence of label markers in step data
- resume, counterfactual overrides (tool result, parameter, branch choice), and that the original run is never changed
- the dataset generator and held-out split
- enforcement of the status and error vocabularies

---

## 14. Known limitations

1. **Mock environment only.** One scenario family, seven steps, deterministic tools. This is intentional for a controlled demo.
2. **Clean data.** Failure patterns are very regular, so models will score very high. Honest reporting should say so.
3. **`incorrect_filtering` crash point varies.** About one third of runs crash at the origin step itself (empty candidate list); the rest crash at step-5.
4. **`wrong_parameter` is recorded as `model_decision_failure`** at step-4. Use `ground_truth` for the true cause.
5. **Checkpoint context contains the injected failure config.** It is needed so a partial replay reproduces the same failure. It must never be used as an ML feature.
6. **Resumed runs omit pre-checkpoint steps.** Consumers must compute the shared prefix from the parent checkpoint.
7. **The sanitizer runs inside `to_json()`.** Persisting a `RunResult` directly skips it. The mock tools never generate secrets.
8. **No `model` or `tokens` data**, because the demo agent does not call an LLM.
9. **No checkpoint before step 1.** A full replay means calling `run_agent` without `resume_from`.

---

## 15. FAQ

**Why is the origin step marked `success`?** The real bug often looks fine where it happens. Black Box must learn to point at the origin even though the crash is later.

**How do I get the true cause of a run?** `result.ground_truth.target_step_id`. It exists for labeling and evaluation only.

**Why does the same seed give different `run_id` values?** Run and checkpoint ids are fresh UUIDs by design. Everything else is identical.

**How do I replay without the original failure?** `run_agent(resume_from=ckpt, use_checkpoint_failure=False)`, or pass an override on the failing step.

**Can I add a new failure type?** Add it to `INJECTIONS` in `failure_injection.py`, implement its effect and its detection in `_run_step` in `demo_agent.py`, and add tests. Coordinate with P2 and P4 first, since the contract is shared.
