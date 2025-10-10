import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { LoadingSpinner } from '@/components/ui/Loading'
import Badge from '@/components/ui/Badge'
import { devicesAPI } from '@/services/api'
import { ArrowLeft, Activity, Info, Settings, AlertTriangle, Clock, Wifi } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function DeviceDetails() {
  const { id } = useParams()
  const [activeTab, setActiveTab] = useState('overview')
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d'>('24h')

  const { data: device, isLoading } = useQuery({
    queryKey: ['device', id],
    queryFn: () => devicesAPI.getById(id!),
    enabled: !!id,
  })

  // Fetch real ping history data
  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['device-history', id, timeRange],
    queryFn: () => devicesAPI.getHistory(id!, timeRange),
    enabled: !!id,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Transform real ping data to chart format
  const metricsData = historyData?.data?.history?.map((point: any) => {
    const date = new Date(point.clock * 1000)
    const hours = date.getHours().toString().padStart(2, '0')
    const minutes = date.getMinutes().toString().padStart(2, '0')
    return {
      time: `${hours}:${minutes}`,
      timestamp: point.clock,
      ping: point.reachable ? point.value : null,
      reachable: point.reachable,
    }
  }).reverse() || []

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Info },
    { id: 'metrics', label: 'Metrics', icon: Activity },
    { id: 'config', label: 'Configuration', icon: Settings },
    { id: 'alerts', label: 'Alerts', icon: AlertTriangle },
  ]

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner size="lg" text="Loading device details..." />
      </div>
    )
  }

  if (!device?.data) {
    return (
      <div className="text-center py-12">
        <Wifi className="h-16 w-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">Device not found</h3>
        <Link to="/devices" className="text-ward-green hover:text-ward-green-dark mt-2 inline-block">
          ← Back to devices
        </Link>
      </div>
    )
  }

  const deviceData = device.data

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to="/devices"
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-gray-600 dark:text-gray-400" />
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">{deviceData.name}</h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1 font-mono">{deviceData.ip}</p>
          </div>
        </div>
        <Badge variant={deviceData.enabled ? 'success' : 'danger'} size="lg" dot>
          {deviceData.enabled ? 'Active' : 'Inactive'}
        </Badge>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex gap-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-ward-green text-ward-green'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              <tab.icon className="h-5 w-5" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Device Information</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between py-2 border-b border-gray-100 dark:border-gray-700">
                  <span className="text-gray-500 dark:text-gray-400">Name</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{deviceData.name}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-100 dark:border-gray-700">
                  <span className="text-gray-500 dark:text-gray-400">IP Address</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100 font-mono">{deviceData.ip}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-100 dark:border-gray-700">
                  <span className="text-gray-500 dark:text-gray-400">Vendor</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{deviceData.vendor || '-'}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-100 dark:border-gray-700">
                  <span className="text-gray-500 dark:text-gray-400">Device Type</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{deviceData.device_type || '-'}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-100 dark:border-gray-700">
                  <span className="text-gray-500 dark:text-gray-400">Model</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{deviceData.model || '-'}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-100 dark:border-gray-700">
                  <span className="text-gray-500 dark:text-gray-400">Status</span>
                  <Badge variant={deviceData.enabled ? 'success' : 'danger'} dot>
                    {deviceData.enabled ? 'Enabled' : 'Disabled'}
                  </Badge>
                </div>
                <div className="flex justify-between py-2">
                  <span className="text-gray-500 dark:text-gray-400">Created At</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">
                    {deviceData.created_at ? new Date(deviceData.created_at).toLocaleString() : 'N/A'}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Quick Stats (24h)</CardTitle>
            </CardHeader>
            <CardContent>
              {historyLoading ? (
                <div className="flex items-center justify-center h-32">
                  <LoadingSpinner text="Loading stats..." />
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Activity className="h-5 w-5 text-green-600 dark:text-green-400" />
                      <span className="text-sm font-medium text-green-900 dark:text-green-100">Uptime</span>
                    </div>
                    <p className="text-2xl font-bold text-green-900 dark:text-green-100">
                      {metricsData.length > 0
                        ? `${((metricsData.filter((p) => p.reachable).length / metricsData.length) * 100).toFixed(1)}%`
                        : 'N/A'}
                    </p>
                  </div>
                  <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Clock className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                      <span className="text-sm font-medium text-blue-900 dark:text-blue-100">Avg Response</span>
                    </div>
                    <p className="text-2xl font-bold text-blue-900 dark:text-blue-100">
                      {metricsData.length > 0 && metricsData.some((p) => p.ping !== null)
                        ? `${Math.round(
                            metricsData.filter((p) => p.ping !== null).reduce((sum, p) => sum + (p.ping || 0), 0) /
                              metricsData.filter((p) => p.ping !== null).length
                          )}ms`
                        : 'N/A'}
                    </p>
                  </div>
                  <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Wifi className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                      <span className="text-sm font-medium text-purple-900 dark:text-purple-100">Status</span>
                    </div>
                    <p className="text-2xl font-bold text-purple-900 dark:text-purple-100">
                      {deviceData.ping_status || 'Unknown'}
                    </p>
                  </div>
                  <div className="p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle className="h-5 w-5 text-orange-600 dark:text-orange-400" />
                      <span className="text-sm font-medium text-orange-900 dark:text-orange-100">Packet Loss</span>
                    </div>
                    <p className="text-2xl font-bold text-orange-900 dark:text-orange-100">
                      {metricsData.length > 0
                        ? `${((metricsData.filter((p) => !p.reachable).length / metricsData.length) * 100).toFixed(1)}%`
                        : 'N/A'}
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'metrics' && (
        <div className="space-y-6">
          {/* Time Range Selector */}
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Time Range:</span>
            <div className="flex gap-2">
              {(['24h', '7d', '30d'] as const).map((range) => (
                <button
                  key={range}
                  onClick={() => setTimeRange(range)}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                    timeRange === range
                      ? 'bg-ward-green text-white'
                      : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
                  }`}
                >
                  {range === '24h' ? 'Last 24 Hours' : range === '7d' ? 'Last 7 Days' : 'Last 30 Days'}
                </button>
              ))}
            </div>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Ping Response Time (ms)</CardTitle>
            </CardHeader>
            <CardContent>
              {historyLoading ? (
                <div className="flex items-center justify-center h-64">
                  <LoadingSpinner text="Loading metrics..." />
                </div>
              ) : metricsData.length === 0 ? (
                <div className="text-center py-12">
                  <Activity className="h-16 w-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No metrics data</h3>
                  <p className="text-gray-500 dark:text-gray-400 mt-1">No ping data available for this time range</p>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={400}>
                  <LineChart data={metricsData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" className="dark:stroke-gray-700" />
                    <XAxis
                      dataKey="time"
                      stroke="#9ca3af"
                      className="dark:stroke-gray-500"
                      tick={{ fontSize: 12 }}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis
                      stroke="#9ca3af"
                      className="dark:stroke-gray-500"
                      label={{ value: 'Response Time (ms)', angle: -90, position: 'insideLeft' }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'rgb(31 41 55)',
                        border: '1px solid rgb(75 85 99)',
                        borderRadius: '8px',
                        color: 'rgb(243 244 246)'
                      }}
                      labelStyle={{ color: 'rgb(243 244 246)' }}
                      formatter={(value: any, name: string) => {
                        if (name === 'ping') return [`${value} ms`, 'Ping RTT']
                        return [value, name]
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="ping"
                      stroke="#5EBBA8"
                      strokeWidth={2}
                      dot={{ fill: '#5EBBA8', r: 2 }}
                      connectNulls={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Device Reachability</CardTitle>
            </CardHeader>
            <CardContent>
              {historyLoading ? (
                <div className="flex items-center justify-center h-64">
                  <LoadingSpinner text="Loading metrics..." />
                </div>
              ) : metricsData.length === 0 ? (
                <div className="text-center py-12">
                  <Activity className="h-16 w-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No metrics data</h3>
                  <p className="text-gray-500 dark:text-gray-400 mt-1">No reachability data available for this time range</p>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={metricsData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" className="dark:stroke-gray-700" />
                    <XAxis
                      dataKey="time"
                      stroke="#9ca3af"
                      className="dark:stroke-gray-500"
                      tick={{ fontSize: 12 }}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis
                      stroke="#9ca3af"
                      className="dark:stroke-gray-500"
                      domain={[0, 1]}
                      ticks={[0, 1]}
                      tickFormatter={(value) => value === 1 ? 'Up' : 'Down'}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'rgb(31 41 55)',
                        border: '1px solid rgb(75 85 99)',
                        borderRadius: '8px',
                        color: 'rgb(243 244 246)'
                      }}
                      labelStyle={{ color: 'rgb(243 244 246)' }}
                      formatter={(value: any) => [value ? 'Reachable' : 'Unreachable', 'Status']}
                    />
                    <Line
                      type="stepAfter"
                      dataKey="reachable"
                      stroke="#3B82F6"
                      strokeWidth={2}
                      dot={{ fill: '#3B82F6', r: 2 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'config' && (
        <Card>
          <CardHeader>
            <CardTitle>Device Configuration</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">SNMP Configuration</h4>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-500 dark:text-gray-400">Community String</span>
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">••••••••</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-500 dark:text-gray-400">SNMP Version</span>
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">v2c</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-500 dark:text-gray-400">Port</span>
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">161</span>
                  </div>
                </div>
              </div>

              <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">Monitoring Settings</h4>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-500 dark:text-gray-400">Polling Interval</span>
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">60 seconds</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-500 dark:text-gray-400">Timeout</span>
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">10 seconds</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-500 dark:text-gray-400">Retries</span>
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">3</span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'alerts' && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Alerts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center py-12">
              <AlertTriangle className="h-16 w-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No alerts</h3>
              <p className="text-gray-500 dark:text-gray-400 mt-1">This device has no recent alerts</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
