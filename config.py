"""Shared config. Reads .env locally; never hard-code secrets."""
import os
from dotenv import load_dotenv
load_dotenv()
DB_URL = os.getenv("SUPABASE_DB_URL", "")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
SCENARIOS = ["flight_basic", "flight_group", "flight_tight_budget"]
FAILURE_TYPES = ["stale_search_result", "incorrect_filtering", "invalid_tool_output",
                 "calculation_error", "wrong_parameter"]
