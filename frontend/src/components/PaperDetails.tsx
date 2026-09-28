import { clusterColor } from '../palette'
import type { Cluster, GraphNode } from '../types'

interface Props {
  paper: GraphNode
  cluster: Cluster | undefined
  isCurrentSeed: boolean
  onExplore: (id: string) => void
  onClose: () => void
}

export default function PaperDetails({ paper, cluster, isCurrentSeed, onExplore, onClose }: Props) {
  return (
    <section className="panel details" aria-labelledby="details-title">
      <div className="panel__header">
        <span className="eyebrow">{paper.is_seed ? 'Seed paper' : `Rank #${paper.rank}`}</span>
        <button type="button" className="icon-button" aria-label="Close details" onClick={onClose}>
          ×
        </button>
      </div>
      <h2 id="details-title" className="details__title">
        {paper.title}
      </h2>
      <p className="details__authors">{paper.authors.join(', ') || 'Unknown authors'}</p>
      <p className="muted small">
        {[paper.venue, paper.year].filter((part) => part !== null && part !== '').join(', ')}
      </p>

      <dl className="stats">
        <div>
          <dt>Citations (global)</dt>
          <dd>{paper.cited_by_count.toLocaleString('en-US')}</dd>
        </div>
        <div>
          <dt>Cited in this network</dt>
          <dd>{paper.local_citations}</dd>
        </div>
        <div>
          <dt>References in network</dt>
          <dd>{paper.references_in_network}</dd>
        </div>
        <div>
          <dt>PageRank</dt>
          <dd>{paper.pagerank.toFixed(4)}</dd>
        </div>
      </dl>

      {cluster && (
        <p className="details__cluster">
          <span className="swatch" style={{ background: clusterColor(cluster.id) }} />
          Topic: {cluster.label}
        </p>
      )}

      {paper.abstract && (
        <>
          <h3 className="details__subtitle">Abstract</h3>
          <p className="details__abstract">{paper.abstract}</p>
        </>
      )}

      <div className="details__actions">
        {!isCurrentSeed && (
          <button type="button" className="button button--primary" onClick={() => onExplore(paper.id)}>
            Explore from this paper
          </button>
        )}
        {paper.url && (
          <a className="button" href={paper.url} target="_blank" rel="noreferrer">
            Open source page
          </a>
        )}
      </div>
      <p className="muted small">Id: {paper.id}</p>
    </section>
  )
}
