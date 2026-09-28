import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from './App'
import { job, mockFetch, view } from './test/fixtures'

// Cytoscape needs a real canvas, so the graph itself is replaced by a list of nodes.
vi.mock('./components/GraphCanvas', () => ({
  default: (props: { nodes: { id: string }[]; onSelect: (id: string) => void }) => (
    <ul data-testid="graph">
      {props.nodes.map((n) => (
        <li key={n.id}>
          <button type="button" onClick={() => props.onSelect(n.id)}>
            node {n.id}
          </button>
        </li>
      ))}
    </ul>
  ),
}))

beforeEach(() => {
  window.history.replaceState(null, '', '/')
})

afterEach(() => {
  vi.unstubAllGlobals()
})

function api(overrides: Record<string, { status?: number; body: unknown }> = {}) {
  return mockFetch((url, init) => {
    const key = `${init?.method ?? 'GET'} ${url.split('?')[0]}`
    if (overrides[key]) return overrides[key]
    if (key === 'GET /api/sources') {
      return { body: [{ name: 'demo', label: 'Demo', example: 'D002' }] }
    }
    if (key === 'POST /api/graphs') return { status: 202, body: job() }
    if (key === 'GET /api/graphs/demo/D002') return { body: view() }
    return { status: 404, body: { detail: `unexpected ${key}` } }
  })
}

it('opens the example graph, shows the ranking and paper details', async () => {
  const fetchMock = api()
  render(<App />)
  expect(screen.getByText('Start from one paper')).toBeInTheDocument()
  await userEvent.click(await screen.findByRole('button', { name: 'Open example D002' }))

  expect(await screen.findByTestId('summary')).toHaveTextContent('3 of 3 papers shown, 2 citations')
  expect(screen.getByText('synthetic demo data')).toBeInTheDocument()
  expect(window.location.search).toBe('?source=demo&seed=D002')
  expect(screen.getByRole('link', { name: 'Ranking CSV' })).toHaveAttribute(
    'href',
    '/api/graphs/demo/D002/export.csv?limit=150',
  )

  await userEvent.click(screen.getByRole('button', { name: 'node D003' }))
  expect(screen.getByRole('heading', { name: 'Embeddings of abstracts' })).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Close details' }))
  expect(screen.getByText('Most influential papers')).toBeInTheDocument()

  await userEvent.click(screen.getByRole('checkbox', { name: /embeddings/ }))
  await waitFor(() =>
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('clusters=0'))).toBe(true),
  )
})

it('loads the graph named in the address bar', async () => {
  window.history.replaceState(null, '', '/?source=demo&seed=D002')
  api()
  render(<App />)
  expect(await screen.findByTestId('summary')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'node D001' })).toBeInTheDocument()
})

it('explains failed jobs', async () => {
  api({ 'POST /api/graphs': { status: 202, body: job({ status: 'failed', error: 'Paper D002 is gone' }) } })
  render(<App />)
  await userEvent.click(await screen.findByRole('button', { name: 'Open example D002' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Paper D002 is gone')
})

it('explains rejected requests and falls back to built-in sources', async () => {
  api({
    'GET /api/sources': { status: 500, body: {} },
    'POST /api/graphs': { status: 400, body: { detail: 'Not a demo paper id' } },
  })
  render(<App />)
  await userEvent.click(await screen.findByRole('button', { name: 'Open example D042' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Not a demo paper id')
  expect(screen.getByRole('radio', { name: 'OpenAlex' })).toBeInTheDocument()
})
