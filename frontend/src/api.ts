import type { Filters, GraphView, Job, SearchHit, SourceInfo, SourceName } from './types'

/** Error with the message the API put in its `detail` field. */
export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, init)
  } catch {
    throw new ApiError(0, 'Cannot reach the CiteMap server. Is the backend running?')
  }
  if (!response.ok) {
    let message = `Request failed with HTTP ${response.status}`
    try {
      const body: unknown = await response.json()
      if (body && typeof body === 'object' && 'detail' in body) {
        const detail = (body as { detail: unknown }).detail
        message = typeof detail === 'string' ? detail : JSON.stringify(detail)
      }
    } catch {
      // keep the generic message
    }
    throw new ApiError(response.status, message)
  }
  return (await response.json()) as T
}

export function getSources(): Promise<SourceInfo[]> {
  return request('/api/sources')
}

export function searchPapers(source: SourceName, q: string, limit = 10): Promise<SearchHit[]> {
  const params = new URLSearchParams({ source, q, limit: String(limit) })
  return request(`/api/search?${params}`)
}

export function startGraph(source: SourceName, seedId: string, refresh = false): Promise<Job> {
  return request('/api/graphs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source, seed_id: seedId, refresh }),
  })
}

export function getJob(id: string): Promise<Job> {
  return request(`/api/jobs/${encodeURIComponent(id)}`)
}

export function filterParams(filters: Filters): URLSearchParams {
  const params = new URLSearchParams({ limit: String(filters.limit) })
  if (filters.fromYear !== null) params.set('from_year', String(filters.fromYear))
  if (filters.toYear !== null) params.set('to_year', String(filters.toYear))
  if (filters.minCitations > 0) params.set('min_citations', String(filters.minCitations))
  if (filters.clusters !== null) params.set('clusters', filters.clusters.join(','))
  return params
}

function graphPath(source: SourceName, seedId: string): string {
  return `/api/graphs/${encodeURIComponent(source)}/${encodeURIComponent(seedId)}`
}

export function getGraph(source: SourceName, seedId: string, filters: Filters): Promise<GraphView> {
  return request(`${graphPath(source, seedId)}?${filterParams(filters)}`)
}

export function exportUrl(
  source: SourceName,
  seedId: string,
  format: 'csv' | 'json',
  filters: Filters,
): string {
  return `${graphPath(source, seedId)}/export.${format}?${filterParams(filters)}`
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

/**
 * Poll a job until it is done or failed.
 *
 * The backend builds graphs in the background (live OpenAlex requests take a
 * few seconds), so the client asks for the status at a fixed interval.
 */
export async function waitForJob(
  job: Job,
  onUpdate: (job: Job) => void = () => {},
  intervalMs = 600,
  timeoutMs = 120_000,
  signal?: AbortSignal,
): Promise<Job> {
  const started = Date.now()
  let current = job
  onUpdate(current)
  while (current.status === 'queued' || current.status === 'running') {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
    if (Date.now() - started > timeoutMs) {
      throw new ApiError(0, 'Building the graph took too long. Please try again.')
    }
    await sleep(intervalMs)
    current = await getJob(current.id)
    onUpdate(current)
  }
  return current
}
