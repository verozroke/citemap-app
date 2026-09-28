import type { SourceInfo, SourceName } from '../types'

interface Props {
  sources: SourceInfo[]
  value: SourceName
  onChange: (source: SourceName) => void
}

const SHORT: Record<string, string> = { demo: 'Demo data', openalex: 'OpenAlex' }

export default function SourceToggle({ sources, value, onChange }: Props) {
  return (
    <div className="segmented" role="radiogroup" aria-label="Data source">
      {sources.map((source) => (
        <button
          key={source.name}
          type="button"
          role="radio"
          aria-checked={value === source.name}
          title={source.label}
          className={value === source.name ? 'segmented__item is-active' : 'segmented__item'}
          onClick={() => onChange(source.name)}
        >
          {SHORT[source.name] ?? source.name}
        </button>
      ))}
    </div>
  )
}
