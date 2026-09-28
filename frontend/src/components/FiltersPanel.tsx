import { clusterColor } from '../palette'
import { DEFAULT_FILTERS, type Cluster, type Filters, type Summary } from '../types'

interface Props {
  filters: Filters
  clusters: Cluster[]
  summary: Summary
  onChange: (filters: Filters) => void
}

function parseYear(value: string): number | null {
  if (!value.trim()) return null
  const year = Number.parseInt(value, 10)
  return Number.isNaN(year) ? null : year
}

export default function FiltersPanel({ filters, clusters, summary, onChange }: Props) {
  const selected = new Set(filters.clusters ?? clusters.map((c) => c.id))

  function toggleCluster(id: number) {
    const next = new Set(selected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    const all = clusters.every((c) => next.has(c.id))
    onChange({ ...filters, clusters: all ? null : [...next].sort((a, b) => a - b) })
  }

  return (
    <section className="panel" aria-labelledby="filters-title">
      <div className="panel__header">
        <h2 id="filters-title" className="panel__title">
          Filters
        </h2>
        <button
          type="button"
          className="link-button small"
          onClick={() => onChange({ ...DEFAULT_FILTERS })}
        >
          Reset
        </button>
      </div>

      <div className="field-row">
        <label className="field">
          <span>From year</span>
          <input
            className="input"
            type="number"
            inputMode="numeric"
            placeholder={summary.year_min?.toString() ?? ''}
            value={filters.fromYear ?? ''}
            onChange={(e) => onChange({ ...filters, fromYear: parseYear(e.target.value) })}
          />
        </label>
        <label className="field">
          <span>To year</span>
          <input
            className="input"
            type="number"
            inputMode="numeric"
            placeholder={summary.year_max?.toString() ?? ''}
            value={filters.toYear ?? ''}
            onChange={(e) => onChange({ ...filters, toYear: parseYear(e.target.value) })}
          />
        </label>
      </div>

      <label className="field">
        <span>Minimum citations</span>
        <input
          className="input"
          type="number"
          min={0}
          value={filters.minCitations}
          onChange={(e) =>
            onChange({ ...filters, minCitations: Math.max(0, Number(e.target.value) || 0) })
          }
        />
      </label>

      <label className="field">
        <span>
          Show at most <strong>{filters.limit}</strong> papers
        </span>
        <input
          type="range"
          min={10}
          max={500}
          step={10}
          value={filters.limit}
          aria-label="Maximum number of papers"
          onChange={(e) => onChange({ ...filters, limit: Number(e.target.value) })}
        />
      </label>

      <fieldset className="clusters">
        <legend>Topic clusters</legend>
        {clusters.map((cluster) => (
          <label key={cluster.id} className="cluster">
            <input
              type="checkbox"
              checked={selected.has(cluster.id)}
              onChange={() => toggleCluster(cluster.id)}
            />
            <span className="swatch" style={{ background: clusterColor(cluster.id) }} />
            <span className="cluster__label">{cluster.label}</span>
            <span className="cluster__size">{cluster.size}</span>
          </label>
        ))}
      </fieldset>
    </section>
  )
}
