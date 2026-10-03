import json
import httpx
import pytest
from agent.llm_agent import LLMFault, run_llm_agent, make_task
from agent.llm_client import AnthropicClient, GroqClient, HeuristicBaseline, ScriptedAgentClient
from agent.llm_tools import ALL_FAULTS
from agent import llm_pipeline as P
from tracing.render import render_trace
from tracing.schema import Step

C = ScriptedAgentClient()

def test_healthy_run_succeeds_and_has_no_truth():
    r = run_llm_agent(C, log_dir=None)
    assert r.result.run.status == "success"
    assert [s.tool for s in r.result.steps] == ["search_flights", "check_availability", "calculate_price", "prepare_booking", None]
    assert r.result.ground_truth.target_step_id is None and not r.fault_applied

@pytest.mark.parametrize("kind,tool", ALL_FAULTS)
@pytest.mark.parametrize("scenario", ["flight_basic", "flight_group", "flight_tight_budget"])
def test_every_fault_breaks_run_and_records_origin(kind, tool, scenario):
    for seed in (1, 7, 42):
        r = run_llm_agent(C, scenario, seed, LLMFault(kind=kind, tool=tool), log_dir=None)
        gt = r.result.ground_truth
        assert r.result.run.status == "failure", (kind, tool, scenario, seed)
        assert r.fault_applied and gt.target_step_id
        origin = next(s for s in r.result.steps if s.step_id == gt.target_step_id)
        assert origin.tool == tool
        first_fail = min(s.step_index for s in r.result.steps if s.status == "failure")
        assert first_fail >= origin.step_index  # never blamed before the origin

def test_steps_follow_shared_schema_and_dependencies():
    r = run_llm_agent(C, "flight_basic", 3, LLMFault(kind="faulty_tool", tool="search_flights"), log_dir=None)
    ids = [s.step_id for s in r.result.steps]
    assert ids == [f"step-{i}" for i in range(1, len(ids) + 1)]
    for s in r.result.steps:
        Step.model_validate(s.model_dump())
        assert set(s.dependency_ids) <= set(ids[: s.step_index - 1])
        assert s.model == "scripted-policy-v1"

def test_retry_count_recorded():
    r = run_llm_agent(C, "flight_basic", 5, LLMFault(kind="faulty_parameter", tool="search_flights"), log_dir=None)
    searches = [s for s in r.result.steps if s.tool == "search_flights"]
    assert [s.retry_count for s in searches] == [0, 1]

def test_fault_times_allows_recovery():
    r = run_llm_agent(C, "flight_basic", 5, LLMFault(kind="faulty_parameter", tool="search_flights", times=1), log_dir=None)
    assert r.result.run.status == "success"                      # recovered via retry
    assert r.result.ground_truth.target_step_id == "step-1"      # origin still labeled
    assert r.result.steps[0].status == "failure"

def test_unsupported_fault_rejected():
    with pytest.raises(ValueError):
        run_llm_agent(C, log_dir=None, fault=LLMFault(kind="faulty_tool", tool="prepare_booking"))

def test_deterministic_scripted_runs():
    def norm(r):
        return json.dumps([{k: v for k, v in s.model_dump(mode="json").items() if k not in ("run_id", "created_at")}
                           for s in r.result.steps], sort_keys=True)
    f = LLMFault(kind="faulty_tool", tool="calculate_price")
    assert norm(run_llm_agent(C, "flight_group", 9, f, log_dir=None)) == norm(run_llm_agent(C, "flight_group", 9, f, log_dir=None))

def test_log_files_written_and_label_separation(tmp_path):
    r = run_llm_agent(C, "flight_basic", 2, LLMFault(kind="faulty_tool", tool="check_availability"), log_dir=str(tmp_path))
    doc = json.loads(r.log_path.read_text())
    assert set(doc) == {"meta", "trace", "transcript"}
    text = json.dumps(doc["trace"])
    assert "ground_truth" not in text and "faulty_tool" not in text and "target_step" not in text
    labels = json.loads((tmp_path / "labels.json").read_text())
    assert labels[r.result.run.run_id]["target_step_id"] == r.result.ground_truth.target_step_id

def test_render_has_no_labels():
    r = run_llm_agent(C, "flight_basic", 2, LLMFault(kind="faulty_tool", tool="search_flights"), log_dir=None)
    from agent.demo_agent import to_json
    txt = render_trace(to_json(r.result))
    assert "[step-1]" in txt and "faulty" not in txt and "ground" not in txt.lower()

def test_pipeline_end_to_end_offline(tmp_path):
    runs = P.generate_logs(15, 1, C, str(tmp_path))
    assert len(runs) == 15 and len(list(tmp_path.glob("*.log.json"))) == 15
    rep = P.evaluate(str(tmp_path), HeuristicBaseline())
    assert rep["n_train"] == 10 and rep["n_test"] == 5
    assert (tmp_path / "generalized_patterns.md").exists() and (tmp_path / "eval_report.json").exists()
    assert rep["grounded_evidence_rate"] in (None, 1.0)  # baseline quotes verbatim from the log

