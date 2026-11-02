import { describe, expect, it } from 'vitest'

import { formatDate } from './format'

describe('formatDate', () => {
  it('formats an ISO timestamp as a short date', () => {
    expect(formatDate('2024-03-01T12:00:00Z', 'en-US')).toBe('Mar 1, 2024')
  })
})
