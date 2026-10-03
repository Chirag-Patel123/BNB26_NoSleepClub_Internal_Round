"""LLM clients (P1): real Claude via HTTPS, plus an offline scripted agent policy.

AnthropicClient   - real model; needs ANTHROPIC_API_KEY. Env: BLACKBOX_LLM_MODEL (default claude-sonnet-5-5)
ScriptedAgentClient - deterministic offline stand-in that behaves like a tool-using model (NOT an LLM).
HeuristicBaseline - offline rules diagnoser used as a baseline / for tests (NOT an LLM).
"""
from __future__ import annotations
import json, os, re, time
from typing import Any, Optional
import httpx

DEFAULT_MODEL = "claude-sonnet-5-5"

class AnthropicClient:
    name = "anthropic"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None,
                 transport: Optional[httpx.BaseTransport] = None, timeout: float = 90.0):
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set (put it in your local .env / environment, never in git)")
        self.model = model or os.getenv("BLACKBOX_LLM_MODEL", DEFAULT_MODEL)
        self._http = httpx.Client(base_url="https://api.anthropic.com", timeout=timeout, transport=transport,
                                  headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                           "content-type": "application/json"})

    def _post(self, payload: dict) -> dict:
        r = self._http.post("/v1/messages", json={**payload, "temperature": 0})
        if r.status_code == 400 and "temperature" in r.text:  # some models reject it
            r = self._http.post("/v1/messages", json=payload)
        r.raise_for_status()
        return r.json()

    def step(self, system: str, messages: list, tools: list) -> dict:
        t0 = time.time()
        data = self._post({"model": self.model, "max_tokens": 1024, "system": system,
                           "messages": messages, "tools": tools})
        blocks = data["content"]
        u = data.get("usage", {})
        return {"text": "".join(b.get("text", "") for b in blocks if b["type"] == "text"),
                "tool_calls": [{"id": b["id"], "name": b["name"], "input": b["input"]}
                               for b in blocks if b["type"] == "tool_use"],
                "content": blocks, "llm_ms": int((time.time() - t0) * 1000),
                "usage": {"input_tokens": u.get("input_tokens", 0), "output_tokens": u.get("output_tokens", 0)}}

    def complete(self, system: str, user: str, max_tokens: int = 1500) -> str:
        data = self._post({"model": self.model, "max_tokens": max_tokens, "system": system,
                           "messages": [{"role": "user", "content": user}]})
        return "".join(b.get("text", "") for b in data["content"] if b["type"] == "text")


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
