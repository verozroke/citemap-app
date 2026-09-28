import { useCallback, useEffect, useRef, useState } from 'react'
import { getGraph, startGraph, waitForJob } from './api'
import { DEFAULT_FILTERS, type Filters, type GraphView, type Job, type SourceName } from './types'

export type Phase = 'idle' | 'building' | 'loading' | 'ready' | 'error'

export interface ActiveGraph {
  source: SourceName
  seedId: string
}

/**
 * Lifecycle of the graph on screen: start a job, poll it, then load the view
 * and reload it (debounced) whenever the filters change.
 */
export function useGraph(filterDelayMs = 250) {
  const [active, setActive] = useState<ActiveGraph | null>(null)
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS)
  const [view, setView] = useState<GraphView | null>(null)
  const [job, setJob] = useState<Job | null>(null)
  const [phase, setPhase] = useState<Phase>('idle')
  const [error, setError] = useState<string | null>(null)
  const buildToken = useRef(0)

  const open = useCallback(async (source: SourceName, seedId: string, refresh = false) => {
    const token = ++buildToken.current
    setPhase('building')
    setError(null)
    setJob(null)
    try {
      const started = await startGraph(source, seedId, refresh)
      const finished = await waitForJob(started, (update) => {
        if (token === buildToken.current) setJob(update)
      })
      if (token !== buildToken.current) return
      if (finished.status === 'failed') {
        setPhase('error')
        setError(finished.error ?? 'Building the graph failed.')
        return
      }
      setFilters(DEFAULT_FILTERS)
      setActive({ source, seedId: finished.seed_id })
      setPhase('loading')
    } catch (err) {
      if (token !== buildToken.current) return
      setPhase('error')
      setError(err instanceof Error ? err.message : String(err))
    }
  }, [])

  useEffect(() => {
    if (!active) return
    let cancelled = false
    const timer = setTimeout(async () => {
      try {
        const next = await getGraph(active.source, active.seedId, filters)
        if (cancelled) return
        setView(next)
        setPhase('ready')
      } catch (err) {
        if (cancelled) return
        setPhase('error')
        setError(err instanceof Error ? err.message : String(err))
      }
    }, filterDelayMs)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [active, filters, filterDelayMs])

  return { active, filters, setFilters, view, job, phase, error, open }
}
