import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { devicesAPI, type Device } from '@/services/api'
import {
  Network,
  Search,
  ZoomIn,
  ZoomOut,
  Maximize,
  Filter,
  CheckCircle,
  XCircle
} from 'lucide-react'

// Import vis.js types
declare global {
  interface Window {
    vis: any
  }
}

interface DeviceNode {
  id: string
  label: string
  title?: string
  level?: number
  deviceType?: string
  branch?: string
  region?: string
  hidden?: boolean
  font?: any
  color?: any
}

interface DeviceEdge {
  id: string
  from: string
  to: string
  label?: string
  title?: string
  hidden?: boolean
  color?: any
  width?: number
  font?: any
}

interface TopologyData {
  nodes: DeviceNode[]
  edges: DeviceEdge[]
  stats: {
    total_nodes: number
    total_edges: number
  }
}

export default function Topology() {
  const [loading, setLoading] = useState(true)
  const [visJsLoading, setVisJsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedDevice, setSelectedDevice] = useState<any>(null)
  const [showDetailsPanel, setShowDetailsPanel] = useState(false)
  const [interfaceData, setInterfaceData] = useState<any>(null)
  const [filters, setFilters] = useState({
    routers: true,
    switches: true,
    payboxes: true,
    online: true,
    offline: true,
  })
  const [stats, setStats] = useState({ total: 0, online: 0, offline: 0, filtered: 0 })

  // Device selector states
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('')
  const [selectedDeviceName, setSelectedDeviceName] = useState<string>('')

  const canvasRef = useRef<HTMLDivElement>(null)
  const networkRef = useRef<any>(null)
  const nodesRef = useRef<any>(null)
  const edgesRef = useRef<any>(null)
  const pollingIntervalRef = useRef<number | null>(null)

  // Fetch all devices
  const { data: allDevices } = useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesAPI.getAll(),
  })

  // Filter to only show Routers and Switches
  const networkDevices = useMemo(() => {
    if (!allDevices?.data) return []
    return allDevices.data.filter((d: Device) => {
      const type = d.device_type?.toLowerCase() || ''
      return type.includes('router') || type.includes('switch') || type.includes('core')
    }).sort((a, b) => a.display_name.localeCompare(b.display_name))
  }, [allDevices])

  // Load vis.js library first
  useEffect(() => {
    loadVisJS()
      .then(() => {
        console.log('[Topology] vis.js ready')
        setVisJsLoading(false)
      })
      .catch(err => {
        console.error('[Topology] Failed to load vis.js:', err)
        setVisJsLoading(false)
      })

    return () => {
      // Cleanup
      if (pollingIntervalRef.current) {
        window.clearInterval(pollingIntervalRef.current)
      }
      if (networkRef.current) {
        networkRef.current.destroy()
      }
    }
  }, [])

  // Check URL parameters on mount and auto-select first device
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const deviceId = params.get('deviceId')
    const deviceName = params.get('deviceName')

    if (deviceId && deviceName) {
      setSelectedDeviceId(deviceId)
      setSelectedDeviceName(deviceName)
    } else if (networkDevices.length > 0) {
      // Auto-select first router/switch
      setSelectedDeviceId(networkDevices[0].hostid)
      setSelectedDeviceName(networkDevices[0].display_name)
    }
  }, [networkDevices])

  // Load topology once when vis.js is ready and canvas is available
  useEffect(() => {
    if (visJsLoading) return
    if (!window.vis) return

    // Retry mechanism to wait for canvas
    let retries = 0
    const maxRetries = 10

    const attemptLoad = () => {
      if (canvasRef.current) {
        console.log('[Topology] Canvas ready, loading topology data')
        loadTopologyData()
      } else if (retries < maxRetries) {
        retries++
        console.log(`[Topology] Canvas not ready, retry ${retries}/${maxRetries}`)
        setTimeout(attemptLoad, 100 * retries) // Increasing delay: 100ms, 200ms, 300ms...
      } else {
        console.error('[Topology] Canvas failed to initialize after', maxRetries, 'retries')
        setLoading(false)
      }
    }

    // Start first attempt after a small delay
    const timer = setTimeout(attemptLoad, 50)

    return () => clearTimeout(timer)
  }, [visJsLoading])

  // Fetch router interfaces using REST API with polling
  useEffect(() => {
    if (!selectedDeviceId || !selectedDeviceName) return

    console.log(`[Topology] Setting up interface monitoring for: ${selectedDeviceName}`)

    // Fetch immediately
    fetchRouterInterfaces(selectedDeviceId, selectedDeviceName)

    // Setup polling every 30 seconds
    if (pollingIntervalRef.current) {
      window.clearInterval(pollingIntervalRef.current)
    }

    pollingIntervalRef.current = window.setInterval(() => {
      fetchRouterInterfaces(selectedDeviceId, selectedDeviceName)
    }, 30000) // 30 seconds

    return () => {
      if (pollingIntervalRef.current) {
        window.clearInterval(pollingIntervalRef.current)
      }
    }
  }, [selectedDeviceId, selectedDeviceName])

  const loadVisJS = (): Promise<void> => {
    return new Promise((resolve, reject) => {
      // Check if already loaded
      if (window.vis) {
        console.log('[Topology] vis.js already loaded')
        resolve()
        return
      }

      // Load vis.js from CDN
      const script = document.createElement('script')
      script.src = 'https://unpkg.com/vis-network@9.1.6/dist/vis-network.min.js'
      script.async = true
      script.onload = () => {
        console.log('[Topology] vis.js loaded successfully')
        resolve()
      }
      script.onerror = () => {
        console.error('[Topology] Failed to load vis.js')
        reject(new Error('Failed to load vis.js'))
      }
      document.head.appendChild(script)

      // Load vis.js CSS
      const link = document.createElement('link')
      link.rel = 'stylesheet'
      link.href = 'https://unpkg.com/vis-network@9.1.6/dist/vis-network.min.css'
      document.head.appendChild(link)
    })
  }

  const loadTopologyData = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/topology?view=hierarchical&limit=200')

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data: TopologyData = await response.json()
      console.log('[Topology] Data loaded:', data.stats)

      if (!window.vis) {
        console.error('[Topology] vis.js not available')
        setTimeout(loadTopologyData, 500)
        return
      }

      // Initialize DataSets
      nodesRef.current = new window.vis.DataSet(data.nodes || [])
      edgesRef.current = new window.vis.DataSet(data.edges || [])

      // Update statistics
      updateStatistics(data.stats)

      // Create network visualization
      createNetworkVisualization()

      setLoading(false)
    } catch (error) {
      console.error('[Topology] Error loading data:', error)
      setLoading(false)
    }
  }

  const createNetworkVisualization = () => {
    if (!canvasRef.current) {
      console.error('[Topology] Canvas ref not available')
      return
    }
    if (!window.vis) {
      console.error('[Topology] vis.js not loaded')
      return
    }
    if (!nodesRef.current || !edgesRef.current) {
      console.error('[Topology] Nodes or edges DataSet not initialized')
      return
    }

    console.log('[Topology] Creating network with', nodesRef.current.length, 'nodes and', edgesRef.current.length, 'edges')
    console.log('[Topology] Container dimensions:', canvasRef.current.offsetWidth, 'x', canvasRef.current.offsetHeight)

    const isDark = document.documentElement.classList.contains('dark')

    const options = {
      nodes: {
        shape: 'dot',
        size: 25,
        font: {
          size: 16,
          color: isDark ? '#F3F4F6' : '#1a1a1a',
          face: 'Arial, sans-serif'
        },
        borderWidth: 2,
        shadow: {
          enabled: true,
          color: 'rgba(94, 187, 168, 0.4)',
          size: 10,
          x: 0,
          y: 0
        }
      },
      edges: {
        width: 4,
        color: {
          color: isDark ? '#30363d' : '#e5e7eb',
          highlight: '#5EBBA8',
          hover: '#72CFB8'
        },
        smooth: {
          enabled: true,
          type: 'cubicBezier',
          roundness: 0.4
        },
        font: {
          size: 13,
          color: isDark ? '#FFFFFF' : '#1a1a1a',
          background: isDark ? 'rgba(0, 0, 0, 0.8)' : 'rgba(255, 255, 255, 0.9)',
          strokeWidth: 2,
          align: 'top',
          vadjust: -8,
        },
        arrows: {
          to: {
            enabled: false
          }
        },
      },
      physics: {
        enabled: true,
        stabilization: {
          enabled: true,
          iterations: 500,
          fit: true
        },
        hierarchicalRepulsion: {
          nodeDistance: 400,
          springLength: 450,
          springConstant: 0.002,
          damping: 0.09
        },
        solver: 'hierarchicalRepulsion'
      },
      layout: {
        hierarchical: {
          enabled: false
        }
      },
      interaction: {
        hover: true,
        tooltipDelay: 100,
        navigationButtons: false,
        keyboard: true
      }
    }

    try {
      // Create network
      networkRef.current = new window.vis.Network(
        canvasRef.current,
        {
          nodes: nodesRef.current,
          edges: edgesRef.current
        },
        options
      )

      console.log('[Topology] Network created successfully:', networkRef.current)

      // Setup event handlers
      setupEventHandlers()

      // Apply force layout after stabilization
      networkRef.current.once('stabilizationIterationsDone', () => {
        console.log('[Topology] Stabilization complete')

        networkRef.current.fit({
          animation: {
            duration: 800,
            easingFunction: 'easeInOutQuad'
          }
        })
      })

      // Also fit immediately in case stabilization doesn't trigger
      setTimeout(() => {
        if (networkRef.current) {
          networkRef.current.fit({ animation: false })
          console.log('[Topology] Initial fit completed')
        }
      }, 100)

    } catch (error) {
      console.error('[Topology] Error creating network:', error)
    }
  }

  const setupEventHandlers = () => {
    if (!networkRef.current) return

    // Click event - show device details
    networkRef.current.on('click', (params: any) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0]
        const node = nodesRef.current.get(nodeId)
        handleNodeClick(node)
      } else {
        setShowDetailsPanel(false)
        setSelectedDevice(null)
      }
    })

    // Double click event - navigate to device details
    networkRef.current.on('doubleClick', (params: any) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0]
        if (!nodeId.startsWith('region_') && !nodeId.startsWith('branch_')) {
          window.location.href = `/devices/${nodeId}`
        }
      }
    })

    // Hover events
    networkRef.current.on('hoverNode', () => {
      if (canvasRef.current) {
        canvasRef.current.style.cursor = 'pointer'
      }
    })

    networkRef.current.on('blurNode', () => {
      if (canvasRef.current) {
        canvasRef.current.style.cursor = 'default'
      }
    })
  }

  const handleNodeClick = (node: any) => {
    setSelectedDevice(node)
    setShowDetailsPanel(true)

    // If it's a core router, fetch interface data via REST API
    if (node.level === 0 || node.deviceType === 'Core Router') {
      fetchRouterInterfaces(node.id, node.label)
    } else {
      setInterfaceData(null)
    }
  }

  const fetchRouterInterfaces = useCallback(async (hostid: string, routerName: string) => {
    try {
      // Get auth token from localStorage
      const token = localStorage.getItem('token')

      if (!token) {
        console.error('[REST API] No authentication token found')
        return
      }

      const response = await fetch(`/api/v1/router/${hostid}/interfaces`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      // Transform data to match expected format
      if (data.interfaces) {
        // Convert interfaces object to array and add Mbps conversions
        const interfacesArray = Object.entries(data.interfaces).map(([, iface]: [string, any]) => ({
          name: iface.name,
          description: iface.description || '',
          status: iface.status,
          bandwidth_in: iface.bandwidth_in,
          bandwidth_out: iface.bandwidth_out,
          bandwidth_in_mbps: iface.bandwidth_in / 1_000_000, // Convert bits/sec to Mbps
          bandwidth_out_mbps: iface.bandwidth_out / 1_000_000, // Convert bits/sec to Mbps
          errors_in: iface.errors_in || 0,
          errors_out: iface.errors_out || 0
        }))

        setInterfaceData({
          hostid: data.hostid,
          interfaces: interfacesArray
        })

        console.log(`[REST API] Fetched ${interfacesArray.length} interfaces for ${routerName}`)
      }
    } catch (error) {
      console.error('[REST API] Failed to fetch router interfaces:', error)
    }
  }, [])

  const updateStatistics = (apiStats: any) => {
    setStats({
      total: apiStats.total_nodes || 0,
      online: 0,
      offline: 0,
      filtered: apiStats.total_nodes || 0
    })

    // Calculate online/offline from nodes
    if (nodesRef.current) {
      const nodes = nodesRef.current.get()
      const onlineCount = nodes.filter((n: any) => n.title && n.title.includes('Status: Up')).length
      const offlineCount = nodes.filter((n: any) => n.title && n.title.includes('Status: Down')).length

      setStats(prev => ({
        ...prev,
        online: onlineCount,
        offline: offlineCount
      }))
    }
  }

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query)

    if (!networkRef.current || !nodesRef.current) return

    if (!query.trim()) {
      networkRef.current.unselectAll()
      return
    }

    const matchingNodes = nodesRef.current.get().filter((node: any) => {
      const label = (node.label || '').toLowerCase()
      const title = (node.title || '').toLowerCase()
      return label.includes(query.toLowerCase()) || title.includes(query.toLowerCase())
    })

    if (matchingNodes.length > 0) {
      const ids = matchingNodes.map((n: any) => n.id)
      networkRef.current.selectNodes(ids)
      networkRef.current.fit({
        nodes: ids,
        animation: { duration: 500 }
      })
    }
  }, [])

  const applyFilters = useCallback(() => {
    if (!networkRef.current || !nodesRef.current || !edgesRef.current) return

    const allNodesArray = nodesRef.current.get()
    const visibleNodeIds: string[] = []

    allNodesArray.forEach((node: any) => {
      let show = true

      // Filter by device type
      const deviceType = (node.deviceType || node.group || '').toLowerCase()
      if (deviceType.includes('router') && !filters.routers) show = false
      if (deviceType.includes('switch') && !filters.switches) show = false
      if (deviceType.includes('paybox') && !filters.payboxes) show = false

      // Filter by status
      const isOnline = node.title && node.title.includes('Status: Up')
      const isOffline = node.title && node.title.includes('Status: Down')

      if (isOnline && !filters.online) show = false
      if (isOffline && !filters.offline) show = false

      if (show) {
        visibleNodeIds.push(node.id)
      }
    })

    // Update node visibility
    const nodeUpdates = allNodesArray.map((node: any) => ({
      id: node.id,
      hidden: !visibleNodeIds.includes(node.id)
    }))
    nodesRef.current.update(nodeUpdates)

    // Update edge visibility
    const allEdgesArray = edgesRef.current.get()
    const edgeUpdates = allEdgesArray.map((edge: any) => ({
      id: edge.id,
      hidden: !visibleNodeIds.includes(edge.from) || !visibleNodeIds.includes(edge.to)
    }))
    edgesRef.current.update(edgeUpdates)

    setStats(prev => ({ ...prev, filtered: visibleNodeIds.length }))

    console.log(`[Filter] Showing ${visibleNodeIds.length} of ${allNodesArray.length} nodes`)
  }, [filters])

  useEffect(() => {
    applyFilters()
  }, [filters, applyFilters])

  const handleZoomIn = () => {
    if (networkRef.current) {
      const scale = networkRef.current.getScale()
      networkRef.current.moveTo({ scale: scale * 1.3, animation: { duration: 300 } })
    }
  }

  const handleZoomOut = () => {
    if (networkRef.current) {
      const scale = networkRef.current.getScale()
      networkRef.current.moveTo({ scale: scale * 0.7, animation: { duration: 300 } })
    }
  }

  const handleResetZoom = () => {
    if (networkRef.current) {
      networkRef.current.fit({ animation: { duration: 800 } })
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Network Topology</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Interactive network visualization with live data</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={handleZoomOut} size="sm">
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button variant="outline" onClick={handleZoomIn} size="sm">
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button variant="outline" onClick={handleResetZoom} size="sm">
            <Maximize className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Device Selector */}
      <div className="mb-6">
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Network className="h-5 w-5 text-ward-green" />
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Select Network Device:
                </label>
              </div>
              <select
                value={selectedDeviceId}
                onChange={(e) => {
                  const device = networkDevices.find(d => d.hostid === e.target.value)
                  if (device) {
                    setSelectedDeviceId(device.hostid)
                    setSelectedDeviceName(device.display_name)
                    // Update URL
                    const url = new URL(window.location.href)
                    url.searchParams.set('deviceId', device.hostid)
                    url.searchParams.set('deviceName', device.display_name)
                    window.history.pushState({}, '', url)
                  }
                }}
                className="flex-1 max-w-md px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-ward-green focus:border-transparent"
              >
                <option value="">Select a Router or Switch...</option>
                {networkDevices.map((device) => (
                  <option key={device.hostid} value={device.hostid}>
                    {device.display_name} ({device.device_type}) - {device.branch}
                  </option>
                ))}
              </select>
              {selectedDeviceId && (
                <Badge variant={networkDevices.find(d => d.hostid === selectedDeviceId)?.ping_status === 'Up' ? 'success' : 'danger'}>
                  {networkDevices.find(d => d.hostid === selectedDeviceId)?.ping_status || 'Unknown'}
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex-1 min-w-[300px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <Input
                  type="text"
                  placeholder="Search devices or IP addresses..."
                  value={searchQuery}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Filter className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Filters:</span>
              </div>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.routers}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, routers: e.target.checked })}
                  className="rounded border-gray-300 text-ward-green focus:ring-ward-green"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Routers</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.switches}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, switches: e.target.checked })}
                  className="rounded border-gray-300 text-ward-green focus:ring-ward-green"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Switches</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.payboxes}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, payboxes: e.target.checked })}
                  className="rounded border-gray-300 text-ward-green focus:ring-ward-green"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Payboxes</span>
              </label>

              <div className="w-px h-6 bg-gray-300 dark:bg-gray-700" />

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.online}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, online: e.target.checked })}
                  className="rounded border-gray-300 text-ward-green focus:ring-ward-green"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Online</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.offline}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, offline: e.target.checked })}
                  className="rounded border-gray-300 text-ward-green focus:ring-ward-green"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Offline</span>
              </label>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Total Nodes</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.total}</p>
              </div>
              <Network className="h-8 w-8 text-ward-green" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Filtered</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.filtered}</p>
              </div>
              <Filter className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Online</p>
                <p className="text-2xl font-bold text-green-600">{stats.online}</p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Offline</p>
                <p className="text-2xl font-bold text-red-600">{stats.offline}</p>
              </div>
              <XCircle className="h-8 w-8 text-red-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Topology Visualization */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Canvas */}
        <Card className="lg:col-span-3">
          <CardContent className="p-6">
            <div className="relative">
              <div
                ref={canvasRef}
                className="w-full bg-gray-50 dark:bg-gray-900 rounded-lg"
                style={{
                  height: '600px',
                  minHeight: '600px',
                  border: '1px solid rgb(55, 65, 81)'
                }}
              />
              {(visJsLoading || loading) && (
                <div className="absolute inset-0 w-full h-full bg-gray-900 rounded-lg flex items-center justify-center">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-ward-green mx-auto mb-4"></div>
                    <p className="text-gray-400">Loading network visualization...</p>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Device Details Panel */}
        <Card>
          <CardHeader>
            <CardTitle>Device Details</CardTitle>
          </CardHeader>
          <CardContent>
            {showDetailsPanel && selectedDevice ? (
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Name</label>
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-1">{selectedDevice.label}</p>
                </div>

                {selectedDevice.deviceType && (
                  <div>
                    <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Type</label>
                    <p className="text-sm text-gray-900 dark:text-gray-100 mt-1">{selectedDevice.deviceType}</p>
                  </div>
                )}

                {selectedDevice.branch && (
                  <div>
                    <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Branch</label>
                    <p className="text-sm text-gray-900 dark:text-gray-100 mt-1">{selectedDevice.branch}</p>
                  </div>
                )}

                {selectedDevice.region && (
                  <div>
                    <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Region</label>
                    <p className="text-sm text-gray-900 dark:text-gray-100 mt-1">{selectedDevice.region}</p>
                  </div>
                )}

                {/* Interface Data for Core Routers */}
                {interfaceData && interfaceData.interfaces && (
                  <div className="mt-4">
                    <label className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 block">
                      Live Interfaces ({interfaceData.interfaces.length})
                    </label>
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {interfaceData.interfaces.slice(0, 10).map((iface: any, index: number) => (
                        <div
                          key={index}
                          className="p-2 bg-gray-100 dark:bg-gray-800 rounded text-xs"
                        >
                          <div className="font-semibold text-gray-900 dark:text-gray-100">{iface.name}</div>
                          {iface.description && (
                            <div className="text-gray-600 dark:text-gray-400">{iface.description}</div>
                          )}
                          <div className="flex justify-between mt-1">
                            <span className="text-blue-600 dark:text-blue-400">
                              ↓ {iface.bandwidth_in_mbps?.toFixed(1) || 0} Mbps
                            </span>
                            <span className="text-purple-600 dark:text-purple-400">
                              ↑ {iface.bandwidth_out_mbps?.toFixed(1) || 0} Mbps
                            </span>
                          </div>
                          <Badge
                            variant={iface.status === 'up' ? 'success' : 'danger'}
                            className="mt-1"
                          >
                            {iface.status.toUpperCase()}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-12">
                <Network className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Click on a device to view details
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Legend */}
      <Card>
        <CardHeader>
          <CardTitle>Legend</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded-full bg-orange-500"></div>
              <span className="text-sm text-gray-700 dark:text-gray-300">Core Router</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded-full bg-teal-500"></div>
              <span className="text-sm text-gray-700 dark:text-gray-300">Switch</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded-full bg-ward-green"></div>
              <span className="text-sm text-gray-700 dark:text-gray-300">Server</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded-full bg-green-500"></div>
              <span className="text-sm text-gray-700 dark:text-gray-300">Online</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded-full bg-red-500"></div>
              <span className="text-sm text-gray-700 dark:text-gray-300">Offline</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
