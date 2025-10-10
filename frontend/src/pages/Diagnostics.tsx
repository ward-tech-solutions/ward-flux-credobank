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

type DiagnosticTool = 'ping' | 'traceroute' | 'dns' | 'portscan'

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
    queryKey: ['diagnostics-traceroute-map', selectedRouteIp],
    queryFn: () => diagnosticsAPI.tracerouteMap(selectedRouteIp!),
    enabled: Boolean(selectedRouteIp),
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
    <div className="space-y-8">
      <Card variant="glass" className="relative overflow-hidden">
        <div
          className="pointer-events-none absolute -right-24 top-0 h-56 w-56 rounded-full bg-ward-green/20 blur-3xl dark:bg-ward-green/10"
          aria-hidden="true"
        />
        <CardHeader className="relative z-10 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle className="text-3xl">Network Diagnostics</CardTitle>
            <CardDescription className="max-w-2xl text-gray-600 dark:text-gray-300">
              Monitor reachability, visualize routing paths, and launch targeted checks without leaving the
              command center.
            </CardDescription>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={overallStatusVariant} size="sm" dot>
              {overallStatusText}
            </Badge>
            <Button
              onClick={handleRunDiagnostic}
              loading={loading}
              icon={<Terminal className="h-4 w-4" />}
            >
              Run {selectedToolConfig?.title ?? 'Diagnostic'}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="relative z-10 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {highlightMetrics.map(metric => {
            const Icon = metric.icon
            return (
              <div
                key={metric.key}
                className="rounded-xl border border-gray-100 bg-white/80 p-4 shadow-sm backdrop-blur dark:border-gray-700 dark:bg-gray-900/70"
              >
                <div className="flex items-center gap-3">
                  <span className="rounded-full bg-ward-green/10 p-2 text-ward-green">
                    <Icon className="h-4 w-4" />
                  </span>
                  <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200">{metric.title}</h2>
                </div>
                <p className="mt-3 text-2xl font-semibold text-gray-900 dark:text-gray-100">{metric.value}</p>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{metric.subtext}</p>
              </div>
            )
          })}
        </CardContent>
      </Card>

      <div className="space-y-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Health Snapshot</h2>
          <Badge variant="info" size="sm">
            Data from the latest diagnostics rollup
          </Badge>
        </div>

        {summaryLoading ? (
          <Card>
            <CardContent className="flex items-center justify-center py-12">
              <LoadingSpinner />
            </CardContent>
          </Card>
        ) : summary ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            {snapshotCards.map(card => {
              const Icon = card.icon
              return (
                <Card key={card.key} hover className="border border-gray-100 dark:border-gray-700">
                  <CardContent className="flex flex-col gap-4 p-5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="rounded-xl bg-gray-100 p-2 text-ward-green dark:bg-gray-900/60">
                          <Icon className="h-5 w-5" />
                        </span>
                        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{card.title}</p>
                      </div>
                      <Badge variant={card.variant} size="sm">
                        {card.badge}
                      </Badge>
                    </div>
                    <p className="text-3xl font-semibold text-gray-900 dark:text-gray-100">{card.primary}</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{card.meta}</p>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        ) : (
          <Card>
            <CardContent className="py-10 text-center text-sm text-gray-500 dark:text-gray-400">
              Run a diagnostic to populate this dashboard.
            </CardContent>
          </Card>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 2xl:grid-cols-3">
        <Card className="2xl:col-span-2">
          <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="h-5 w-5 text-ward-green" />
                Traceroute Map
              </CardTitle>
              <CardDescription>Visualize path latency for the most recent traces.</CardDescription>
            </div>
            <div className="flex w-full flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
              <Select
                value={selectedRouteIp}
                onChange={event => setSelectedRouteIp(event.target.value)}
                options={tracerouteOptions}
                fullWidth
                disabled={(summary?.recent_traceroutes?.length ?? 0) === 0}
              />
              <Badge variant="info" size="sm" dot>
                {summary?.recent_traceroutes?.length ?? 0} saved paths
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="h-[26rem]">
            {tracerouteLoading ? (
              <div className="flex h-full items-center justify-center">
                <LoadingSpinner />
              </div>
            ) : tracerouteMap && traceroutePositions.length > 0 ? (
              <MapContainer
                center={mapCenter}
                zoom={7}
                className="h-full w-full overflow-hidden rounded-xl"
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
              <div className="flex h-full flex-col items-center justify-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <MapPin className="h-8 w-8 text-gray-400" />
                No traceroute coordinates available yet.
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-ward-green" />
              Latency by Region
            </CardTitle>
            <CardDescription>Rolling window from the latest diagnostics.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {(summary?.region_latency?.length ?? 0) === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Run diagnostics to populate regional metrics.
              </p>
            ) : (
              summary?.region_latency?.map(region => (
                <div
                  key={region.region}
                  className="space-y-2 rounded-xl border border-gray-100 bg-white p-4 dark:border-gray-700 dark:bg-gray-900"
                >
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-gray-900 dark:text-gray-100">{region.region}</span>
                    <Badge variant="info" size="sm">
                      {region.samples} samples
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                    <span className={latencyColor(region.avg_latency)}>
                      {region.avg_latency !== null ? `${Math.round(region.avg_latency)} ms` : 'n/a'}
                    </span>
                    <span>{region.avg_packet_loss.toFixed(1)}% loss</span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
                    <div
                      className="h-full rounded-full bg-ward-green"
                      style={{
                        width: `${Math.max(
                          8,
                          Math.round((region.samples / maxRegionSamples) * 100)
                        )}%`,
                      }}
                    />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <CardTitle>Diagnostics Workbench</CardTitle>
              <CardDescription>
                Select a tool, provide a target, and launch on-demand checks. Results render instantly for quick triage.
              </CardDescription>
            </div>
            {selectedToolConfig?.helper && (
              <Badge variant="info" size="sm">
                {selectedToolConfig.helper}
              </Badge>
            )}
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {TOOL_OPTIONS.map(tool => {
                const Icon = tool.icon
                const isActive = selectedTool === tool.key
                return (
                  <button
                    key={tool.key}
                    onClick={() => setSelectedTool(tool.key)}
                    className={clsx(
                      'rounded-xl border-2 p-4 text-left transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-ward-green/60',
                      isActive
                        ? 'border-ward-green bg-ward-green/5 text-ward-green shadow-sm'
                        : 'border-gray-200 text-gray-700 hover:border-ward-green/60 hover:text-ward-green dark:border-gray-700 dark:text-gray-200'
                    )}
                  >
                    <Icon className={clsx('mb-3 h-6 w-6', isActive ? 'text-ward-green' : 'text-gray-400')} />
                    <p className="text-sm font-semibold">{tool.title}</p>
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{tool.description}</p>
                  </button>
                )
              })}
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <div className="space-y-4 lg:col-span-1">
                <Input
                  label="Target IP"
                  placeholder="192.0.2.10"
                  value={targetIP}
                  onChange={event => setTargetIP(event.target.value)}
                  helperText="IPv4 or IPv6 address"
                  icon={<Server className="h-4 w-4" />}
                />
                {selectedTool === 'dns' && (
                  <Input
                    label="Hostname"
                    placeholder="router.example.com"
                    value={targetHostname}
                    onChange={event => setTargetHostname(event.target.value)}
                    helperText="FQDN or short hostname to resolve"
                    icon={<Globe className="h-4 w-4" />}
                  />
                )}
                {selectedTool === 'portscan' && (
                  <Input
                    label="Ports"
                    placeholder="22,80,443"
                    value={ports}
                    onChange={event => setPorts(event.target.value)}
                    helperText="Comma-separated list or ranges (e.g. 1-1024)"
                    icon={<Terminal className="h-4 w-4" />}
                  />
                )}
                <div className="flex flex-wrap items-center gap-3">
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
                      void refetchTracerouteMap()
                    }}
                    icon={<TrendingUp className="h-4 w-4" />}
                  >
                    Refresh Insights
                  </Button>
                </div>
              </div>

              <div className="lg:col-span-2 space-y-4">
                {selectedTool === 'ping' && pingResult && (
                  <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                          {pingResult.device_name || pingResult.device_ip}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">{pingResult.device_ip}</p>
                      </div>
                      <Badge variant={pingResult.is_reachable ? 'success' : 'danger'} dot>
                        {pingResult.is_reachable ? 'Reachable' : 'Unreachable'}
                      </Badge>
                    </div>
                    <div className="mt-4 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
                      <div className="rounded-lg bg-gray-50 p-3 text-gray-700 dark:bg-gray-900/60 dark:text-gray-200">
                        <p className="text-xs uppercase text-gray-500 dark:text-gray-400">Packets</p>
                        <p className="mt-2 font-semibold">
                          {pingResult.packets_received}/{pingResult.packets_sent}
                        </p>
                      </div>
                      <div className="rounded-lg bg-gray-50 p-3 text-gray-700 dark:bg-gray-900/60 dark:text-gray-200">
                        <p className="text-xs uppercase text-gray-500 dark:text-gray-400">Loss</p>
                        <p className="mt-2 font-semibold">{pingResult.packet_loss_percent}%</p>
                      </div>
                      <div className="rounded-lg bg-gray-50 p-3 text-gray-700 dark:bg-gray-900/60 dark:text-gray-200">
                        <p className="text-xs uppercase text-gray-500 dark:text-gray-400">Avg RTT</p>
                        <p className={clsx('mt-2 font-semibold', latencyColor(pingResult.avg_rtt_ms))}>
                          {pingResult.avg_rtt_ms !== null && pingResult.avg_rtt_ms !== undefined
                            ? `${Math.round(pingResult.avg_rtt_ms)} ms`
                            : 'n/a'}
                        </p>
                      </div>
                      <div className="rounded-lg bg-gray-50 p-3 text-gray-700 dark:bg-gray-900/60 dark:text-gray-200">
                        <p className="text-xs uppercase text-gray-500 dark:text-gray-400">Min / Max</p>
                        <p className="mt-2 font-semibold">
                          {pingResult.min_rtt_ms !== undefined && pingResult.max_rtt_ms !== undefined
                            ? `${pingResult.min_rtt_ms} / ${pingResult.max_rtt_ms} ms`
                            : 'n/a'}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {selectedTool === 'traceroute' && tracerouteResult && (
                  <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                          {tracerouteResult.device_name || tracerouteResult.device_ip}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(tracerouteResult.timestamp).toLocaleString()}
                        </p>
                      </div>
                      <Badge variant="info" size="sm">
                        {tracerouteResult.hops.length} hops
                      </Badge>
                    </div>
                    <div className="mt-4 max-h-56 space-y-2 overflow-y-auto pr-2 text-sm text-gray-600 dark:text-gray-300">
                      {tracerouteResult.hops.map(hop => (
                        <div
                          key={hop.hop_number}
                          className="flex items-center justify-between rounded-lg bg-gray-50 p-3 dark:bg-gray-900/60"
                        >
                          <div>
                            <p className="text-xs uppercase text-gray-500 dark:text-gray-400">
                              Hop {hop.hop_number}
                            </p>
                            <p className="font-medium text-gray-800 dark:text-gray-200">
                              {hop.hostname || hop.ip || 'Unknown'}
                            </p>
                          </div>
                          <span className={clsx('text-sm font-semibold', latencyColor(hop.latency_ms))}>
                            {hop.latency_ms !== undefined ? `${hop.latency_ms} ms` : '—'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {selectedTool === 'dns' && dnsResult && (
                  <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">DNS Lookup</p>
                      <Badge variant={dnsResult.success ? 'success' : 'danger'} dot>
                        {dnsResult.success ? 'Resolved' : 'Failed'}
                      </Badge>
                    </div>
                    <div className="mt-3 space-y-1 text-sm text-gray-600 dark:text-gray-300">
                      {dnsResult.success ? (
                        <>
                          <p>Hostname: {dnsResult.hostname}</p>
                          <p>IP Address: {dnsResult.ip_address}</p>
                          {dnsResult.all_ips && dnsResult.all_ips.length > 0 && (
                            <p>All IPs: {dnsResult.all_ips.join(', ')}</p>
                          )}
                          {dnsResult.reverse_hostname && (
                            <p>Reverse: {dnsResult.reverse_hostname}</p>
                          )}
                        </>
                      ) : (
                        <p className="text-red-500 dark:text-red-400">
                          {dnsResult.error || 'Lookup failed'}
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {selectedTool === 'portscan' && portScanResult && (
                  <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">Port Scan</p>
                      <Badge variant="info" size="sm">
                        {portScanResult.open_ports} open
                      </Badge>
                    </div>
                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                      {portScanResult.ports_scanned} ports scanned
                    </p>
                    <div className="mt-4 grid grid-cols-3 gap-2">
                      {portScanResult.results.map(result => (
                        <Badge
                          key={result.port}
                          variant={result.is_open ? 'success' : 'default'}
                          className={clsx(
                            'justify-center py-2 font-semibold',
                            !result.is_open && 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                          )}
                        >
                          {result.port}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Ping Observations</CardTitle>
            <CardDescription>Snapshot from the rolling diagnostics summary.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {(summary?.recent_pings?.length ?? 0) === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                No diagnostics recorded yet.
              </p>
            ) : (
              summary?.recent_pings?.map(result => (
                <div
                  key={`${result.device_ip}-${result.timestamp}`}
                  className="rounded-xl border border-gray-100 bg-white p-4 dark:border-gray-700 dark:bg-gray-900"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-gray-900 dark:text-gray-100">{result.device_name}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{result.device_ip}</p>
                    </div>
                    <Badge variant={result.is_reachable ? 'success' : 'danger'} dot>
                      {result.is_reachable ? 'Reachable' : 'Down'}
                    </Badge>
                  </div>
                  <div className="mt-3 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                    <span className={latencyColor(result.avg_rtt_ms)}>
                      Latency {result.avg_rtt_ms ? `${Math.round(result.avg_rtt_ms)} ms` : 'n/a'}
                    </span>
                    <span>Loss {result.packet_loss_percent}%</span>
                  </div>
                  <p className="mt-2 text-xs text-gray-400">
                    {new Date(result.timestamp).toLocaleString()}
                  </p>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5 text-ward-green" />
            Diagnostics Timeline
          </CardTitle>
          <CardDescription>Latest activity across ping, traceroute, DNS, and port scans.</CardDescription>
        </CardHeader>
        <CardContent>
          {(summary?.timeline?.length ?? 0) === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">No timeline entries yet.</p>
          ) : (
            <div className="space-y-5">
              {summary?.timeline?.map(entry => (
                <div
                  key={`${entry.type}-${entry.timestamp}-${entry.device_ip}`}
                  className="relative border-l-2 border-gray-100 pl-5 dark:border-gray-800"
                >
                  <span
                    className={clsx(
                      'absolute -left-[5px] top-2 h-3 w-3 rounded-full',
                      entry.status === 'success' ? 'bg-ward-green' : 'bg-red-500'
                    )}
                  />
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-3">
                      <p className="font-semibold text-gray-900 dark:text-gray-100">
                        {entry.device_name}
                      </p>
                      <Badge variant={entry.status === 'success' ? 'success' : 'danger'} size="sm">
                        {entry.type.toUpperCase()}
                      </Badge>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {new Date(entry.timestamp).toLocaleString()} • {entry.device_ip}
                    </p>
                    {entry.type === 'ping' && entry.avg_rtt_ms !== undefined && (
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Avg latency {entry.avg_rtt_ms ? `${Math.round(entry.avg_rtt_ms)} ms` : 'n/a'}
                      </p>
                    )}
                    <p className="text-xs text-gray-400">
                      Status: {entry.status === 'success' ? 'Successful' : 'Attention required'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
