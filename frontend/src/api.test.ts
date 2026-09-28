import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, exportUrl, filterParams, getGraph, searchPapers, startGraph, waitForJob } from './api'
import { job, mockFetch, view } from './test/fixtures'
import { DEFAULT_FILTERS } from './types'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('filterParams', () => {
  it('sends only the limit for default filters', () => {
    expect(filterParams(DEFAULT_FILTERS).toString()).toBe('limit=150')
  })

  it('encodes every active filter', () => {
    const params = filterParams({
      fromYear: 2000,
      toYear: 2010,
      minCitations: 5,
      clusters: [0, 2],
      limit: 50,
    })
    expect(Object.fromEntries(params)).toEqual({
      limit: '50',
      from_year: '2000',
      to_year: '2010',
      min_citations: '5',
      clusters: '0,2',
    })
  })
})

describe('requests', () => {
  it('searches with source, query and limit', async () => {
    const fetchMock = mockFetch(() => ({ body: [] }))
    await searchPapers('openalex', 'graph layout', 5)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/search?source=openalex&q=graph+layout&limit=5')
  })

  it('posts graph jobs as JSON', async () => {
    const fetchMock = mockFetch(() => ({ status: 202, body: job() }))
    await startGraph('demo', 'D002', true)
    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({ source: 'demo', seed_id: 'D002', refresh: true })
  })

  it('loads a filtered view', async () => {
    const fetchMock = mockFetch(() => ({ body: view() }))
    const result = await getGraph('demo', 'D002', { ...DEFAULT_FILTERS, minCitations: 3 })
    expect(result.seed_id).toBe('D002')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/graphs/demo/D002?limit=150&min_citations=3')
  })

  it('turns the API detail into an ApiError', async () => {
    mockFetch(() => ({ status: 400, body: { detail: 'Not a demo paper id' } }))
    await expect(startGraph('demo', 'X')).rejects.toEqual(new ApiError(400, 'Not a demo paper id'))
  })

  it('reports validation errors and unreadable bodies', async () => {
    mockFetch(() => ({ status: 422, body: { detail: [{ msg: 'bad' }] } }))
    await expect(searchPapers('demo', 'x')).rejects.toThrow('[{"msg":"bad"}]')
    vi.stubGlobal('fetch', vi.fn(async () => new Response('oops', { status: 500 })))
    await expect(searchPapers('demo', 'x')).rejects.toThrow('HTTP 500')
  })

  it('explains when the server cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('network'))))
    await expect(searchPapers('demo', 'x')).rejects.toThrow('Cannot reach the CiteMap server')
  })
})

describe('waitForJob', () => {
  it('polls until the job finishes and reports each state', async () => {
    const states = ['running', 'done']
    mockFetch(() => ({ body: job({ status: states.shift() as 'running' | 'done' }) }))
    const seen: string[] = []
    const result = await waitForJob(job({ status: 'queued' }), (j) => seen.push(j.status), 1)
    expect(result.status).toBe('done')
    expect(seen).toEqual(['queued', 'running', 'done'])
  })

  it('returns finished jobs without polling', async () => {
    const fetchMock = mockFetch(() => ({ body: job() }))
    await waitForJob(job({ status: 'failed', error: 'boom' }))
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('gives up after the timeout', async () => {
    mockFetch(() => ({ body: job({ status: 'running' }) }))
    await expect(waitForJob(job({ status: 'running' }), undefined, 1, 5)).rejects.toThrow(
      'took too long',
    )
  })

  it('stops when aborted', async () => {
    const controller = new AbortController()
    controller.abort()
    await expect(
      waitForJob(job({ status: 'queued' }), undefined, 1, 1000, controller.signal),
    ).rejects.toThrow('Aborted')
  })
})

it('builds export links with the current filters', () => {
  expect(exportUrl('openalex', 'W1', 'csv', { ...DEFAULT_FILTERS, clusters: [1] })).toBe(
    '/api/graphs/openalex/W1/export.csv?limit=150&clusters=1',
  )
})
