import { vi } from 'vitest'
import type { GraphNode, GraphView, Job } from '../types'

export function node(overrides: Partial<GraphNode> = {}): GraphNode {
  return {
    id: 'D001',
    title: 'Graph layouts for citation maps',
    year: 2001,
    authors: ['Ada Lovelace', 'Alan Turing'],
    cited_by_count: 120,
    local_citations: 4,
    references_in_network: 2,
    pagerank: 0.2,
    rank: 1,
    cluster: 0,
    is_seed: false,
    abstract: 'We draw citation networks.',
    doi: null,
    url: 'https://example.org/D001',
    venue: 'Journal of Tests',
    ...overrides,
  }
}

export function view(overrides: Partial<GraphView> = {}): GraphView {
  const nodes = [
    node({ id: 'D002', title: 'Seed paper about maps', rank: 2, is_seed: true, pagerank: 0.1 }),
    node(),
    node({ id: 'D003', title: 'Embeddings of abstracts', rank: 3, cluster: 1, pagerank: 0.05 }),
  ]
  return {
    source: 'demo',
    seed_id: 'D002',
    provenance: { synthetic: true },
    fetched_at: '2026-01-01T00:00:00+00:00',
    nodes,
    links: [
      { source: 'D002', target: 'D001' },
      { source: 'D003', target: 'D001' },
    ],
    clusters: [
      { id: 0, label: 'maps, layout', size: 2 },
      { id: 1, label: 'embeddings', size: 1 },
    ],
    summary: {
      papers: 3,
      citations: 2,
      density: 0.33,
      components: 1,
      isolated_papers: 0,
      year_min: 1999,
      year_max: 2020,
    },
    total_nodes: 3,
    matching_nodes: 3,
    shown_nodes: 3,
    ...overrides,
  }
}

export function job(overrides: Partial<Job> = {}): Job {
  return {
    id: 'job1',
    source: 'demo',
    seed_id: 'D002',
    status: 'done',
    error: null,
    cached: false,
    created_at: '2026-01-01T00:00:00+00:00',
    updated_at: '2026-01-01T00:00:00+00:00',
    ...overrides,
  }
}

type Handler = (url: string, init?: RequestInit) => { status?: number; body: unknown }

/** Replace `fetch` with a router; returns the mock so tests can inspect calls. */
export function mockFetch(handler: Handler) {
  const mock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const { status = 200, body } = handler(String(input), init)
    return new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    })
  })
  vi.stubGlobal('fetch', mock)
  return mock
}
