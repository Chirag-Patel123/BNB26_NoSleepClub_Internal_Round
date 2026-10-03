# CONTRACTS (frozen unless all 4 agree at a checkpoint)
Source: MASTER SYNC SPEC. Trace/run/diagnosis/experiment fields, statuses, DB tables, API shapes as in the spec.

## Conventions added by P1 (confirm at sync)
- run_id / checkpoint_id / experiment_id: UUID strings. step_id: `step-N` (1-indexed == step_index).
- Injection names (POST /runs `failure_type`): stale_search_result, incorrect_filtering, invalid_tool_output, calculation_error, wrong_parameter
  -> root-cause class: retrieval_context_failure, model_decision_failure, tool_output_failure, state_corruption, parameter_failure.
  NOTE: the trace's recorded error_type is what the DETECTING step observed (wrong_parameter is recorded as model_decision_failure at step-4). Use ground_truth for the true cause.
- scenario_id: flight_basic | flight_group | flight_tight_budget (tight_budget is the held-out test scenario).
- Failure propagation: first detecting step = failure with own error_type; later steps = failure/state_corruption "depends on failed step-N".
- Ground truth is a sidecar (`RunResult.ground_truth`), never a step field or ML feature.
- Checkpoint after every successful step; context_snapshot has task, scenario_id, seed, failure config, versions.
- Resume: `run_agent(resume_from=ckpt, parent_run_id=..., override={"step_id","value"}, use_checkpoint_failure=False)`; pre-checkpoint steps are not re-recorded.
- Entry for API: `agent.service.start_run(...)` returns a RunResult-JSON dict.
- Counterfactual override (works with default args; wins over inherited failure):
  step-2/3 params, step-3 results, step-4 candidates or selected_flight_id, step-5/6/7 output merge. Details: docs/handoffs/p1_handoff.md.
