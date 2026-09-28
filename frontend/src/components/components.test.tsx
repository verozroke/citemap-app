import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockFetch, node, view } from '../test/fixtures'
import { DEFAULT_FILTERS } from '../types'
import FiltersPanel from './FiltersPanel'
import PaperDetails from './PaperDetails'
import RankingTable from './RankingTable'
import SearchPanel from './SearchPanel'
import SourceToggle from './SourceToggle'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('SearchPanel', () => {
  it('searches and lets the user pick a result', async () => {
    mockFetch(() => ({
      body: [{ id: 'D007', title: 'Graph layout', year: 2003, authors: ['A B', 'C D', 'E F'], cited_by_count: 9 }],
    }))
    const onPick = vi.fn()
    render(<SearchPanel source="demo" example="D042" onPick={onPick} />)
    await userEvent.type(screen.getByLabelText('Search papers'), 'layout{Enter}')
    const result = await screen.findByRole('button', { name: /Graph layout/ })
    expect(result).toHaveTextContent('A B, C D et al. (2003), cited 9')
    await userEvent.click(result)
    expect(onPick).toHaveBeenCalledWith('D007')
  })

  it('offers the example and ignores empty queries', async () => {
    const fetchMock = mockFetch(() => ({ body: [] }))
    const onPick = vi.fn()
    render(<SearchPanel source="demo" example="D042" onPick={onPick} />)
    await userEvent.click(screen.getByRole('button', { name: 'Search' }))
    expect(fetchMock).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: 'D042' }))
    expect(onPick).toHaveBeenCalledWith('D042')
  })

  it('shows empty results and errors', async () => {
    let fail = false
    mockFetch(() => (fail ? { status: 502, body: { detail: 'OpenAlex is down' } } : { body: [] }))
    render(<SearchPanel source="openalex" example="" onPick={() => {}} />)
    await userEvent.type(screen.getByLabelText('Search papers'), 'x{Enter}')
    expect(await screen.findByText('No papers found.')).toBeInTheDocument()
    fail = true
    await userEvent.click(screen.getByRole('button', { name: 'Search' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('OpenAlex is down')
  })
})

describe('FiltersPanel', () => {
  const { clusters, summary } = view()

  it('turns cluster checkboxes into a cluster filter', async () => {
    const onChange = vi.fn()
    const { rerender } = render(
      <FiltersPanel filters={DEFAULT_FILTERS} clusters={clusters} summary={summary} onChange={onChange} />,
    )
    await userEvent.click(screen.getByRole('checkbox', { name: /embeddings/ }))
    expect(onChange).toHaveBeenLastCalledWith({ ...DEFAULT_FILTERS, clusters: [0] })

    rerender(
      <FiltersPanel filters={{ ...DEFAULT_FILTERS, clusters: [0] }} clusters={clusters} summary={summary} onChange={onChange} />,
    )
    await userEvent.click(screen.getByRole('checkbox', { name: /embeddings/ }))
    expect(onChange).toHaveBeenLastCalledWith({ ...DEFAULT_FILTERS, clusters: null })
  })

  it('edits years, citations and resets', async () => {
    const onChange = vi.fn()
    render(<FiltersPanel filters={{ ...DEFAULT_FILTERS, limit: 60 }} clusters={clusters} summary={summary} onChange={onChange} />)
    expect(screen.getByPlaceholderText('1999')).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText('From year'), '7')
    expect(onChange).toHaveBeenLastCalledWith({ ...DEFAULT_FILTERS, limit: 60, fromYear: 7 })
    await userEvent.type(screen.getByLabelText('To year'), '9')
    expect(onChange).toHaveBeenLastCalledWith({ ...DEFAULT_FILTERS, limit: 60, toYear: 9 })
    await userEvent.type(screen.getByLabelText('Minimum citations'), '3')
    expect(onChange).toHaveBeenLastCalledWith({ ...DEFAULT_FILTERS, limit: 60, minCitations: 3 })
    await userEvent.click(screen.getByRole('button', { name: 'Reset' }))
    expect(onChange).toHaveBeenLastCalledWith(DEFAULT_FILTERS)
  })
})

describe('PaperDetails', () => {
  it('shows metrics and offers to explore from a non-seed paper', async () => {
    const onExplore = vi.fn()
    const onClose = vi.fn()
    render(
      <PaperDetails
        paper={node({ rank: 3 })}
        cluster={{ id: 0, label: 'maps, layout', size: 2 }}
        isCurrentSeed={false}
        onExplore={onExplore}
        onClose={onClose}
      />,
    )
    expect(screen.getByText('Rank #3')).toBeInTheDocument()
    expect(screen.getByText('Topic: maps, layout')).toBeInTheDocument()
    expect(screen.getByText('0.2000')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open source page' })).toHaveAttribute('href', 'https://example.org/D001')
    await userEvent.click(screen.getByRole('button', { name: 'Explore from this paper' }))
    expect(onExplore).toHaveBeenCalledWith('D001')
    await userEvent.click(screen.getByRole('button', { name: 'Close details' }))
    expect(onClose).toHaveBeenCalled()
  })

  it('hides exploring for the current seed', () => {
    render(
      <PaperDetails
        paper={node({ is_seed: true, abstract: null, url: null, authors: [] })}
        cluster={undefined}
        isCurrentSeed
        onExplore={() => {}}
        onClose={() => {}}
      />,
    )
    expect(screen.getByText('Seed paper')).toBeInTheDocument()
    expect(screen.getByText('Unknown authors')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Explore from this paper' })).toBeNull()
  })
})

describe('RankingTable and SourceToggle', () => {
  it('lists papers by rank', async () => {
    const onSelect = vi.fn()
    render(<RankingTable nodes={view().nodes} onSelect={onSelect} top={2} />)
    const rows = within(screen.getByRole('table')).getAllByRole('row')
    expect(rows).toHaveLength(3)
    expect(rows[1]).toHaveTextContent('Graph layouts for citation maps')
    await userEvent.click(screen.getByRole('button', { name: /Seed paper about maps/ }))
    expect(onSelect).toHaveBeenCalledWith('D002')
  })

  it('switches the data source', async () => {
    const onChange = vi.fn()
    render(
      <SourceToggle
        sources={[
          { name: 'demo', label: 'Demo', example: 'D042' },
          { name: 'openalex', label: 'Live', example: 'W1' },
        ]}
        value="demo"
        onChange={onChange}
      />,
    )
    expect(screen.getByRole('radio', { name: 'Demo data' })).toHaveAttribute('aria-checked', 'true')
    await userEvent.click(screen.getByRole('radio', { name: 'OpenAlex' }))
    expect(onChange).toHaveBeenCalledWith('openalex')
  })
})
