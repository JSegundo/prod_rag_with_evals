const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function apiFetch<T = unknown>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `API error: ${res.status}`)
  }
  return res.json()
}

export function apiUpload<T = unknown>(path: string, body: FormData): Promise<T> {
  return fetch(`${API_URL}${path}`, {
    method: 'POST',
    credentials: 'include',
    body,
  }).then(async (res) => {
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
    return res.json()
  })
}
