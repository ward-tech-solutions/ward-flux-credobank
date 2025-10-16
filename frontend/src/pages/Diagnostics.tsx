import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { diagnosticsAPI } from '@/services/api'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Badge from '@/components/ui/Badge'
import Select from '@/components/ui/Select'
import { LoadingSpinner } from '@/components/ui/Loading'
import {
  Activity,
  Terminal,
  Network,
  Globe,
  Server,
  MapPin,
  TrendingUp,
  History,
  Gauge,
  AlertTriangle,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { MapContainer, TileLayer, Polyline, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import clsx from 'clsx'

const DefaultIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
})

L.Marker.prototype.options.icon = DefaultIcon

const GEORGIA_CENTER: [number, number] = [42.3154, 43.3569]

type DiagnosticTool = 'ping' | 'traceroute' | 'mtr' | 'dns' | 'portscan'

type PingResult = {
  device_ip: string
  device_name?: string
  is_reachable: boolean
  packets_sent: number
  packets_received: number
  packet_loss_percent: number
  min_rtt_ms?: number
  avg_rtt_ms?: number
  max_rtt_ms?: number
}

type TracerouteHop = {
  hop_number: number
  ip?: string
  hostname?: string
  latency_ms?: number
  coordinates?: {
    lat: number
    lng: number
  } | null
}

type TracerouteMap = {
  device_ip: string
  device_name: string
  timestamp: string
  hops: TracerouteHop[]
}

type DNSResult = {
  hostname?: string
  ip_address?: string
  all_ips?: string[]
  reverse_hostname?: string
  success: boolean
  error?: string
}

type PortScanResult = {
  ip_address: string
  ports_scanned: number
  open_ports: number
  results: Array<{
    port: number
    status: string
    is_open: boolean
  }>
}

type DiagnosticsSummary = {
  status_cards: {
    ping: {
      total: number
      success: number
      failures: number
      avg_latency: number | null
    }
    traceroute: {
      total: number
      success: number
    }
  }
  recent_pings: Array<{
    device_ip: string
    device_name: string
    avg_rtt_ms: number | null
    packet_loss_percent: number
    is_reachable: boolean
    timestamp: string
  }>
  region_latency: Array<{
    region: string
    avg_latency: number | null
    avg_packet_loss: number
    samples: number
  }>
  recent_traceroutes: Array<{
    device_ip: string
    device_name: string
    timestamp: string | null
    hop_count: number
    last_latency_ms: number | null
    region?: string | null
  }>
  timeline: Array<{
    type: string
    device_ip: string
    device_name: string
    status: string
    avg_rtt_ms?: number | null
    timestamp: string
  }>
}

type ToolOption = {
  key: DiagnosticTool
  title: string
  description: string
  icon: LucideIcon
  helper?: string
}

type HighlightMetric = {
  key: string
  title: string
  value: string
  subtext: string
  icon: LucideIcon
}

type SnapshotCard = {
  key: string
  title: string
  primary: string
  badge: string
  meta: string
  icon: LucideIcon
  variant: 'success' | 'warning' | 'danger' | 'info' | 'default'
}

const latencyColor = (value?: number | null) => {
  if (value === undefined || value === null) return 'text-gray-400'
  if (value < 50) return 'text-ward-green'
  if (value < 120) return 'text-yellow-600'
  return 'text-red-600'
}

const TOOL_OPTIONS: ToolOption[] = [
  {
    key: 'ping',
    title: 'Ping',
    description: 'Reachability & latency checks',
    icon: Activity,
    helper: 'Ideal for quick availability validation.',
  },
  {
    key: 'traceroute',
    title: 'Traceroute',
    description: 'Hop-by-hop path discovery',
    icon: Network,
    helper: 'Surface routing shifts or bottlenecks.',
  },
  {
    key: 'mtr',
    title: 'MTR',
    description: 'Traceroute + Ping combined',
    icon: Activity,
    helper: 'Shows packet loss and latency per hop.',
  },
  {
    key: 'dns',
    title: 'DNS Lookup',
    description: 'Forward and reverse resolution',
    icon: Globe,
    helper: 'Validate DNS records and delegation.',
  },
  {
    key: 'portscan',
    title: 'Port Scan',
    description: 'Service visibility snapshot',
    icon: Server,
    helper: 'Confirm exposed services or firewall rules.',
  },
]

