import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Loading'
import Badge from '@/components/ui/Badge'
import { devicesAPI } from '@/services/api'
import { Activity, Wifi, AlertTriangle, CheckCircle, Clock, TrendingUp } from 'lucide-react'
import { AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['device-stats'],
    queryFn: () => devicesAPI.getStats(),
  })

  const { data: devices, isLoading: devicesLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesAPI.getAll(),
  })

  const statsCards = [
    {
      title: 'Total Devices',
      value: stats?.data?.total_devices || 0,
      icon: Wifi,
      color: 'text-ward-green',
      bgColor: 'bg-ward-green/10',
      trend: '+12%',
    },
    {
      title: 'Online',
      value: stats?.data?.online_devices || 0,
      icon: CheckCircle,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
      trend: '+5%',
    },
    {
      title: 'Offline',
      value: stats?.data?.offline_devices || 0,
      icon: AlertTriangle,
      color: 'text-red-600',
      bgColor: 'bg-red-100',
      trend: '-2%',
    },
    {
      title: 'Active Monitoring',
      value: stats?.data?.monitored_devices || 0,
      icon: Activity,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
      trend: '+8%',
    },
  ]

  // Sample data for charts
  const activityData = [
    { time: '00:00', devices: 120, traffic: 450 },
    { time: '04:00', devices: 118, traffic: 380 },
    { time: '08:00', devices: 145, traffic: 620 },
    { time: '12:00', devices: 152, traffic: 780 },
    { time: '16:00', devices: 148, traffic: 890 },
    { time: '20:00', devices: 142, traffic: 650 },
  ]

  const deviceTypeData = [
    { name: 'Routers', value: 35, color: '#5EBBA8' },
    { name: 'Switches', value: 48, color: '#72CFB8' },
    { name: 'Firewalls', value: 12, color: '#4A9D8A' },
    { name: 'Servers', value: 28, color: '#DFDFDF' },
    { name: 'Other', value: 15, color: '#2C3E50' },
  ]

  const vendorData = [
    { vendor: 'Cisco', count: 45 },
    { vendor: 'Juniper', count: 28 },
    { vendor: 'HP', count: 22 },
    { vendor: 'Dell', count: 18 },
    { vendor: 'Other', count: 25 },
  ]

  if (statsLoading || devicesLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
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
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">Network monitoring overview</p>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-gray-400" />
          <span className="text-sm text-gray-600">
            Last updated: {new Date().toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statsCards.map((stat, index) => (
          <Card key={index} hover className="relative overflow-hidden">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">{stat.title}</p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">{stat.value}</p>
                  <div className="flex items-center gap-1 mt-2">
                    <TrendingUp className="h-4 w-4 text-green-600" />
                    <span className="text-sm text-green-600 font-medium">{stat.trend}</span>
                  </div>
                </div>
                <div className={`p-3 rounded-xl ${stat.bgColor}`}>
                  <stat.icon className={`h-8 w-8 ${stat.color}`} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Activity Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Network Activity (24h)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={activityData}>
                <defs>
                  <linearGradient id="colorDevices" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#5EBBA8" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#5EBBA8" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="time" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="devices"
                  stroke="#5EBBA8"
                  fillOpacity={1}
                  fill="url(#colorDevices)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Device Types Pie Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Device Types</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={deviceTypeData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {deviceTypeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Vendor Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Vendor Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={vendorData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="vendor" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                  }}
                />
                <Bar dataKey="count" fill="#5EBBA8" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Recent Devices */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Recent Devices</CardTitle>
              <Link
                to="/devices"
                className="text-sm text-ward-green hover:text-ward-green-dark font-medium"
              >
                View all →
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {devices?.data?.slice(0, 5).map((device: any) => {
                // Use old UI status logic: ping_status === 'Up' OR available === 'Available'
                const isOnline = device.ping_status === 'Up' || device.available === 'Available'
                return (
                  <div key={device.hostid} className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-ward-green/10 rounded-lg">
                        <Wifi className="h-5 w-5 text-ward-green" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{device.display_name}</p>
                        <p className="text-sm text-gray-500">{device.ip}</p>
                      </div>
                    </div>
                    <Badge variant={isOnline ? 'success' : 'danger'} dot>
                      {isOnline ? 'Online' : 'Offline'}
                    </Badge>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link
              to="/discovery"
              className="p-4 border-2 border-gray-200 rounded-lg hover:border-ward-green hover:bg-ward-green/5 transition-all group"
            >
              <Activity className="h-8 w-8 text-ward-green mb-3" />
              <h3 className="font-semibold text-gray-900 group-hover:text-ward-green">
                Start Discovery
              </h3>
              <p className="text-sm text-gray-500 mt-1">
                Scan network for new devices
              </p>
            </Link>
            <Link
              to="/devices"
              className="p-4 border-2 border-gray-200 rounded-lg hover:border-ward-green hover:bg-ward-green/5 transition-all group"
            >
              <Wifi className="h-8 w-8 text-ward-green mb-3" />
              <h3 className="font-semibold text-gray-900 group-hover:text-ward-green">
                Add Device
              </h3>
              <p className="text-sm text-gray-500 mt-1">
                Manually add a new device
              </p>
            </Link>
            <Link
              to="/diagnostics"
              className="p-4 border-2 border-gray-200 rounded-lg hover:border-ward-green hover:bg-ward-green/5 transition-all group"
            >
              <AlertTriangle className="h-8 w-8 text-ward-green mb-3" />
              <h3 className="font-semibold text-gray-900 group-hover:text-ward-green">
                Run Diagnostics
              </h3>
              <p className="text-sm text-gray-500 mt-1">
                Test network connectivity
              </p>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
