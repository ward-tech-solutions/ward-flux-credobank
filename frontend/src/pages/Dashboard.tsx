import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { SkeletonKPICard, SkeletonDeviceCard } from '../components/Skeleton'

export const Dashboard = () => {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.getDashboardStats().then((res) => res.data),
    refetchInterval: 30000, // Refetch every 30 seconds
  })

  if (error) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⚠️</div>
        <h2 className="empty-state-title">Failed to load dashboard</h2>
        <p className="empty-state-message">
          {error instanceof Error ? error.message : 'An unknown error occurred'}
        </p>
        <button
          className="btn-primary"
          onClick={() => window.location.reload()}
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-title">
          <h1>Dashboard</h1>
          <span className="page-subtitle">Network Monitoring Overview</span>
        </div>
        <div className="page-actions">
          <button className="btn-refresh" onClick={() => window.location.reload()}>
            <i className="fas fa-sync-alt"></i>
            Refresh
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid">
        {isLoading ? (
          <>
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <SkeletonKPICard key={i} />
            ))}
          </>
        ) : (
          <>
            <div className="kpi-card">
              <div className="kpi-icon total">
                <i className="fas fa-server"></i>
              </div>
              <div className="kpi-content">
                <div className="kpi-value">{stats?.total_devices || 0}</div>
                <div className="kpi-label">Total Devices</div>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-icon online">
                <i className="fas fa-check-circle"></i>
              </div>
              <div className="kpi-content">
                <div className="kpi-value">{stats?.online_devices || 0}</div>
                <div className="kpi-label">Online</div>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-icon offline">
                <i className="fas fa-times-circle"></i>
              </div>
              <div className="kpi-content">
                <div className="kpi-value">{stats?.offline_devices || 0}</div>
                <div className="kpi-label">Offline</div>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-icon uptime">
                <i className="fas fa-chart-line"></i>
              </div>
              <div className="kpi-content">
                <div className="kpi-value">{stats?.uptime_percentage || 0}%</div>
                <div className="kpi-label">Uptime</div>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-icon alerts">
                <i className="fas fa-exclamation-triangle"></i>
              </div>
              <div className="kpi-content">
                <div className="kpi-value">{stats?.active_alerts || 0}</div>
                <div className="kpi-label">Active Alerts</div>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-icon critical">
                <i className="fas fa-fire"></i>
              </div>
              <div className="kpi-content">
                <div className="kpi-value">{stats?.critical_alerts || 0}</div>
                <div className="kpi-label">Critical</div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Device Types */}
      <div className="card">
        <div className="card-header">
          <h2>Device Types</h2>
        </div>
        <div className="card-content">
          <div className="device-types-grid">
            {isLoading ? (
              <>
                {[1, 2, 3, 4].map((i) => (
                  <SkeletonDeviceCard key={i} />
                ))}
              </>
            ) : (
              Object.entries(stats?.device_types || {}).map(
                ([type, data]: [string, any]) => (
                  <div key={type} className="device-type-card">
                    <h4>{type}</h4>
                    <div className="device-type-stats">
                      <div>
                        <strong>{data.total}</strong>
                        <small>Total</small>
                      </div>
                      <div>
                        <strong style={{ color: 'var(--success-green)' }}>
                          {data.online}
                        </strong>
                        <small>Online</small>
                      </div>
                      <div>
                        <strong style={{ color: 'var(--danger-red)' }}>
                          {data.offline}
                        </strong>
                        <small>Offline</small>
                      </div>
                    </div>
                  </div>
                )
              )
            )}
          </div>
        </div>
      </div>

      {/* Regions */}
      <div className="card">
        <div className="card-header">
          <h2>Regions Overview</h2>
        </div>
        <div className="card-content">
          <div className="region-grid">
            {isLoading ? (
              <>
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <SkeletonDeviceCard key={i} />
                ))}
              </>
            ) : (
              Object.entries(stats?.regions_stats || {}).map(
                ([region, data]: [string, any]) => (
                  <div key={region} className="region-card">
                    <h3>{region}</h3>
                    <div className="device-type-stats">
                      <div>
                        <strong>{data.total}</strong>
                        <small>Total</small>
                      </div>
                      <div>
                        <strong style={{ color: 'var(--success-green)' }}>
                          {data.online}
                        </strong>
                        <small>Online</small>
                      </div>
                      <div>
                        <strong style={{ color: 'var(--danger-red)' }}>
                          {data.offline}
                        </strong>
                        <small>Offline</small>
                      </div>
                    </div>
                  </div>
                )
              )
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
