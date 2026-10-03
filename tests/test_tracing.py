import json
import pytest
from agent.demo_agent import run_agent, to_json
from agent.failure_injection import inject_failure, INJECTIONS
from tracing.schema import RunResult, Step

FIELDS = {"run_id","step_id","parent_step_id","step_index","step_type","input_summary","output_summary",
          "state_before","state_after","tool","model","latency_ms","tokens","status","error_type",
          "error_message","retry_count","dependency_ids","checkpoint_id","created_at"}

def norm(r):
    d = to_json(r)
    for s in d["steps"]:
        for k in ("run_id","created_at","checkpoint_id"): s.pop(k)
    return d["steps"]

def test_normal_run_ordered_seven_steps():
    r = run_agent()
    assert [s.step_index for s in r.steps] == list(range(1, 8))
    assert r.run.status == "success" and all(s.status == "success" for s in r.steps)
    assert len(r.checkpoints) == 7

def test_step_fields_match_contract():
    assert set(Step.model_fields) == FIELDS

def test_dependencies_consistent():
    r = run_agent()
    ids = {s.step_id for s in r.steps}
    for s in r.steps:
        assert set(s.dependency_ids) <= ids
        assert all(int(d.split("-")[1]) < s.step_index for d in s.dependency_ids)
        assert s.parent_step_id in (None, f"step-{s.step_index-1}")

@pytest.mark.parametrize("ft", list(INJECTIONS))
def test_failure_reproducible_and_target_recorded(ft):
    tgt = int(INJECTIONS[ft][0].split("-")[1])
    cfg = inject_failure(ft, tgt, seed=7)
    a, b = run_agent(seed=7, failure=cfg), run_agent(seed=7, failure=cfg)
    assert norm(a) == norm(b)
    assert a.run.status == "failure"
    assert a.ground_truth.target_step_id == f"step-{tgt}"
    first_fail = min(s.step_index for s in a.steps if s.status == "failure")
    assert first_fail >= tgt  # visible crash never earlier than origin

def test_crash_differs_from_origin_for_stale_search():
    r = run_agent(failure=inject_failure("stale_search_result", 3))
    assert r.ground_truth.target_step_id == "step-3"
    assert next(s for s in r.steps if s.status == "failure").step_id == "step-5"
    assert r.steps[2].status == "success"  # origin looks fine

def test_roundtrip():
    r = run_agent(failure=inject_failure("invalid_tool_output", 5))
    r2 = RunResult.model_validate_json(r.model_dump_json())
    assert r2 == r

def test_ground_truth_not_in_steps():
    d = json.dumps(to_json(run_agent(failure=inject_failure("invalid_tool_output", 5)))["steps"])
    assert "ground_truth" not in d and "target_step" not in d

def test_no_secrets():
    s = json.dumps(to_json(run_agent()))
    assert "sk-" not in s and "postgres" not in s

def test_resume_from_checkpoint_counterfactual():
    orig = run_agent(failure=inject_failure("invalid_tool_output", 5))
    ck = next(c for c in orig.checkpoints if c.step_index == 4)
    alt = run_agent(resume_from=ck, parent_run_id=orig.run.run_id, use_checkpoint_failure=False,
                    override={"step_id": "step-5", "value": {"available": True}})
    assert alt.run.status == "success" and alt.run.run_id != orig.run.run_id
    assert [s.step_index for s in alt.steps] == [5, 6, 7]
    assert orig.run.status == "failure"

# ---- batch 2: dataset variation ----
from agent.tools import SCENARIOS

@pytest.mark.parametrize("sc", list(SCENARIOS))
def test_all_scenarios_succeed_normally(sc):
    for seed in range(1, 40):
        assert run_agent(seed=seed, scenario_id=sc).run.status == "success"

@pytest.mark.parametrize("sc", list(SCENARIOS))
@pytest.mark.parametrize("ft", list(INJECTIONS))
def test_all_failures_fail_for_all_scenarios(sc, ft):
    tgt = int(INJECTIONS[ft][0].split("-")[1])
    for seed in range(1, 25):
        r = run_agent(seed=seed, scenario_id=sc, failure=inject_failure(ft, tgt, seed))
        assert r.run.status == "failure", (sc, ft, seed)
        assert min(s.step_index for s in r.steps if s.status == "failure") >= tgt

