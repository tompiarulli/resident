import type { QueryClient } from '@tanstack/react-query'
import { createRootRouteWithContext, Link, Outlet } from '@tanstack/react-router'

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  component: RootLayout,
})

function RootLayout() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <header className="mb-8 flex items-center justify-between">
        <Link to="/" className="text-xl font-semibold tracking-tight">
          Resident
        </Link>
      </header>
      <Outlet />
    </div>
  )
}
