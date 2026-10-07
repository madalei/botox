// Base URL of the FastAPI backend.
// Override in frontend/.env.local, e.g. VITE_API_URL=http://localhost:8001 for the Docker backend.
const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`)
  if (!response.ok) {
    throw new Error(`GET ${path} failed: ${response.status} ${response.statusText}`)
  }
  return response.json() as Promise<T>
}

// Mirrors RunningBot in backend/app/api/queries/bots.py
export type RunningBot = {
  bot_id: string
  status: string
  strategy: string
  params: Record<string, unknown>
}
