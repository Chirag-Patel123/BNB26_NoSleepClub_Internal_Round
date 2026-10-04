"""Deterministic mock tools (P1). Same seed + input => same output."""
import random

def _rng(seed: int, salt: str) -> random.Random:
    return random.Random(f"{seed}:{salt}")

def parse_request(task: str) -> dict:
    return {"intent": "find_flight", "raw": task}

SCENARIOS = {  # scenario_id -> (base max_price, passengers)
    "agent_basic": (6000, 1),
    "agent_group": (7500, 3),
    "agent_tight_budget": (5500, 1),
    "flight_basic": (6000, 1),
    "flight_group": (7500, 3),
    "flight_tight_budget": (5500, 1),
}

def extract_journey(task: str, scenario_id: str = "agent_basic", seed: int = 42) -> dict:
    base, pax = SCENARIOS.get(scenario_id, SCENARIOS["agent_basic"])
    jitter = _rng(seed, "budget").randrange(0, 5) * 100
    origin = "DEL" if "Delhi" in task or "DEL" in task else "BOM"
    destination = "BLR" if "Bengaluru" in task or "Bangalore" in task or "BLR" in task else ("DEL" if origin != "DEL" else "BOM")
    if "Bengaluru" not in task and "BLR" not in task and "Delhi to" not in task:
        origin, destination = "BOM", "DEL"
    return {"from": origin, "to": destination, "date": "2026-10-04", "max_price": base + jitter, "passengers": pax}

def search_flights(query: dict, seed: int) -> dict:
    base = 4800 + _rng(seed, "search").randrange(0, 4) * 100
    q_from = query.get("from", "BOM")
    q_to = query.get("to", "DEL")
    return {"tool": "search_flights", "query": query, "results": [
        {"id": "F101", "origin": q_from, "destination": q_to, "price": base + 200, "available": True},
        {"id": "F202", "origin": q_from, "destination": q_to, "price": base + 1100, "available": True},
        {"id": "F303", "origin": q_from, "destination": q_to, "price": base + 2500, "available": True}]}

def filter_flights(results: list, max_price: int) -> list:
    return [f for f in results if f["price"] <= max_price]

def validate_availability(flight: dict, seed: int) -> dict:
    return {"flight_id": flight["id"], "available": True, "seats_left": 3 + _rng(seed, "avail").randrange(5)}

def calculate_price(flight: dict, passengers: int) -> dict:
    taxes = round(flight["price"] * 0.12)
    return {"base": flight["price"], "taxes": taxes, "total": flight["price"] * passengers + taxes}

def prepare_booking_payload(flight: dict, price: dict) -> dict:
    return {
        "mock": True,
        "flight_id": flight["id"],
        "origin": flight.get("origin", "BOM"),
        "destination": flight.get("destination", "DEL"),
        "total": price["total"],
        "status": "ready_to_book"
    }

parse_query = parse_request
fetch_data = search_flights
filter_records = filter_flights
validate_constraints = validate_availability
compute_metrics = calculate_price
execute_action = prepare_booking_payload
