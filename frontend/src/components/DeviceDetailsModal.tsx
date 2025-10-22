import { useState, useEffect, useMemo, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Modal, ModalHeader, ModalTitle, ModalContent } from '@/components/ui/Modal'
import { Skeleton } from '@/components/ui/Loading'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import { devicesAPI } from '@/services/api'
import { toast } from 'sonner'
import {
  Globe,
  Copy,
  MapPin,
  RefreshCw,
  Wrench,
  Terminal,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Activity,
  Info,
  Network,
  Wifi,
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
} from 'recharts'

interface DeviceDetailsModalProps {
  open: boolean
  onClose: () => void
  hostid: string
  onOpenSSH?: (deviceName: string, deviceIP: string) => void
}

type TimeRange = '30m' | '1h' | '3h' | '6h' | '12h' | '24h' | '7d' | '30d'

const getDeviceIcon = (deviceType: string): any => {
  const type = deviceType?.toLowerCase() || ''

  // Return Lucide icon component
  if (type.includes('paybox')) return Activity
  if (type.includes('atm')) return Activity
  if (type.includes('nvr') || type.includes('camera')) return Activity
  if (type.includes('access point') || type.includes('ap')) return Wifi
  if (type.includes('switch')) return Network
  if (type.includes('router')) return Globe
  if (type.includes('biostar')) return Activity
  if (type.includes('disaster')) return Activity

  return Activity // Default
}

const getSeverityName = (priority: number) => {
  const severities = ['Not classified', 'Information', 'Warning', 'Average', 'High', 'Disaster']
  return severities[priority] || 'Unknown'
}

const getSeverityVariant = (priority: number): 'default' | 'success' | 'warning' | 'danger' => {
  if (priority >= 4) return 'danger'
  if (priority === 3) return 'warning'
  if (priority === 2) return 'warning'
  return 'default'
}

const formatDuration = (ms: number) => {
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 0) return `${days}d ${hours % 24}h`
  if (hours > 0) return `${hours}h ${minutes % 60}m`
  if (minutes > 0) return `${minutes}m`
  return `${seconds}s`
}

