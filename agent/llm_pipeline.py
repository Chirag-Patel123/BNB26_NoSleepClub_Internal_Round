"""Generate static logs from the faulty LLM agent, let an AI generalize them, then pinpoint failures (P1).

  python -m agent.llm_pipeline generate --n 15 --agent-client scripted
  python -m agent.llm_pipeline evaluate --analysis-client heuristic
  python -m agent.llm_pipeline evaluate --agent-client groq --analysis-client groq   (needs GROQ_API_KEY)
"""
from __future__ import annotations
import argparse, json, pathlib, random
from typing import Any
from tracing.render import render_trace
from . import llm_tools as T
from .llm_agent import LLMFault, run_llm_agent
from .llm_client import GroqClient, HeuristicBaseline, ScriptedAgentClient
from .tools import SCENARIOS

GEN_SYSTEM = (
    "You analyze logs of a tool-using AI agent. Each log comes with a LABEL naming the ORIGIN step: the step where the "
    "fault was introduced. The origin is often EARLIER than the step where the run visibly fails. Write a concise "
    "playbook (max 400 words): for each distinct failure pattern, which observable signals in the log (tool, args, "
    "output, status, error_type, error_message, retries) identify the origin step versus the visible crash. Only cite "
    "signals visible in the logs. No speculation.")
DIAG_SYSTEM = (
    "You debug logs of a tool-using AI agent. Using the playbook, identify the step that most likely INTRODUCED the "
    "failure (the origin), which may be earlier than the visible crash; answer \"none\" if the run looks healthy. "
    "Respond with ONLY JSON: {\"origin_step_id\": \"step-N\" or \"none\", \"confidence\": 0-1, "
    "\"evidence\": [{\"step_id\": \"step-N\", \"quote\": \"<text copied verbatim from the log>\"}], "
    "\"reasoning\": \"<1-2 sentences>\"}. Quotes must be copied verbatim from the log.")

def make_agent_client(name: str):
    if name == "groq":
        return GroqClient()
    return ScriptedAgentClient()

def make_analysis_client(name: str):
    if name == "groq":
        return GroqClient()
    return HeuristicBaseline()


def generate_logs(n: int, seed: int, agent_client, log_dir: str, healthy_every: int = 8):
    """Deterministic mix: every supported fault x scenarios, plus healthy runs, cycled until n logs exist."""
    rng, scen, out = random.Random(seed), sorted(SCENARIOS), []
    cases: list[Any] = [None] + [LLMFault(kind=k, tool=t) for k, t in T.ALL_FAULTS]
    for i in range(n):
        fault = cases[i % len(cases)]
        out.append(run_llm_agent(agent_client, scen[rng.randrange(len(scen))], rng.randrange(1, 10_000_000), fault, log_dir))
    return out

def load_logs(log_dir: str):
    d = pathlib.Path(log_dir)
    labels = json.loads((d / "labels.json").read_text())
    logs = [json.loads(p.read_text()) for p in sorted(d.glob("*.log.json"))]
    return logs, labels

def split(logs):
    """Every third log is held out for testing; the rest train the playbook."""
    return [l for i, l in enumerate(logs) if i % 3 != 2], [l for i, l in enumerate(logs) if i % 3 == 2]

def generalize(train_logs, labels, client, max_logs: int = 12) -> str:
    parts = []
    for log in train_logs[:max_logs]:
        lab = labels[log["meta"]["run_id"]]
        tag = f"LABEL: origin={lab['target_step_id'] or 'none'} (fault: {lab['fault_kind']} on {lab['fault_tool']})" \
            if lab["fault_applied"] else "LABEL: healthy run, origin=none"
        parts.append(f"<log>\n{render_trace(log['trace'])}\n</log>\n{tag}")
    return client.complete(GEN_SYSTEM, "\n\n".join(parts), 1200)

def _parse_json(text: str) -> dict:
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b < a:
        return {"origin_step_id": "none", "confidence": 0.0, "evidence": [], "reasoning": "unparseable reply"}
    try:
        return json.loads(text[a:b + 1])
    except json.JSONDecodeError:
        return {"origin_step_id": "none", "confidence": 0.0, "evidence": [], "reasoning": "unparseable reply"}

def diagnose(log: dict, playbook: str, client) -> dict:
    rendered = render_trace(log["trace"])
    reply = _parse_json(client.complete(DIAG_SYSTEM, f"PLAYBOOK:\n{playbook}\n\n<log>\n{rendered}\n</log>", 600))
    ev = reply.get("evidence") or []
    for e in ev:  # evidence rule: every quote must be verbatim from the log
        e["grounded"] = bool(e.get("quote")) and e["quote"].strip() in rendered
    reply["evidence"] = ev
    return reply

def evaluate(log_dir: str, analysis_client) -> dict:
    logs, labels = load_logs(log_dir)
    train, test = split(logs)
    playbook = generalize(train, labels, analysis_client)
    pathlib.Path(log_dir, "generalized_patterns.md").write_text(playbook)
    rows = []
    for log in test:
        lab = labels[log["meta"]["run_id"]]
        d = diagnose(log, playbook, analysis_client)
        steps = log["trace"]["steps"]
        first_fail = next((s["step_id"] for s in steps if s["status"] == "failure"), None)
        ev = d.get("evidence", [])
        rows.append({"run_id": log["meta"]["run_id"], "truth": lab["target_step_id"] or "none",
                     "fault": f"{lab['fault_kind']}:{lab['fault_tool']}" if lab["fault_applied"] else "healthy",
                     "predicted": d.get("origin_step_id", "none"), "first_failure_baseline": first_fail or "none",
                     "grounded_evidence": (sum(e["grounded"] for e in ev), len(ev))})
    faulty = [r for r in rows if r["truth"] != "none"]
    hit = lambda key: sum(r[key] == r["truth"] for r in faulty)
    report = {"analysis_client": analysis_client.name, "model": analysis_client.model,
              "n_logs": len(logs), "n_train": len(train), "n_test": len(test), "n_test_faulty": len(faulty),
              "top1_origin_accuracy": hit("predicted") / len(faulty) if faulty else None,
              "naive_first_failure_accuracy": hit("first_failure_baseline") / len(faulty) if faulty else None,
              "healthy_false_alarms": sum(r["truth"] == "none" and r["predicted"] != "none" for r in rows),
              "grounded_evidence_rate": (lambda g: g[0] / g[1] if g[1] else None)(
                  (sum(r["grounded_evidence"][0] for r in rows), sum(r["grounded_evidence"][1] for r in rows))),
              "rows": rows}
    pathlib.Path(log_dir, "eval_report.json").write_text(json.dumps(report, indent=1))
    return report

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["generate", "evaluate"])
    ap.add_argument("--n", type=int, default=15)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--log-dir", default="logs/llm_agent")
    ap.add_argument("--agent-client", default="scripted", choices=["scripted", "groq"])
    ap.add_argument("--analysis-client", default="heuristic", choices=["heuristic", "groq"])
    a = ap.parse_args(argv)
    if a.cmd == "generate":
        runs = generate_logs(a.n, a.seed, make_agent_client(a.agent_client), a.log_dir)
        print(f"wrote {len(runs)} logs to {a.log_dir} "
              f"(failed: {sum(r.result.run.status == 'failure' for r in runs)}, fault applied: {sum(r.fault_applied for r in runs)})")
    else:
        rep = evaluate(a.log_dir, make_analysis_client(a.analysis_client))
        print(json.dumps({k: v for k, v in rep.items() if k != "rows"}, indent=1))

if __name__ == "__main__":
    main()
