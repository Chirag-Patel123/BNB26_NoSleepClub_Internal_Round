# LLM Agent with Faulty Tools, Static Logs, and AI Log Analysis (P1)

Follows the mentor's advice: record logs as plain files first (no database), collect 10-15+ runs, give them
to an AI to generalize and pinpoint the failing step, use pre-trained models only, UI afterwards.

## Pipeline

```
faulty tool / faulty parameters ──► LLM agent loop ──► logs/llm_agent/<run_id>.log.json   (what a debugger sees)
                                                  └──► logs/llm_agent/labels.json         (ground truth, evaluation only)
                    10-15+ logs ──► AI "generalize" ──► logs/llm_agent/generalized_patterns.md
                    fresh log   ──► AI "diagnose"   ──► origin step + verbatim evidence (grounding-checked)
```

## Quick start

```bash
# offline, no API key: scripted agent policy + rules baseline (good for testing the pipeline)
python -m agent.llm_pipeline generate --n 15 --agent-client scripted
python -m agent.llm_pipeline evaluate --analysis-client heuristic

# real Claude as the agent AND as the analyst (needs a key; never commit it)
set ANTHROPIC_API_KEY=your-key-here          (Windows cmd)   |   export ANTHROPIC_API_KEY=...   (bash)
set BLACKBOX_LLM_MODEL=claude-sonnet-5-5     (optional override)
python -m agent.llm_pipeline generate --n 20 --agent-client anthropic --log-dir logs/claude_agent
python -m agent.llm_pipeline evaluate --log-dir logs/claude_agent --analysis-client anthropic

# real Groq (Llama-3.3-70b-versatile, ultra-fast & free tier available)
set GROQ_API_KEY=your-key-here               (Windows cmd)   |   export GROQ_API_KEY=...        (bash)
set GROQ_MODEL=llama-3.3-70b-versatile       (optional override)
python -m agent.llm_pipeline generate --n 20 --agent-client groq --log-dir logs/groq_agent
python -m agent.llm_pipeline evaluate --log-dir logs/groq_agent --analysis-client groq
```

Add `ANTHROPIC_API_KEY=`, `BLACKBOX_LLM_MODEL=`, `GROQ_API_KEY=`, and `GROQ_MODEL=` (names only) to `.env.example`.

## The agent
A tool-using loop: the model chooses tools and arguments. Tools: `search_flights`, `check_availability`,
`calculate_price`, `prepare_booking` (all mock). Each tool call is one canonical `Step` (same schema as the
deterministic agent; `model` and `tokens` are filled). A final `final_answer` step is success only if a valid
booking was prepared. A run that recovers from an early failed step still ends `success`.

## Faults (`agent/llm_tools.py`, `ALL_FAULTS`)

| Kind | Tool | What goes wrong |
|---|---|---|
| faulty_tool | search_flights | Prices silently stale (lower than the truth) |
| faulty_parameter | search_flights | Destination corrupted to BLR, so no results |
| faulty_tool | check_availability | Garbage response (`available: null`, `seats_left: -1`) |
| faulty_parameter | check_availability | flight_id corrupted to F999 |
| faulty_tool | calculate_price | Total silently negated |
| faulty_parameter | calculate_price | passengers corrupted to 0 |
| faulty_parameter | prepare_booking | flight_id corrupted to F999 |

`LLMFault(kind, tool, times=None)`: `times=None` corrupts every call; `times=1` only the first, so a retry can recover.
Parameter faults are injected at the tool-call boundary: the trace logs the arguments actually executed, while the
raw transcript keeps what the model requested.

## Logs
- `*.log.json`: `meta`, `trace` (run, steps, graph), `transcript` (sanitized messages). No ground truth.
- `labels.json`: per run id, the true origin step, fault kind/tool, whether the fault was applied, and the outcome.
- `tracing/render.py` turns a trace into the plain text an AI reads (no labels, no fault names).

## AI analysis (`agent/llm_pipeline.py`)
1. **Generalize:** training logs plus their labels go to the model, which writes a short playbook of failure
   patterns (which signals identify the origin versus the visible crash).
2. **Diagnose:** the playbook plus one unlabeled log produce JSON: `origin_step_id`, `confidence`, `evidence`, `reasoning`.
3. **Grounding check:** each evidence quote must appear verbatim in the log; otherwise `grounded=false`.
   This keeps the project rule that evidence comes from real trace facts, not model invention.
4. **Evaluate:** every third log is held out. Reports top-1 origin accuracy, a naive "blame the first failure"
   baseline, healthy-run false alarms, and the grounded-evidence rate.

## Offline stand-ins (be honest about these)
- `ScriptedAgentClient` is a deterministic policy that behaves like a tool-using model. It is NOT an LLM.
- `HeuristicBaseline` is a rules diagnoser. It is NOT an LLM. It was written with knowledge of this agent's error
  types, so its near-perfect score on scripted logs is expected and does not show that an LLM will do well.
  Use it only as a baseline and to test the pipeline.
- Real conclusions need `--agent-client anthropic` and `--analysis-client anthropic` runs on your machine.
  Real model logs will be messier (different retries, different reasoning), which is the point.

## Limits
- No checkpoint replay for this agent (it would need the conversation state). Replay targets the deterministic agent.
- Small log counts give noisy accuracy. Use 30+ logs before quoting a number; 15 leaves about 3 faulty test cases.
- Spec tension: the master spec says an LLM must not invent explanations. The grounding check enforces this for
  the AI diagnoser; keep the RandomForest and rules scoring as the primary, trace-grounded diagnoser unless the
  team agrees otherwise.
