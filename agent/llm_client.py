"""LLM clients (P1): pre-trained Groq API via HTTPS, plus an offline scripted agent policy.

GroqClient          - real pre-trained model on Groq (Llama-3.3-70b-versatile); needs GROQ_API_KEY.
ScriptedAgentClient - deterministic offline stand-in that behaves like a tool-using model (NOT an LLM).
HeuristicBaseline   - offline rules diagnoser used as a baseline / for tests (NOT an LLM).
"""
from __future__ import annotations
import json, os, re, time
from typing import Any, Optional
import httpx

DEFAULT_MODEL = "llama-3.3-70b-versatile"


class GroqClient:
    """Real model on Groq via OpenAI-compatible HTTPS API; needs GROQ_API_KEY.
    Env: GROQ_MODEL (default llama-3.3-70b-versatile).
    """
    name = "groq"
    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None,
                 transport: Optional[httpx.BaseTransport] = None, timeout: float = 90.0):
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY is not set (put it in your local .env / environment, never in git)")
        self.model = model or os.getenv("GROQ_MODEL", self.DEFAULT_MODEL)
        self._http = httpx.Client(base_url="https://api.groq.com/openai/v1", timeout=timeout, transport=transport,
                                  headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})

    def _post(self, payload: dict) -> dict:
        r = self._http.post("/chat/completions", json={**payload, "temperature": 0})
        r.raise_for_status()
        return r.json()

    def complete(self, system: str, user: str, max_tokens: int = 1500) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        data = self._post({"model": self.model, "max_tokens": max_tokens, "messages": messages})
        choice = data["choices"][0]["message"]
        return choice.get("content") or ""

    def step(self, system: str, messages: list, tools: list) -> dict:
        openai_tools = [
            {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}
            for t in tools
        ]
        openai_msgs = []
        if system:
            openai_msgs.append({"role": "system", "content": system})
        for m in messages:
            role = m["role"]
            content = m["content"]
            if isinstance(content, str):
                openai_msgs.append({"role": role, "content": content})
            elif isinstance(content, list):
                tool_results = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"]
                tool_uses = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
                text_parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]

                if tool_results:
                    for tr in tool_results:
                        openai_msgs.append({
                            "role": "tool",
                            "tool_call_id": tr["tool_use_id"],
                            "content": tr["content"]
                        })
                elif tool_uses:
                    openai_msgs.append({
                        "role": "assistant",
                        "content": "".join(text_parts) or None,
                        "tool_calls": [
                            {
                                "id": tu["id"],
                                "type": "function",
                                "function": {
                                    "name": tu["name"],
                                    "arguments": json.dumps(tu["input"])
                                }
                            }
                            for tu in tool_uses
                        ]
                    })
                else:
                    openai_msgs.append({"role": role, "content": "".join(text_parts)})

        t0 = time.time()
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": openai_msgs,
            "tools": openai_tools
        }
        data = self._post(payload)
        choice = data["choices"][0]["message"]
        text = choice.get("content") or ""
        raw_tool_calls = choice.get("tool_calls") or []

        blocks = []
        if text:
            blocks.append({"type": "text", "text": text})
        tool_calls = []
        for tc in raw_tool_calls:
            fn = tc["function"]
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except Exception:
                args = {}
            tool_calls.append({"id": tc["id"], "name": fn["name"], "input": args})
            blocks.append({"type": "tool_use", "id": tc["id"], "name": fn["name"], "input": args})

        u = data.get("usage", {})
        return {
            "text": text,
            "tool_calls": tool_calls,
            "content": blocks,
            "llm_ms": int((time.time() - t0) * 1000),
            "usage": {
                "input_tokens": u.get("prompt_tokens", 0),
                "output_tokens": u.get("completion_tokens", 0)
            }
        }



