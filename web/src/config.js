export const API_BASE = (
  import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD
    ? "https://bnb26nosleepclubinternalround-production.up.railway.app"
    : "http://localhost:8000")
).replace(/\/$/, "");

