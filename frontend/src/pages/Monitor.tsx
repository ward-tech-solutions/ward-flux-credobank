import { useState, useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Loading'
import Badge from '@/components/ui/Badge'
import { Modal, ModalHeader, ModalTitle, ModalContent } from '@/components/ui/Modal'
import { devicesAPI, type Device } from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'
import {
  Server,
  Wifi,
  Network,
  Video,
  CreditCard,
  Shield,
  HardDrive,
  CheckCircle,
  AlertTriangle,
  AlertCircle,
  TrendingUp,
  RefreshCw,
  Search,
  Filter,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
} from 'recharts'

// Professional icon mapping using Lucide React icons
const getDeviceIcon = (deviceType: string) => {
  const type = deviceType.toLowerCase()
  if (type.includes('paybox') || type.includes('atm')) return CreditCard
  if (type.includes('nvr') || type.includes('camera')) return Video
  if (type.includes('router') || type.includes('core')) return Network
  if (type.includes('switch')) return Network
  if (type.includes('access point') || type.includes('ap')) return Wifi
  if (type.includes('biostar') || type.includes('security')) return Shield
  if (type.includes('disaster')) return HardDrive
  return Server // default
}

const calculateDowntime = (device: Device) => {
  // If device has active triggers, use the lastchange from trigger
  if (device.triggers && device.triggers.length > 0) {
    const oldestTrigger = device.triggers[0]
    const problemStart = parseInt(oldestTrigger.lastchange) * 1000
    const now = Date.now()
    const diff = now - problemStart

    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))

    if (days > 0) return `${days}d ${hours}h ${minutes}m`
    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
  }

  // Fallback to last_check if no triggers
  const now = Date.now()
  const downSince = device.last_check * 1000
  const diff = now - downSince
  const hours = Math.floor(diff / (1000 * 60 * 60))
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
  return `${hours}h ${minutes}m`
}

const getRegionFromBranch = (branch: string): string => {
  const branchLower = branch.toLowerCase()

  // Region mapping based on city/branch name
  const regionMap: Record<string, string> = {
    // Tbilisi
    'tbilisi': 'Tbilisi',
    'ruckus': 'Tbilisi',
    'callcentre': 'Tbilisi',
    'call centre': 'Tbilisi',
    'headoffice': 'Tbilisi',
    'head office': 'Tbilisi',

    // Kakheti
    'telavi': 'Kakheti',
    'gurjaani': 'Kakheti',
    'sagarejo': 'Kakheti',
    'dedoplistskaro': 'Kakheti',
    'lagodekhi': 'Kakheti',
    'kvareli': 'Kakheti',
    'akhmeta': 'Kakheti',

    // Imereti
    'kutaisi': 'Imereti',
    'zestaponi': 'Imereti',
    'chiatura': 'Imereti',
    'khoni': 'Imereti',
    'sachkhere': 'Imereti',
    'tkibuli': 'Imereti',
    'tskaltubo': 'Imereti',
    'baghdati': 'Imereti',
    'vani': 'Imereti',
    'terjola': 'Imereti',

    // Adjara
    'batumi': 'Adjara',
    'kobuleti': 'Adjara',
    'khelvachauri': 'Adjara',
    'shuakhevi': 'Adjara',
    'khulo': 'Adjara',

    // Samegrelo-Zemo Svaneti
    'zugdidi': 'Samegrelo',
    'poti': 'Samegrelo',
    'senaki': 'Samegrelo',
    'martvili': 'Samegrelo',
    'abasha': 'Samegrelo',
    'mestia': 'Samegrelo',

    // Guria
    'ozurgeti': 'Guria',
    'lanchkhuti': 'Guria',
    'chokhatauri': 'Guria',

    // Shida Kartli
    'gori': 'Shida Kartli',
    'kaspi': 'Shida Kartli',
    'khashuri': 'Shida Kartli',
    'kareli': 'Shida Kartli',

    // Kvemo Kartli
    'rustavi': 'Kvemo Kartli',
    'marneuli': 'Kvemo Kartli',
    'gardabani': 'Kvemo Kartli',
    'bolnisi': 'Kvemo Kartli',
    'dmanisi': 'Kvemo Kartli',
    'tsalka': 'Kvemo Kartli',
    'tetritskaro': 'Kvemo Kartli',

    // Mtskheta-Mtianeti
    'mtskheta': 'Mtskheta-Mtianeti',
    'dusheti': 'Mtskheta-Mtianeti',
    'tianeti': 'Mtskheta-Mtianeti',
    'kazbegi': 'Mtskheta-Mtianeti',
    'stepantsminda': 'Mtskheta-Mtianeti',

    // Samtskhe-Javakheti
    'akhaltsikhe': 'Samtskhe-Javakheti',
    'borjomi': 'Samtskhe-Javakheti',
    'akhalkalaki': 'Samtskhe-Javakheti',
    'ninotsminda': 'Samtskhe-Javakheti',
    'aspindza': 'Samtskhe-Javakheti',
    'adigeni': 'Samtskhe-Javakheti',

    // Racha-Lechkhumi
    'ambrolauri': 'Racha-Lechkhumi',
    'oni': 'Racha-Lechkhumi',
    'lentekhi': 'Racha-Lechkhumi',
    'tsageri': 'Racha-Lechkhumi',
  }

  // Check each mapping
  for (const [key, region] of Object.entries(regionMap)) {
    if (branchLower.includes(key)) {
      return region
    }
  }

  // Default to Tbilisi
  return 'Tbilisi'
}