class ScriptedAgentClient:
    """Deterministic tool-using policy: search -> check -> price -> book, with simple retry/fallback behavior."""
    name = "scripted"
    model = "scripted-policy-v1"

    _TASK = re.compile(r"\((\w+)\).*?\((\w+)\).*?on (\d{4}-\d{2}-\d{2}) under (\d+) INR for (\d+) passenger")

    @staticmethod
    def _history(messages):
        uses, hist = {}, []
        for m in messages[1:]:
            if m["role"] == "assistant":
                for b in m["content"]:
                    if b["type"] == "tool_use":
                        uses[b["id"]] = b
            else:
                for b in m["content"]:
                    if b["type"] == "tool_result":
                        u = uses[b["tool_use_id"]]
                        hist.append({"name": u["name"], "input": u["input"], "result": json.loads(b["content"]),
                                     "error": bool(b.get("is_error"))})
        return hist

    @staticmethod
    def _reply(text, calls=()):
        content = ([{"type": "text", "text": text}] if text else []) + \
                  [{"type": "tool_use", "id": i, "name": n, "input": inp} for i, n, inp in calls]
        return {"text": text, "tool_calls": [{"id": i, "name": n, "input": inp} for i, n, inp in calls],
                "content": content, "llm_ms": 0, "usage": {"input_tokens": 0, "output_tokens": 0}}

    def step(self, system, messages, tools):
        origin, dest, date, budget, pax = self._TASK.search(messages[0]["content"]).groups()
        budget, pax = int(budget), int(pax)
        hist = self._history(messages)
        n = len(hist) + 1
        call = lambda text, name, **inp: self._reply(text, [(f"toolu_scripted_{n}", name, inp)])
        stop = lambda text: self._reply(text)
        consec = 0
        for h in reversed(hist):
            if h["name"] == (hist[-1]["name"] if hist else None) and h["error"]:
                consec += 1
            else:
                break
        if not hist:
            return call("Searching for flights.", "search_flights", origin=origin, destination=dest, date=date)
        last = hist[-1]
        searches = [h for h in hist if h["name"] == "search_flights" and not h["error"]]
        cands = []
        if searches:
            cands = sorted([f for f in searches[-1]["result"]["results"] if f["price"] <= budget], key=lambda f: f["price"])
        if last["name"] == "search_flights":
            if last["error"]:
                if consec <= 1:
                    return call("Search failed; retrying.", "search_flights", origin=origin, destination=dest, date=date)
                return stop("Flight search keeps failing; giving up.")
            if not cands:
                return stop("No flights within budget.")
            return call("Checking the cheapest option.", "check_availability", flight_id=cands[0]["id"])
        if last["name"] == "check_availability":
            if not last["error"]:
                return call("Calculating the price.", "calculate_price", flight_id=last["input"]["flight_id"], passengers=pax)
            tried = {h["input"].get("flight_id") for h in hist if h["name"] == "check_availability"}
            rest = [f for f in cands if f["id"] not in tried]
            if rest and consec <= 2:
                return call("Trying the next option.", "check_availability", flight_id=rest[0]["id"])
            return stop("Could not confirm availability for any flight.")
        if last["name"] == "calculate_price":
            if last["error"]:
                if consec <= 1:
                    return call("Pricing failed; retrying.", "calculate_price", flight_id=last["input"]["flight_id"], passengers=pax)
                return stop("Pricing keeps failing; giving up.")
            return call("Preparing the booking.", "prepare_booking", flight_id=last["input"]["flight_id"],
                        total=last["result"]["total"])
        if last["error"]:
            return stop("Booking preparation failed.")
        return stop(f"Booking prepared for {last['input']['flight_id']}, total {last['input']['total']} INR.")


class HeuristicBaseline:
    """Offline rules diagnoser (NOT an LLM): blames the step before the first failure when the error type
    points at upstream data, otherwise the failing step itself. Serves as a comparison baseline."""
    name = "heuristic-baseline"
    model = "rules-v1"
    _STEP = re.compile(r"^\[(step-\d+)\] tool=(\S+) type=\S+ status=(\S+)", re.M)

    def complete(self, system: str, user: str, max_tokens: int = 0) -> str:
        if "playbook" in system.lower() and "ONLY JSON" not in system:
            return "HEURISTIC BASELINE: no learned playbook."
        log = user.split("<log>")[-1].split("</log>")[0]
        steps = self._STEP.findall(log)
        errs = dict(re.findall(r"^\[(step-\d+)\].*?\n(?:  .*\n)*?  error: (\w+):", log + "\n", re.M))
        fails = [s for s in steps if s[2] == "failure"]
        if not fails:
            return json.dumps({"origin_step_id": "none", "confidence": 0.5, "evidence": [], "reasoning": "no failed step"})
        first = fails[0][0]
        idx = [s[0] for s in steps].index(first)
        upstream = errs.get(first) in ("retrieval_context_failure", "state_corruption", "model_decision_failure")
        origin = steps[idx - 1][0] if upstream and idx > 0 and steps[idx - 1][2] == "success" else first
        quote = next((ln.strip() for ln in log.splitlines() if ln.startswith(f"[{origin}]")), "")
        return json.dumps({"origin_step_id": origin, "confidence": 0.5, "evidence": [{"step_id": origin, "quote": quote}],
                           "reasoning": f"first failure at {first}; error type {errs.get(first)}"})