def test_dataset_generator(tmp_path, monkeypatch):
    import json, sys
    from agent import generate_dataset as g
    monkeypatch.setattr(g, "OUT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["x", "--n", "60", "--seed", "3"])
    g.main()
    rows = [json.loads(l) for l in (tmp_path / "runs.jsonl").read_text().splitlines()]
    assert len(rows) == 60
    assert all(r["split"] == "test" for r in rows if r["run"]["scenario_id"] == "flight_tight_budget")
    assert {r["split"] for r in rows} >= {"train", "test"}

def test_service_start_run():
    from agent.service import start_run
    d = start_run("flight_group", 5, "invalid_tool_output", "step-5")
    assert d["run"]["status"] == "failure" and d["ground_truth"]["target_step_id"] == "step-5"
    with pytest.raises(ValueError):
        start_run(failure_type="nope")

# ---- audit fixes ----
def _ck(res, idx):
    return next(c for c in res.checkpoints if c.step_index == idx)

def test_spec_style_replay_default_args_override_wins():
    orig = run_agent(failure=inject_failure("invalid_tool_output", 5))
    alt = run_agent(resume_from=_ck(orig, 4), parent_run_id=orig.run.run_id,
                    override={"step_id": "step-5", "value": {"available": True}})
    assert alt.run.status == "success" and alt.run.parent_run_id == orig.run.run_id

def test_override_parameter_step3():
    o = run_agent(failure=inject_failure("wrong_parameter", 3))
    a = run_agent(resume_from=_ck(o, 2), override={"step_id": "step-3", "value": {"to": "DEL"}})
    assert o.run.status == "failure" and a.run.status == "success"

def test_override_tool_result_step3_fixes_stale():
    o = run_agent(failure=inject_failure("stale_search_result", 3))
    good = run_agent(seed=42).steps[2].output_summary["results"]
    a = run_agent(resume_from=_ck(o, 2), override={"step_id": "step-3", "value": {"results": good}})
    assert a.run.status == "success"

def test_override_branch_choice_step4():
    n = run_agent()
    a = run_agent(resume_from=_ck(n, 3), override={"step_id": "step-4", "value": {"selected_flight_id": "F202"}})
    assert a.run.status == "success" and a.steps[-1].output_summary["flight_id"] == "F202"

def test_resume_completed_steps_include_reused():
    o = run_agent(failure=inject_failure("invalid_tool_output", 5))
    a = run_agent(resume_from=_ck(o, 4), override={"step_id": "step-5", "value": {"available": True}})
    assert a.checkpoints[0].step_id == "step-5"
    assert a.checkpoints[0].completed_steps == ["step-1", "step-2", "step-3", "step-4", "step-5"]

def test_no_label_marker_in_trace():
    r = run_agent(failure=inject_failure("stale_search_result", 3))
    d = json.dumps([s.model_dump(mode="json") for s in r.steps])  # step data is what ML consumes
    assert "stale" not in d and "wrong_parameter" not in d

def test_vocab_enforced_on_assignment():
    s = run_agent().steps[0]
    with pytest.raises(Exception):
        s.error_type = "bogus"
    with pytest.raises(Exception):
        s.status = "weird"

def test_determinism_across_processes():
    import subprocess, sys, os
    code = ("import json;from agent.demo_agent import run_agent,to_json;from agent.failure_injection import inject_failure;"
            "d=to_json(run_agent(seed=9,scenario_id='flight_group',failure=inject_failure('stale_search_result',3,9)));"
            "[ [s.pop(k) for k in ('run_id','created_at','checkpoint_id')] for s in d['steps']];print(json.dumps(d['steps'],sort_keys=True))")
    outs = {subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
            env={**os.environ, "PYTHONHASHSEED": h}).stdout for h in ("0", "123")}
    assert len(outs) == 1 and list(outs)[0].strip()

def test_original_unchanged_by_replay():
    o = run_agent(failure=inject_failure("invalid_tool_output", 5))
    before = o.model_dump_json()
    run_agent(resume_from=_ck(o, 4), override={"step_id": "step-5", "value": {"available": True}})
    assert o.model_dump_json() == before
