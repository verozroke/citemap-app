import type { ElementDefinition } from 'cytoscape'
import { clusterColor } from './palette'
import type { GraphLink, GraphNode } from './types'

/** How many of the highest ranked papers get a permanent label. */
export const LABELLED_TOP = 12

export function shortLabel(node: GraphNode): string {
  const first = node.authors[0]
  const surname = first ? first.split(' ').slice(-1)[0] : node.id
  return node.year === null ? surname : `${surname} ${node.year}`
}

/** Node diameter in pixels, from 16 (lowest PageRank) to 60 (highest). */
export function nodeSize(pagerank: number, maxPagerank: number): number {
  if (maxPagerank <= 0) return 24
  return Math.round(16 + 44 * Math.sqrt(Math.max(pagerank, 0) / maxPagerank))
}

export function buildElements(nodes: GraphNode[], links: GraphLink[]): ElementDefinition[] {
  const maxPr = Math.max(0, ...nodes.map((n) => n.pagerank))
  const ids = new Set(nodes.map((n) => n.id))
  const nodeElements: ElementDefinition[] = nodes.map((n) => ({
    group: 'nodes',
    data: {
      id: n.id,
      label: shortLabel(n),
      title: n.title,
      size: nodeSize(n.pagerank, maxPr),
      color: clusterColor(n.cluster),
      year: n.year,
      cluster: n.cluster,
    },
    classes: [n.is_seed ? 'seed' : '', n.is_seed || n.rank <= LABELLED_TOP ? 'labelled' : '']
      .filter(Boolean)
      .join(' '),
  }))
  const edgeElements: ElementDefinition[] = links
    .filter((l) => ids.has(l.source) && ids.has(l.target))
    .map((l) => ({
      group: 'edges',
      data: { id: `${l.source}->${l.target}`, source: l.source, target: l.target },
    }))
  return [...nodeElements, ...edgeElements]
}

export interface Point {
  x: number
  y: number
}

/**
 * Positions for the timeline view: publication year on the horizontal axis and
 * one horizontal band per topic cluster. Papers without a year go to the left.
 */
export function timelinePositions(
  nodes: GraphNode[],
  yearWidth = 45,
  bandHeight = 170,
): Record<string, Point> {
  const years = nodes.map((n) => n.year).filter((y): y is number => y !== null)
  const minYear = years.length ? Math.min(...years) : 0
  const clusters = [...new Set(nodes.map((n) => n.cluster))].sort((a, b) => a - b)
  const band = new Map(clusters.map((c, i) => [c, i]))
  const perCell = new Map<string, number>()
  const positions: Record<string, Point> = {}
  const ordered = [...nodes].sort((a, b) => a.rank - b.rank)
  for (const node of ordered) {
    const column = node.year === null ? -2 : node.year - minYear
    const row = band.get(node.cluster) ?? 0
    const key = `${column}:${row}`
    const slot = perCell.get(key) ?? 0
    perCell.set(key, slot + 1)
    // Alternate above and below the band centre so papers in the same year do not overlap.
    const offset = slot === 0 ? 0 : Math.ceil(slot / 2) * 30 * (slot % 2 === 0 ? 1 : -1)
    positions[node.id] = { x: column * yearWidth, y: row * bandHeight + offset }
  }
  return positions
}