export default function DeviceDetailsModal({ open, onClose, hostid, onOpenSSH }: DeviceDetailsModalProps) {
  const [copiedIP, setCopiedIP] = useState(false)
  const [timeRange, setTimeRange] = useState<TimeRange>('1h')
  const [isPinging, setIsPinging] = useState(false)
  const queryClient = useQueryClient()

  const { data: device, isLoading, refetch } = useQuery({
    queryKey: ['device', hostid],
    queryFn: () => devicesAPI.getById(hostid),
    enabled: open && !!hostid,
  })

  // Fetch real historical ping data
  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['device-history', hostid, timeRange],
    queryFn: () => devicesAPI.getHistory(hostid, timeRange),
    enabled: open && !!hostid,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Fetch alert history for this device
  const { data: alertsData, isLoading: alertsLoading } = useQuery({
    queryKey: ['device-alerts', hostid],
    queryFn: () => devicesAPI.getDeviceAlerts(hostid, 50),
    enabled: open && !!hostid,
    refetchInterval: 30000,
  })

  useEffect(() => {
    if (open && hostid) {
      refetch()
    }
  }, [open, hostid, refetch])

  const deviceData = device?.data

  const isOnline = deviceData?.ping_status === 'Up' || deviceData?.available === 'Available'
  const statusText = deviceData?.ping_status || deviceData?.available || 'Unknown'

  // Transform real ping history data to chart format
  type PingHistoryPoint = {
    clock: number
    reachable: boolean
    value: number | null
  }

  const statusHistory = useMemo(() => {
    if (!historyData?.data?.history || historyData.data.history.length === 0) {
      return []
    }

    const history = historyData.data.history as PingHistoryPoint[]

    return history.map((point) => {
      const date = new Date(point.clock * 1000)

      // Format time based on time range
      let timeFormat = ''
      if (timeRange === '30m' || timeRange === '1h' || timeRange === '3h') {
        // For short ranges, show HH:MM:SS
        const hours = date.getHours().toString().padStart(2, '0')
        const minutes = date.getMinutes().toString().padStart(2, '0')
        const seconds = date.getSeconds().toString().padStart(2, '0')
        timeFormat = `${hours}:${minutes}:${seconds}`
      } else if (timeRange === '6h' || timeRange === '12h' || timeRange === '24h') {
        // For medium ranges, show HH:MM
        const hours = date.getHours().toString().padStart(2, '0')
        const minutes = date.getMinutes().toString().padStart(2, '0')
        timeFormat = `${hours}:${minutes}`
      } else if (timeRange === '7d') {
        // For 7 days, show day and hour
        const day = date.toLocaleDateString('en-US', { weekday: 'short' })
        const hours = date.getHours().toString().padStart(2, '0')
        timeFormat = `${day} ${hours}:00`
      } else {
        const month = date.getMonth() + 1
        const day = date.getDate()
        timeFormat = `${month}/${day}`
      }

      return {
        time: timeFormat,
        timestamp: point.clock,
        status: point.reachable ? 1 : 0,
        responseTime: point.reachable && point.value ? point.value : 0,
      }
    }).reverse() // Reverse to show oldest to newest
  }, [historyData, timeRange])

  // Calculate uptime percentage and incidents
  const uptimeStats = useMemo(() => {
    if (statusHistory.length === 0) {
      return { uptime: 0, incidents: 0, mttr: 'N/A' }
    }

    const totalPoints = statusHistory.length
    const upPoints = statusHistory.filter(p => p.status === 1).length
    const uptime = ((upPoints / totalPoints) * 100).toFixed(2)

    // Count incidents (transitions from up to down)
    let incidents = 0
    for (let i = 1; i < statusHistory.length; i++) {
      if (statusHistory[i].status === 0 && statusHistory[i - 1].status === 1) {
        incidents++
      }
    }

    return { uptime, incidents, mttr: 'N/A' }
  }, [statusHistory])

  const copyIP = () => {
    if (!deviceData?.ip) return

    // Try modern clipboard API first (HTTPS only)
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(deviceData.ip)
        .then(() => {
          setCopiedIP(true)
          setTimeout(() => setCopiedIP(false), 2000)
        })
        .catch(() => {
          // Fallback for HTTP or older browsers
          fallbackCopyIP(deviceData.ip)
        })
    } else {
      // Fallback for HTTP or older browsers
      fallbackCopyIP(deviceData.ip)
    }
  }

  const fallbackCopyIP = (text: string) => {
    const textArea = document.createElement('textarea')
    textArea.value = text
    textArea.style.position = 'fixed'
    textArea.style.left = '-999999px'
    document.body.appendChild(textArea)
    textArea.select()
    try {
      document.execCommand('copy')
      setCopiedIP(true)
      setTimeout(() => setCopiedIP(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
    document.body.removeChild(textArea)
  }

  const openWebUI = () => {
    if (deviceData?.ip) {
      window.open(`http://${deviceData.ip}`, '_blank')
    }
  }

  const handleRefresh = () => {
    refetch()
  }

  const handlePing = async () => {
    if (!deviceData) return

    setIsPinging(true)
    try {
      const response = await devicesAPI.pingDevice(hostid)

      // Check actual ping result from backend
      if (response?.data?.success) {
        const responseTime = response.data.response_time
        toast.success('Device is reachable!', {
          description: responseTime
            ? `${deviceData.display_name} responded in ${responseTime}ms`
            : `${deviceData.display_name} responded to ping`,
          duration: 4000,
        })
      } else {
        const errorMsg = response?.data?.error || 'Device did not respond'
        toast.error('Device is unreachable', {
          description: `${deviceData.display_name}: ${errorMsg}`,
          duration: 5000,
        })
      }

      // Refresh device data after ping
      setTimeout(() => {
        refetch()
        queryClient.invalidateQueries({ queryKey: ['device', hostid] })
      }, 1000)
    } catch (error) {
      console.error('Ping failed:', error)
      toast.error('Ping request failed', {
        description: 'Could not send ping request. Please try again.',
        duration: 4000,
      })
    } finally {
      setTimeout(() => setIsPinging(false), 2000)
    }
  }

  const handleSSH = () => {
    if (deviceData && onOpenSSH) {
      const port = deviceData.ssh_port || 22
      onOpenSSH(deviceData.display_name, `${deviceData.ip}:${port}`)
      onClose()
    }
  }

  return (
    <Modal open={open} onClose={onClose} size="xl">
      <ModalHeader onClose={onClose} className="border-none pb-0">
        <div className="flex items-center justify-between w-full pr-8">
          <ModalTitle className="flex items-center gap-3">
            <div className={`p-3 rounded-2xl ${
              isOnline
                ? 'bg-gradient-to-br from-green-400 to-green-600'
                : 'bg-gradient-to-br from-red-400 to-red-600'
            } shadow-lg`}>
              {deviceData && (() => {
                const Icon = getDeviceIcon(deviceData.device_type)
                return <Icon className="h-8 w-8 text-white filter drop-shadow-lg" strokeWidth={2.5} />
              })()}
            </div>
            <div>
              <div className="text-xl font-bold text-gray-900 dark:text-gray-100">
                {deviceData?.display_name || 'Device Details'}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400 font-mono">
                {deviceData?.ip}
              </div>
            </div>
          </ModalTitle>
        </div>
      </ModalHeader>
      <ModalContent className="max-h-[80vh] overflow-y-auto">
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton variant="card" />
            <Skeleton variant="card" />
            <Skeleton variant="card" />
          </div>
        ) : deviceData ? (
          <div className="space-y-4">
            {/* Compact Status & Quick Actions Bar */}
            <div className={`relative overflow-hidden rounded-2xl p-5 ${
              isOnline
                ? 'bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50 dark:from-green-900/10 dark:via-emerald-900/10 dark:to-teal-900/10'
                : 'bg-gradient-to-br from-red-50 via-rose-50 to-pink-50 dark:from-red-900/10 dark:via-rose-900/10 dark:to-pink-900/10'
            }`}>
              {/* Subtle background pattern */}
              <div className="absolute inset-0 opacity-5">
                <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
                  <pattern id="dots" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
                    <circle cx="2" cy="2" r="1" fill="currentColor" />
                  </pattern>
                  <rect width="100%" height="100%" fill="url(#dots)" />
                </svg>
              </div>

              <div className="relative flex items-center justify-between">
                {/* Status Info */}
                <div className="flex items-center gap-4">
                  <div className={`p-2.5 rounded-xl ${isOnline ? 'bg-green-500/20' : 'bg-red-500/20'} backdrop-blur-sm`}>
                    {isOnline ? (
                      <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
                    ) : (
                      <XCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
                    )}
                  </div>
                  <div>
                    <div className={`text-lg font-bold ${isOnline ? 'text-green-900 dark:text-green-100' : 'text-red-900 dark:text-red-100'}`}>
                      {statusText}
                    </div>
                    <div className={`text-sm ${isOnline ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'}`}>
                      {isOnline ? 'Responding normally' : 'Not responding'}
                    </div>
                  </div>
                </div>

                {/* Quick Actions - Compact */}
                <div className="flex items-center gap-2">
                  {onOpenSSH && (
                    <Button
                      onClick={handleSSH}
                      size="sm"
                      className="bg-ward-green/10 hover:bg-ward-green hover:text-white text-ward-green border-ward-green/20 transition-all"
                    >
                      <Terminal className="h-4 w-4 mr-1.5" />
                      SSH
                    </Button>
                  )}
                  <Button
                    onClick={openWebUI}
                    size="sm"
                    variant="outline"
                    className="hover:bg-blue-500 hover:text-white hover:border-blue-500 transition-all"
                  >
                    <Globe className="h-4 w-4 mr-1.5" />
                    Web
                  </Button>
                  <Button
                    onClick={copyIP}
                    size="sm"
                    variant="outline"
                    className="hover:bg-purple-500 hover:text-white hover:border-purple-500 transition-all"
                  >
                    <Copy className="h-4 w-4 mr-1.5" />
                    {copiedIP ? 'Copied!' : 'IP'}
                  </Button>
                  <Button
                    onClick={handlePing}
                    size="sm"
                    variant="outline"
                    disabled={isPinging}
                    className="hover:bg-emerald-500 hover:text-white hover:border-emerald-500 transition-all disabled:opacity-50"
                  >
                    <Activity className={`h-4 w-4 mr-1.5 ${isPinging ? 'animate-pulse' : ''}`} />
                    {isPinging ? 'Pinging...' : 'Ping'}
                  </Button>
                  <Button
                    onClick={handleRefresh}
                    size="sm"
                    variant="outline"
                    className="hover:bg-gray-500 hover:text-white hover:border-gray-500 transition-all"
                  >
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>

            {/* Secondary Actions - Compact Pills */}
            <div className="flex flex-wrap gap-2 text-xs">
              <button
                onClick={() => window.location.href = `/devices?branch=${deviceData.branch}`}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition-all"
              >
                <MapPin className="h-3.5 w-3.5" />
                {deviceData.branch}
              </button>
              {(deviceData.device_type?.toLowerCase().includes('router') ||
                deviceData.device_type?.toLowerCase().includes('switch')) && (
                <button
                  onClick={() => {
                    window.location.href = `/topology?deviceId=${deviceData.hostid}&deviceName=${encodeURIComponent(deviceData.display_name)}`
                  }}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-blue-100 dark:bg-blue-900/20 hover:bg-blue-200 dark:hover:bg-blue-900/30 text-blue-700 dark:text-blue-300 transition-all"
                >
                  <Network className="h-3.5 w-3.5" />
                  Topology
                </button>
              )}
              <button
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-orange-100 dark:bg-orange-900/20 hover:bg-orange-200 dark:hover:bg-orange-900/30 text-orange-700 dark:text-orange-300 transition-all"
              >
                <Wrench className="h-3.5 w-3.5" />
                Maintain Mode
              </button>
            </div>

            {/* Status History */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold flex items-center gap-2 text-gray-900 dark:text-gray-100">
                  <Activity className="h-5 w-5 text-ward-green" />
                  Status History
                </h3>
                <div className="flex gap-2 flex-wrap">
                  <Button
                    size="sm"
                    variant={timeRange === '30m' ? 'primary' : 'outline'}
                    onClick={() => setTimeRange('30m')}
                    className={timeRange === '30m' ? 'bg-ward-green hover:bg-ward-green-dark' : ''}
                  >
                    30m
                  </Button>
                  <Button
                    size="sm"
                    variant={timeRange === '1h' ? 'primary' : 'outline'}
                    onClick={() => setTimeRange('1h')}
                    className={timeRange === '1h' ? 'bg-ward-green hover:bg-ward-green-dark' : ''}
                  >
                    1h
                  </Button>
                  <Button
                    size="sm"
                    variant={timeRange === '3h' ? 'primary' : 'outline'}
                    onClick={() => setTimeRange('3h')}
                    className={timeRange === '3h' ? 'bg-ward-green hover:bg-ward-green-dark' : ''}
                  >
                    3h
                  </Button>
                  <Button
                    size="sm"
                    variant={timeRange === '6h' ? 'primary' : 'outline'}
                    onClick={() => setTimeRange('6h')}
                    className={timeRange === '6h' ? 'bg-ward-green hover:bg-ward-green-dark' : ''}
                  >
                    6h
                  </Button>
                  <Button
                    size="sm"
                    variant={timeRange === '12h' ? 'primary' : 'outline'}
                    onClick={() => setTimeRange('12h')}
                    className={timeRange === '12h' ? 'bg-ward-green hover:bg-ward-green-dark' : ''}
                  >
                    12h
                  </Button>
                  <Button
                    size="sm"
                    variant={timeRange === '24h' ? 'primary' : 'outline'}
                    onClick={() => setTimeRange('24h')}
                    className={timeRange === '24h' ? 'bg-ward-green hover:bg-ward-green-dark' : ''}
                  >
                    24h
                  </Button>
                  <Button
                    size="sm"
                    variant={timeRange === '7d' ? 'primary' : 'outline'}
                    onClick={() => setTimeRange('7d')}
                    className={timeRange === '7d' ? 'bg-ward-green hover:bg-ward-green-dark' : ''}
                  >
                    7d
                  </Button>
                  <Button
                    size="sm"
                    variant={timeRange === '30d' ? 'primary' : 'outline'}
                    onClick={() => setTimeRange('30d')}
                    className={timeRange === '30d' ? 'bg-ward-green hover:bg-ward-green-dark' : ''}
                  >
                    30d
                  </Button>
                </div>
              </div>

              {/* Modern Stats Cards with Gradients */}
              <div className="grid grid-cols-3 gap-3 mb-4">
                {/* Uptime Card */}
                <div className={`relative overflow-hidden rounded-2xl p-4 ${
                  parseFloat(uptimeStats.uptime as string) > 99
                    ? 'bg-gradient-to-br from-green-50 to-emerald-100 dark:from-green-900/20 dark:to-emerald-900/30'
                    : parseFloat(uptimeStats.uptime as string) > 95
                    ? 'bg-gradient-to-br from-yellow-50 to-orange-100 dark:from-yellow-900/20 dark:to-orange-900/30'
                    : 'bg-gradient-to-br from-red-50 to-rose-100 dark:from-red-900/20 dark:to-rose-900/30'
                }`}>
                  <div className="relative z-10">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wider">Uptime</span>
                      <Activity className={`h-4 w-4 ${
                        parseFloat(uptimeStats.uptime as string) > 99 ? 'text-green-600' :
                        parseFloat(uptimeStats.uptime as string) > 95 ? 'text-yellow-600' :
                        'text-red-600'
                      }`} />
                    </div>
                    <div className={`text-3xl font-black ${
                      parseFloat(uptimeStats.uptime as string) > 99 ? 'text-green-700 dark:text-green-400' :
                      parseFloat(uptimeStats.uptime as string) > 95 ? 'text-yellow-700 dark:text-yellow-400' :
                      'text-red-700 dark:text-red-400'
                    }`}>
                      {uptimeStats.uptime}%
                    </div>
                  </div>
                  {/* Decorative circle */}
                  <div className={`absolute -right-6 -bottom-6 w-24 h-24 rounded-full ${
                    parseFloat(uptimeStats.uptime as string) > 99 ? 'bg-green-200/30' :
                    parseFloat(uptimeStats.uptime as string) > 95 ? 'bg-yellow-200/30' :
                    'bg-red-200/30'
                  }`} />
                </div>

                {/* Incidents Card */}
                <div className="relative overflow-hidden rounded-2xl p-4 bg-gradient-to-br from-red-50 to-pink-100 dark:from-red-900/20 dark:to-pink-900/30">
                  <div className="relative z-10">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wider">Incidents</span>
                      <AlertTriangle className="h-4 w-4 text-red-600" />
                    </div>
                    <div className="text-3xl font-black text-red-700 dark:text-red-400">
                      {uptimeStats.incidents}
                    </div>
                  </div>
                  <div className="absolute -right-6 -bottom-6 w-24 h-24 rounded-full bg-red-200/30" />
                </div>

                {/* MTTR Card */}
                <div className="relative overflow-hidden rounded-2xl p-4 bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-blue-900/20 dark:to-indigo-900/30">
                  <div className="relative z-10">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wider">MTTR</span>
                      <Clock className="h-4 w-4 text-blue-600" />
                    </div>
                    <div className="text-3xl font-black text-blue-700 dark:text-blue-400">
                      {uptimeStats.mttr}
                    </div>
                  </div>
                  <div className="absolute -right-6 -bottom-6 w-24 h-24 rounded-full bg-blue-200/30" />
                </div>
              </div>

              {historyLoading ? (
                <div className="bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm rounded-2xl p-8 border border-gray-200/50 dark:border-gray-700/50 mb-4">
                  <div className="text-center text-gray-500">Loading history data...</div>
                </div>
              ) : statusHistory.length === 0 ? (
                <div className="bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm rounded-2xl p-8 border border-gray-200/50 dark:border-gray-700/50 mb-4">
                  <div className="text-center text-gray-500">No history data available for this time range</div>
                </div>
              ) : (
                <>
                  <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-md rounded-2xl p-5 border border-gray-200/50 dark:border-gray-700/50 mb-3 shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex items-center gap-2 mb-4">
                      <div className="p-1.5 rounded-lg bg-gradient-to-br from-green-400 to-emerald-500">
                        <Activity className="h-4 w-4 text-white" />
                      </div>
                      <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">
                        Availability Timeline
                      </h4>
                    </div>
                    <ResponsiveContainer width="100%" height={180}>
                      <AreaChart data={statusHistory}>
                        <defs>
                          <linearGradient id="statusGradientUp" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.8}/>
                            <stop offset="95%" stopColor="#10b981" stopOpacity={0.1}/>
                          </linearGradient>
                          <linearGradient id="statusGradientDown" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8}/>
                            <stop offset="95%" stopColor="#ef4444" stopOpacity={0.1}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.1} />
                        <XAxis
                          dataKey="time"
                          stroke="#6b7280"
                          tick={{ fill: '#6b7280', fontSize: 11 }}
                          tickFormatter={(value, index) => {
                            // Show fewer labels based on data length
                            const skipInterval = Math.max(1, Math.floor(statusHistory.length / 12))
                            if (index % skipInterval !== 0) return ''
                            return value
                          }}
                        />
                        <YAxis
                          stroke="#6b7280"
                          tick={{ fill: '#6b7280', fontSize: 11 }}
                          domain={[0, 1]}
                          ticks={[0, 1]}
                          tickFormatter={(value) => value === 1 ? 'Up' : 'Down'}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#1f2937',
                            border: '1px solid #374151',
                            borderRadius: '8px',
                            color: '#f3f4f6',
                            fontSize: '12px'
                          }}
                          formatter={(value: any, name: string) => {
                            if (name === 'status') {
                              return [value === 1 ? 'Up' : 'Down', 'Status']
                            }
                            return [value, name]
                          }}
                          labelFormatter={(label) => `Time: ${label}`}
                        />
                        <ReferenceLine y={0.5} stroke="#6b7280" strokeDasharray="3 3" />
                        <Area
                          type="stepAfter"
                          dataKey="status"
                          stroke={isOnline ? "#10b981" : "#ef4444"}
                          strokeWidth={2}
                          fill={isOnline ? "url(#statusGradientUp)" : "url(#statusGradientDown)"}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </>
              )}

              {!historyLoading && statusHistory.length > 0 && (
                <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-md rounded-2xl p-5 border border-gray-200/50 dark:border-gray-700/50 mb-3 shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="p-1.5 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-500">
                      <Clock className="h-4 w-4 text-white" />
                    </div>
                    <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">
                      Response Time (ms)
                    </h4>
                  </div>
                  <ResponsiveContainer width="100%" height={180}>
                    <AreaChart data={statusHistory}>
                      <defs>
                        <linearGradient id="responseGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#5EBBA8" stopOpacity={0.8}/>
                          <stop offset="95%" stopColor="#5EBBA8" stopOpacity={0.1}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.1} />
                      <XAxis
                        dataKey="time"
                        stroke="#6b7280"
                        tick={{ fill: '#6b7280', fontSize: 11 }}
                        tickFormatter={(value, index) => {
                          const skipInterval = Math.max(1, Math.floor(statusHistory.length / 12))
                          if (index % skipInterval !== 0) return ''
                          return value
                        }}
                      />
                      <YAxis
                        stroke="#6b7280"
                        tick={{ fill: '#6b7280', fontSize: 11 }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1f2937',
                          border: '1px solid #374151',
                          borderRadius: '8px',
                          color: '#f3f4f6',
                          fontSize: '12px'
                        }}
                        formatter={(value: any) => {
                          if (typeof value === 'number') {
                            return [`${value.toFixed(2)} ms`, 'Response Time']
                          }
                          return ['0 ms', 'Response Time']
                        }}
                        labelFormatter={(label) => `Time: ${label}`}
                      />
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
              )}
            </div>

            {/* Device Information */}
            <div>
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-gray-100">
                <Info className="h-5 w-5 text-ward-green" />
                Device Information
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <InfoRow label="Branch Location" value={deviceData.branch} />
                <InfoRow label="Region" value={deviceData.region} />
                <InfoRow label="IP Address" value={deviceData.ip} />
                <InfoRow label="Device Type" value={deviceData.device_type} />
                <InfoRow label="Hostname" value={deviceData.hostname} />
                <InfoRow label="Vendor" value={deviceData.vendor || 'Not set'} />
                <InfoRow label="Model" value={deviceData.model || 'Not set'} />
                <InfoRow label="Location" value={deviceData.location || 'Not set'} />
                <InfoRow label="SSH Port" value={deviceData.ssh_port?.toString() || '22'} />
                <InfoRow label="SSH Username" value={deviceData.ssh_username || 'Not set'} />
                <InfoRow label="Available" value={deviceData.available} />
              </div>
            </div>

            {/* Alert History Timeline - Modern */}
            <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <div className="p-1.5 rounded-lg bg-gradient-to-br from-orange-400 to-red-500">
                  <AlertTriangle className="h-4 w-4 text-white" />
                </div>
                <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">
                  Alert History
                </h4>
              </div>

              {alertsLoading ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">Loading alert history...</div>
              ) : alertsData?.data?.alerts && alertsData.data.alerts.length > 0 ? (
                <div className="space-y-3">
                  {alertsData.data.alerts.map((alert: any) => {
                    const triggeredAt = new Date(alert.triggered_at)
                    const resolvedAt = alert.resolved_at ? new Date(alert.resolved_at) : null
                    const isActive = !alert.resolved_at
                    const duration = alert.duration_seconds
                      ? formatDuration(alert.duration_seconds * 1000)
                      : isActive
                        ? formatDuration(Date.now() - triggeredAt.getTime())
                        : 'N/A'

                    return (
                      <div
                        key={alert.id}
                        className={`rounded-xl p-4 border transition-all hover:shadow-lg ${
                          isActive
                            ? 'bg-red-50 dark:bg-red-950/50 border-red-300 dark:border-red-800 shadow-md'
                            : 'bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <Badge
                                variant={
                                  alert.severity === 'CRITICAL' ? 'danger' :
                                  alert.severity === 'HIGH' ? 'warning' :
                                  alert.severity === 'WARNING' ? 'warning' :
                                  'default'
                                }
                              >
                                {alert.severity}
                              </Badge>
                              {isActive && (
                                <Badge variant="danger">
                                  <div className="flex items-center gap-1">
                                    <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                                    Active
                                  </div>
                                </Badge>
                              )}
                              {alert.acknowledged && (
                                <Badge variant="default">
                                  Acknowledged
                                </Badge>
                              )}
                            </div>
                            <p className="text-gray-900 dark:text-gray-100 font-medium mb-1">
                              {alert.rule_name}
                            </p>
                            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                              {alert.message}
                            </p>
                            <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                              <span className="flex items-center gap-1">
                                <Clock className="h-4 w-4" />
                                Started: {triggeredAt.toLocaleString()}
                              </span>
                              {resolvedAt && (
                                <span className="flex items-center gap-1">
                                  <CheckCircle className="h-4 w-4 text-green-600" />
                                  Resolved: {resolvedAt.toLocaleString()}
                                </span>
                              )}
                              <span className="flex items-center gap-1">
                                <Activity className="h-4 w-4" />
                                Duration: {duration}
                              </span>
                            </div>
                            {alert.acknowledged_by && (
                              <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                                Acknowledged by {alert.acknowledged_by} at {new Date(alert.acknowledged_at).toLocaleString()}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="bg-white dark:bg-gray-800 rounded-lg p-8 border border-gray-200 dark:border-gray-700">
                  <div className="text-center">
                    <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-3" />
                    <p className="text-gray-500">No alerts recorded for this device</p>
                    <p className="text-sm text-gray-400 mt-1">This device has a clean alert history</p>
                  </div>
                </div>
              )}
            </div>

            {/* Active Problems */}
            {deviceData.triggers && deviceData.triggers.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-gray-100">
                  <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
                  Active Problems ({deviceData.triggers.length})
                </h3>
                <div className="space-y-3">
                  {deviceData.triggers.map((trigger: any, index: number) => {
                    const startTime = parseInt(trigger.lastchange) * 1000
                    const duration = formatDuration(Date.now() - startTime)
                    return (
                      <div
                        key={index}
                        className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow bg-white dark:bg-gray-800"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <Badge variant={getSeverityVariant(parseInt(trigger.priority))}>
                                {getSeverityName(parseInt(trigger.priority))}
                              </Badge>
                            </div>
                            <p className="text-gray-900 dark:text-gray-100 font-medium">{trigger.description}</p>
                            <div className="flex items-center gap-4 mt-2 text-sm text-gray-600 dark:text-gray-400">
                              <span className="flex items-center gap-1">
                                <Clock className="h-4 w-4" />
                                {new Date(startTime).toLocaleString()}
                              </span>
                              <span className="flex items-center gap-1">
                                <Activity className="h-4 w-4" />
                                {duration}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-12">
            <AlertTriangle className="h-16 w-16 text-red-500 mx-auto mb-4" />
            <p className="text-gray-900 font-medium">Failed to load device information</p>
          </div>
        )}
      </ModalContent>
    </Modal>
  )
}

function InfoRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-gray-100 dark:border-gray-700">
      <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
      <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{value}</span>
    </div>
  )
}
