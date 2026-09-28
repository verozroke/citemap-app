import { useEffect, useMemo, useRef, useState } from 'react'
import { exportUrl, getSources } from './api'
import ExportPanel from './components/ExportPanel'
import FiltersPanel from './components/FiltersPanel'
import GraphCanvas, { type GraphCanvasHandle, type LayoutMode } from './components/GraphCanvas'
import PaperDetails from './components/PaperDetails'
import RankingTable from './components/RankingTable'
import SearchPanel from './components/SearchPanel'
import SourceToggle from './components/SourceToggle'
import type { SourceInfo, SourceName } from './types'
import { readUrl, writeUrl } from './url'
import { useGraph } from './useGraph'

const FALLBACK_SOURCES: SourceInfo[] = [
  { name: 'demo', label: 'Demo dataset (synthetic, offline)', example: 'D042' },
  { name: 'openalex', label: 'OpenAlex (live, needs internet)', example: 'W2741809807' },
]

const STATUS_TEXT = {
  queued: 'Waiting for a worker',
  running: 'Fetching papers and building the graph',
  done: 'Loading the graph',
  failed: 'Failed',
} as const

export default function App() {
  const initial = useMemo(() => readUrl(), [])
  const [sources, setSources] = useState<SourceInfo[]>(FALLBACK_SOURCES)
  const [source, setSource] = useState<SourceName>(initial.source)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [layout, setLayout] = useState<LayoutMode>('force')
  const canvas = useRef<GraphCanvasHandle>(null)
  const { active, filters, setFilters, view, job, phase, error, open } = useGraph()

  useEffect(() => {
    getSources()
      .then(setSources)
      .catch(() => setSources(FALLBACK_SOURCES))
  }, [])

  useEffect(() => {
    if (initial.seed) void open(initial.source, initial.seed)
  }, [initial, open])

  useEffect(() => {
    if (active) writeUrl(active.source, active.seedId)
  }, [active])

  const explore = (id: string, from: SourceName = source) => {
    setSelectedId(null)
    void open(from, id)
  }

  const selected = view?.nodes.find((n) => n.id === selectedId) ?? null
  const example = sources.find((s) => s.name === source)?.example ?? ''
  const busy = phase === 'building' || phase === 'loading'

  function downloadPng() {
    const data = canvas.current?.exportPng()
    if (!data || !active) return
    const link = document.createElement('a')
    link.href = data
    link.download = `citemap-${active.seedId}.png`
    link.click()
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <img src="/favicon.svg" alt="" width={28} height={28} />
          <div>
            <h1>CiteMap</h1>
            <p>Interactive citation network explorer</p>
          </div>
        </div>
        <SourceToggle sources={sources} value={source} onChange={setSource} />
      </header>

      <main className="layout">
        <aside className="sidebar">
          <SearchPanel key={source} source={source} example={example} onPick={(id) => explore(id)} />
          {view && (
            <>
              <FiltersPanel
                filters={filters}
                clusters={view.clusters}
                summary={view.summary}
                onChange={setFilters}
              />
              <ExportPanel
                csvUrl={exportUrl(view.source, view.seed_id, 'csv', filters)}
                jsonUrl={exportUrl(view.source, view.seed_id, 'json', filters)}
                onPng={downloadPng}
              />
            </>
          )}
        </aside>

        <section className="stage" aria-label="Citation graph">
          {view && (
            <div className="stage__toolbar">
              <div className="summary" data-testid="summary">
                <strong>{view.shown_nodes}</strong> of {view.total_nodes} papers shown,{' '}
                <strong>{view.links.length}</strong> citations
                {view.source === 'demo' && <span className="badge">synthetic demo data</span>}
              </div>
              <div className="toolbar-actions">
                <div className="segmented segmented--small" role="radiogroup" aria-label="Layout">
                  {(['force', 'timeline'] as const).map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      role="radio"
                      aria-checked={layout === mode}
                      className={layout === mode ? 'segmented__item is-active' : 'segmented__item'}
                      onClick={() => setLayout(mode)}
                    >
                      {mode === 'force' ? 'Network' : 'Timeline'}
                    </button>
                  ))}
                </div>
                <button type="button" className="button button--small" onClick={() => canvas.current?.fit()}>
                  Fit
                </button>
                {view.source === 'openalex' && (
                  <button
                    type="button"
                    className="button button--small"
                    disabled={busy}
                    onClick={() => void open(view.source, view.seed_id, true)}
                  >
                    Refresh data
                  </button>
                )}
              </div>
            </div>
          )}

          <div className="stage__canvas">
            <GraphCanvas
              ref={canvas}
              nodes={view?.nodes ?? []}
              links={view?.links ?? []}
              selectedId={selectedId}
              onSelect={setSelectedId}
              layout={layout}
            />
            {layout === 'timeline' && view && (
              <div className="axis-hint">Older papers on the left, newer on the right. One row per topic.</div>
            )}
            {!view && phase === 'idle' && (
              <div className="overlay">
                <div className="empty">
                  <h2>Start from one paper</h2>
                  <p>
                    Search for a paper on the left. CiteMap collects the papers it cites and the
                    papers citing it, ranks them with PageRank and groups them into topics.
                  </p>
                  <button type="button" className="button button--primary" onClick={() => explore(example)}>
                    Open example {example}
                  </button>
                </div>
              </div>
            )}
            {busy && (
              <div className="overlay overlay--soft" role="status">
                <div className="spinner" aria-hidden="true" />
                <p>{phase === 'building' ? STATUS_TEXT[job?.status ?? 'queued'] : 'Loading the graph'}</p>
              </div>
            )}
            {phase === 'error' && error && (
              <div className="overlay overlay--soft">
                <div className="alert alert--error" role="alert">
                  <strong>Could not build the graph.</strong> {error}
                </div>
              </div>
            )}
          </div>
        </section>

        <aside className="inspector">
          {selected && view ? (
            <PaperDetails
              paper={selected}
              cluster={view.clusters.find((c) => c.id === selected.cluster)}
              isCurrentSeed={selected.id === view.seed_id}
              onExplore={(id) => explore(id, view.source)}
              onClose={() => setSelectedId(null)}
            />
          ) : view ? (
            <RankingTable nodes={view.nodes} onSelect={setSelectedId} />
          ) : (
            <section className="panel">
              <h2 className="panel__title">How to read the graph</h2>
              <ul className="legend-list">
                <li>Each circle is a paper; an arrow points from a citing paper to the cited one.</li>
                <li>Bigger circles have higher PageRank, i.e. more influence in this network.</li>
                <li>Colours are topic clusters found from titles and abstracts.</li>
                <li>The seed paper has a dark outline.</li>
              </ul>
            </section>
          )}
        </aside>
      </main>
    </div>
  )
}