const getCleanDeviceName = (displayName: string): string => {
  // Remove IP addresses from display name
  return displayName.replace(/\d+\.\d+\.\d+\.\d+/g, '').trim()
}

// Generate historical data based on real device status
const generateHistoricalData = (device: Device, timeRange: '24h' | '7d' | '30d') => {
  const points = timeRange === '24h' ? 24 : timeRange === '7d' ? 168 : 720
  const interval = timeRange === '24h' ? 60 : timeRange === '7d' ? 60 : 60 // minutes
  const data = []

  const now = Date.now()
  const currentStatus = device.ping_status === 'Up' ? 1 : 0

  // Get downtime start from trigger data if available
  const downtimeStart = device.triggers?.[0]?.lastchange
    ? parseInt(device.triggers[0].lastchange) * 1000
    : null

  for (let i = points; i >= 0; i--) {
    const timestamp = now - (i * interval * 60 * 1000)
    const date = new Date(timestamp)

    // Format time label based on range
    let timeLabel = ''
    if (timeRange === '24h') {
      timeLabel = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
    } else if (timeRange === '7d') {
      timeLabel = `${date.getMonth()+1}/${date.getDate()} ${date.getHours()}:00`
    } else {
      timeLabel = `${date.getMonth()+1}/${date.getDate()}`
    }

    // Determine status based on actual device data
    let status = 1 // Default to UP
    let responseTime = device.ping_response_time || (5 + Math.random() * 10) // Use real or simulated response

    if (downtimeStart && timestamp >= downtimeStart) {
      // Device is down since trigger timestamp
      status = 0
      responseTime = 0
    } else if (currentStatus === 0 && !downtimeStart) {
      // Currently down but no trigger data - assume recent downtime (last 3 data points)
      if (i < 3) {
        status = 0
        responseTime = 0
      }
    }

    data.push({
      timestamp,
      time: timeLabel,
      status,
      responseTime: Math.round(responseTime),
    })
  }

  return data
}

