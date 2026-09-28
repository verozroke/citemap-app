import { describe, expect, it } from 'vitest'
import { buildElements, nodeSize, shortLabel, timelinePositions } from './graphElements'
import { clusterColor, CLUSTER_COLORS } from './palette'
import { node } from './test/fixtures'

describe('labels and sizes', () => {
  it('uses the first author surname and year', () => {
    expect(shortLabel(node())).toBe('Lovelace 2001')
    expect(shortLabel(node({ authors: [], year: null }))).toBe('D001')
  })

  it('scales node size with PageRank', () => {
    expect(nodeSize(0, 0.5)).toBe(16)
    expect(nodeSize(0.5, 0.5)).toBe(60)
    expect(nodeSize(0.125, 0.5)).toBe(38)
    expect(nodeSize(0.1, 0)).toBe(24)
  })

  it('cycles through the palette', () => {
    expect(clusterColor(0)).toBe(CLUSTER_COLORS[0])
    expect(clusterColor(CLUSTER_COLORS.length + 1)).toBe(CLUSTER_COLORS[1])
  })
})

describe('buildElements', () => {
  it('creates nodes and drops links to hidden papers', () => {
    const nodes = [node({ is_seed: true }), node({ id: 'D002', rank: 40 })]
    const elements = buildElements(nodes, [
      { source: 'D002', target: 'D001' },
      { source: 'D002', target: 'D999' },
    ])
    expect(elements.filter((e) => e.group === 'nodes')).toHaveLength(2)
    expect(elements.filter((e) => e.group === 'edges')).toEqual([
      { group: 'edges', data: { id: 'D002->D001', source: 'D002', target: 'D001' } },
    ])
    expect(elements[0].classes).toBe('seed labelled')
    expect(elements[1].classes).toBe('')
  })
})

describe('timelinePositions', () => {
  it('orders papers by year and separates clusters and duplicates', () => {
    const nodes = [
      node({ id: 'A', year: 2000, cluster: 0, rank: 1 }),
      node({ id: 'B', year: 2005, cluster: 0, rank: 2 }),
      node({ id: 'C', year: 2005, cluster: 0, rank: 3 }),
      node({ id: 'D', year: 2005, cluster: 1, rank: 4 }),
      node({ id: 'E', year: null, cluster: 1, rank: 5 }),
    ]
    const pos = timelinePositions(nodes, 10, 100)
    expect(pos.A.x).toBeLessThan(pos.B.x)
    expect(pos.B.x).toBe(pos.C.x)
    expect(pos.B.y).not.toBe(pos.C.y)
    expect(pos.D.y).toBeGreaterThan(pos.B.y)
    expect(pos.E.x).toBeLessThan(pos.A.x)
    const keys = Object.values(pos).map((p) => `${p.x},${p.y}`)
    expect(new Set(keys).size).toBe(keys.length)
  })
})
