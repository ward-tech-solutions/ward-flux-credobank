import { useState, useEffect, useMemo, useCallback } from 'react'
import type { ChangeEvent } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Loading'
import Badge from '@/components/ui/Badge'
import Select from '@/components/ui/Select'
import MultiSelect from '@/components/ui/MultiSelect'
import { Button } from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import DeviceDetailsModal from '@/components/DeviceDetailsModal'
import { devicesAPI, interfacesAPI, type Device } from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'
import { useResilientWebSocket } from '@/hooks/useResilientWebSocket'
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
  Radio,
  Globe,
} from 'lucide-react'

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

// ISP Detection - Devices ending with .5 are ISP routers with BOTH Magti and Silknet
const isISPRouter = (ip: string): boolean => {
  return ip && ip.endsWith('.5')
}

const calculateDowntime = (device: Device) => {
  // Priority 1: Use triggers if available (most accurate for Zabbix-monitored devices)
  if (device.triggers && device.triggers.length > 0) {
    const oldestTrigger = device.triggers[0]
    // lastchange is a Unix timestamp string in seconds
    const problemStart = parseInt(oldestTrigger.lastchange) * 1000
    const now = Date.now()
    const diff = now - problemStart

    // Debug logging
    console.log(`[${device.name}] Trigger lastchange:`, oldestTrigger.lastchange,
                'Date:', new Date(problemStart).toISOString(),
                'Diff hours:', (diff / (1000 * 60 * 60)).toFixed(2))

    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))

    if (days > 0) return `${days}d ${hours}h ${minutes}m`
    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
  }

  // Priority 2: Use down_since timestamp (accurate for standalone devices)
  if (device.ping_status === 'Down' && device.down_since) {
    const downSinceTime = new Date(device.down_since).getTime()
    const now = Date.now()
    const diff = now - downSinceTime

    // Debug logging
    console.log(`[${device.name}] down_since:`, device.down_since,
                'Date:', new Date(downSinceTime).toISOString(),
                'Diff hours:', (diff / (1000 * 60 * 60)).toFixed(2))

    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))

    if (days > 0) return `${days}d ${hours}h ${minutes}m`
    if (hours > 0) return `${hours}h ${minutes}m`
    if (minutes > 0) return `${minutes}m`
    return '< 1m'
  }

  // Priority 3: Device is down but no down_since timestamp yet
  if (device.ping_status === 'Down') {
    return ''  // Return empty string - will show just "Down" in the UI
  }

  return 'Unknown'
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

  // Check down_since timestamp
  if (device.down_since) {
    const downSinceTime = new Date(device.down_since).getTime()
    const now = Date.now()
    const tenMinutes = 10 * 60 * 1000
    return (now - downSinceTime) < tenMinutes
  }

  // Without timestamp data, assume not recent
  return false
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

    // Transform history data to chart format
    return history.map((point: any) => {
      // API returns 'clock' field as Unix timestamp in seconds
      const timestamp = point.clock * 1000 // Convert to milliseconds
      const date = new Date(timestamp)
      let timeLabel = ''

      if (timeRange === '24h') {
        timeLabel = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
      } else if (timeRange === '7d') {
        timeLabel = `${date.getMonth()+1}/${date.getDate()} ${date.getHours()}:00`
      } else {
        timeLabel = `${date.getMonth()+1}/${date.getDate()}`
      }

      return {
        timestamp: timestamp,
        time: timeLabel,
        status: point.reachable ? 1 : 0, // Convert boolean to 1/0
        responseTime: point.reachable && point.value ? point.value : 0,
      }
    }).reverse() // Reverse to show oldest to newest
  } catch (error) {
    console.error('Failed to fetch historical data:', error)
    return []
  }
}

type ViewMode = 'grid' | 'regions' | 'table'