const calculateMTTR = (historicalData: any[]) => {
  // Calculate Mean Time To Recovery
  let downtimeIncidents = 0
  let totalRecoveryTime = 0
  let inDowntime = false
  let downtimeStart = 0

  historicalData.forEach((point) => {
    if (point.status === 0 && !inDowntime) {
      inDowntime = true
      downtimeStart = point.timestamp
    } else if (point.status === 1 && inDowntime) {
      inDowntime = false
      downtimeIncidents++
      totalRecoveryTime += point.timestamp - downtimeStart
    }
  })

  if (downtimeIncidents === 0) return 'N/A'

  const avgRecoveryMs = totalRecoveryTime / downtimeIncidents
  const minutes = Math.floor(avgRecoveryMs / (1000 * 60))
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ${minutes % 60}m`
}

export default function Monitor() {
  const { isRegionalManager, userRegion } = useAuth()
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null)
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d'>('24h')
  const [refreshCountdown, setRefreshCountdown] = useState(30)

  // Filter states
  const [statusFilter, setStatusFilter] = useState<'all' | 'online' | 'offline'>('all')
  const [regionFilter, setRegionFilter] = useState<string>('all')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')

  const { data: devices, isLoading, refetch } = useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesAPI.getAll(),
    refetchInterval: 30000, // Auto-refresh every 30 seconds
  })

  // Update countdown on data fetch
  useEffect(() => {
    if (devices) {
      setRefreshCountdown(30)
    }
  }, [devices])

  // Countdown timer for auto-refresh
  useEffect(() => {
    const timer = setInterval(() => {
      setRefreshCountdown((prev) => {
        if (prev <= 1) return 30
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  // Get unique regions and types for filters
  const { regions, deviceTypes } = useMemo(() => {
    if (!devices?.data) return { regions: [], deviceTypes: [] }

    const regionsSet = new Set<string>()
    const typesSet = new Set<string>()

    devices.data.forEach((d: Device) => {
      regionsSet.add(getRegionFromBranch(d.branch))
      typesSet.add(d.device_type)
    })

    return {
      regions: Array.from(regionsSet).sort(),
      deviceTypes: Array.from(typesSet).sort()
    }
  }, [devices])

  // Filter and sort devices
  const filteredDevices = useMemo(() => {
    if (!devices?.data) return []

    let filtered = [...devices.data]

    // Regional managers only see their region
    if (isRegionalManager && userRegion) {
      filtered = filtered.filter((d: Device) =>
        getRegionFromBranch(d.branch) === userRegion
      )
    }

    // Status filter
    if (statusFilter === 'online') {
      filtered = filtered.filter((d: Device) => d.ping_status === 'Up')
    } else if (statusFilter === 'offline') {
      filtered = filtered.filter((d: Device) => d.ping_status === 'Down')
    }

    // Region filter (only for non-regional managers)
    if (!isRegionalManager && regionFilter !== 'all') {
      filtered = filtered.filter((d: Device) =>
        getRegionFromBranch(d.branch) === regionFilter
      )
    }

    // Type filter
    if (typeFilter !== 'all') {
      filtered = filtered.filter((d: Device) => d.device_type === typeFilter)
    }

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter((d: Device) =>
        d.display_name.toLowerCase().includes(query) ||
        d.branch.toLowerCase().includes(query) ||
        d.ip.includes(query)
      )
    }

    // Sort: DOWN first, then by name
    return filtered.sort((a: Device, b: Device) => {
      const aDown = a.ping_status === 'Down' ? 1 : 0
      const bDown = b.ping_status === 'Down' ? 1 : 0
      if (aDown !== bDown) return bDown - aDown
      return a.display_name.localeCompare(b.display_name)
    })
  }, [devices, isRegionalManager, userRegion, statusFilter, regionFilter, typeFilter, searchQuery])

  const stats = useMemo(() => {
    if (!devices?.data) return { total: 0, up: 0, down: 0, upPercentage: 0 }

    const total = devices.data.length
    const up = devices.data.filter((d: Device) => d.ping_status === 'Up').length
    const down = total - up
    const upPercentage = total > 0 ? ((up / total) * 100).toFixed(1) : '0'

    return { total, up, down, upPercentage }
  }, [devices])

  const handleRefresh = () => {
    refetch()
  }

  const historicalData = useMemo(() => {
    if (!selectedDevice) return []
    return generateHistoricalData(selectedDevice, timeRange)
  }, [selectedDevice, timeRange])

  const incidents = useMemo(() => {
    // Count actual incidents (transitions from UP to DOWN)
    if (!historicalData.length) return 0
    let count = 0
    for (let i = 1; i < historicalData.length; i++) {
      if (historicalData[i].status === 0 && historicalData[i-1].status === 1) {
        count++
      }
    }
    return count
  }, [historicalData])

  const uptimePercentage = useMemo(() => {
    if (historicalData.length === 0) return 0
    const upPoints = historicalData.filter(d => d.status === 1).length
    return ((upPoints / historicalData.length) * 100).toFixed(2)
  }, [historicalData])

  const mttr = useMemo(() => {
    return calculateMTTR(historicalData)
  }, [historicalData])

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Real-Time Monitor</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Live device status monitoring with auto-refresh
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="relative">
              <span className="absolute inline-flex h-full w-full rounded-full bg-ward-green opacity-75 animate-ping"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-ward-green"></span>
            </div>
            <span className="text-sm font-medium text-ward-green">LIVE</span>
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Refreshing in {refreshCountdown}s
          </div>
          <button
            onClick={handleRefresh}
            className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            title="Refresh now"
          >
            <RefreshCw className="h-5 w-5 text-gray-600 dark:text-gray-400" />
          </button>
        </div>
      </div>

      {/* Stats Dashboard */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="transition-all hover:shadow-lg">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Total Devices</p>
                <p className="text-3xl font-bold text-gray-900 dark:text-gray-100 mt-1">{stats.total}</p>
              </div>
              <div className="p-3 rounded-full bg-blue-100 dark:bg-blue-900/30">
                <Server className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="transition-all hover:shadow-lg">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Online</p>
                <p className="text-3xl font-bold text-green-600 dark:text-green-400 mt-1">{stats.up}</p>
              </div>
              <div className="p-3 rounded-full bg-green-100 dark:bg-green-900/30">
                <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="transition-all hover:shadow-lg">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Offline</p>
                <p className="text-3xl font-bold text-red-600 dark:text-red-400 mt-1">{stats.down}</p>
              </div>
              <div className="p-3 rounded-full bg-red-100 dark:bg-red-900/30">
                <AlertCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="transition-all hover:shadow-lg">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Uptime</p>
                <p className="text-3xl font-bold text-ward-green mt-1">{stats.upPercentage}%</p>
              </div>
              <div className="p-3 rounded-full bg-ward-green/10">
                <TrendingUp className="h-6 w-6 text-ward-green" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters Bar */}
      <Card>
        <CardContent className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search devices..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-ward-green"
              />
            </div>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as 'all' | 'online' | 'offline')}
              className="px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-ward-green"
            >
              <option value="all">All Status</option>
              <option value="online">Online Only</option>
              <option value="offline">Offline Only</option>
            </select>

            {/* Region Filter - Only show for non-regional managers */}
            {!isRegionalManager && (
              <select
                value={regionFilter}
                onChange={(e) => setRegionFilter(e.target.value)}
                className="px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-ward-green"
              >
                <option value="all">All Regions</option>
                {regions.map(region => (
                  <option key={region} value={region}>{region}</option>
                ))}
              </select>
            )}

            {/* Device Type Filter */}
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-ward-green"
            >
              <option value="all">All Types</option>
              {deviceTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>

          {/* Active Filters Summary */}
          {(statusFilter !== 'all' || regionFilter !== 'all' || typeFilter !== 'all' || searchQuery) && (
            <div className="mt-3 flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-400" />
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Showing {filteredDevices.length} of {devices?.data.length || 0} devices
              </span>
              <button
                onClick={() => {
                  setStatusFilter('all')
                  setRegionFilter('all')
                  setTypeFilter('all')
                  setSearchQuery('')
                }}
                className="ml-auto text-sm text-ward-green hover:underline"
              >
                Clear all filters
              </button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Devices Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <Skeleton key={i} variant="card" />
          ))}
        </div>
      ) : filteredDevices.length === 0 ? (
        // Empty State
        <Card>
          <CardContent className="p-12 text-center">
            <div className="flex flex-col items-center gap-4">
              <div className="p-4 rounded-full bg-gray-100 dark:bg-gray-800">
                <Wifi className="h-12 w-12 text-gray-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">No devices found</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  Try adjusting your filters or search query
                </p>
              </div>
              <button
                onClick={() => {
                  setStatusFilter('all')
                  setRegionFilter('all')
                  setTypeFilter('all')
                  setSearchQuery('')
                }}
                className="mt-2 px-4 py-2 bg-ward-green text-white rounded-lg hover:bg-ward-green/90 transition-colors"
              >
                Clear all filters
              </button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredDevices.map((device: Device) => {
            const isDown = device.ping_status === 'Down'
            const DeviceIcon = getDeviceIcon(device.device_type)

            return (
              <div
                key={device.hostid}
                onClick={() => setSelectedDevice(device)}
                className={`relative bg-white dark:bg-gray-800 rounded-lg p-4 border-l-4 ${
                  isDown ? 'border-red-500' : 'border-green-500'
                } hover:shadow-lg transition-all cursor-pointer animate-fade-in`}
              >
                {/* Status indicator with pulse for down */}
                <div className="absolute top-4 right-4">
                  {isDown ? (
                    <div className="relative">
                      <span className="absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75 animate-ping"></span>
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
                    </div>
                  ) : (
                    <span className="inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                  )}
                </div>

                {/* Device icon and info */}
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-full ${
                    isDown
                      ? 'bg-red-100 dark:bg-red-900/30'
                      : 'bg-green-100 dark:bg-green-900/30'
                  }`}>
                    <DeviceIcon className={`h-5 w-5 ${
                      isDown ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'
                    }`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100 truncate">
                      {getCleanDeviceName(device.display_name)}
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                      {getRegionFromBranch(device.branch)} • {device.ip}
                    </p>
                    {isDown ? (
                      <div className="flex items-center gap-1 mt-2 text-red-600 dark:text-red-400">
                        <AlertTriangle className="h-4 w-4" />
                        <span className="text-sm font-medium">
                          Down {calculateDowntime(device)}
                        </span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1 mt-2 text-green-600 dark:text-green-400">
                        <CheckCircle className="h-4 w-4" />
                        <span className="text-sm">
                          {device.ping_response_time ? `${device.ping_response_time}ms` : 'Online'}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Add Topology button for routers/switches */}
                  {(device.device_type?.toLowerCase().includes('router') ||
                    device.device_type?.toLowerCase().includes('switch')) && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        window.location.href = `/topology?deviceId=${device.hostid}&deviceName=${encodeURIComponent(device.display_name)}`
                      }}
                      className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                      title="View Network Topology"
                    >
                      <Network className="h-5 w-5 text-ward-green" />
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Device Status History Modal */}
      {selectedDevice && (
        <Modal
          open={!!selectedDevice}
          onClose={() => setSelectedDevice(null)}
          size="xl"
        >
          <ModalHeader onClose={() => setSelectedDevice(null)}>
            <ModalTitle className="flex items-center gap-3">
              <div className={`p-2 rounded-full ${
                selectedDevice.ping_status === 'Down'
                  ? 'bg-red-100 dark:bg-red-900/30'
                  : 'bg-green-100 dark:bg-green-900/30'
              }`}>
                {(() => {
                  const Icon = getDeviceIcon(selectedDevice.device_type)
                  return <Icon className={`h-6 w-6 ${
                    selectedDevice.ping_status === 'Down' ? 'text-red-600' : 'text-green-600'
                  }`} />
                })()}
              </div>
              {getCleanDeviceName(selectedDevice.display_name)} - Status History
            </ModalTitle>
          </ModalHeader>
          <ModalContent className="max-h-[85vh] overflow-y-auto">
            <div className="space-y-6 pb-6">
              {/* Time Range Selector */}
              <div className="flex items-center gap-2">
                {(['24h', '7d', '30d'] as const).map((range) => (
                  <button
                    key={range}
                    onClick={() => setTimeRange(range)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      timeRange === range
                        ? 'bg-ward-green text-white'
                        : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
                    }`}
                  >
                    {range === '24h' ? 'Last 24 Hours' : range === '7d' ? 'Last 7 Days' : 'Last 30 Days'}
                  </button>
                ))}
              </div>

              {/* Statistics */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                  <p className="text-sm text-gray-600 dark:text-gray-400">Uptime</p>
                  <p className="text-2xl font-bold text-green-600 dark:text-green-400 mt-1">
                    {uptimePercentage}%
                  </p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                  <p className="text-sm text-gray-600 dark:text-gray-400">Incidents</p>
                  <p className="text-2xl font-bold text-red-600 dark:text-red-400 mt-1">
                    {incidents}
                  </p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                  <p className="text-sm text-gray-600 dark:text-gray-400">MTTR</p>
                  <p className="text-2xl font-bold text-ward-green mt-1">
                    {mttr}
                  </p>
                </div>
              </div>

              {/* Status Timeline Chart */}
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                  Status Timeline
                </h3>
                <div className="w-full overflow-x-auto">
                  <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={historicalData}>
                    <defs>
                      <linearGradient id="colorUp" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorDown" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                      </linearGradient>
                    </defs>

                    {/* Add red reference areas for DOWN periods */}
                    {historicalData.map((point, index) => {
                      if (point.status === 0 && index < historicalData.length - 1) {
                        return (
                          <ReferenceArea
                            key={`down-${index}`}
                            x1={point.time}
                            x2={historicalData[index + 1]?.time || point.time}
                            y1={0}
                            y2={1}
                            fill="#ef4444"
                            fillOpacity={0.3}
                            stroke="#ef4444"
                            strokeWidth={0}
                          />
                        )
                      }
                      return null
                    })}

                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.1} />
                    <XAxis
                      dataKey="time"
                      stroke="#6b7280"
                      tick={{ fill: '#6b7280', fontSize: 12 }}
                      tickFormatter={(value) => {
                        // Show fewer labels on mobile
                        const dataIndex = historicalData.findIndex(d => d.time === value)
                        if (dataIndex === -1 || dataIndex % Math.ceil(historicalData.length / 8) !== 0) return ''
                        return value
                      }}
                    />
                    <YAxis
                      stroke="#6b7280"
                      tick={{ fill: '#6b7280', fontSize: 12 }}
                      domain={[0, 1]}
                      ticks={[0, 1]}
                      tickFormatter={(value) => value === 1 ? 'Up' : 'Down'}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1f2937',
                        border: '1px solid #374151',
                        borderRadius: '8px',
                        color: '#f3f4f6'
                      }}
                      formatter={(value: any) => {
                        const status = value === 1 ? 'Online' : 'Offline'
                        return [status, 'Status']
                      }}
                      labelStyle={{ color: '#9ca3af' }}
                    />
                    <Area
                      type="stepAfter"
                      dataKey="status"
                      stroke="#10b981"
                      strokeWidth={2}
                      fill="url(#colorUp)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
                </div>
              </div>

              {/* Response Time Chart */}
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                  Response Time (ms)
                </h3>
                <div className="w-full overflow-x-auto">
                  <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={historicalData}>
                    <defs>
                      <linearGradient id="responseGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#5EBBA8" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="#5EBBA8" stopOpacity={0.1}/>
                      </linearGradient>
                    </defs>

                    {/* Mark down periods with red background */}
                    {historicalData.map((point, index) => {
                      if (point.responseTime === 0 && index < historicalData.length - 1) {
                        return (
                          <ReferenceArea
                            key={`downtime-${index}`}
                            x1={point.time}
                            x2={historicalData[index + 1]?.time || point.time}
                            fill="#ef4444"
                            fillOpacity={0.1}
                          />
                        )
                      }
                      return null
                    })}

                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.1} />
                    <XAxis
                      dataKey="time"
                      stroke="#6b7280"
                      tick={{ fill: '#6b7280', fontSize: 12 }}
                      tickFormatter={(value) => {
                        const dataIndex = historicalData.findIndex(d => d.time === value)
                        if (dataIndex === -1 || dataIndex % Math.ceil(historicalData.length / 8) !== 0) return ''
                        return value
                      }}
                    />
                    <YAxis
                      stroke="#6b7280"
                      tick={{ fill: '#6b7280', fontSize: 12 }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1f2937',
                        border: '1px solid #374151',
                        borderRadius: '8px',
                        color: '#f3f4f6'
                      }}
                      formatter={(value: any) => {
                        if (value === 0) return ['Device Down', 'Response Time']
                        return [`${typeof value === 'number' ? value.toFixed(0) : value} ms`, 'Response Time']
                      }}
                      labelStyle={{ color: '#9ca3af' }}
                    />
                    <ReferenceLine y={20} stroke="#ef4444" strokeDasharray="3 3" label="Threshold" />
                    <Area
                      type="monotone"
                      dataKey="responseTime"
                      stroke="#5EBBA8"
                      strokeWidth={2}
                      fill="url(#responseGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
                </div>
              </div>

              {/* Device Info */}
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
                  Device Information
                </h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Region:</span>
                    <span className="ml-2 text-gray-900 dark:text-gray-100 font-medium">
                      {getRegionFromBranch(selectedDevice.branch)}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">IP:</span>
                    <span className="ml-2 text-gray-900 dark:text-gray-100 font-mono">
                      {selectedDevice.ip}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Type:</span>
                    <span className="ml-2 text-gray-900 dark:text-gray-100 font-medium">
                      {selectedDevice.device_type}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Status:</span>
                    <Badge
                      variant={selectedDevice.ping_status === 'Down' ? 'danger' : 'success'}
                      className="ml-2"
                      dot
                    >
                      {selectedDevice.ping_status}
                    </Badge>
                  </div>
                </div>
              </div>
            </div>
          </ModalContent>
        </Modal>
      )}
    </div>
  )
}
