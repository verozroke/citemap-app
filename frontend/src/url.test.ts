import { expect, it } from 'vitest'
import { readUrl, writeUrl } from './url'

it('reads source and seed from the query string', () => {
  expect(readUrl('?source=openalex&seed=W1')).toEqual({ source: 'openalex', seed: 'W1' })
  expect(readUrl('?source=other&seed=%20')).toEqual({ source: 'demo', seed: null })
  expect(readUrl('')).toEqual({ source: 'demo', seed: null })
})

it('writes the current graph into the address bar', () => {
  writeUrl('demo', 'D042')
  expect(window.location.search).toBe('?source=demo&seed=D042')
  expect(readUrl()).toEqual({ source: 'demo', seed: 'D042' })
})
