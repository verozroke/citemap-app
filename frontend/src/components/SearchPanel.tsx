import { useState, type FormEvent } from 'react'
import { searchPapers } from '../api'
import type { SearchHit, SourceName } from '../types'

interface Props {
  source: SourceName
  example: string
  onPick: (id: string) => void
}

const HINTS: Record<SourceName, string> = {
  demo: 'Title, author or id (D042)',
  openalex: 'Title, DOI or OpenAlex id',
}

export default function SearchPanel({ source, example, onPick }: Props) {
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<SearchHit[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      setHits(await searchPapers(source, query.trim()))
    } catch (err) {
      setHits(null)
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="panel" aria-labelledby="search-title">
      <h2 id="search-title" className="panel__title">
        Find a seed paper
      </h2>
      <form className="search" onSubmit={submit} role="search">
        <input
          className="input"
          type="search"
          value={query}
          placeholder={HINTS[source]}
          aria-label="Search papers"
          onChange={(event) => setQuery(event.target.value)}
        />
        <button className="button button--primary" type="submit" disabled={loading}>
          {loading ? 'Searching' : 'Search'}
        </button>
      </form>
      {example && (
        <p className="muted small">
          Or try the example{' '}
          <button type="button" className="link-button" onClick={() => onPick(example)}>
            {example}
          </button>
        </p>
      )}
      {error && (
        <p className="alert alert--error" role="alert">
          {error}
        </p>
      )}
      {hits && hits.length === 0 && <p className="muted small">No papers found.</p>}
      {hits && hits.length > 0 && (
        <ul className="hits" aria-label="Search results">
          {hits.map((hit) => (
            <li key={hit.id}>
              <button type="button" className="hit" onClick={() => onPick(hit.id)}>
                <span className="hit__title">{hit.title}</span>
                <span className="hit__meta">
                  {hit.authors.slice(0, 2).join(', ')}
                  {hit.authors.length > 2 ? ' et al.' : ''}
                  {hit.year !== null ? ` (${hit.year})` : ''}, cited {hit.cited_by_count}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
