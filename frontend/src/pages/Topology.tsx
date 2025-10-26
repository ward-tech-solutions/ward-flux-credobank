import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Select from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/Loading'
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

// Device type to icon/shape mapping for topology visualization
const getDeviceVisualization = (deviceType: string): { shape: string; unicode: string; color: string } => {
  const type = deviceType?.toLowerCase() || ''

  // Switch devices
  if (type.includes('switch')) {
    return { shape: 'icon', unicode: '⚡', color: '#14b8a6' } // Network/Switch
  }
  // Router devices
  if (type.includes('router') && !type.includes('core')) {
    return { shape: 'icon', unicode: '🌐', color: '#3b82f6' } // Globe/Router
  }
  // Core Router
  if (type.includes('core')) {
    return { shape: 'icon', unicode: '🖥️', color: '#FF6B35' } // Monitor/Core
  }
  // Access Point / WiFi
  if (type.includes('access point') || type.includes('wifi') || type.includes('wireless')) {
    return { shape: 'icon', unicode: '📡', color: '#10b981' } // WiFi
  }
  // NVR / Camera
  if (type.includes('nvr') || type.includes('camera')) {
    return { shape: 'icon', unicode: '📹', color: '#8b5cf6' } // Video
  }
  // Paybox
  if (type.includes('paybox')) {
    return { shape: 'icon', unicode: '💳', color: '#ec4899' } // Credit Card
  }
  // ATM
  if (type.includes('atm')) {
    return { shape: 'icon', unicode: '💵', color: '#f59e0b' } // Banknote
  }
  // Biostar
  if (type.includes('biostar') || type.includes('biometric')) {
    return { shape: 'icon', unicode: '👆', color: '#6366f1' } // Fingerprint
  }
  // Disaster Recovery
  if (type.includes('disaster') || type.includes('dr')) {
    return { shape: 'icon', unicode: '🛡️', color: '#14b8a6' } // Shield
  }
  // Default - Server
  return { shape: 'icon', unicode: '🖥️', color: '#6b7280' } // Server
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
        // vis.js ready
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
        // Canvas ready, loading topology data
        loadTopologyData()
      } else if (retries < maxRetries) {
        retries++
        // Canvas not ready, retrying...
        setTimeout(attemptLoad, 100 * retries) // Increasing delay: 100ms, 200ms, 300ms...
      } else {
        console.error('[Topology] Canvas failed to initialize after', maxRetries, 'retries')
        setLoading(false)
      }
    }

    // Start first attempt after a small delay
    const timer = setTimeout(attemptLoad, 50)

    return () => clearTimeout(timer)
  }, [visJsLoading, selectedDeviceId])

  // Focus and highlight selected device when selection changes
  useEffect(() => {
    if (!visJsLoading && window.vis && networkRef.current && selectedDeviceId && nodesRef.current) {
      // Check if the node exists in the topology
      const node = nodesRef.current.get(selectedDeviceId)

      if (node) {
        // Device selection changed, focusing on device

        // Select and focus on the node
        networkRef.current.selectNodes([selectedDeviceId])
        networkRef.current.focus(selectedDeviceId, {
          scale: 1.5,
          animation: {
            duration: 1000,
            easingFunction: 'easeInOutQuad'
          }
        })

        // Automatically show device details
        handleNodeClick(node)
      } else {
        // Device not found in topology
        // Optionally show a message to the user
        setShowDetailsPanel(false)
        setSelectedDevice(null)
      }
    }
  }, [selectedDeviceId])

  // Fetch router interfaces using REST API with polling
  useEffect(() => {
    if (!selectedDeviceId || !selectedDeviceName) return

    // Setting up interface monitoring

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
        // vis.js already loaded
        resolve()
        return
      }

      // Load vis.js from CDN (using jsdelivr for better reliability)
      const script = document.createElement('script')
      script.src = 'https://cdn.jsdelivr.net/npm/vis-network@9.1.6/dist/vis-network.min.js'
      script.async = true
      script.onload = () => {
        // vis.js loaded successfully
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
      link.href = 'https://cdn.jsdelivr.net/npm/vis-network@9.1.6/dist/vis-network.min.css'
      document.head.appendChild(link)
    })
  }

  const loadTopologyData = async () => {
    try {
      setLoading(true)

      // Load topology via authenticated API client
      const { api } = await import('@/api/client')
      const res = await api.getTopology({ view: 'hierarchical', limit: 200 })
      const data: TopologyData = res.data as any
      // Data loaded successfully

      if (!window.vis) {
        console.error('[Topology] vis.js not available')
        setTimeout(loadTopologyData, 500)
        return
      }

      // Initialize DataSets
      let filteredNodes = data.nodes || []
      let filteredEdges = data.edges || []

      // Processing network data

      // Filter nodes and edges based on selected device
      if (selectedDeviceId) {
        // Filtering topology for selected device

        // Find all directly connected nodes (neighbors)
        const connectedNodeIds = new Set<string>()
        connectedNodeIds.add(selectedDeviceId) // Add the selected device itself
        connectedNodeIds.add(String(selectedDeviceId)) // Also add string version for matching

        // Find all edges connected to the selected device
        const relevantEdges = filteredEdges.filter((edge: DeviceEdge) => {
          // Convert IDs to strings for consistent comparison
          const fromId = String(edge.from)
          const toId = String(edge.to)
          const selectedId = String(selectedDeviceId)
          const matches = fromId === selectedId || toId === selectedId

          if (matches) {
            // Found matching edge
          }

          return matches
        })

        // Found edges connected to device

        // Add all neighbor node IDs
        relevantEdges.forEach((edge: DeviceEdge) => {
          const fromId = String(edge.from)
          const toId = String(edge.to)
          const selectedId = String(selectedDeviceId)

          if (fromId === selectedId) {
            connectedNodeIds.add(edge.to)
            connectedNodeIds.add(String(edge.to))
            // Added neighbor node
          }
          if (toId === selectedId) {
            connectedNodeIds.add(edge.from)
            connectedNodeIds.add(String(edge.from))
            // Added neighbor node
          }
        })

        // Filter nodes to show selected device and its neighbors (exclude only core routers)
        filteredNodes = filteredNodes.filter((node: DeviceNode) => {
          const nodeId = String(node.id)
          const isConnected = connectedNodeIds.has(node.id) || connectedNodeIds.has(nodeId)
          const deviceType = (node.deviceType || '').toLowerCase()
          const isCoreRouter = deviceType.includes('core')

          // If it's the selected device, always include it
          if (nodeId === String(selectedDeviceId)) {
            return true
          }

          // For neighbors: include all except core routers
          const shouldInclude = isConnected && !isCoreRouter
          if (isConnected) {
          }

          return shouldInclude
        })

        // Use the relevant edges
        filteredEdges = relevantEdges

      }

      // Enhance nodes with device-specific icons and extract IP for label
      const enhancedNodes = filteredNodes.map((node: DeviceNode) => {
        const deviceType = node.deviceType || 'Unknown'
        const visualization = getDeviceVisualization(deviceType)

        // Extract IP address from title field (format: "DeviceName\nIP\n...")
        let ipAddress = ''
        if (node.title) {
          const titleLines = node.title.split('\n')
          if (titleLines.length > 1) {
            ipAddress = titleLines[1]  // Second line is typically the IP
          }
        }

        // Create label with device name and IP - use title's first line if label is empty
        let displayLabel = node.label || ''
        if (!displayLabel && node.title) {
          displayLabel = node.title.split('\n')[0]  // Use first line from title if label is empty
        }
        const labelWithIP = ipAddress ? `${displayLabel}\n${ipAddress}` : displayLabel

        return {
          ...node,
          label: labelWithIP,  // Add IP address to label
          shape: visualization.shape,
          icon: {
            code: visualization.unicode,
            size: 60,  // Larger icon size for better visibility
            color: node.color || visualization.color
          },
          font: {
            ...node.font,
            size: 16,  // Larger font for better readability
            multi: 'html',
            bold: true
          },
          size: 40  // Increase node size
        }
      })

      // Enhance edges with bandwidth-based width
      const enhancedEdges = filteredEdges.map((edge: DeviceEdge) => {
        let width = edge.width || 2

        // Parse bandwidth from label if available (format: "↓123.4M ↑56.7M")
        if (edge.label) {
          const match = edge.label.match(/↓(\d+\.?\d*)M/)
          if (match) {
            const bandwidthMbps = parseFloat(match[1])
            // Scale width based on bandwidth: 0-100 Mbps = 2-4px, 100-500 Mbps = 4-6px, 500+ Mbps = 6-10px
            if (bandwidthMbps > 500) {
              width = 8
            } else if (bandwidthMbps > 100) {
              width = 5
            } else if (bandwidthMbps > 10) {
              width = 3
            } else {
              width = 2
            }
          }
        }

        return {
          ...edge,
          width,
          selectionWidth: 2, // Additional width when selected
          hoverWidth: 1.5 // Additional width multiplier on hover
        }
      })

      nodesRef.current = new window.vis.DataSet(enhancedNodes)
      edgesRef.current = new window.vis.DataSet(enhancedEdges)

      // Update statistics
      updateStatistics(data.stats)

      // Create network visualization
      createNetworkVisualization()

      // Force fit after data loads (especially important for small filtered views)
      setTimeout(() => {
        if (networkRef.current) {
          networkRef.current.fit({
            animation: {
              duration: 500,
              easingFunction: 'easeInOutQuad'
            }
          })
        }
      }, 300)

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

    // Creating network visualization
    // Setting up network visualization with container dimensions

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
        selectionWidth: 2,
        hoverWidth: 1.5,
        chosen: {
          edge: function(values: any, _id: any, selected: any, hovering: any) {
            if (hovering || selected) {
              values.width *= 1.5
              values.color = '#5EBBA8'
            }
          }
        }
      },
      physics: {
        enabled: true,
        stabilization: {
          enabled: true,
          iterations: 500,
          fit: true
        },
        hierarchicalRepulsion: {
          nodeDistance: 200,  // Reduced for better small network visibility
          springLength: 250,  // Reduced for better small network visibility
          springConstant: 0.01,
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
        keyboard: true,
        selectConnectedEdges: false,
        hoverConnectedEdges: true
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
      } else if (params.edges.length > 0) {
        // Edge clicked - show bandwidth info
        const edgeId = params.edges[0]
        const edge = edgesRef.current.get(edgeId)
        handleEdgeClick(edge)
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

    // Hover events for nodes
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

    // Hover events for edges - cursor only, vis.js handles visual highlighting
    networkRef.current.on('hoverEdge', () => {
      if (canvasRef.current) {
        canvasRef.current.style.cursor = 'pointer'
      }
    })

    networkRef.current.on('blurEdge', () => {
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

  const handleEdgeClick = (edge: any) => {
    // Create a pseudo-device object to display edge/connection info
    const fromNode = nodesRef.current.get(edge.from)
    const toNode = nodesRef.current.get(edge.to)

    const connectionInfo = {
      id: edge.id,
      label: `Connection: ${fromNode?.label || 'Unknown'} → ${toNode?.label || 'Unknown'}`,
      isEdge: true,
      edgeLabel: edge.label || 'No bandwidth data',
      edgeTitle: edge.title || 'Connection details unavailable',
      fromDevice: fromNode?.label || 'Unknown',
      toDevice: toNode?.label || 'Unknown'
    }

    setSelectedDevice(connectionInfo)
    setShowDetailsPanel(true)
    setInterfaceData(null)
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
              <Select
                value={selectedDeviceId}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
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
                options={[
                  { value: '', label: 'Select a Router or Switch...' },
                  ...networkDevices.map((device) => ({
                    value: device.hostid,
                    label: `${device.display_name} (${device.device_type}) - ${device.branch}`
                  }))
                ]}
                className="flex-1 max-w-md"
              />
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
                    <LoadingSpinner size="lg" text="Loading network visualization..." />
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

                {selectedDevice.isEdge ? (
                  // Display edge/connection information
                  <>
                    <div className="border-t border-gray-200 dark:border-gray-700 pt-3">
                      <label className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 block">
                        Connection Details
                      </label>
                      <div className="space-y-2">
                        <div>
                          <label className="text-xs text-gray-500 dark:text-gray-400">From</label>
                          <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{selectedDevice.fromDevice}</p>
                        </div>
                        <div>
                          <label className="text-xs text-gray-500 dark:text-gray-400">To</label>
                          <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{selectedDevice.toDevice}</p>
                        </div>
                        {selectedDevice.edgeLabel && selectedDevice.edgeLabel !== 'No bandwidth data' && (
                          <div className="bg-ward-green/10 dark:bg-ward-green/20 p-3 rounded-lg mt-2">
                            <label className="text-xs font-medium text-ward-green dark:text-ward-green">Bandwidth</label>
                            <p className="text-sm font-mono text-gray-900 dark:text-gray-100 mt-1">{selectedDevice.edgeLabel}</p>
                          </div>
                        )}
                        {selectedDevice.edgeTitle && (
                          <div className="bg-gray-100 dark:bg-gray-800 p-3 rounded-lg mt-2">
                            <pre className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                              {selectedDevice.edgeTitle}
                            </pre>
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                ) : (
                  // Display device information
                  <>
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
                  </>
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
