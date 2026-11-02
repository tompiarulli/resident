import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link } from '@tanstack/react-router'

import { api } from '../api/client'
import { formatDate } from '../lib/format'

export const Route = createFileRoute('/')({
  component: Overview,
})

function Overview() {
  const metrics = useQuery({
    queryKey: ['metrics'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/metrics')
      if (error) throw error
      return data
    },
  })

  if (metrics.isPending) return <p className="text-stone-500">Loading…</p>
  if (metrics.isError) return <p className="text-red-600">Couldn't reach the Resident server.</p>
  if (metrics.data.length === 0) {
    return (
      <p className="text-stone-500">
        No data yet. Sync from the iOS app or import an Apple Health export to get started.
      </p>
    )
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {metrics.data.map((m) => (
        <Link
          key={m.metric}
          to="/metrics/$metric"
          params={{ metric: m.metric }}
          className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm transition hover:border-stone-400 dark:border-stone-800 dark:bg-stone-900"
        >
          <div className="font-medium">{m.name ?? m.metric}</div>
          <div className="mt-1 text-sm text-stone-500">
            {m.count.toLocaleString()} readings · latest {formatDate(m.latest_at)}
          </div>
        </Link>
      ))}
    </div>
  )
}
