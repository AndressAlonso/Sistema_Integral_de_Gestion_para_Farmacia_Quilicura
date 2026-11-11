import { expect, it } from 'vitest'
import { chileToday } from './businessDate'

it.each([
  ['2026-11-06T02:59:59Z', '2026-11-05'],
  ['2026-11-06T03:00:00Z', '2026-11-06'],
  ['2026-07-06T03:59:59Z', '2026-07-05'],
  ['2026-07-06T04:00:00Z', '2026-07-06'],
])('usa el día chileno en %s', (instant, expected) => {
  expect(chileToday(new Date(instant))).toBe(expected)
})
