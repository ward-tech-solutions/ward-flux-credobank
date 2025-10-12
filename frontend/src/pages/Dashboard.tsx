import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Loading'
import Badge from '@/components/ui/Badge'
import Select from '@/components/ui/Select'
import { Button } from '@/components/ui/Button'
import { devicesAPI } from '@/services/api'
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  Server,
  XCircle,
  CreditCard,
  Banknote,
  Video,
  Wifi,
  Network,
  Globe,
  Monitor,
  Fingerprint,
  Shield,
  Package,
  type LucideIcon,
} from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'

// Device type icons mapping
const deviceIcons: Record<string, any> = {
  Paybox: CreditCard,
  ATM: Banknote,
  NVR: Video,
  'Access Point': Wifi,
  Switch: Network,
  Router: Globe,
  'Core Router': Monitor,
  Biostar: Fingerprint,
  'Disaster Recovery': Shield,
}

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info'

export default function DashboardEnhanced() {
  const navigate = useNavigate()
  const [selectedSeverity, setSelectedSeverity] = useState('')

  const { data: statsResponse, isLoading: statsLoading } = useQuery({
    queryKey: ['device-stats'],
    queryFn: () => devicesAPI.getStats(),
  })

  const { data: devicesResponse, isLoading: devicesLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesAPI.getAll(),
  })

  const { data: alertsResponse } = useQuery({
    queryKey: ['alerts', selectedSeverity],
    queryFn: () => devicesAPI.getAlerts(selectedSeverity),
  })

  const stats = statsResponse?.data
  const devices = devicesResponse?.data || []
  // Safely extract alerts array - handle both response formats
  const alertsData = alertsResponse?.data
  const alerts = Array.isArray(alertsData?.alerts) ? alertsData.alerts : []

  // Calculate regional statistics
  const regionalStats: Record<string, any> = {}
  devices.forEach((device: any) => {
    const region = device.region || 'Other'
    if (!regionalStats[region]) {
      regionalStats[region] = { total: 0, online: 0, offline: 0 }
    }
    regionalStats[region].total++
    if (device.ping_status === 'Up' || device.available === 'Available') {
      regionalStats[region].online++
    } else {
      regionalStats[region].offline++
    }
  })

  // Calculate device type statistics
  const deviceTypeStats: Record<string, any> = {}
  devices.forEach((device: any) => {
    const type = device.device_type || 'Unknown'
    if (!deviceTypeStats[type]) {
      deviceTypeStats[type] = { total: 0, online: 0, offline: 0 }
    }
    deviceTypeStats[type].total++
    if (device.ping_status === 'Up' || device.available === 'Available') {
      deviceTypeStats[type].online++
    } else {
      deviceTypeStats[type].offline++
    }
  })

  const statsCards: Array<{ title: string; value: number | string; icon: LucideIcon; badgeVariant: BadgeVariant }> = [
    {
      title: 'Total Devices',
      value: stats?.total_devices || 0,
      icon: Server,
      badgeVariant: 'info' as const,
    },
    {
      title: 'Online',
      value: stats?.online_devices || 0,
      icon: CheckCircle,
      badgeVariant: 'success' as const,
    },
    {
      title: 'Offline',
      value: stats?.offline_devices || 0,
      icon: XCircle,
      badgeVariant: 'danger' as const,
    },
    {
      title: 'System Uptime',
      value: `${stats?.uptime_percentage || 0}%`,
      icon: TrendingUp,
      badgeVariant: 'info' as const,
    },
    {
      title: 'Active Alerts',
      value: stats?.active_alerts || 0,
      icon: AlertTriangle,
      badgeVariant: 'warning' as const,
    },
    {
      title: 'Critical Issues',
      value: stats?.critical_alerts || 0,
      icon: AlertTriangle,
      badgeVariant: 'danger' as const,
    },
  ]

  const severityOptions = [
    { value: '', label: 'All Severities' },
    { value: 'Disaster', label: 'Disaster' },
    { value: 'High', label: 'High' },
    { value: 'Average', label: 'Average' },
    { value: 'Warning', label: 'Warning' },
    { value: 'Information', label: 'Information' },
  ]

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      Disaster: 'bg-red-600 text-white',
      High: 'bg-orange-600 text-white',
      Average: 'bg-yellow-600 text-white',
      Warning: 'bg-yellow-500 text-white',
      Information: 'bg-blue-500 text-white',
    }
    return colors[severity] || 'bg-gray-500 text-white'
  }

  if (statsLoading || devicesLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} variant="card" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Network Overview</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Last updated: {new Date().toLocaleTimeString()}
          </p>
        </div>
        <Button
          onClick={() => window.location.reload()}
          icon={<Activity className="h-4 w-4 animate-spin" />}
        >
          Refresh
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {statsCards.map((stat, index) => (
          <Card key={index} variant="glass" hover>
            <CardContent className="p-6 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{stat.title}</p>
                <p className="text-3xl font-bold text-gray-900 dark:text-gray-100 mt-2">{stat.value}</p>
              </div>
              <Badge variant={stat.badgeVariant} className="px-3 py-2 rounded-lg">
                <stat.icon className="h-5 w-5" />
              </Badge>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Regional Statistics */}
      {Object.keys(regionalStats).length > 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Regional Statistics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {Object.entries(regionalStats)
                .filter(([region]) => region !== 'Other')
                .map(([region, data]: [string, any]) => {
                  const uptime =
                    data.total > 0 ? Math.round((data.online / data.total) * 100) : 0
                  return (
                    <div
                      key={region}
                      onClick={() => navigate(`/devices?region=${encodeURIComponent(region)}`)}
                      className="p-4 bg-gradient-to-br from-ward-green/5 to-ward-green/10 dark:from-ward-green/10 dark:to-ward-green/20 rounded-lg border border-ward-green/20 dark:border-ward-green/30 hover:shadow-md transition-shadow cursor-pointer"
                    >
                      <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">{region}</h4>
                      <div className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">{data.total}</div>
                      <div className="text-sm space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Online:</span>
                          <span className="font-medium text-green-600 dark:text-green-400">{data.online}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Offline:</span>
                          <span className="font-medium text-red-600 dark:text-red-400">{data.offline}</span>
                        </div>
                        <div className="pt-2 border-t border-ward-green/20 dark:border-ward-green/30">
                          <div className="flex items-center justify-between">
                            <span className="text-gray-600 dark:text-gray-400">Uptime:</span>
                            <span className="font-bold text-ward-green">{uptime}%</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Device Types Overview */}
      <Card>
        <CardHeader>
          <CardTitle>Device Types Overview</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {Object.entries(deviceTypeStats).map(([type, data]: [string, any]) => {
              const uptime =
                data.total > 0 ? Math.round((data.online / data.total) * 100) : 0
              const IconComponent = deviceIcons[type] || Package
              return (
                <div
                  key={type}
                  onClick={() => navigate(`/devices?device_type=${encodeURIComponent(type)}`)}
                  className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:shadow-md transition-shadow cursor-pointer"
                >
                  <div className="flex items-center gap-2 mb-3">
                    <IconComponent className="h-6 w-6 text-ward-green" />
                    <h4 className="font-semibold text-gray-900 dark:text-gray-100">{type}</h4>
                  </div>
                  <div className="grid grid-cols-3 gap-2 mb-3">
                    <div className="text-center">
                      <div className="text-xl font-bold text-gray-900 dark:text-gray-100">{data.total}</div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">Total</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xl font-bold text-green-600 dark:text-green-400">{data.online}</div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">Online</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xl font-bold text-red-600 dark:text-red-400">{data.offline}</div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">Offline</div>
                    </div>
                  </div>
                  <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
                    <div className="text-center">
                      <span className="text-sm font-semibold text-gray-600 dark:text-gray-300">{uptime}% Uptime</span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Active Alerts */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Active Alerts</CardTitle>
            <div className="flex items-center gap-3">
              <Select
                label="Severity"
                value={selectedSeverity}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSelectedSeverity(e.target.value)}
                options={severityOptions}
              />
              <Badge variant="default" className="h-8 px-3 flex items-center justify-center">
                {alerts.length}
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {alerts.length === 0 ? (
            <div className="text-center py-12">
              <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No alerts</h3>
              <p className="text-gray-500 dark:text-gray-400 mt-1">All systems are operating normally</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      Severity
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      Host
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      Description
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      Time
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {alerts.slice(0, 100).map((alert: any, index: number) => (
                    <tr key={alert.id || index} className="hover:bg-gray-50 dark:hover:bg-gray-900">
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(
                            alert.severity
                          )}`}
                        >
                          {alert.severity}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <Link
                          to={`/devices/${alert.device_id}`}
                          className="text-ward-green hover:text-ward-green-dark font-medium"
                        >
                          {alert.device_name} ({alert.device_ip})
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-gray-900 dark:text-gray-100">{alert.message}</td>
                      <td className="px-4 py-3 text-gray-500 dark:text-gray-400 whitespace-nowrap">
                        {alert.triggered_at ? new Date(alert.triggered_at).toLocaleString() : 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Device Status by Region */}
      <Card>
        <CardHeader>
          <CardTitle>Device Status by Region</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Device Name
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Branch
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    IP Address
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Type
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Problems
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {devices
                  .sort((a: any, b: any) => b.problems - a.problems)
                  .slice(0, 20)
                  .map((device: any) => {
                    const isOnline =
                      device.ping_status === 'Up' || device.available === 'Available'
                    return (
                      <tr
                        key={device.hostid}
                        className="hover:bg-gray-50 dark:hover:bg-gray-900 cursor-pointer"
                        onClick={() => (window.location.href = `/devices/${device.hostid}`)}
                      >
                        <td className="px-4 py-3 whitespace-nowrap">
                          <Badge variant={isOnline ? 'success' : 'danger'} dot>
                            {isOnline ? 'Up' : 'Down'}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">
                          {device.display_name}
                        </td>
                        <td className="px-4 py-3 text-gray-700 dark:text-gray-300">{device.branch}</td>
                        <td className="px-4 py-3 text-gray-700 dark:text-gray-300 font-mono text-sm">{device.ip}</td>
                        <td className="px-4 py-3 text-gray-700 dark:text-gray-300">{device.device_type}</td>
                        <td className="px-4 py-3">
                          {device.problems > 0 ? (
                            <Badge variant="danger">{device.problems}</Badge>
                          ) : (
                            <CheckCircle className="h-5 w-5 text-green-500" />
                          )}
                        </td>
                      </tr>
                    )
                  })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
