// Shapes returned by the CiteMap API (see backend/src/citemap_api/schemas.py).

export type SourceName = 'demo' | 'openalex'

export interface SourceInfo {
  name: SourceName
  label: string
  example: string
}

export interface SearchHit {
  id: string
  title: string
  year: number | null
  authors: string[]
  cited_by_count: number
}

export type JobStatus = 'queued' | 'running' | 'done' | 'failed'

export interface Job {
  id: string
  source: SourceName
  seed_id: string
  status: JobStatus
  error: string | null
  cached: boolean
  created_at: string
  updated_at: string
}

export interface GraphNode {
  id: string
  title: string
  year: number | null
  authors: string[]
  cited_by_count: number
  local_citations: number
  references_in_network: number
  pagerank: number
  rank: number
  cluster: number
  is_seed: boolean
  abstract: string | null
  doi: string | null
  url: string | null
  venue: string | null
}

export interface GraphLink {
  source: string
  target: string
}

export interface Cluster {
  id: number
  label: string
  size: number
}

export interface Summary {
  papers: number
  citations: number
  density: number
  components: number
  isolated_papers: number
  year_min: number | null
  year_max: number | null
}

export interface GraphView {
  source: SourceName
  seed_id: string
  provenance: Record<string, unknown>
  fetched_at: string
  nodes: GraphNode[]
  links: GraphLink[]
  clusters: Cluster[]
  summary: Summary
  total_nodes: number
  matching_nodes: number
  shown_nodes: number
}

export interface Filters {
  fromYear: number | null
  toYear: number | null
  minCitations: number
  /** Cluster ids to show; null means all clusters. */
  clusters: number[] | null
  limit: number
}

export const DEFAULT_FILTERS: Filters = {
  fromYear: null,
  toYear: null,
  minCitations: 0,
  clusters: null,
  limit: 150,
}
