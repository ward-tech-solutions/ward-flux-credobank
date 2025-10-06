import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import {
  Activity,
  Terminal,
  Network,
  Globe,
  Server
} from 'lucide-react'
import api from '@/services/api'

type DiagnosticTool = 'ping' | 'traceroute' | 'dns' | 'portscan'

interface PingResult {
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

interface TracerouteHop {
  hop_number: number
  ip?: string
  hostname?: string
  latency_ms?: number
}

interface TracerouteResult {
  device_ip: string
  device_name?: string
  hops: TracerouteHop[]
  total_hops: number
}

interface DNSResult {
  hostname?: string
  ip_address?: string
  all_ips?: string[]
  reverse_hostname?: string
  success: boolean
  error?: string
}

interface PortScanResult {
  ip_address: string
  ports_scanned: number
  open_ports: number
  results: Array<{
    port: number
    status: string
    is_open: boolean
  }>
}

export default function Diagnostics() {
  const [selectedTool, setSelectedTool] = useState<DiagnosticTool>('ping')
  const [targetIP, setTargetIP] = useState('')
  const [targetHostname, setTargetHostname] = useState('')
  const [ports, setPorts] = useState('22,80,443,3389,8080')
  const [loading, setLoading] = useState(false)
  const [pingResult, setPingResult] = useState<PingResult | null>(null)
  const [tracerouteResult, setTracerouteResult] = useState<TracerouteResult | null>(null)
  const [dnsResult, setDNSResult] = useState<DNSResult | null>(null)
  const [portScanResult, setPortScanResult] = useState<PortScanResult | null>(null)

  const handlePing = async () => {
    if (!targetIP) return
    setLoading(true)
    try {
      const response = await api.post('/diagnostics/ping', null, {
        params: { ip: targetIP, count: 5 }
      })
      setPingResult(response.data)
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
      const response = await api.post('/diagnostics/traceroute', null, {
        params: { ip: targetIP, max_hops: 30 }
      })
      setTracerouteResult(response.data)
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
      const response = await api.post('/diagnostics/dns/lookup', null, {
        params: { hostname: targetHostname }
      })
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
      const response = await api.post('/diagnostics/portscan', null, {
        params: { ip: targetIP, ports }
      })
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

  const getLatencyColor = (latency?: number) => {
    if (!latency) return 'text-gray-500'
    if (latency < 50) return 'text-green-600'
    if (latency < 100) return 'text-yellow-600'
    return 'text-red-600'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Network Diagnostics</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Test network connectivity and performance</p>
      </div>

      {/* Tool Selection */}
      <Card>
        <CardHeader>
          <CardTitle>Diagnostic Tools</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <button
              onClick={() => setSelectedTool('ping')}
              className={`p-4 rounded-lg border-2 transition-all ${
                selectedTool === 'ping'
                  ? 'border-ward-green bg-ward-green/5'
                  : 'border-gray-200 dark:border-gray-700 hover:border-ward-green/50'
              }`}
            >
              <Activity className={`h-8 w-8 mx-auto mb-2 ${selectedTool === 'ping' ? 'text-ward-green' : 'text-gray-400'}`} />
              <h3 className={`font-semibold ${selectedTool === 'ping' ? 'text-ward-green' : 'text-gray-900 dark:text-gray-100'}`}>
                Ping
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Test connectivity</p>
            </button>

            <button
              onClick={() => setSelectedTool('traceroute')}
              className={`p-4 rounded-lg border-2 transition-all ${
                selectedTool === 'traceroute'
                  ? 'border-ward-green bg-ward-green/5'
                  : 'border-gray-200 dark:border-gray-700 hover:border-ward-green/50'
              }`}
            >
              <Network className={`h-8 w-8 mx-auto mb-2 ${selectedTool === 'traceroute' ? 'text-ward-green' : 'text-gray-400'}`} />
              <h3 className={`font-semibold ${selectedTool === 'traceroute' ? 'text-ward-green' : 'text-gray-900 dark:text-gray-100'}`}>
                Traceroute
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Trace network path</p>
            </button>

            <button
              onClick={() => setSelectedTool('dns')}
              className={`p-4 rounded-lg border-2 transition-all ${
                selectedTool === 'dns'
                  ? 'border-ward-green bg-ward-green/5'
                  : 'border-gray-200 dark:border-gray-700 hover:border-ward-green/50'
              }`}
            >
              <Globe className={`h-8 w-8 mx-auto mb-2 ${selectedTool === 'dns' ? 'text-ward-green' : 'text-gray-400'}`} />
              <h3 className={`font-semibold ${selectedTool === 'dns' ? 'text-ward-green' : 'text-gray-900 dark:text-gray-100'}`}>
                DNS Lookup
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Resolve hostnames</p>
            </button>

            <button
              onClick={() => setSelectedTool('portscan')}
              className={`p-4 rounded-lg border-2 transition-all ${
                selectedTool === 'portscan'
                  ? 'border-ward-green bg-ward-green/5'
                  : 'border-gray-200 dark:border-gray-700 hover:border-ward-green/50'
              }`}
            >
              <Server className={`h-8 w-8 mx-auto mb-2 ${selectedTool === 'portscan' ? 'text-ward-green' : 'text-gray-400'}`} />
              <h3 className={`font-semibold ${selectedTool === 'portscan' ? 'text-ward-green' : 'text-gray-900 dark:text-gray-100'}`}>
                Port Scan
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Check open ports</p>
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Input Form */}
      <Card>
        <CardHeader>
          <CardTitle>
            {selectedTool === 'ping' && 'Ping Configuration'}
            {selectedTool === 'traceroute' && 'Traceroute Configuration'}
            {selectedTool === 'dns' && 'DNS Lookup Configuration'}
            {selectedTool === 'portscan' && 'Port Scan Configuration'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {selectedTool === 'dns' ? (
              <Input
                label="Hostname or Domain"
                placeholder="e.g., google.com or example.org"
                value={targetHostname}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTargetHostname(e.target.value)}
              />
            ) : (
              <Input
                label="Target IP Address"
                placeholder="e.g., 192.168.1.1"
                value={targetIP}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTargetIP(e.target.value)}
              />
            )}

            {selectedTool === 'portscan' && (
              <Input
                label="Ports to Scan"
                placeholder="e.g., 22,80,443,3389,8080"
                value={ports}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPorts(e.target.value)}
                helperText="Comma-separated list of ports"
              />
            )}

            <Button onClick={handleRunDiagnostic} disabled={loading} className="w-full">
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Running...
                </>
              ) : (
                <>
                  <Terminal className="h-4 w-4 mr-2" />
                  Run {selectedTool.charAt(0).toUpperCase() + selectedTool.slice(1)}
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {pingResult && selectedTool === 'ping' && (
        <Card>
          <CardHeader>
            <CardTitle>Ping Results</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Target</p>
                  <p className="font-mono font-semibold text-gray-900 dark:text-gray-100">{pingResult.device_ip}</p>
                </div>
                <Badge variant={pingResult.is_reachable ? 'success' : 'danger'} dot>
                  {pingResult.is_reachable ? 'REACHABLE' : 'UNREACHABLE'}
                </Badge>
              </div>

              {pingResult.is_reachable && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                    <p className="text-sm text-gray-500 dark:text-gray-400">Packet Loss</p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{pingResult.packet_loss_percent}%</p>
                  </div>
                  <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                    <p className="text-sm text-gray-500 dark:text-gray-400">Min RTT</p>
                    <p className="text-2xl font-bold text-green-600">{pingResult.min_rtt_ms?.toFixed(2)}ms</p>
                  </div>
                  <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                    <p className="text-sm text-gray-500 dark:text-gray-400">Avg RTT</p>
                    <p className="text-2xl font-bold text-ward-green">{pingResult.avg_rtt_ms?.toFixed(2)}ms</p>
                  </div>
                  <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                    <p className="text-sm text-gray-500 dark:text-gray-400">Max RTT</p>
                    <p className="text-2xl font-bold text-orange-600">{pingResult.max_rtt_ms?.toFixed(2)}ms</p>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {tracerouteResult && selectedTool === 'traceroute' && (
        <Card>
          <CardHeader>
            <CardTitle>Traceroute Results</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Target</p>
                  <p className="font-mono font-semibold text-gray-900 dark:text-gray-100">{tracerouteResult.device_ip}</p>
                </div>
                <Badge variant="default">
                  {tracerouteResult.total_hops} Hops
                </Badge>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-gray-900">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Hop
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        IP Address
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Hostname
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Latency
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-800">
                    {tracerouteResult.hops.map((hop) => (
                      <tr key={hop.hop_number} className="hover:bg-gray-50 dark:hover:bg-gray-900">
                        <td className="px-4 py-3">
                          <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-ward-green text-white font-semibold text-sm">
                            {hop.hop_number}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono text-sm text-gray-900 dark:text-gray-100">
                          {hop.ip || '*'}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                          {hop.hostname || '-'}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`font-semibold ${getLatencyColor(hop.latency_ms)} dark:opacity-90`}>
                            {hop.latency_ms ? `${hop.latency_ms.toFixed(2)}ms` : '*'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {dnsResult && selectedTool === 'dns' && (
        <Card>
          <CardHeader>
            <CardTitle>DNS Lookup Results</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {dnsResult.success ? (
                <>
                  <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Hostname</p>
                    <p className="font-semibold text-gray-900 dark:text-gray-100">{dnsResult.hostname}</p>
                  </div>
                  <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">IP Address</p>
                    <p className="font-mono font-semibold text-ward-green">{dnsResult.ip_address}</p>
                  </div>
                  {dnsResult.all_ips && dnsResult.all_ips.length > 1 && (
                    <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                      <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">All IP Addresses</p>
                      <div className="flex flex-wrap gap-2">
                        {dnsResult.all_ips.map((ip, i) => (
                          <Badge key={i} variant="default">{ip}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  {dnsResult.reverse_hostname && (
                    <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                      <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Reverse Hostname</p>
                      <p className="font-semibold text-gray-900 dark:text-gray-100">{dnsResult.reverse_hostname}</p>
                    </div>
                  )}
                </>
              ) : (
                <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
                  <p className="text-red-600 dark:text-red-400">{dnsResult.error || 'DNS lookup failed'}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {portScanResult && selectedTool === 'portscan' && (
        <Card>
          <CardHeader>
            <CardTitle>Port Scan Results</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Target</p>
                  <p className="font-mono font-semibold text-gray-900 dark:text-gray-100">{portScanResult.ip_address}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-500 dark:text-gray-400">Open Ports</p>
                  <p className="text-2xl font-bold text-ward-green">{portScanResult.open_ports}/{portScanResult.ports_scanned}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {portScanResult.results.map((result) => (
                  <div
                    key={result.port}
                    className={`p-4 rounded-lg border-2 ${
                      result.is_open
                        ? 'border-green-500 dark:border-green-600 bg-green-50 dark:bg-green-900/20'
                        : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900'
                    }`}
                  >
                    <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{result.port}</p>
                    <Badge variant={result.is_open ? 'success' : 'default'} className="mt-2">
                      {result.status.toUpperCase()}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
