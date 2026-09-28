import { clusterColor } from '../palette'
import type { GraphNode } from '../types'

interface Props {
  nodes: GraphNode[]
  onSelect: (id: string) => void
  top?: number
}

export default function RankingTable({ nodes, onSelect, top = 15 }: Props) {
  const rows = [...nodes].sort((a, b) => a.rank - b.rank).slice(0, top)
  return (
    <section className="panel" aria-labelledby="ranking-title">
      <h2 id="ranking-title" className="panel__title">
        Most influential papers
      </h2>
      <p className="muted small">Ranked by PageRank within the network. Click a row for details.</p>
      <table className="ranking">
        <thead>
          <tr>
            <th scope="col">#</th>
            <th scope="col">Paper</th>
            <th scope="col" className="num" title="Citations from other papers in this network">
              Cited here
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((node) => (
            <tr key={node.id} className={node.is_seed ? 'is-seed' : ''}>
              <td className="num">{node.rank}</td>
              <td>
                <button type="button" className="ranking__paper" onClick={() => onSelect(node.id)}>
                  <span className="swatch" style={{ background: clusterColor(node.cluster) }} />
                  <span>
                    {node.title}
                    <span className="muted"> {node.year ?? ''}</span>
                  </span>
                </button>
              </td>
              <td className="num">{node.local_citations}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
