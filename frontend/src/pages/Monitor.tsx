import { useState, useEffect, useMemo, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Loading'
import Badge from '@/components/ui/Badge'
import Select from '@/components/ui/Select'
import { Button } from '@/components/ui/Button'
import { Modal, ModalHeader, ModalTitle, ModalContent } from '@/components/ui/Modal'
import { devicesAPI, type Device } from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'
import { toast } from 'sonner'
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
  Grid3x3,
  List,
  TableIcon,
  ChevronDown,
  ChevronUp,
  Loader2,
  Activity,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
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

const isRecentlyDown = (device: Device): boolean => {
  if (device.ping_status !== 'Down') {
    return false
  }

  // Check if device has triggers
  if (device.triggers && device.triggers.length > 0) {
    const problemStart = parseInt(device.triggers[0].lastchange) * 1000
    const now = Date.now()
    const tenMinutes = 10 * 60 * 1000
    return (now - problemStart) < tenMinutes
  }

  // Fallback: check last_check if no triggers (recently went down)
  const now = Date.now()
  const lastCheck = device.last_check * 1000
  const tenMinutes = 10 * 60 * 1000
  return (now - lastCheck) < tenMinutes
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
    'bakuriani': 'Samtskhe-Javakheti',
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

// Fetch real historical data from backend
const fetchHistoricalData = async (device: Device, timeRange: '24h' | '7d' | '30d') => {
  try {
    const response = await devicesAPI.getHistory(device.hostid, timeRange)
    const history = response.data.history || []

    if (history.length === 0) {
      return []
    }

    // Transform Zabbix history to chart format
    return history.map((point: any) => {
      const date = new Date(point.timestamp)
      let timeLabel = ''

      if (timeRange === '24h') {
        timeLabel = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
      } else if (timeRange === '7d') {
        timeLabel = `${date.getMonth()+1}/${date.getDate()} ${date.getHours()}:00`
      } else {
        timeLabel = `${date.getMonth()+1}/${date.getDate()}`
      }

      return {
        timestamp: point.timestamp,
        time: timeLabel,
        status: point.value, // 1 = UP, 0 = DOWN
        responseTime: point.value === 1 ? (device.ping_response_time || 10) : 0,
      }
    })
  } catch (error) {
    console.error('Failed to fetch historical data:', error)
    return []
  }
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

type ViewMode = 'grid' | 'regions' | 'table'

export default function Monitor() {
  const { isRegionalManager, userRegion } = useAuth()
  const queryClient = useQueryClient()
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null)
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d'>('24h')
  const [refreshCountdown, setRefreshCountdown] = useState(30)
  const [historicalData, setHistoricalData] = useState<any[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)

  // View mode state
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [expandedRegions, setExpandedRegions] = useState<Set<string>>(new Set())

  // Ping state
  const [pingLoading, setPingLoading] = useState<Set<string>>(new Set())

  // WebSocket state
  const wsRef = useRef<WebSocket | null>(null)

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

  // Ping mutation
  const pingMutation = useMutation({
    mutationFn: (hostid: string) => devicesAPI.pingDevice(hostid),
    onSuccess: (response: any, hostid: string) => {
      setPingLoading(prev => {
        const newSet = new Set(prev)
        newSet.delete(hostid)
        return newSet
      })

      if (response.data.success) {
        const responseTime = response.data.response_time
        toast.success(`Ping Successful - Response time: ${responseTime}ms`)
      } else {
        toast.error(response.data.error || 'Ping Failed - Device did not respond')
      }
    },
    onError: (error: any, hostid: string) => {
      setPingLoading(prev => {
        const newSet = new Set(prev)
        newSet.delete(hostid)
        return newSet
      })
      toast.error(error.message || 'Ping Error - Failed to ping device')
    },
  })

  // Handle ping action
  const handlePing = (hostid: string, event?: React.MouseEvent) => {
    if (event) event.stopPropagation()
    setPingLoading(prev => new Set(prev).add(hostid))
    pingMutation.mutate(hostid)
  }

  // WebSocket connection for real-time updates
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/updates`

    const connectWebSocket = () => {
      try {
        const ws = new WebSocket(wsUrl)
        wsRef.current = ws

        ws.onopen = () => {
          // WebSocket connected for real-time updates
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.type === 'device_status_update') {
              // Refetch devices to get latest status
              queryClient.invalidateQueries({ queryKey: ['devices'] })
              toast.info(`Device Update: ${data.device_name} status changed`)
            }
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
          }
        }

        ws.onerror = (error) => {
          console.error('WebSocket error:', error)
        }

        ws.onclose = () => {
          // WebSocket disconnected, will attempt reconnection
          setTimeout(connectWebSocket, 5000)
        }
      } catch (error) {
        console.error('Failed to connect WebSocket:', error)
      }
    }

    connectWebSocket()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [queryClient])

  // Load historical data when device is selected
  useEffect(() => {
    if (selectedDevice) {
      setLoadingHistory(true)
      fetchHistoricalData(selectedDevice, timeRange)
        .then(data => {
          setHistoricalData(data)
          setLoadingHistory(false)
        })
        .catch(error => {
          console.error('Failed to load history:', error)
          setLoadingHistory(false)
        })
    }
  }, [selectedDevice, timeRange])

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

  // Initialize expanded regions
  useEffect(() => {
    if (regions.length > 0 && expandedRegions.size === 0) {
      setExpandedRegions(new Set(regions))
    }
  }, [regions])

  // Filter and sort devices with priority for recently down
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

    // Sort with priority: Critical problems first, then by downtime duration
    return filtered.sort((a: Device, b: Device) => {
      const aRecentlyDown = isRecentlyDown(a)
      const bRecentlyDown = isRecentlyDown(b)
      const aDown = a.ping_status === 'Down'
      const bDown = b.ping_status === 'Down'

      // Priority 1: Down devices first
      if (aDown && !bDown) return -1
      if (!aDown && bDown) return 1

      // Priority 2: Among down devices, recently down first (<10 min)
      if (aDown && bDown) {
        if (aRecentlyDown && !bRecentlyDown) return -1
        if (!aRecentlyDown && bRecentlyDown) return 1

        // Priority 3: Among recently down or older down devices, sort by recency (most recent first)
        const aDowntime = a.triggers?.[0] ? parseInt(a.triggers[0].lastchange) : a.last_check
        const bDowntime = b.triggers?.[0] ? parseInt(b.triggers[0].lastchange) : b.last_check
        return bDowntime - aDowntime // Later timestamp = more recent = higher priority
      }

      // Priority 4: Up devices - sort by response time (slower = lower quality)
      if (!aDown && !bDown) {
        const aResponse = a.ping_response_time || 0
        const bResponse = b.ping_response_time || 0
        if (aResponse !== bResponse) return bResponse - aResponse
      }

      // Final: Alphabetical
      return a.display_name.localeCompare(b.display_name)
    })
  }, [devices, isRegionalManager, userRegion, statusFilter, regionFilter, typeFilter, searchQuery])

  // Group devices by region
  const devicesByRegion = useMemo(() => {
    const grouped: Record<string, Device[]> = {}
    filteredDevices.forEach((device: Device) => {
      const region = getRegionFromBranch(device.branch)
      if (!grouped[region]) {
        grouped[region] = []
      }
      grouped[region].push(device)
    })
    return grouped
  }, [filteredDevices])

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

  // Toggle region expansion
  const toggleRegion = (region: string) => {
    setExpandedRegions(prev => {
      const newSet = new Set(prev)
      if (newSet.has(region)) {
        newSet.delete(region)
      } else {
        newSet.add(region)
      }
      return newSet
    })
  }


  // Render device card
  const renderDeviceCard = (device: Device) => {
    const isDown = device.ping_status === 'Down'
    const recentlyDown = isRecentlyDown(device)
    const DeviceIcon = getDeviceIcon(device.device_type)

    return (
      <div
        key={device.hostid}
        onClick={() => setSelectedDevice(device)}
        className={`relative bg-white dark:bg-gray-800 rounded-lg p-4 border-l-4 cursor-pointer transition-all duration-300 ${
          recentlyDown
            ? 'border-red-600 shadow-lg shadow-red-500/30 animate-pulse-glow'
            : isDown
            ? 'border-red-500 hover:shadow-lg'
            : 'border-green-500 hover:shadow-lg'
        }`}
      >
        {/* Status indicator with stronger pulse for recently down */}
        <div className="absolute top-3 right-3">
          {isDown ? (
            <div className="relative flex items-center justify-center w-5 h-5">
              {recentlyDown && (
                <>
                  <span className="absolute inline-flex h-6 w-6 rounded-full bg-red-500 opacity-75 animate-ping"></span>
                  <span className="absolute inline-flex h-5 w-5 rounded-full bg-red-400 opacity-60 animate-pulse"></span>
                </>
              )}
              <span className="relative inline-flex rounded-full h-3 w-3 bg-red-600 shadow-lg shadow-red-500/50"></span>
            </div>
          ) : (
            <span className="inline-flex rounded-full h-3 w-3 bg-green-500 shadow-sm"></span>
          )}
        </div>

        {/* Device content */}
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-full flex-shrink-0 ${
            isDown
              ? 'bg-red-100 dark:bg-red-900/30'
              : 'bg-green-100 dark:bg-green-900/30'
          }`}>
            <DeviceIcon className={`h-5 w-5 ${
              isDown ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'
            }`} />
          </div>
          <div className="flex-1 min-w-0 pr-8">
            <h3 className="font-semibold text-gray-900 dark:text-gray-100 truncate">
              {getCleanDeviceName(device.display_name)}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 break-words">
              {getRegionFromBranch(device.branch)}
            </p>
            <p className="text-xs font-mono text-gray-600 dark:text-gray-500 mt-1">
              {device.ip}
            </p>
            {isDown ? (
              <div className="flex items-center gap-1 mt-2 text-red-600 dark:text-red-400">
                <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                <span className="text-sm font-medium">
                  Down {calculateDowntime(device)}
                  {recentlyDown && ' • RECENT'}
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-1 mt-2 text-green-600 dark:text-green-400">
                <CheckCircle className="h-4 w-4 flex-shrink-0" />
                <span className="text-sm">
                  {device.ping_response_time ? `${device.ping_response_time}ms` : 'Online'}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

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
            <Select
              value={statusFilter}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setStatusFilter(e.target.value as 'all' | 'online' | 'offline')}
              options={[
                { value: 'all', label: 'All Status' },
                { value: 'online', label: 'Online Only' },
                { value: 'offline', label: 'Offline Only' },
              ]}
            />

            {/* Region Filter - Only show for non-regional managers */}
            {!isRegionalManager && (
              <Select
                value={regionFilter}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setRegionFilter(e.target.value)}
                options={[
                  { value: 'all', label: 'All Regions' },
                  ...regions.map(region => ({ value: region, label: region }))
                ]}
              />
            )}

            {/* Device Type Filter */}
            <Select
              value={typeFilter}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setTypeFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Types' },
                ...deviceTypes.map(type => ({ value: type, label: type }))
              ]}
            />
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

      {/* View Mode Toggle */}
      <div className="flex gap-2">
        <button
          onClick={() => setViewMode('grid')}
          className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
            viewMode === 'grid'
              ? 'bg-ward-green text-white'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
        >
          <Grid3x3 className="h-4 w-4" />
          Grid
        </button>
        <button
          onClick={() => setViewMode('regions')}
          className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
            viewMode === 'regions'
              ? 'bg-ward-green text-white'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
        >
          <List className="h-4 w-4" />
          Regions
        </button>
        <button
          onClick={() => setViewMode('table')}
          className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
            viewMode === 'table'
              ? 'bg-ward-green text-white'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
        >
          <TableIcon className="h-4 w-4" />
          Table
        </button>
      </div>

      {/* Devices Grid/Regions/Table View */}
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
              <Button
                onClick={() => {
                  setStatusFilter('all')
                  setRegionFilter('all')
                  setTypeFilter('all')
                  setSearchQuery('')
                }}
                className="mt-2"
              >
                Clear all filters
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : viewMode === 'grid' ? (
        // Grid View
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredDevices.map((device: Device) => renderDeviceCard(device))}
        </div>
      ) : viewMode === 'regions' ? (
        // Regions View
        <div className="space-y-4">
          {Object.entries(devicesByRegion).map(([region, devices]) => {
            const isExpanded = expandedRegions.has(region)
            const regionDevices = devices as Device[]
            const onlineCount = regionDevices.filter(d => d.ping_status === 'Up').length
            const offlineCount = regionDevices.length - onlineCount

            return (
              <Card key={region}>
                <CardContent className="p-4">
                  <div
                    className="flex items-center justify-between cursor-pointer"
                    onClick={() => toggleRegion(region)}
                  >
                    <div className="flex items-center gap-3">
                      {isExpanded ? (
                        <ChevronDown className="h-5 w-5 text-gray-500" />
                      ) : (
                        <ChevronUp className="h-5 w-5 text-gray-500" />
                      )}
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                        {region}
                      </h3>
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        ({regionDevices.length} devices)
                      </span>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-green-600 dark:text-green-400">
                          {onlineCount} Online
                        </span>
                        <span className="text-sm text-gray-400">•</span>
                        <span className="text-sm text-red-600 dark:text-red-400">
                          {offlineCount} Offline
                        </span>
                      </div>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                      {regionDevices.map((device: Device) => renderDeviceCard(device))}
                    </div>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      ) : (
        // Table View
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Device Name
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Region/Branch
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      IP Address
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Response Time
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {filteredDevices.map((device: Device, index: number) => {
                    const isDown = device.ping_status === 'Down'
                    const recentlyDown = isRecentlyDown(device)
                    const DeviceIcon = getDeviceIcon(device.device_type)
                    const isPinging = pingLoading.has(device.hostid)

                    return (
                      <tr
                        key={device.hostid}
                        className={`${
                          index % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50 dark:bg-gray-900'
                        } hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer`}
                        onClick={() => setSelectedDevice(device)}
                      >
                        <td className="px-4 py-3">
                          {isDown ? (
                            <div className="relative flex items-center justify-center w-4 h-4">
                              {recentlyDown && (
                                <>
                                  <span className="absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-75 animate-ping"></span>
                                  <span className="absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-50 animate-pulse"></span>
                                </>
                              )}
                              <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500 shadow-lg shadow-red-500/50"></span>
                            </div>
                          ) : (
                            <span className="inline-flex rounded-full h-3 w-3 bg-green-500 shadow-sm"></span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <DeviceIcon className={`h-5 w-5 ${
                              isDown ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'
                            }`} />
                            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                              {getCleanDeviceName(device.display_name)}
                            </span>
                            {recentlyDown && (
                              <Badge variant="danger" className="text-xs">RECENT</Badge>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                          {device.device_type}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                          {getRegionFromBranch(device.branch)} • {device.branch}
                        </td>
                        <td className="px-4 py-3 text-sm font-mono text-gray-600 dark:text-gray-400">
                          {device.ip}
                        </td>
                        <td className="px-4 py-3">
                          {isDown ? (
                            <span className="text-sm text-red-600 dark:text-red-400">
                              Down {calculateDowntime(device)}
                            </span>
                          ) : (
                            <span className="text-sm text-green-600 dark:text-green-400">
                              {device.ping_response_time ? `${device.ping_response_time}ms` : 'Online'}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-1">
                            <button
                              onClick={(e) => handlePing(device.hostid, e)}
                              disabled={isPinging}
                              className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
                              title="Ping"
                            >
                              {isPinging ? (
                                <Loader2 className="h-4 w-4 text-ward-green animate-spin" />
                              ) : (
                                <Activity className="h-4 w-4 text-ward-green" />
                              )}
                            </button>
                            {(device.device_type?.toLowerCase().includes('router') ||
                              device.device_type?.toLowerCase().includes('switch')) && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  window.location.href = `/topology?deviceId=${device.hostid}&deviceName=${encodeURIComponent(device.display_name)}`
                                }}
                                className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                                title="Topology"
                              >
                                <Network className="h-4 w-4 text-ward-green" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
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

              {loadingHistory ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 text-ward-green animate-spin" />
                </div>
              ) : (
                <>
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
                  {historicalData.length > 0 && (
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
                  )}

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
                </>
              )}
            </div>
          </ModalContent>
        </Modal>
      )}
    </div>
  )
}
