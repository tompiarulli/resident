import { useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import ReactECharts from 'echarts-for-react'

import { api } from '../api/client'

export const Route = createFileRoute('/metrics/$metric')({
  component: MetricDetail,
})

function MetricDetail() {
  const { metric } = Route.useParams()
  const observations = useQuery({
    queryKey: ['observations', metric],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/metrics/{metric}/observations', {
        params: { path: { metric }, query: { limit: 5000 } },
      })
      if (error) throw error
      return data
    },
  })

  if (observations.isPending) return <p className="text-stone-500">Loading…</p>
  if (observations.isError) return <p className="text-red-600">Couldn't load {metric}.</p>

  const unit = observations.data[0]?.unit ?? ''
  const points = observations.data
    .filter((o) => o.value !== null)
    .map((o) => [o.start_at, o.value])
    .reverse()

  return (
    <section>
      <h1 className="mb-4 text-lg font-semibold">{metric}</h1>
      <ReactECharts
        style={{ height: 360 }}
        option={{
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'time' },
          yAxis: { type: 'value', name: unit, scale: true },
          dataZoom: [{ type: 'inside' }, { type: 'slider' }],
          series: [{ type: 'line', showSymbol: false, data: points, sampling: 'lttb' }],
        }}
      />
    </section>
  )
}