export default function Diagnostics() {
  const [selectedTool, setSelectedTool] = useState<DiagnosticTool>('ping')
  const [targetIP, setTargetIP] = useState('')
  const [targetHostname, setTargetHostname] = useState('')
  const [ports, setPorts] = useState('22,80,443,3389,8080')
  const [loading, setLoading] = useState(false)
  const [pingResult, setPingResult] = useState<PingResult | null>(null)
  const [tracerouteResult, setTracerouteResult] = useState<TracerouteMap | null>(null)
  const [dnsResult, setDNSResult] = useState<DNSResult | null>(null)
  const [portScanResult, setPortScanResult] = useState<PortScanResult | null>(null)
  const [selectedRouteIp, setSelectedRouteIp] = useState<string>('')

  const {
    data: summaryResponse,
    isLoading: summaryLoading,
    refetch: refetchSummary,
  } = useQuery({
    queryKey: ['diagnostics-summary'],
    queryFn: () => diagnosticsAPI.summary(),
    staleTime: 30_000,
  })

  const summary: DiagnosticsSummary | undefined = summaryResponse?.data

  useEffect(() => {
    if (summary && summary.recent_traceroutes.length > 0 && !selectedRouteIp) {
      setSelectedRouteIp(summary.recent_traceroutes[0].device_ip)
    }
  }, [summary, selectedRouteIp])

  const {
    data: tracerouteMapResponse,
    isLoading: tracerouteLoading,
    refetch: refetchTracerouteMap,
  } = useQuery({
    queryKey: ['diagnostics-traceroute-map', selectedTool === 'traceroute' ? selectedRouteIp : null],
    queryFn: () => diagnosticsAPI.tracerouteMap(selectedRouteIp!),
    enabled: Boolean(selectedTool === 'traceroute' && selectedRouteIp && selectedRouteIp.trim().length > 0),
    retry: false, // Don't retry on 404 - traceroute may not exist yet
  })

  const tracerouteMap: TracerouteMap | undefined = tracerouteMapResponse?.data

  const traceroutePositions = useMemo(() => {
    if (!tracerouteMap) return [] as [number, number][]
    return tracerouteMap.hops
      .filter(hop => hop.coordinates)
      .map(hop => [hop.coordinates!.lat, hop.coordinates!.lng] as [number, number])
  }, [tracerouteMap])

  const mapCenter = traceroutePositions.length > 0 ? traceroutePositions[0] : GEORGIA_CENTER

  const pingStats = summary?.status_cards?.ping
  const tracerouteStats = summary?.status_cards?.traceroute

  const pingSuccessRate = useMemo(() => {
    if (!pingStats || pingStats.total === 0) return null
    return Math.round((pingStats.success / pingStats.total) * 100)
  }, [pingStats])

  const tracerouteCoverage = useMemo(() => {
    if (!tracerouteStats || tracerouteStats.total === 0) return null
    return Math.round((tracerouteStats.success / tracerouteStats.total) * 100)
  }, [tracerouteStats])

  const lastTimelineEntry = summary?.timeline?.[0]
  const lastRunTimestamp = lastTimelineEntry ? new Date(lastTimelineEntry.timestamp) : null

  const unreachableCount = useMemo(() => {
    if (!summary?.recent_pings) return 0
    return summary.recent_pings.reduce((count, entry) => count + (entry.is_reachable ? 0 : 1), 0)
  }, [summary])

  const worstRegion = useMemo(() => {
    if (!summary?.region_latency || summary.region_latency.length === 0) return null
    return [...summary.region_latency]
      .filter(region => region.avg_latency !== null)
      .sort((a, b) => (b.avg_latency ?? 0) - (a.avg_latency ?? 0))[0] ?? null
  }, [summary])

  const maxRegionSamples = useMemo(() => {
    if (!summary?.region_latency || summary.region_latency.length === 0) return 1
    return summary.region_latency.reduce((max, region) => Math.max(max, region.samples), 1)
  }, [summary])

  const highlightMetrics = useMemo<HighlightMetric[]>(() => {
    return [
      {
        key: 'ping',
        title: 'Ping Success',
        value: pingSuccessRate !== null ? `${pingSuccessRate}%` : 'No checks yet',
        subtext:
          pingStats?.avg_latency !== null && pingStats?.avg_latency !== undefined
            ? `Avg latency ${Math.round(pingStats.avg_latency ?? 0)} ms`
            : 'Latency data pending',
        icon: Activity,
      },
      {
        key: 'traceroute',
        title: 'Traceroute Coverage',
        value: tracerouteCoverage !== null ? `${tracerouteCoverage}%` : 'No traces yet',
        subtext: tracerouteStats
          ? `${tracerouteStats.success} of ${tracerouteStats.total} succeeded`
          : 'Run traceroute diagnostics',
        icon: Network,
      },
      {
        key: 'timeline',
        title: 'Last Activity',
        value: lastTimelineEntry
          ? `${lastTimelineEntry.type.toUpperCase()} • ${lastTimelineEntry.status === 'success' ? 'Success' : 'Issue'}`
          : 'Awaiting diagnostics',
        subtext: lastRunTimestamp
          ? `Ran ${lastRunTimestamp.toLocaleString()}`
          : 'No timeline entries yet',
        icon: History,
      },
    ]
  }, [pingSuccessRate, pingStats, tracerouteCoverage, tracerouteStats, lastTimelineEntry, lastRunTimestamp])

  const snapshotCards = useMemo<SnapshotCard[]>(() => {
    return [
      {
        key: 'ping',
        title: 'Ping Checks',
        primary: pingStats ? `${pingStats.success}/${pingStats.total}` : 'No data',
        badge:
          pingSuccessRate !== null
            ? `${pingSuccessRate}% success`
            : 'Awaiting first run',
        meta: pingStats
          ? `${pingStats.failures} failures recorded`
          : 'Trigger a ping diagnostic to populate this card.',
        icon: Gauge,
        variant:
          pingSuccessRate === null
            ? 'info'
            : pingSuccessRate < 70
              ? 'danger'
              : pingSuccessRate < 85
                ? 'warning'
                : 'success',
      },
      {
        key: 'traceroute',
        title: 'Traceroute Coverage',
        primary: tracerouteStats ? `${tracerouteStats.success}/${tracerouteStats.total}` : 'No data',
        badge:
          tracerouteCoverage !== null
            ? `${tracerouteCoverage}% success`
            : 'Awaiting first run',
        meta: tracerouteStats
          ? `Latest hop count ${summary?.recent_traceroutes?.[0]?.hop_count ?? '—'}`
          : 'Run traceroute diagnostics to surface routing paths.',
        icon: MapPin,
        variant:
          tracerouteCoverage === null
            ? 'info'
            : tracerouteCoverage < 70
              ? 'warning'
              : 'success',
      },
      {
        key: 'availability',
        title: 'Unreachable Devices',
        primary: `${unreachableCount}`,
        badge: `${summary?.recent_pings?.length ?? 0} observed`,
        meta:
          unreachableCount > 0
            ? 'Investigate impacted sites.'
            : 'All sampled devices reachable.',
        icon: AlertTriangle,
        variant: unreachableCount > 0 ? 'danger' : 'success',
      },
      {
        key: 'regions',
        title: 'Highest Latency Region',
        primary: worstRegion ? worstRegion.region : 'No samples',
        badge:
          worstRegion && worstRegion.avg_latency !== null
            ? `${Math.round(worstRegion.avg_latency)} ms`
            : 'n/a',
        meta: worstRegion
          ? `${worstRegion.samples} samples • ${worstRegion.avg_packet_loss.toFixed(1)}% loss`
          : 'Run diagnostics to populate regional metrics.',
        icon: TrendingUp,
        variant: 'info',
      },
    ]
  }, [pingStats, pingSuccessRate, tracerouteStats, tracerouteCoverage, summary, unreachableCount, worstRegion])

  const tracerouteOptions = useMemo(() => {
    const options = summary?.recent_traceroutes ?? []
    if (options.length === 0) {
      return [{ value: '', label: 'No recorded paths yet' }]
    }
    return [
      { value: '', label: 'Select recorded path' },
      ...options.map(route => ({
        value: route.device_ip,
        label: route.device_name || route.device_ip,
      })),
    ]
  }, [summary])

  const selectedToolConfig = TOOL_OPTIONS.find(tool => tool.key === selectedTool)

  const handlePing = async () => {
    if (!targetIP) return
    setLoading(true)
    try {
      const response = await diagnosticsAPI.ping(targetIP)
      setPingResult(response.data)
      await refetchSummary()
    } catch (error) {
      console.error('Ping failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleTraceroute = async () => {
    if (!targetIP) return
    setLoading(true)
    try {
      const response = await diagnosticsAPI.traceroute(targetIP)
      setTracerouteResult(response.data)
      setSelectedRouteIp(targetIP)
      await Promise.all([refetchSummary(), refetchTracerouteMap()])
    } catch (error) {
      console.error('Traceroute failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleMTR = async () => {
    if (!targetIP) return
    setLoading(true)
    try {
      const response = await diagnosticsAPI.mtr(targetIP, 10)
      setTracerouteResult(response.data)
      setSelectedRouteIp(targetIP)
      await refetchSummary()
    } catch (error) {
      console.error('MTR failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDNSLookup = async () => {
    if (!targetHostname) return
    setLoading(true)
    try {
      const response = await diagnosticsAPI.dnsLookup(targetHostname)
      setDNSResult(response.data)
    } catch (error) {
      console.error('DNS lookup failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const handlePortScan = async () => {
    if (!targetIP) return
    setLoading(true)
    try {
      const response = await diagnosticsAPI.portScan(targetIP, ports)
      setPortScanResult(response.data)
    } catch (error) {
      console.error('Port scan failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleRunDiagnostic = () => {
    switch (selectedTool) {
      case 'ping':
        handlePing()
        break
      case 'traceroute':
        handleTraceroute()
        break
      case 'mtr':
        handleMTR()
        break
      case 'dns':
        handleDNSLookup()
        break
      case 'portscan':
        handlePortScan()
        break
    }
  }

  const overallStatusVariant: SnapshotCard['variant'] =
    pingSuccessRate === null
      ? 'info'
      : pingSuccessRate < 70
        ? 'danger'
        : pingSuccessRate < 85
          ? 'warning'
          : 'success'

  const overallStatusText =
    pingSuccessRate === null
      ? 'Awaiting Checks'
      : pingSuccessRate >= 90
        ? 'Healthy'
        : pingSuccessRate >= 75
          ? 'Watch'
          : 'At Risk'

  return (
    <div className="space-y-6">
      {/* Hero Section */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-ward-green via-emerald-600 to-teal-700 p-8 shadow-2xl">
        {/* Decorative elements */}
        <div className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-white/10 blur-3xl" aria-hidden="true" />
        <div className="pointer-events-none absolute -bottom-16 -left-16 h-48 w-48 rounded-full bg-emerald-400/20 blur-3xl" aria-hidden="true" />

        <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-3 rounded-xl bg-white/20 backdrop-blur-sm">
                <Terminal className="h-7 w-7 text-white" />
              </div>
              <h1 className="text-3xl font-bold text-white">Network Diagnostics</h1>
            </div>
            <p className="text-emerald-50 text-base max-w-2xl leading-relaxed">
              Monitor reachability, visualize routing paths, and launch targeted checks without leaving the command center. Real-time insights into your network infrastructure.
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <Badge
              variant={overallStatusVariant}
              size="sm"
              dot
              className="bg-white/20 backdrop-blur-sm border-white/30 text-white text-base px-4 py-2"
            >
              {overallStatusText}
            </Badge>
            <Button
              onClick={handleRunDiagnostic}
              loading={loading}
              icon={<Terminal className="h-4 w-4" />}
              className="bg-white text-ward-green hover:bg-gray-50 font-semibold shadow-lg"
            >
              Run {selectedToolConfig?.title ?? 'Diagnostic'}
            </Button>
          </div>
        </div>

        {/* Metrics Cards */}
        <div className="relative z-10 mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {highlightMetrics.map(metric => {
            const Icon = metric.icon
            return (
              <div
                key={metric.key}
                className="group rounded-xl border border-white/20 bg-white/10 backdrop-blur-md p-5 shadow-lg transition-all duration-300 hover:bg-white/15 hover:shadow-xl hover:scale-105"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="rounded-lg bg-white/20 p-2">
                    <Icon className="h-5 w-5 text-white" />
                  </div>
                  <h3 className="text-sm font-semibold text-emerald-50 uppercase tracking-wide">{metric.title}</h3>
                </div>
                <p className="text-2xl font-bold text-white mb-1">{metric.value}</p>
                <p className="text-sm text-emerald-100">{metric.subtext}</p>
              </div>
            )
          })}
        </div>
      </div>

      {/* Health Snapshot Section */}
      <div className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-ward-green/10 dark:bg-ward-green/20">
              <Gauge className="h-5 w-5 text-ward-green" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Health Snapshot</h2>
          </div>
          <Badge variant="info" size="sm" className="bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 border-blue-200 dark:border-blue-800">
            Live diagnostics data
          </Badge>
        </div>

        {summaryLoading ? (
          <Card className="border-gray-200 dark:border-gray-700">
            <CardContent className="flex items-center justify-center py-16">
              <div className="text-center">
                <LoadingSpinner />
                <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">Loading diagnostics data...</p>
              </div>
            </CardContent>
          </Card>
        ) : summary ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            {snapshotCards.map(card => {
              const Icon = card.icon
              const variantColors = {
                success: 'from-emerald-500/10 to-green-500/10 dark:from-emerald-500/20 dark:to-green-500/20 border-emerald-200 dark:border-emerald-800',
                warning: 'from-yellow-500/10 to-orange-500/10 dark:from-yellow-500/20 dark:to-orange-500/20 border-yellow-200 dark:border-yellow-800',
                danger: 'from-red-500/10 to-rose-500/10 dark:from-red-500/20 dark:to-rose-500/20 border-red-200 dark:border-red-800',
                info: 'from-blue-500/10 to-indigo-500/10 dark:from-blue-500/20 dark:to-indigo-500/20 border-blue-200 dark:border-blue-800',
                default: 'from-gray-500/10 to-slate-500/10 dark:from-gray-500/20 dark:to-slate-500/20 border-gray-200 dark:border-gray-700',
              }
              return (
                <div
                  key={card.key}
                  className={clsx(
                    'group relative overflow-hidden rounded-2xl border bg-gradient-to-br p-6 shadow-lg transition-all duration-300 hover:shadow-2xl hover:scale-105',
                    variantColors[card.variant]
                  )}
                >
                  <div className="relative z-10">
                    <div className="flex items-start justify-between mb-4">
                      <div className="p-3 rounded-xl bg-white/50 dark:bg-gray-900/50 backdrop-blur-sm">
                        <Icon className="h-6 w-6 text-ward-green" />
                      </div>
                      <Badge variant={card.variant} size="sm" dot className="shadow-sm">
                        {card.badge}
                      </Badge>
                    </div>
                    <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide mb-2">
                      {card.title}
                    </p>
                    <p className="text-4xl font-bold text-gray-900 dark:text-white mb-3">{card.primary}</p>
                    <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{card.meta}</p>
                  </div>
                  {/* Decorative corner accent */}
                  <div className="absolute -right-8 -bottom-8 h-24 w-24 rounded-full bg-ward-green/10 dark:bg-ward-green/20 blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                </div>
              )
            })}
          </div>
        ) : (
          <Card className="border-gray-200 dark:border-gray-700">
            <CardContent className="py-16 text-center">
              <div className="flex flex-col items-center gap-4">
                <div className="p-4 rounded-full bg-gray-100 dark:bg-gray-800">
                  <Activity className="h-8 w-8 text-gray-400 dark:text-gray-500" />
                </div>
                <div>
                  <p className="text-base font-semibold text-gray-900 dark:text-white mb-1">No diagnostics data yet</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Run a diagnostic to populate this dashboard</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Traceroute Map & Regional Latency */}
      <div className="grid grid-cols-1 gap-6 2xl:grid-cols-3">
        <Card className="2xl:col-span-2 border-gray-200 dark:border-gray-700 shadow-lg">
          <CardHeader className="border-b border-gray-100 dark:border-gray-800 bg-gradient-to-r from-gray-50 to-white dark:from-gray-900 dark:to-gray-800">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-ward-green/10 dark:bg-ward-green/20">
                  <MapPin className="h-5 w-5 text-ward-green" />
                </div>
                <div>
                  <CardTitle className="text-xl">Traceroute Map</CardTitle>
                  <CardDescription className="text-xs">Visualize network path latency for recent traces</CardDescription>
                </div>
              </div>
              <div className="flex w-full flex-col gap-3 sm:flex-row sm:items-center lg:w-auto">
                <Select
                  value={selectedRouteIp}
                  onChange={event => setSelectedRouteIp(event.target.value)}
                  options={tracerouteOptions}
                  fullWidth
                  disabled={(summary?.recent_traceroutes?.length ?? 0) === 0}
                  className="min-w-[200px]"
                />
                <Badge variant="info" size="sm" dot className="whitespace-nowrap">
                  {summary?.recent_traceroutes?.length ?? 0} saved paths
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="h-[28rem] p-0">
            {tracerouteLoading ? (
              <div className="flex h-full items-center justify-center">
                <div className="text-center">
                  <LoadingSpinner />
                  <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">Loading traceroute data...</p>
                </div>
              </div>
            ) : tracerouteMap && traceroutePositions.length > 0 ? (
              <MapContainer
                center={mapCenter}
                zoom={7}
                className="h-full w-full"
              >
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution="&copy; OpenStreetMap contributors"
                />
                <Polyline positions={traceroutePositions} color="#10b981" weight={4} opacity={0.85} />
                {tracerouteMap.hops.map(hop =>
                  hop.coordinates ? (
                    <Marker key={hop.hop_number} position={[hop.coordinates.lat, hop.coordinates.lng]}>
                      <Popup>
                        <div className="space-y-1 text-sm">
                          <p className="font-semibold text-gray-900 dark:text-gray-100">Hop {hop.hop_number}</p>
                          {hop.hostname && <p className="text-sm text-gray-500">{hop.hostname}</p>}
                          {hop.ip && <p className="text-xs text-gray-400">{hop.ip}</p>}
                          {typeof hop.latency_ms === 'number' && (
                            <p className="text-xs font-medium text-ward-green">{hop.latency_ms} ms</p>
                          )}
                        </div>
                      </Popup>
                    </Marker>
                  ) : null
                )}
              </MapContainer>
            ) : (
              <div className="flex h-full flex-col items-center justify-center gap-4 bg-gray-50 dark:bg-gray-900/30">
                <div className="p-4 rounded-full bg-gray-200 dark:bg-gray-800">
                  <MapPin className="h-10 w-10 text-gray-400 dark:text-gray-600" />
                </div>
                <div className="text-center">
                  <p className="font-semibold text-gray-700 dark:text-gray-300">No traceroute data available</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Run a traceroute to visualize network paths</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-700 shadow-lg">
          <CardHeader className="border-b border-gray-100 dark:border-gray-800 bg-gradient-to-r from-gray-50 to-white dark:from-gray-900 dark:to-gray-800">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-ward-green/10 dark:bg-ward-green/20">
                <TrendingUp className="h-5 w-5 text-ward-green" />
              </div>
              <div>
                <CardTitle className="text-xl">Regional Latency</CardTitle>
                <CardDescription className="text-xs">Rolling window from latest diagnostics</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 max-h-[25rem] overflow-y-auto">
            {(summary?.region_latency?.length ?? 0) === 0 ? (
              <div className="py-12 text-center">
                <div className="flex flex-col items-center gap-3">
                  <div className="p-3 rounded-full bg-gray-100 dark:bg-gray-800">
                    <TrendingUp className="h-6 w-6 text-gray-400 dark:text-gray-500" />
                  </div>
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300">No regional data yet</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Run diagnostics to populate metrics</p>
                </div>
              </div>
            ) : (
              summary?.region_latency?.map(region => {
                const latencyPercentage = region.avg_latency ? Math.min((region.avg_latency / 200) * 100, 100) : 0
                const latencyClass = region.avg_latency && region.avg_latency < 50
                  ? 'bg-ward-green dark:bg-ward-green'
                  : region.avg_latency && region.avg_latency < 120
                    ? 'bg-yellow-500 dark:bg-yellow-600'
                    : 'bg-red-500 dark:bg-red-600'

                return (
                  <div
                    key={region.region}
                    className="group relative space-y-3 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900 transition-all duration-200 hover:shadow-md hover:border-ward-green/50 dark:hover:border-ward-green/50"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-gray-900 dark:text-white">{region.region}</span>
                      <Badge variant="info" size="sm" className="bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
                        {region.samples} samples
                      </Badge>
                    </div>

                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <Activity className="h-4 w-4 text-gray-400" />
                        <span className={clsx('font-bold', latencyColor(region.avg_latency))}>
                          {region.avg_latency !== null ? `${Math.round(region.avg_latency)} ms` : 'n/a'}
                        </span>
                      </div>
                      <span className="text-gray-600 dark:text-gray-400">
                        {region.avg_packet_loss.toFixed(1)}% loss
                      </span>
                    </div>

                    {/* Latency bar */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                        <span>Latency</span>
                        <span>{region.avg_latency ? `${Math.round(latencyPercentage)}%` : '—'}</span>
                      </div>
                      <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
                        <div
                          className={clsx('h-full rounded-full transition-all duration-300', latencyClass)}
                          style={{
                            width: `${Math.max(8, latencyPercentage)}%`,
                          }}
                        />
                      </div>
                    </div>

                    {/* Sample size bar */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                        <span>Sample Size</span>
                        <span>{Math.round((region.samples / maxRegionSamples) * 100)}%</span>
                      </div>
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-ward-green to-emerald-600 transition-all duration-300"
                          style={{
                            width: `${Math.max(8, Math.round((region.samples / maxRegionSamples) * 100))}%`,
                          }}
                        />
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </CardContent>
        </Card>
      </div>

      {/* Diagnostics Workbench */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2 border-gray-200 dark:border-gray-700">
          <CardHeader className="border-b border-gray-100 dark:border-gray-800 pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Terminal className="h-4 w-4 text-ward-green" />
                <CardTitle className="text-base">Diagnostics Workbench</CardTitle>
              </div>
              {selectedToolConfig?.helper && (
                <Badge variant="info" size="sm" className="text-xs">
                  {selectedToolConfig.helper}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4 p-4">
            {/* Tool Selection */}
            <div className="grid grid-cols-5 gap-2">
              {TOOL_OPTIONS.map(tool => {
                const Icon = tool.icon
                const isActive = selectedTool === tool.key
                return (
                  <button
                    key={tool.key}
                    onClick={() => setSelectedTool(tool.key)}
                    className={clsx(
                      'rounded-lg border p-3 text-left transition-all',
                      isActive
                        ? 'border-ward-green bg-ward-green/10 dark:bg-ward-green/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-ward-green/50'
                    )}
                  >
                    <Icon className={clsx(
                      'h-4 w-4 mb-1',
                      isActive ? 'text-ward-green' : 'text-gray-400'
                    )} />
                    <p className={clsx(
                      'text-xs font-semibold',
                      isActive ? 'text-ward-green' : 'text-gray-900 dark:text-white'
                    )}>
                      {tool.title}
                    </p>
                  </button>
                )
              })}
            </div>

            <div className="flex items-end gap-3">
              <div className="flex-1">
                <Input
                  label="Target IP"
                  placeholder="8.8.8.8"
                  value={targetIP}
                  onChange={event => setTargetIP(event.target.value)}
                  icon={<Server className="h-4 w-4" />}
                />
              </div>
              {selectedTool === 'dns' && (
                <div className="flex-1">
                  <Input
                    label="Hostname"
                    placeholder="router.example.com"
                    value={targetHostname}
                    onChange={event => setTargetHostname(event.target.value)}
                    icon={<Globe className="h-4 w-4" />}
                  />
                </div>
              )}
              {selectedTool === 'portscan' && (
                <div className="flex-1">
                  <Input
                    label="Ports"
                    placeholder="22,80,443"
                    value={ports}
                    onChange={event => setPorts(event.target.value)}
                    icon={<Terminal className="h-4 w-4" />}
                  />
                </div>
              )}
              <Button
                onClick={handleRunDiagnostic}
                loading={loading}
                icon={<Terminal className="h-4 w-4" />}
              >
                Run {selectedToolConfig?.title ?? 'Diagnostic'}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  void refetchSummary()
                  if (selectedTool === 'traceroute') {
                    void refetchTracerouteMap()
                  }
                }}
                icon={<TrendingUp className="h-4 w-4" />}
              >
                Refresh
              </Button>
            </div>

            {/* Results Display */}
            <div className="space-y-3">
                {selectedTool === 'ping' && pingResult && (
                  <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <Activity className={clsx(
                          'h-5 w-5',
                          pingResult.is_reachable ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
                        )} />
                        <div>
                          <p className="text-sm font-semibold text-gray-900 dark:text-white">
                            {pingResult.device_name || pingResult.device_ip}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{pingResult.device_ip}</p>
                        </div>
                      </div>
                      <Badge
                        variant={pingResult.is_reachable ? 'success' : 'danger'}
                        size="sm"
                      >
                        {pingResult.is_reachable ? 'Reachable' : 'Unreachable'}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-4 gap-3">
                      <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
                        <p className="text-[10px] font-semibold uppercase text-gray-500 dark:text-gray-400 mb-1">Packets</p>
                        <p className="text-lg font-bold text-gray-900 dark:text-white">
                          {pingResult.packets_received}/{pingResult.packets_sent}
                        </p>
                      </div>
                      <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
                        <p className="text-[10px] font-semibold uppercase text-gray-500 dark:text-gray-400 mb-1">Loss</p>
                        <p className="text-lg font-bold text-gray-900 dark:text-white">{pingResult.packet_loss_percent}%</p>
                      </div>
                      <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
                        <p className="text-[10px] font-semibold uppercase text-gray-500 dark:text-gray-400 mb-1">Avg RTT</p>
                        <p className={clsx('text-lg font-bold', latencyColor(pingResult.avg_rtt_ms))}>
                          {pingResult.avg_rtt_ms !== null && pingResult.avg_rtt_ms !== undefined
                            ? `${Math.round(pingResult.avg_rtt_ms)} ms`
                            : 'n/a'}
                        </p>
                      </div>
                      <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
                        <p className="text-[10px] font-semibold uppercase text-gray-500 dark:text-gray-400 mb-1">Min / Max</p>
                        <p className="text-lg font-bold text-gray-900 dark:text-white">
                          {pingResult.min_rtt_ms !== undefined && pingResult.max_rtt_ms !== undefined
                            ? `${pingResult.min_rtt_ms} / ${pingResult.max_rtt_ms}`
                            : 'n/a'}
                        </p>
                        <p className="text-[9px] text-gray-500 dark:text-gray-400 mt-0.5">ms</p>
                      </div>
                    </div>
                  </div>
                )}

                {selectedTool === 'traceroute' && tracerouteResult && (
                  <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <Network className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                        <div>
                          <p className="text-sm font-semibold text-gray-900 dark:text-white">
                            {tracerouteResult.device_name || tracerouteResult.device_ip}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {new Date(tracerouteResult.timestamp).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      <Badge variant="info" size="sm">
                        {tracerouteResult.hops.length} hops
                      </Badge>
                    </div>
                    <div className="max-h-64 space-y-1.5 overflow-y-auto">
                      {tracerouteResult.hops.map(hop => (
                        <div
                          key={hop.hop_number}
                          className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-3"
                        >
                          <div className="flex items-center gap-2">
                            <div className="flex h-6 w-6 items-center justify-center rounded bg-ward-green/10 dark:bg-ward-green/20 text-[10px] font-bold text-ward-green">
                              {hop.hop_number}
                            </div>
                            <div>
                              <p className="font-medium text-gray-900 dark:text-white text-xs">
                                {hop.hostname || hop.ip || 'Unknown'}
                              </p>
                              {hop.ip && hop.hostname && (
                                <p className="text-[10px] text-gray-500 dark:text-gray-400">{hop.ip}</p>
                              )}
                            </div>
                          </div>
                          <span className={clsx('text-sm font-bold', latencyColor(hop.latency_ms))}>
                            {hop.latency_ms !== undefined ? `${hop.latency_ms} ms` : '—'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {selectedTool === 'dns' && dnsResult && (
                  <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <Globe className={clsx(
                          'h-5 w-5',
                          dnsResult.success ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
                        )} />
                        <p className="text-sm font-semibold text-gray-900 dark:text-white">DNS Lookup</p>
                      </div>
                      <Badge
                        variant={dnsResult.success ? 'success' : 'danger'}
                        size="sm"
                      >
                        {dnsResult.success ? 'Resolved' : 'Failed'}
                      </Badge>
                    </div>
                    {dnsResult.success ? (
                      <div className="space-y-2">
                        <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
                          <p className="text-[10px] font-semibold uppercase text-gray-500 dark:text-gray-400 mb-1">Hostname</p>
                          <p className="text-sm font-bold text-gray-900 dark:text-white">{dnsResult.hostname}</p>
                        </div>
                        <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
                          <p className="text-[10px] font-semibold uppercase text-gray-500 dark:text-gray-400 mb-1">IP Address</p>
                          <p className="text-sm font-bold text-gray-900 dark:text-white font-mono">{dnsResult.ip_address}</p>
                        </div>
                        {dnsResult.all_ips && dnsResult.all_ips.length > 1 && (
                          <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
                            <p className="text-[10px] font-semibold uppercase text-gray-500 dark:text-gray-400 mb-1">All IP Addresses</p>
                            <div className="flex flex-wrap gap-1.5">
                              {dnsResult.all_ips.map((ip, idx) => (
                                <Badge key={idx} variant="info" size="sm" className="font-mono text-xs">
                                  {ip}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}
                        {dnsResult.reverse_hostname && (
                          <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
                            <p className="text-[10px] font-semibold uppercase text-gray-500 dark:text-gray-400 mb-1">Reverse Lookup</p>
                            <p className="text-sm font-bold text-gray-900 dark:text-white">{dnsResult.reverse_hostname}</p>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3">
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400" />
                          <p className="text-sm font-semibold text-red-900 dark:text-red-100">
                            {dnsResult.error || 'DNS lookup failed'}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {selectedTool === 'portscan' && portScanResult && (
                  <div className="rounded-2xl border-2 border-gray-200 bg-gradient-to-br from-white to-gray-50 p-6 dark:border-gray-700 dark:from-gray-900 dark:to-gray-800 shadow-lg">
                    <div className="flex items-center justify-between mb-6">
                      <div className="flex items-center gap-3">
                        <div className="p-3 rounded-xl bg-purple-100 dark:bg-purple-900/30">
                          <Server className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                        </div>
                        <div>
                          <p className="text-base font-bold text-gray-900 dark:text-white">Port Scan Results</p>
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            {portScanResult.ports_scanned} ports scanned
                          </p>
                        </div>
                      </div>
                      <Badge variant="info" size="sm" className="text-sm px-3 py-1">
                        {portScanResult.open_ports} open
                      </Badge>
                    </div>
                    <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2">
                      {portScanResult.results.map(result => (
                        <div
                          key={result.port}
                          className={clsx(
                            'group relative rounded-lg p-3 text-center font-bold transition-all duration-200',
                            result.is_open
                              ? 'bg-emerald-100 dark:bg-emerald-900/30 border-2 border-emerald-500 dark:border-emerald-600 text-emerald-700 dark:text-emerald-300 hover:shadow-lg hover:scale-110'
                              : 'bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-500 dark:text-gray-400'
                          )}
                        >
                          <span className="text-sm">{result.port}</span>
                          {result.is_open && (
                            <div className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-emerald-500 dark:bg-emerald-400 animate-pulse" />
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-700 shadow-lg">
          <CardHeader className="border-b border-gray-100 dark:border-gray-800 bg-gradient-to-r from-gray-50 to-white dark:from-gray-900 dark:to-gray-800">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-ward-green/10 dark:bg-ward-green/20">
                <Activity className="h-5 w-5 text-ward-green" />
              </div>
              <div>
                <CardTitle className="text-xl">Recent Ping Observations</CardTitle>
                <CardDescription className="text-xs">Rolling window from diagnostics summary</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 max-h-[28rem] overflow-y-auto">
            {(summary?.recent_pings?.length ?? 0) === 0 ? (
              <div className="py-12 text-center">
                <div className="flex flex-col items-center gap-3">
                  <div className="p-3 rounded-full bg-gray-100 dark:bg-gray-800">
                    <Activity className="h-6 w-6 text-gray-400 dark:text-gray-500" />
                  </div>
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300">No ping data yet</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Run ping diagnostics to see results</p>
                </div>
              </div>
            ) : (
              summary?.recent_pings?.map(result => (
                <div
                  key={`${result.device_ip}-${result.timestamp}`}
                  className="group relative rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900 transition-all duration-200 hover:shadow-md hover:border-ward-green/50 dark:hover:border-ward-green/50"
                >
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-3">
                      <div className={clsx(
                        'p-2 rounded-lg',
                        result.is_reachable
                          ? 'bg-emerald-100 dark:bg-emerald-900/30'
                          : 'bg-red-100 dark:bg-red-900/30'
                      )}>
                        <Activity className={clsx(
                          'h-4 w-4',
                          result.is_reachable
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-red-600 dark:text-red-400'
                        )} />
                      </div>
                      <div>
                        <p className="font-bold text-gray-900 dark:text-white text-sm">{result.device_name}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">{result.device_ip}</p>
                      </div>
                    </div>
                    <Badge variant={result.is_reachable ? 'success' : 'danger'} dot size="sm">
                      {result.is_reachable ? 'Up' : 'Down'}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-2">
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Latency</p>
                      <p className={clsx('text-sm font-bold', latencyColor(result.avg_rtt_ms))}>
                        {result.avg_rtt_ms ? `${Math.round(result.avg_rtt_ms)} ms` : 'n/a'}
                      </p>
                    </div>
                    <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-2">
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Packet Loss</p>
                      <p className="text-sm font-bold text-gray-900 dark:text-white">
                        {result.packet_loss_percent}%
                      </p>
                    </div>
                  </div>

                  <p className="mt-3 text-xs text-gray-400 dark:text-gray-500">
                    {new Date(result.timestamp).toLocaleString()}
                  </p>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* Diagnostics Timeline */}
      <Card className="border-gray-200 dark:border-gray-700 shadow-lg">
        <CardHeader className="border-b border-gray-100 dark:border-gray-800 bg-gradient-to-r from-gray-50 to-white dark:from-gray-900 dark:to-gray-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-ward-green/10 dark:bg-ward-green/20">
              <History className="h-5 w-5 text-ward-green" />
            </div>
            <div>
              <CardTitle className="text-xl">Diagnostics Timeline</CardTitle>
              <CardDescription className="text-xs">
                Latest activity across ping, traceroute, DNS, and port scans
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6">
          {(summary?.timeline?.length ?? 0) === 0 ? (
            <div className="py-12 text-center">
              <div className="flex flex-col items-center gap-3">
                <div className="p-3 rounded-full bg-gray-100 dark:bg-gray-800">
                  <History className="h-6 w-6 text-gray-400 dark:text-gray-500" />
                </div>
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">No timeline entries yet</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Start running diagnostics to see activity</p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {summary?.timeline?.map((entry, index) => {
                const isSuccess = entry.status === 'success'
                const typeIcons = {
                  ping: Activity,
                  traceroute: Network,
                  dns: Globe,
                  portscan: Server,
                }
                const TypeIcon = typeIcons[entry.type as keyof typeof typeIcons] || Activity

                return (
                  <div
                    key={`${entry.type}-${entry.timestamp}-${entry.device_ip}`}
                    className="group relative"
                  >
                    {/* Timeline line */}
                    {index < (summary?.timeline?.length ?? 0) - 1 && (
                      <div className="absolute left-[21px] top-12 h-[calc(100%+0.5rem)] w-0.5 bg-gray-200 dark:bg-gray-700" />
                    )}

                    {/* Timeline item */}
                    <div className="relative flex gap-4">
                      {/* Icon */}
                      <div
                        className={clsx(
                          'relative z-10 flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border-2 shadow-sm transition-all duration-200 group-hover:scale-110',
                          isSuccess
                            ? 'border-emerald-500 bg-emerald-100 dark:border-emerald-600 dark:bg-emerald-900/30'
                            : 'border-red-500 bg-red-100 dark:border-red-600 dark:bg-red-900/30'
                        )}
                      >
                        <TypeIcon
                          className={clsx(
                            'h-5 w-5',
                            isSuccess
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-red-600 dark:text-red-400'
                          )}
                        />
                        {isSuccess && (
                          <div className="absolute -right-1 -top-1 h-3 w-3 rounded-full border-2 border-white dark:border-gray-900 bg-ward-green" />
                        )}
                      </div>

                      {/* Content */}
                      <div className="flex-1 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900 transition-all duration-200 group-hover:shadow-md group-hover:border-ward-green/50">
                        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-2">
                          <div>
                            <p className="font-bold text-gray-900 dark:text-white text-base mb-1">
                              {entry.device_name}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                              {entry.device_ip}
                            </p>
                          </div>
                          <Badge
                            variant={isSuccess ? 'success' : 'danger'}
                            size="sm"
                            className="self-start sm:self-center"
                          >
                            {entry.type.toUpperCase()}
                          </Badge>
                        </div>

                        <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                          <div className="flex items-center gap-1">
                            <div className="h-1.5 w-1.5 rounded-full bg-gray-400 dark:bg-gray-500" />
                            <span>{new Date(entry.timestamp).toLocaleString()}</span>
                          </div>
                          {entry.type === 'ping' && entry.avg_rtt_ms !== undefined && (
                            <div className="flex items-center gap-1">
                              <div className="h-1.5 w-1.5 rounded-full bg-ward-green" />
                              <span className={latencyColor(entry.avg_rtt_ms)}>
                                {entry.avg_rtt_ms ? `${Math.round(entry.avg_rtt_ms)} ms latency` : 'latency n/a'}
                              </span>
                            </div>
                          )}
                          <div className="flex items-center gap-1">
                            <div
                              className={clsx(
                                'h-1.5 w-1.5 rounded-full',
                                isSuccess ? 'bg-emerald-500' : 'bg-red-500'
                              )}
                            />
                            <span className={isSuccess ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}>
                              {isSuccess ? 'Successful' : 'Attention required'}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
