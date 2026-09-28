import cytoscape, { type Core, type EventObject, type LayoutOptions } from 'cytoscape'
import fcose from 'cytoscape-fcose'
import { useEffect, useImperativeHandle, useRef, useState, type Ref } from 'react'
import { buildElements, timelinePositions } from '../graphElements'
import { SEED_COLOR } from '../palette'
import type { GraphLink, GraphNode } from '../types'

cytoscape.use(fcose)

export type LayoutMode = 'force' | 'timeline'

export interface GraphCanvasHandle {
  /** PNG of the whole graph as a data URL. */
  exportPng: () => string | null
  fit: () => void
}

interface Props {
  nodes: GraphNode[]
  links: GraphLink[]
  selectedId: string | null
  onSelect: (id: string | null) => void
  layout: LayoutMode
  ref?: Ref<GraphCanvasHandle>
}

interface Hover {
  x: number
  y: number
  text: string
}

const STYLE: cytoscape.StylesheetJson = [
  {
    selector: 'node',
    style: {
      width: 'data(size)',
      height: 'data(size)',
      'background-color': 'data(color)',
      'border-width': 1.5,
      'border-color': '#ffffff',
      label: '',
      'font-size': 11,
      'font-family': 'Inter, system-ui, sans-serif',
      color: '#1f2937',
      'text-valign': 'bottom',
      'text-margin-y': 4,
      'text-outline-color': '#ffffff',
      'text-outline-width': 2,
      'transition-property': 'opacity',
      'transition-duration': 150,
    },
  },
  { selector: 'node.labelled', style: { label: 'data(label)' } },
  {
    selector: 'node.seed',
    style: { 'border-width': 5, 'border-color': SEED_COLOR, 'font-weight': 'bold' },
  },
  {
    selector: 'node:selected, node.selected',
    style: { 'border-width': 5, 'border-color': '#f2b134', label: 'data(label)', 'z-index': 10 },
  },
  {
    selector: 'edge',
    style: {
      width: 1,
      'line-color': '#b8c1cc',
      'target-arrow-color': '#b8c1cc',
      'target-arrow-shape': 'triangle',
      'arrow-scale': 0.7,
      'curve-style': 'straight',
      opacity: 0.65,
    },
  },
  { selector: 'edge.highlighted', style: { 'line-color': '#4b5563', 'target-arrow-color': '#4b5563', opacity: 1, width: 1.6 } },
  { selector: '.faded', style: { opacity: 0.12 } },
]

function layoutOptions(mode: LayoutMode, nodes: GraphNode[]): LayoutOptions {
  if (mode === 'timeline') {
    const positions = timelinePositions(nodes)
    return {
      name: 'preset',
      positions: (node: cytoscape.NodeSingular) => positions[node.id()],
      fit: true,
      padding: 40,
    } as LayoutOptions
  }
  return {
    name: 'fcose',
    quality: 'default',
    randomize: true,
    animate: false,
    nodeRepulsion: 9000,
    idealEdgeLength: 80,
    nodeSeparation: 90,
    fit: true,
    padding: 40,
  } as LayoutOptions
}

export default function GraphCanvas({ nodes, links, selectedId, onSelect, layout, ref }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)
  const onSelectRef = useRef(onSelect)
  const [hover, setHover] = useState<Hover | null>(null)

  useEffect(() => {
    onSelectRef.current = onSelect
  }, [onSelect])

  useEffect(() => {
    const cy = cytoscape({
      container: container.current,
      style: STYLE,
      minZoom: 0.1,
      maxZoom: 4,
      boxSelectionEnabled: false,
    })
    cy.on('tap', 'node', (event: EventObject) => onSelectRef.current(event.target.id()))
    cy.on('tap', (event: EventObject) => {
      if (event.target === cy) onSelectRef.current(null)
    })
    cy.on('mouseover', 'node', (event: EventObject) => {
      const position = event.target.renderedPosition()
      setHover({ x: position.x, y: position.y, text: event.target.data('title') })
    })
    cy.on('mouseout', 'node', () => setHover(null))
    cy.on('viewport', () => setHover(null))
    cyRef.current = cy
    return () => {
      cy.destroy()
      cyRef.current = null
    }
  }, [])

  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return
    cy.batch(() => {
      cy.elements().remove()
      cy.add(buildElements(nodes, links))
    })
    if (nodes.length) cy.layout(layoutOptions(layout, nodes)).run()
  }, [nodes, links, layout])

  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return
    cy.batch(() => {
      cy.elements().removeClass('faded highlighted selected')
      if (!selectedId) return
      const node = cy.getElementById(selectedId)
      if (node.empty()) return
      const neighbourhood = node.closedNeighborhood()
      cy.elements().not(neighbourhood).addClass('faded')
      neighbourhood.edges().addClass('highlighted')
      node.addClass('selected')
    })
  }, [selectedId, nodes, links, layout])

  useImperativeHandle(ref, () => ({
    exportPng: () => cyRef.current?.png({ full: true, scale: 2, bg: '#ffffff' }) ?? null,
    fit: () => {
      cyRef.current?.fit(undefined, 40)
    },
  }))

  return (
    <div className="graph-canvas">
      <div ref={container} className="graph-canvas__surface" data-testid="graph-surface" />
      {hover && (
        <div className="graph-canvas__tooltip" style={{ left: hover.x + 14, top: hover.y + 14 }}>
          {hover.text}
        </div>
      )}
    </div>
  )
}
