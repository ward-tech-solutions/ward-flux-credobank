import { LoadingSpinner, Skeleton } from './Loading'

/**
 * Full-page loader for initial page loads
 * Shows centered spinner with optional message
 */
export const PageLoader = ({ message = 'Loading...' }: { message?: string }) => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <LoadingSpinner size="lg" text={message} />
    </div>
  )
}

/**
 * Table skeleton loader
 * Shows realistic table-like skeleton while data loads
 */
export const TableLoader = ({ rows = 10 }: { rows?: number }) => {
  return (
    <div className="space-y-4">
      {/* Table header */}
      <div className="flex gap-4">
        <Skeleton variant="rect" className="h-10 flex-1" />
        <Skeleton variant="rect" className="h-10 flex-1" />
        <Skeleton variant="rect" className="h-10 flex-1" />
        <Skeleton variant="rect" className="h-10 w-32" />
      </div>

      {/* Table rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4">
          <Skeleton variant="rect" className="h-16 flex-1" />
          <Skeleton variant="rect" className="h-16 flex-1" />
          <Skeleton variant="rect" className="h-16 flex-1" />
          <Skeleton variant="rect" className="h-16 w-32" />
        </div>
      ))}
    </div>
  )
}

/**
 * Card grid skeleton loader
 * Shows realistic card grid while data loads
 */
export const CardGridLoader = ({ cards = 8 }: { cards?: number }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {Array.from({ length: cards }).map((_, i) => (
        <Skeleton key={i} variant="card" className="h-48" />
      ))}
    </div>
  )
}

/**
 * Stats cards skeleton loader
 * Shows stat card skeletons while dashboard loads
 */
export const StatsLoader = ({ stats = 4 }: { stats?: number }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {Array.from({ length: stats }).map((_, i) => (
        <div key={i} className="bg-white rounded-lg border border-gray-200 p-6 space-y-3">
          <Skeleton variant="text" className="w-24 h-4" />
          <Skeleton variant="text" className="w-16 h-8" />
          <Skeleton variant="text" className="w-32 h-3" />
        </div>
      ))}
    </div>
  )
}

/**
 * Device details skeleton loader
 * Shows realistic device details layout while loading
 */
export const DeviceDetailsLoader = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Skeleton variant="circle" className="h-16 w-16" />
        <div className="flex-1 space-y-2">
          <Skeleton variant="text" className="w-48 h-6" />
          <Skeleton variant="text" className="w-64 h-4" />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Skeleton variant="rect" className="h-24" />
        <Skeleton variant="rect" className="h-24" />
        <Skeleton variant="rect" className="h-24" />
      </div>

      {/* Content sections */}
      <Skeleton variant="rect" className="h-64" />
      <Skeleton variant="rect" className="h-64" />
    </div>
  )
}