def test_grounding_check_flags_invented_quotes(tmp_path):
    class Liar:
        name, model = "liar", "x"
        def complete(self, system, user, max_tokens=0):
            return 'noise {"origin_step_id": "step-1", "confidence": 0.9, "evidence": [{"step_id": "step-1", "quote": "totally invented text"}], "reasoning": "r"} tail'
    run_llm_agent(C, "flight_basic", 2, LLMFault(kind="faulty_tool", tool="search_flights"), log_dir=str(tmp_path))
    logs, _ = P.load_logs(str(tmp_path))
    d = P.diagnose(logs[0], "playbook", Liar())
    assert d["origin_step_id"] == "step-1" and d["evidence"][0]["grounded"] is False

def test_unparseable_llm_reply_is_safe():
    assert P._parse_json("sorry, I can't")["origin_step_id"] == "none"

def _mock_api(script):
    """Mock Anthropic API returning scripted tool_use / text responses in order."""
    state = {"i": 0, "requests": []}
    def handler(request: httpx.Request):
        body = json.loads(request.content)
        state["requests"].append(body)
        resp = script[state["i"]]
        state["i"] += 1
        return httpx.Response(200, json={"content": resp, "usage": {"input_tokens": 10, "output_tokens": 5}})
    return httpx.MockTransport(handler), state

def test_anthropic_client_drives_real_tool_loop():
    tu = lambda i, n, inp: {"type": "tool_use", "id": i, "name": n, "input": inp}
    script = [
        [{"type": "text", "text": "Searching."}, tu("t1", "search_flights", {"origin": "BOM", "destination": "DEL", "date": "2026-10-04"})],
        [tu("t2", "check_availability", {"flight_id": "F101"})],
        [tu("t3", "calculate_price", {"flight_id": "F101", "passengers": 1})],
        None,  # filled below with the real total
    ]
    ref = run_llm_agent(C, "flight_basic", 42, log_dir=None).result.steps[2].output_summary["total"]
    script[3] = [tu("t4", "prepare_booking", {"flight_id": "F101", "total": ref})]
    script.append([{"type": "text", "text": "Done."}])
    transport, state = _mock_api(script)
    client = AnthropicClient(api_key="test-key", model="test-model", transport=transport)
    r = run_llm_agent(client, "flight_basic", 42, log_dir=None)
    assert r.result.run.status == "success"
    assert [s.tool for s in r.result.steps] == ["search_flights", "check_availability", "calculate_price", "prepare_booking", None]
    assert all(s.model == "test-model" for s in r.result.steps)
    assert r.result.steps[0].tokens == 15
    # second request must carry the tool_result for the first call, in API format
    msgs = state["requests"][1]["messages"]
    assert msgs[-1]["role"] == "user" and msgs[-1]["content"][0]["type"] == "tool_result" and msgs[-1]["content"][0]["tool_use_id"] == "t1"
    assert state["requests"][0]["tools"][0]["name"] == "search_flights" and "x-api-key" not in json.dumps(state["requests"][0])

def test_anthropic_client_requires_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        AnthropicClient()


def _mock_groq_api(script):
    """Mock Groq OpenAI-compatible chat completion API returning scripted responses in order."""
    state = {"i": 0, "requests": []}
    def handler(request: httpx.Request):
        body = json.loads(request.content)
        state["requests"].append(body)
        resp = script[state["i"]]
        state["i"] += 1
        msg = {"role": "assistant"}
        if "tool_calls" in resp:
            msg["tool_calls"] = resp["tool_calls"]
        if "text" in resp:
            msg["content"] = resp["text"]
        return httpx.Response(200, json={
            "choices": [{"message": msg}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8}
        })
    return httpx.MockTransport(handler), state


def test_groq_client_requires_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        GroqClient()


def test_groq_client_complete():
    script = [{"text": "Groq analysis completed."}]
    transport, _ = _mock_groq_api(script)
    client = GroqClient(api_key="test-groq-key", model="llama-3.3-70b-versatile", transport=transport)
    res = client.complete("System prompt", "User question")
    assert res == "Groq analysis completed."


def test_groq_client_drives_real_tool_loop():
    tc = lambda i, n, inp: {"id": i, "type": "function", "function": {"name": n, "arguments": json.dumps(inp)}}
    script = [
        {"text": "Searching.", "tool_calls": [tc("t1", "search_flights", {"origin": "BOM", "destination": "DEL", "date": "2026-10-04"})]},
        {"tool_calls": [tc("t2", "check_availability", {"flight_id": "F101"})]},
        {"tool_calls": [tc("t3", "calculate_price", {"flight_id": "F101", "passengers": 1})]},
        None,
    ]
    ref = run_llm_agent(C, "flight_basic", 42, log_dir=None).result.steps[2].output_summary["total"]
    script[3] = {"tool_calls": [tc("t4", "prepare_booking", {"flight_id": "F101", "total": ref})]}
    script.append({"text": "Done."})
    transport, state = _mock_groq_api(script)
    client = GroqClient(api_key="test-groq-key", model="test-groq-model", transport=transport)
    r = run_llm_agent(client, "flight_basic", 42, log_dir=None)
    assert r.result.run.status == "success"
    assert [s.tool for s in r.result.steps] == ["search_flights", "check_availability", "calculate_price", "prepare_booking", None]
    assert all(s.model == "test-groq-model" for s in r.result.steps)
    assert r.result.steps[0].tokens == 20
    # second request carried tool result in OpenAI format
    msgs = state["requests"][1]["messages"]
    assert any(m["role"] == "tool" and m["tool_call_id"] == "t1" for m in msgs)

