import type { SourceName } from './types'

export interface UrlState {
  source: SourceName
  seed: string | null
}

/** The graph on screen is kept in the address bar, so a view can be reloaded or shared. */
export function readUrl(search: string = window.location.search): UrlState {
  const params = new URLSearchParams(search)
  const source = params.get('source') === 'openalex' ? 'openalex' : 'demo'
  const seed = params.get('seed')?.trim() || null
  return { source, seed }
}

export function writeUrl(source: SourceName, seed: string): void {
  const params = new URLSearchParams({ source, seed })
  window.history.replaceState(null, '', `${window.location.pathname}?${params}`)
}
