"""Batch dataset generator for P2 (P1). Run: python -m agent.generate_dataset --n 600 --seed 1
Writes data/synthetic/runs.jsonl (one RunResult JSON per line) and data/synthetic/benchmark_cases.json.
Split rule (by whole run): scenario 'flight_tight_budget' is HELD OUT entirely -> test; others hashed 70/15/15.
~15% of runs are normal (no injected failure)."""
import argparse, json, pathlib, random, uuid
from .demo_agent import run_agent, to_json
from .failure_injection import INJECTIONS, inject_failure
from .tools import SCENARIOS

OUT = pathlib.Path("data/synthetic")

def split_for(scenario_id: str, rng: random.Random) -> str:
    if scenario_id == "flight_tight_budget":
        return "test"
    x = rng.random()
    return "train" if x < 0.70 else "validation" if x < 0.85 else "test"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    scenarios, fts = sorted(SCENARIOS), sorted(INJECTIONS)
    cases, runs_f = [], open(OUT / "runs.jsonl", "w")
    for i in range(a.n):
        seed = rng.randrange(1, 10_000_000)
        sc = rng.choice(scenarios)
        cfg = None
        if rng.random() >= 0.15:
            ft = rng.choice(fts)
            cfg = inject_failure(ft, int(INJECTIONS[ft][0].split("-")[1]), seed)
        r = run_agent(seed=seed, failure=cfg, scenario_id=sc)
        d = to_json(r); d["split"] = split_for(sc, rng)
        runs_f.write(json.dumps(d) + "\n")
        cases.append({"benchmark_id": str(uuid.UUID(int=rng.getrandbits(128))), "scenario_id": sc,
                      "failure_type": cfg.failure_type if cfg else "none",
                      "target_step_id": cfg.target_step if cfg else None, "split": d["split"],
                      "seed": seed, "notes": r.run.run_id})
    runs_f.close()
    (OUT / "benchmark_cases.json").write_text(json.dumps(cases, indent=1))
    from collections import Counter
    print("runs:", a.n, "| splits:", dict(Counter(c["split"] for c in cases)),
          "| failure types:", dict(Counter(c["failure_type"] for c in cases)))

if __name__ == "__main__":
    main()
