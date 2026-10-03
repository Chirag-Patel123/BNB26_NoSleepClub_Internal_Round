"""Tools for the LLM-driven agent, with optional injected faults (P1).

Two fault kinds:
  faulty_parameter : the arguments the model asked for are corrupted at the tool-call boundary
  faulty_tool      : the tool itself misbehaves (stale data / garbage response / wrong math)
Tools return {"error": <code>, ...} when they detect a problem; the harness also validates response shape.
"""
from __future__ import annotations
from . import tools as base

ERROR_TYPES = {
    "no_results": "retrieval_context_failure", "price_mismatch": "retrieval_context_failure",
    "unknown_flight": "parameter_failure", "invalid_parameter": "parameter_failure",
    "unavailable": "tool_output_failure", "invalid_response": "tool_output_failure",
    "invalid_total": "state_corruption", "total_mismatch": "state_corruption",
    "unknown_tool": "model_decision_failure",
}

TOOL_SPECS = [
    {"name": "search_flights", "description": "Search flights for a route and date. Returns a list of flights with id and price (INR).",
     "input_schema": {"type": "object", "properties": {"origin": {"type": "string"}, "destination": {"type": "string"},
                      "date": {"type": "string"}}, "required": ["origin", "destination", "date"]}},
    {"name": "check_availability", "description": "Confirm that a flight from the latest search is available.",
     "input_schema": {"type": "object", "properties": {"flight_id": {"type": "string"}}, "required": ["flight_id"]}},
    {"name": "calculate_price", "description": "Compute the total price (INR, incl. taxes) for a flight and passenger count.",
     "input_schema": {"type": "object", "properties": {"flight_id": {"type": "string"}, "passengers": {"type": "integer"}},
                      "required": ["flight_id", "passengers"]}},
    {"name": "prepare_booking", "description": "Prepare a mock booking payload (no real booking). Total must match calculate_price.",
     "input_schema": {"type": "object", "properties": {"flight_id": {"type": "string"}, "total": {"type": "number"}},
                      "required": ["flight_id", "total"]}},
]

# (kind, tool) combinations the harness supports
ALL_FAULTS = [
    ("faulty_tool", "search_flights"), ("faulty_parameter", "search_flights"),
    ("faulty_tool", "check_availability"), ("faulty_parameter", "check_availability"),
    ("faulty_tool", "calculate_price"), ("faulty_parameter", "calculate_price"),
    ("faulty_parameter", "prepare_booking"),
]

def corrupt_args(tool: str, args: dict) -> dict:
    a = dict(args)
    if tool == "search_flights":
        a["destination"] = "BLR"
    elif tool in ("check_availability", "prepare_booking"):
        a["flight_id"] = "F999"
    elif tool == "calculate_price":
        a["passengers"] = 0
    return a

def _find(env: dict, key: str, fid):
    return next((f for f in env.get(key, []) if f["id"] == fid), None)

def search_flights(args, env, seed, bad):
    o, d, date = args.get("origin"), args.get("destination"), args.get("date")
    res = base.search_flights({"from": o, "to": d, "date": date}, seed)["results"]
    if o != "BOM" or d != "DEL":
        res = []
    env["truth_search"] = [dict(f) for f in res]
    if bad:  # stale prices, silently
        res = [{**f, "price": f["price"] - 1800} for f in res]
    env["search"] = res
    if not res:
        return {"error": "no_results", "message": f"no flights found for {o}->{d} on {date}", "results": []}
    return {"results": res}

def check_availability(args, env, seed, bad):
    fid = args.get("flight_id")
    f = _find(env, "search", fid)
    if f is None:
        return {"error": "unknown_flight", "message": f"flight {fid} not in latest search results"}
    if bad:  # garbage response, no error flag
        return {"flight_id": fid, "available": None, "seats_left": -1}
    t = _find(env, "truth_search", fid)
    if t is None or t["price"] != f["price"]:
        return {"error": "price_mismatch", "message": "listed price does not match availability service"}
    return base.validate_availability(f, seed)

def calculate_price(args, env, seed, bad):
    fid, pax = args.get("flight_id"), args.get("passengers")
    if not isinstance(pax, int) or pax < 1:
        return {"error": "invalid_parameter", "message": "passengers must be an integer >= 1"}
    f = _find(env, "search", fid)
    if f is None:
        return {"error": "unknown_flight", "message": f"flight {fid} not in latest search results"}
    out = base.calculate_price(f, pax)
    if bad:  # wrong math, silently
        out = {**out, "total": -out["total"]}
    return out

def prepare_booking(args, env, seed, bad):
    fid, total = args.get("flight_id"), args.get("total")
    f = _find(env, "search", fid)
    if f is None:
        return {"error": "unknown_flight", "message": f"flight {fid} not in latest search results"}
    if not isinstance(total, (int, float)) or total <= 0:
        return {"error": "invalid_total", "message": f"invalid total price {total}"}
    expected = base.calculate_price(f, env["journey"]["passengers"])["total"]
    if total != expected:
        return {"error": "total_mismatch", "message": f"total {total} does not match computed price {expected}"}
    payload = base.prepare_booking_payload(f, {"total": total})
    env["booking"] = payload
    return payload

TOOLS = {"search_flights": search_flights, "check_availability": check_availability,
         "calculate_price": calculate_price, "prepare_booking": prepare_booking}

def validate_result(name: str, result: dict):
    """Return an error code if a response is structurally invalid even without an 'error' key."""
    if "error" in result:
        return result["error"]
    if name == "check_availability" and not isinstance(result.get("available"), bool):
        return "invalid_response"
    return None
