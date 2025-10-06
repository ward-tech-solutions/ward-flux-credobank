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

  const { data: device, isLoading } = useQuery({
    queryKey: ['device', id],
    queryFn: () => devicesAPI.getById(id!),
    enabled: !!id,
  })

  // Sample metrics data
  const metricsData = [
    { time: '00:00', cpu: 45, memory: 62, bandwidth: 340 },
    { time: '04:00', cpu: 38, memory: 58, bandwidth: 280 },
    { time: '08:00', cpu: 65, memory: 72, bandwidth: 520 },
    { time: '12:00', cpu: 72, memory: 78, bandwidth: 680 },
    { time: '16:00', cpu: 68, memory: 75, bandwidth: 590 },
    { time: '20:00', cpu: 52, memory: 65, bandwidth: 420 },
  ]

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
              <CardTitle>Quick Stats</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Activity className="h-5 w-5 text-green-600 dark:text-green-400" />
                    <span className="text-sm font-medium text-green-900 dark:text-green-100">Uptime</span>
                  </div>
                  <p className="text-2xl font-bold text-green-900 dark:text-green-100">99.9%</p>
                </div>
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    <span className="text-sm font-medium text-blue-900 dark:text-blue-100">Response Time</span>
                  </div>
                  <p className="text-2xl font-bold text-blue-900 dark:text-blue-100">12ms</p>
                </div>
                <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Wifi className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                    <span className="text-sm font-medium text-purple-900 dark:text-purple-100">Bandwidth</span>
                  </div>
                  <p className="text-2xl font-bold text-purple-900 dark:text-purple-100">450 Mbps</p>
                </div>
                <div className="p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="h-5 w-5 text-orange-600 dark:text-orange-400" />
                    <span className="text-sm font-medium text-orange-900 dark:text-orange-100">Alerts</span>
                  </div>
                  <p className="text-2xl font-bold text-orange-900 dark:text-orange-100">0</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'metrics' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>CPU Usage (%)</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={metricsData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" className="dark:stroke-gray-700" />
                  <XAxis dataKey="time" stroke="#9ca3af" className="dark:stroke-gray-500" />
                  <YAxis stroke="#9ca3af" className="dark:stroke-gray-500" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgb(31 41 55)',
                      border: '1px solid rgb(75 85 99)',
                      borderRadius: '8px',
                      color: 'rgb(243 244 246)'
                    }}
                    labelStyle={{ color: 'rgb(243 244 246)' }}
                  />
                  <Line type="monotone" dataKey="cpu" stroke="#5EBBA8" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Memory Usage (%)</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={metricsData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" className="dark:stroke-gray-700" />
                  <XAxis dataKey="time" stroke="#9ca3af" className="dark:stroke-gray-500" />
                  <YAxis stroke="#9ca3af" className="dark:stroke-gray-500" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgb(31 41 55)',
                      border: '1px solid rgb(75 85 99)',
                      borderRadius: '8px',
                      color: 'rgb(243 244 246)'
                    }}
                    labelStyle={{ color: 'rgb(243 244 246)' }}
                  />
                  <Line type="monotone" dataKey="memory" stroke="#3B82F6" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Bandwidth (Mbps)</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={metricsData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" className="dark:stroke-gray-700" />
                  <XAxis dataKey="time" stroke="#9ca3af" className="dark:stroke-gray-500" />
                  <YAxis stroke="#9ca3af" className="dark:stroke-gray-500" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgb(31 41 55)',
                      border: '1px solid rgb(75 85 99)',
                      borderRadius: '8px',
                      color: 'rgb(243 244 246)'
                    }}
                    labelStyle={{ color: 'rgb(243 244 246)' }}
                  />
                  <Line type="monotone" dataKey="bandwidth" stroke="#8B5CF6" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
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
