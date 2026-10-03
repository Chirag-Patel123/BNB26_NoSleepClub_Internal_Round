// Backend access. With VITE_API_URL unset the app runs on sample data (see data.js).
const BASE = import.meta.env.VITE_API_URL || ''
export const live = Boolean(BASE)

export async function api(path, opts) {
  const res = await fetch(BASE + path, opts)
  if (!res.ok) throw new Error(`${res.status} ${path}`)
  return res.json()
}

// Endpoints expected from api/routes.py:
//   GET /runs/recent · GET /runs/{id} · GET /runs/{id}/diagnosis · POST /runs
//   POST /runs/{id}/replay · GET /runs/compare?original_id=&alternative_id= · GET /evaluation
// TODO: map each response onto the run shape in data.js ({id, ok, ft, culprit, steps, scores, ev, parent}).