export default function Monitor() {
  const { isRegionalManager, userRegion } = useAuth()
  const queryClient = useQueryClient()
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null)
  const [timeRange] = useState<'24h' | '7d' | '30d'>('24h')
  const [refreshCountdown, setRefreshCountdown] = useState(30)
  const [_historicalData, setHistoricalData] = useState<any[]>([])
  const [_loadingHistory, setLoadingHistory] = useState(false)
  const [, setCurrentTime] = useState(Date.now()) // Force re-render for downtime updates

  // View mode state
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [expandedRegions, setExpandedRegions] = useState<Set<string>>(new Set())

  // Ping state
  const [pingLoading, setPingLoading] = useState<Set<string>>(new Set())

  // WebSocket state
  // Filter states with localStorage persistence
  const [statusFilter, setStatusFilter] = useState<'all' | 'online' | 'offline'>(() => {
    return (localStorage.getItem('monitor_statusFilter') as any) || 'all'
  })
  const [regionFilters, setRegionFilters] = useState<string[]>(() => {
    const saved = localStorage.getItem('monitor_regionFilters')
    return saved ? JSON.parse(saved) : []
  })
  const [branchFilters, setBranchFilters] = useState<string[]>(() => {
    const saved = localStorage.getItem('monitor_branchFilters')
    return saved ? JSON.parse(saved) : []
  })
  const [typeFilters, setTypeFilters] = useState<string[]>(() => {
    const saved = localStorage.getItem('monitor_typeFilters')
    return saved ? JSON.parse(saved) : []
  })
  const [searchQuery, setSearchQuery] = useState(() => {
    return localStorage.getItem('monitor_searchQuery') || ''
  })

  // Save filters to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('monitor_statusFilter', statusFilter)
  }, [statusFilter])

  useEffect(() => {
    localStorage.setItem('monitor_regionFilters', JSON.stringify(regionFilters))
  }, [regionFilters])

  useEffect(() => {
    localStorage.setItem('monitor_branchFilters', JSON.stringify(branchFilters))
  }, [branchFilters])

  useEffect(() => {
    localStorage.setItem('monitor_typeFilters', JSON.stringify(typeFilters))
  }, [typeFilters])

  useEffect(() => {
    localStorage.setItem('monitor_searchQuery', searchQuery)
  }, [searchQuery])

  // OPTIMIZATION: Pause auto-refresh when modal is open to prevent request contention
  const { data: devices, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesAPI.getAll(),
    refetchInterval: selectedDevice ? false : 30000, // Pause refresh when modal open
    refetchIntervalInBackground: false, // Don't refetch when tab not active
  })

  // ISP Status Query - Fetch status for all .5 routers (optimized bulk query)
  const ispRouterIPs = useMemo(() => {
    if (!devices?.data) return []
    return devices.data
      .filter((device: Device) => isISPRouter(device.ip))
      .map((device: Device) => device.ip)
  }, [devices])

  const { data: ispStatusData } = useQuery({
    queryKey: ['isp-status', ispRouterIPs],
    queryFn: async () => {
      if (ispRouterIPs.length === 0) return {}
      const response = await interfacesAPI.getBulkISPStatus(ispRouterIPs)
      return response.data
    },
    enabled: ispRouterIPs.length > 0,
    refetchInterval: 30000, // Refresh every 30 seconds
    staleTime: 25000, // Consider data stale after 25 seconds
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

  const wsUrl = useMemo(() => {
    if (typeof window === 'undefined') return null
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}/ws/updates`
  }, [])

  const handleWsMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data)
      if (data?.type === 'heartbeat') {
        return
      }
      if (data?.type === 'device_status_update') {
        queryClient.invalidateQueries({ queryKey: ['devices'] })
        toast.info(`Device Update: ${data.device_name} status changed`)
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error)
    }
  }, [queryClient])

  const handleWsError = useCallback((event: Event) => {
    console.error('WebSocket error:', event)
  }, [])

  const websocketOptions = useMemo(
    () => ({
      onMessage: handleWsMessage,
      onError: handleWsError,
    }),
    [handleWsMessage, handleWsError],
  )

  const { state: socketState, reconnectAttempts } = useResilientWebSocket(wsUrl, websocketOptions)

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

  // Fetch alert history for selected device
  const [_deviceAlerts, setDeviceAlerts] = useState<any[]>([])
  const [_loadingAlerts, setLoadingAlerts] = useState(false)

  useEffect(() => {
    if (selectedDevice) {
      setLoadingAlerts(true)
      devicesAPI.getDeviceAlerts(selectedDevice.hostid, 50)
        .then(response => {
          setDeviceAlerts(response.data?.alerts || [])
          setLoadingAlerts(false)
        })
        .catch(error => {
          console.error('Failed to load alerts:', error)
          setDeviceAlerts([])
          setLoadingAlerts(false)
        })
    }
  }, [selectedDevice])

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

  // Update downtime display every second for real-time countdown
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(Date.now()) // Force re-render to update downtime calculations
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  // Extract unique values for multi-select filters
  const uniqueRegions = useMemo(() => {
    if (!devices?.data) return []
    const regions = new Set<string>()
    devices.data.forEach((d: Device) => {
      const region = getRegionFromBranch(d.branch) || d.region
      if (region) regions.add(region)
    })

    const sorted = Array.from(regions).sort()
    if (isRegionalManager && userRegion) {
      return sorted.filter(region => region === userRegion)
    }
    return sorted
  }, [devices, isRegionalManager, userRegion])

  const uniqueBranches = useMemo(() => {
    if (!devices?.data) return []
    const selectedRegions = regionFilters.length > 0 ? new Set(regionFilters) : null
    const branches = new Set<string>()

    devices.data.forEach((d: Device) => {
      const region = getRegionFromBranch(d.branch) || d.region
      if (isRegionalManager && userRegion && region !== userRegion) return
      if (selectedRegions && (!region || !selectedRegions.has(region))) return
      if (d.branch) branches.add(d.branch)
    })
    return Array.from(branches).sort()
  }, [devices, regionFilters, isRegionalManager, userRegion])

  const uniqueTypes = useMemo(() => {
    if (!devices?.data) return []
    const selectedRegions = regionFilters.length > 0 ? new Set(regionFilters) : null
    const selectedBranches = branchFilters.length > 0 ? new Set(branchFilters) : null
    const types = new Set<string>()

    devices.data.forEach((d: Device) => {
      const region = getRegionFromBranch(d.branch) || d.region
      if (isRegionalManager && userRegion && region !== userRegion) return
      if (selectedRegions && (!region || !selectedRegions.has(region))) return
      if (selectedBranches && (!d.branch || !selectedBranches.has(d.branch))) return
      if (d.device_type) types.add(d.device_type)
    })
    return Array.from(types).sort()
  }, [devices, regionFilters, branchFilters, isRegionalManager, userRegion])

  // Initialize expanded regions
  useEffect(() => {
    if (uniqueRegions.length === 0) return
    setExpandedRegions(prev => {
      if (prev.size > 0) return prev
      return new Set(uniqueRegions)
    })
  }, [uniqueRegions])

  useEffect(() => {
    if (uniqueRegions.length === 0) return
    setRegionFilters(prev => {
      if (prev.length === 0) return prev
      const allowed = new Set(uniqueRegions)
      const next = prev.filter(region => allowed.has(region))
      return next.length === prev.length ? prev : next
    })
  }, [uniqueRegions])

  useEffect(() => {
    // Only validate filters if we have branches loaded, don't clear on initial load
    if (uniqueBranches.length === 0) return

    setBranchFilters(prev => {
      if (prev.length === 0) return prev
      const allowed = new Set(uniqueBranches)
      const next = prev.filter(branch => allowed.has(branch))
      return next.length === prev.length ? prev : next
    })
  }, [uniqueBranches])

  useEffect(() => {
    // Only validate filters if we have types loaded, don't clear on initial load
    if (uniqueTypes.length === 0) return

    setTypeFilters(prev => {
      if (prev.length === 0) return prev
      const allowed = new Set(uniqueTypes)
      const next = prev.filter(type => allowed.has(type))
      return next.length === prev.length ? prev : next
    })
  }, [uniqueTypes])

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

    // Multi-select region filter
    if (regionFilters.length > 0) {
      filtered = filtered.filter((d: Device) =>
        regionFilters.includes(getRegionFromBranch(d.branch) || d.region || '')
      )
    }

    // Multi-select branch filter
    if (branchFilters.length > 0) {
      filtered = filtered.filter((d: Device) =>
        branchFilters.includes(d.branch || '')
      )
    }

    // Multi-select type filter
    if (typeFilters.length > 0) {
      filtered = filtered.filter((d: Device) =>
        typeFilters.includes(d.device_type || '')
      )
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
        // Use down_since timestamp for standalone devices, fallback to triggers for Zabbix
        const aDowntime = a.down_since
          ? new Date(a.down_since).getTime()
          : (a.triggers?.[0] ? parseInt(a.triggers[0].lastchange) * 1000 : a.last_check * 1000)
        const bDowntime = b.down_since
          ? new Date(b.down_since).getTime()
          : (b.triggers?.[0] ? parseInt(b.triggers[0].lastchange) * 1000 : b.last_check * 1000)
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
  }, [devices, isRegionalManager, userRegion, statusFilter, regionFilters, branchFilters, typeFilters, searchQuery])

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
    const isPinging = pingLoading.has(device.hostid)

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
            {/* Monitoring Type Badges */}
            <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-700">
                <Activity className="h-3 w-3" />
                ICMP
              </span>
              {device.snmp_community && device.snmp_community.trim() !== '' && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border border-green-300 dark:border-green-700">
                  <Network className="h-3 w-3" />
                  SNMP
                </span>
              )}
              {/* ISP Indicators for .5 routers - Show BOTH Magti and Silknet with INDEPENDENT status */}
              {isISPRouter(device.ip) && (() => {
                const ispStatus = ispStatusData?.[device.ip]
                const magtiStatus = ispStatus?.magti?.status || 'unknown'
                const silknetStatus = ispStatus?.silknet?.status || 'unknown'

                // Determine badge colors based on INDIVIDUAL ISP status
                const magtiIsUp = magtiStatus === 'up'
                const silknetIsUp = silknetStatus === 'up'

                return (
                  <>
                    {/* Magti Badge - Independent status */}
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold ${
                      magtiIsUp
                        ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border-purple-300 dark:border-purple-700'
                        : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-300 dark:border-red-700'
                    } border`} title={`Magti: ${magtiStatus.toUpperCase()}${ispStatus?.magti ? ` (${ispStatus.magti.if_name})` : ''}`}>
                      <Radio className="h-3 w-3" />
                      <span className="font-bold">Magti</span>
                    </span>
                    {/* Silknet Badge - Independent status */}
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold ${
                      silknetIsUp
                        ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 border-orange-300 dark:border-orange-700'
                        : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-300 dark:border-red-700'
                    } border`} title={`Silknet: ${silknetStatus.toUpperCase()}${ispStatus?.silknet ? ` (${ispStatus.silknet.if_name})` : ''}`}>
                      <Globe className="h-3 w-3" />
                      <span className="font-bold">Silknet</span>
                    </span>
                  </>
                )
              })()}
            </div>
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

        {/* Ping Now button */}
        <button
          onClick={(e) => handlePing(device.hostid, e)}
          disabled={isPinging}
          className="absolute bottom-3 right-3 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-gray-200 dark:border-gray-600"
          title="Ping Now"
        >
          <Activity className="h-4 w-4 text-ward-green" />
        </button>
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
            {selectedDevice ? (
              <span className="text-yellow-600 dark:text-yellow-400">Auto-refresh paused (modal open)</span>
            ) : isFetching ? (
              <span className="flex items-center gap-1">
                <Loader2 className="h-3 w-3 animate-spin" />
                Refreshing...
              </span>
            ) : (
              <span>Refreshing in {refreshCountdown}s</span>
            )}
          </div>
          <button
            onClick={handleRefresh}
            disabled={isFetching}
            className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title={isFetching ? "Refresh in progress..." : "Refresh now"}
          >
            <RefreshCw className={`h-5 w-5 text-gray-600 dark:text-gray-400 ${isFetching ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {socketState !== 'open' && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-amber-800">
          <AlertTriangle className="h-5 w-5 flex-shrink-0" />
          <div>
            <p className="font-medium">
              Live updates {socketState === 'connecting' ? 'connecting…' : socketState === 'reconnecting' ? 'reconnecting…' : 'temporarily paused'}
            </p>
            {socketState === 'reconnecting' && reconnectAttempts > 0 && (
              <p className="text-sm opacity-80">Retry attempt {reconnectAttempts}</p>
            )}
            {socketState === 'error' && (
              <p className="text-sm opacity-80">We&apos;ll retry automatically; manual refresh remains available.</p>
            )}
          </div>
        </div>
      )}

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
        <CardContent className="p-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Search"
              placeholder="Search devices..."
              value={searchQuery}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
              icon={<Search className="h-5 w-5" />}
            />

            <Select
              label="Status"
              value={statusFilter}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                setStatusFilter(e.target.value as 'all' | 'online' | 'offline')
              }
              options={[
                { value: 'all', label: 'All Status' },
                { value: 'online', label: 'Online Only' },
                { value: 'offline', label: 'Offline Only' },
              ]}
              fullWidth
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <MultiSelect
              label="Regions"
              options={uniqueRegions}
              selected={regionFilters}
              onChange={setRegionFilters}
              placeholder="All regions"
            />

            <MultiSelect
              label="Branches"
              options={uniqueBranches}
              selected={branchFilters}
              onChange={setBranchFilters}
              placeholder="All branches"
            />

            <MultiSelect
              label="Device Types"
              options={uniqueTypes}
              selected={typeFilters}
              onChange={setTypeFilters}
              placeholder="All types"
            />
          </div>

          {/* Active Filters Summary */}
          {(statusFilter !== 'all' || regionFilters.length > 0 || branchFilters.length > 0 || typeFilters.length > 0 || searchQuery) && (
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-400" />
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Showing {filteredDevices?.length || 0} of {devices?.data?.length || 0} devices
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setStatusFilter('all')
                  setRegionFilters([])
                  setBranchFilters([])
                  setTypeFilters([])
                  setSearchQuery('')
                }}
                className="ml-auto"
              >
                Clear all filters
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* View Mode Toggle */}
      <div className="flex gap-2">
        <Button
          variant={viewMode === 'grid' ? 'primary' : 'ghost'}
          size="sm"
          onClick={() => setViewMode('grid')}
          icon={<Grid3x3 className="h-4 w-4" />}
        >
          Grid
        </Button>
        <Button
          variant={viewMode === 'regions' ? 'primary' : 'ghost'}
          size="sm"
          onClick={() => setViewMode('regions')}
          icon={<List className="h-4 w-4" />}
        >
          Regions
        </Button>
        <Button
          variant={viewMode === 'table' ? 'primary' : 'ghost'}
          size="sm"
          onClick={() => setViewMode('table')}
          icon={<TableIcon className="h-4 w-4" />}
        >
          Table
        </Button>
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
                  setRegionFilters([])
                  setBranchFilters([])
                  setTypeFilters([])
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
                      Monitoring
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
                          <div className="flex items-center gap-1.5">
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-700">
                              <Activity className="h-3 w-3" />
                              ICMP
                            </span>
                            {device.snmp_community && device.snmp_community.trim() !== '' && (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border border-green-300 dark:border-green-700">
                                <Network className="h-3 w-3" />
                                SNMP
                              </span>
                            )}
                          </div>
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


      {/* Device Details Modal */}
      <DeviceDetailsModal
        open={!!selectedDevice}
        onClose={() => setSelectedDevice(null)}
        hostid={selectedDevice?.hostid || ''}
      />
    </div>
  )
}
