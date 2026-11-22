// API Client connecting Next.js Frontend with Member 4 (FastAPI) and Member 2 (Intelligence Engine).

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || 'http://localhost:8000'

const TIMEOUT_MS = 2500

async function fetchWithTimeout(url, options = {}) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), options.timeout || TIMEOUT_MS)
  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...(options.headers || {}),
      },
    })
    clearTimeout(timeoutId)
    return res
  } catch (err) {
    clearTimeout(timeoutId)
    throw err
  }
}

export async function checkBackendHealth() {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/health`, {
      method: 'GET',
      next: { revalidate: 10 },
    })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

export async function fetchCoordinationStatus() {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/coordination/status`, {
      method: 'GET',
      next: { revalidate: 10 },
    })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

export async function fetchBackendSatellites(page = 1, pageSize = 50) {
  try {
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/satellites?page=${page}&page_size=${pageSize}`,
      { method: 'GET', next: { revalidate: 10 } },
    )
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

export async function fetchBackendConjunctions() {
  try {
    // 1. Try unified conjunctions endpoint (Member 1 screened + Member 2 risk scored)
    const coordRes = await fetchWithTimeout(`${API_BASE_URL}/coordination/conjunctions?limit=40`, {
      method: 'GET',
      next: { revalidate: 10 },
    })
    if (coordRes.ok) {
      return await coordRes.json()
    }

    // 2. Try orbital enriched-conjunctions endpoint directly
    const enrichedRes = await fetchWithTimeout(`${API_BASE_URL}/orbital/enriched-conjunctions?limit=40`, {
      method: 'GET',
      next: { revalidate: 10 },
    })
    if (enrichedRes.ok) {
      return await enrichedRes.json()
    }

    // 3. Try legacy scenario-conjunctions endpoint
    const scenarioRes = await fetchWithTimeout(`${API_BASE_URL}/coordination/scenario-conjunctions`, {
      method: 'GET',
      next: { revalidate: 10 },
    })
    if (scenarioRes.ok) {
      return await scenarioRes.json()
    }

    // 4. Fallback to standard Supabase conjunction-events table
    const res = await fetchWithTimeout(`${API_BASE_URL}/conjunction-events?page=1&page_size=50`, {
      method: 'GET',
      next: { revalidate: 10 },
    })
    if (!res.ok) return null
    const data = await res.json()
    return data.items || []
  } catch {
    return null
  }
}

export async function fetchOrbitalMetadata() {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/orbital/metadata`, {
      method: 'GET',
      next: { revalidate: 10 },
    })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

export async function fetchOrbitalSatellites(limit = 200, offset = 0) {
  try {
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/orbital/satellites?limit=${limit}&offset=${offset}`,
      { method: 'GET', next: { revalidate: 10 } },
    )
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

export async function fetchOrbitalTrajectories(step = 15, limit = 20) {
  try {
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/orbital/trajectories?step=${step}&limit=${limit}`,
      { method: 'GET', next: { revalidate: 10 } },
    )
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

export async function fetchOrbitalConjunctions() {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/orbital/conjunctions`, {
      method: 'GET',
      next: { revalidate: 10 },
    })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

export async function fetchOrbitalUncertainty() {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/orbital/uncertainty`, {
      method: 'GET',
      next: { revalidate: 10 },
    })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

export { API_BASE_URL }
