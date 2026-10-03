"""Write sanitized sample traces to data/sample_traces/ (P1). Run: python -m agent.generate_samples"""
import json, pathlib
from .demo_agent import run_agent, to_json
from .failure_injection import INJECTIONS, inject_failure

OUT = pathlib.Path("data/sample_traces"); OUT.mkdir(parents=True, exist_ok=True)

def main():
    index = []
    cases = [("success", None, 42)] + [(ft, inject_failure(ft, int(t.split("-")[1]), 42), 42)
                                        for ft, (t, _) in INJECTIONS.items()]
    for name, cfg, seed in cases:
        r = run_agent(seed=seed, failure=cfg)
        (OUT / f"{name}_seed{seed}.json").write_text(json.dumps(to_json(r), indent=2))
        first_fail = next((s.step_id for s in r.steps if s.status == "failure"), None)
        index.append({"file": f"{name}_seed{seed}.json", "run_id": r.run.run_id, "status": r.run.status,
                      "injected_target": r.ground_truth.target_step_id, "first_visible_failure": first_fail})
    (OUT / "index.json").write_text(json.dumps(index, indent=2))
    print(json.dumps(index, indent=2))

if __name__ == "__main__":
    main()
