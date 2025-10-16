import { useEffect, useState, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import MarkerClusterGroup from 'react-leaflet-cluster'
import L from 'leaflet'
import { useQuery } from '@tanstack/react-query'
import { devicesAPI } from '@/services/api'
import { Card, CardContent } from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import Select from '@/components/ui/Select'
import MultiSelect from '@/components/ui/MultiSelect'
import Input from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/Loading'
import { Globe, CheckCircle, XCircle, Search, AlertCircle } from 'lucide-react'
import 'leaflet/dist/leaflet.css'

// Fix for default marker icons in Leaflet
import icon from 'leaflet/dist/images/marker-icon.png'
import iconShadow from 'leaflet/dist/images/marker-shadow.png'

const DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
})

L.Marker.prototype.options.icon = DefaultIcon

// Georgia center coordinates
const GEORGIA_CENTER: [number, number] = [42.3154, 43.3569]

interface Device {
  hostid: string
  display_name: string
  ip: string
  branch: string
  region: string
  ping_status: string
  available?: string
  device_type: string
  latitude?: number
  longitude?: number
  problems: number
  ping_response_time?: number | null
  triggers?: any[]
  last_check?: number
}

// Helper to check if device is recently down (< 10 minutes)
const isRecentlyDown = (device: Device): boolean => {
  if (device.ping_status !== 'Down') return false

  if (device.triggers && device.triggers.length > 0) {
    const problemStart = parseInt(device.triggers[0].lastchange) * 1000
    const now = Date.now()
    const tenMinutes = 10 * 60 * 1000
    return (now - problemStart) < tenMinutes
  }

  return false
}

// Component to fit map bounds to markers
function MapBounds({ devices, filter, searchQuery }: { devices: Device[]; filter: string; searchQuery: string }) {
  const map = useMap()

  useEffect(() => {
    if (devices.length === 0) return

    const validDevices = devices.filter(d => d.latitude && d.longitude)
    if (validDevices.length === 0) {
      map.setView(GEORGIA_CENTER, 7)
      return
    }

    const bounds = L.latLngBounds(
      validDevices.map(d => [d.latitude!, d.longitude!] as [number, number])
    )
    map.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 })
  }, [devices, filter, searchQuery, map])

  return null
}

export default function Map() {
  const [filter, setFilter] = useState<'all' | 'online' | 'offline'>('all')
  const [selectedRegions, setSelectedRegions] = useState<string[]>([])
  const [deviceTypeFilter, setDeviceTypeFilter] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  const mapRef = useRef<L.Map | null>(null)

  const { data: devicesResponse, isLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesAPI.getAll(),
    refetchInterval: 30000, // Auto-refresh every 30 seconds
  })

  const devices: Device[] = devicesResponse?.data || []

  // Get unique device types
  const deviceTypes = Array.from(new Set(devices.map(d => d.device_type))).filter(Boolean).sort()

  // Apply filters
  const filteredDevices = devices.filter(device => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      const matchesSearch = device.display_name.toLowerCase().includes(query) ||
                           device.ip.toLowerCase().includes(query) ||
                           device.branch?.toLowerCase().includes(query)
      if (!matchesSearch) return false
    }

    // Region filter - support multiple regions
    if (selectedRegions.length > 0 && !selectedRegions.includes(device.region)) return false

    // Device type filter
    if (deviceTypeFilter && device.device_type !== deviceTypeFilter) return false

    // Status filter
    if (filter === 'online') {
      return device.ping_status === 'Up' || device.available === 'Available'
    } else if (filter === 'offline') {
      return device.ping_status === 'Down' || device.available === 'Unavailable'
    }
    return true
  })

  // Get unique regions
  const regions = Array.from(new Set(devices.map(d => d.region))).filter(Boolean).sort()

  // Calculate stats
  const stats = {
    total: filteredDevices.length,
    online: filteredDevices.filter(d => d.ping_status === 'Up' || d.available === 'Available').length,
    offline: filteredDevices.filter(d => d.ping_status === 'Down' || d.available === 'Unavailable').length,
  }

  // Calculate region stats
  const regionStats = regions.map(region => {
    const regionDevices = devices.filter(d => d.region === region)
    const online = regionDevices.filter(d => d.ping_status === 'Up' || d.available === 'Available').length
    const total = regionDevices.length
    const uptime = total > 0 ? ((online / total) * 100).toFixed(1) : '0'
    return { region, total, online, offline: total - online, uptime }
  }).sort((a, b) => parseFloat(a.uptime) - parseFloat(b.uptime))

  // Create custom marker icon with pulse animation for recently down devices
  const createMarkerIcon = (isOnline: boolean, count: number = 1, isRecent: boolean = false) => {
    const color = isOnline ? '#10b981' : '#ef4444' // green-500 : red-500
    const uniqueId = `marker-${Math.random().toString(36).substr(2, 9)}`
    const pulseKeyframes = `
      @keyframes ${uniqueId}-pulse {
        0%, 100% {
          transform: scale(1);
          opacity: 1;
          box-shadow: 0 2px 8px rgba(0,0,0,0.3), 0 0 0 0 rgba(239, 68, 68, 0.7);
        }
        50% {
          transform: scale(1.15);
          opacity: 0.9;
          box-shadow: 0 2px 12px rgba(0,0,0,0.4), 0 0 0 10px rgba(239, 68, 68, 0);
        }
      }
    `

    return L.divIcon({
      html: `
        ${isRecent ? `<style>${pulseKeyframes}</style>` : ''}
        <div class="${uniqueId}" style="
          background: ${color};
          width: 32px;
          height: 32px;
          border-radius: 50%;
          border: 3px solid white;
          box-shadow: 0 2px 8px rgba(0,0,0,0.3);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-weight: bold;
          font-size: 12px;
          ${isRecent ? `animation: ${uniqueId}-pulse 2s ease-in-out infinite;` : ''}
        ">
          ${count > 1 ? count : ''}
        </div>
      `,
      className: '',
      iconSize: [32, 32],
      iconAnchor: [16, 16],
      popupAnchor: [0, -16],
    })
  }

  // Group devices by location
  const groupDevicesByLocation = (devices: Device[]) => {
    const groups: { [key: string]: Device[] } = {}

    devices.forEach(device => {
      if (!device.latitude || !device.longitude) return

      const key = `${device.latitude.toFixed(6)},${device.longitude.toFixed(6)}`
      if (!groups[key]) {
        groups[key] = []
      }
      groups[key].push(device)
    })

    return Object.values(groups)
  }

  const deviceGroups = groupDevicesByLocation(filteredDevices)

  // Handle search and zoom to device
  const handleSearch = (query: string) => {
    setSearchQuery(query)

    if (query.length > 2 && mapRef.current) {
      const matchedDevice = devices.find(d =>
        d.display_name.toLowerCase().includes(query.toLowerCase()) &&
        d.latitude && d.longitude
      )

      if (matchedDevice && matchedDevice.latitude && matchedDevice.longitude) {
        mapRef.current.setView([matchedDevice.latitude, matchedDevice.longitude], 14)
      }
    }
  }

  const clearFilters = () => {
    setFilter('all')
    setSelectedRegions([])
    setDeviceTypeFilter('')
    setSearchQuery('')
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Georgia Network Map</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Geographical view of all network devices</p>
        </div>

        {/* Filter Buttons */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${
              filter === 'all'
                ? 'bg-ward-green text-white shadow-md'
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            <Globe className="h-4 w-4" />
            All ({stats.total})
          </button>
          <button
            onClick={() => setFilter('online')}
            className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${
              filter === 'online'
                ? 'bg-green-500 text-white shadow-md'
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            <CheckCircle className="h-4 w-4" />
            Online ({stats.online})
          </button>
          <button
            onClick={() => setFilter('offline')}
            className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${
              filter === 'offline'
                ? 'bg-red-500 text-white shadow-md'
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            <XCircle className="h-4 w-4" />
            Offline ({stats.offline})
          </button>
        </div>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                type="text"
                placeholder="Search devices..."
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                className="pl-10"
              />
            </div>

            {/* Region Filter */}
            <MultiSelect
              options={regions}
              selected={selectedRegions}
              onChange={setSelectedRegions}
              placeholder="All Regions"
            />

            {/* Device Type Filter */}
            <Select
              value={deviceTypeFilter}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setDeviceTypeFilter(e.target.value)}
              options={[
                { value: '', label: 'All Device Types' },
                ...deviceTypes.map(type => ({ value: type, label: type }))
              ]}
            />

            {/* Clear Filters */}
            {(selectedRegions.length > 0 || deviceTypeFilter || searchQuery || filter !== 'all') && (
              <button
                onClick={clearFilters}
                className="px-4 py-2 text-sm font-medium text-ward-green hover:bg-ward-green/10 rounded-lg transition-colors"
              >
                Clear All Filters
              </button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Region Statistics Panel */}
      {regionStats.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">Regional Overview</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {regionStats.slice(0, 6).map(({ region, online, offline, uptime }) => {
                const isSelected = selectedRegions.includes(region)
                return (
                  <div
                    key={region}
                    className={`p-3 rounded-lg border transition-colors cursor-pointer ${
                      isSelected
                        ? 'border-ward-green bg-ward-green/10 dark:bg-ward-green/20'
                        : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
                    }`}
                    onClick={() => {
                      if (isSelected) {
                        setSelectedRegions(selectedRegions.filter(r => r !== region))
                      } else {
                        setSelectedRegions([...selectedRegions, region])
                      }
                    }}
                  >
                    <div className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">{region}</div>
                    <div className="mt-1 flex items-baseline gap-2">
                      <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">{uptime}%</span>
                      <span className="text-xs text-gray-500">uptime</span>
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-xs">
                      <span className="text-green-600 dark:text-green-400">{online}</span>
                      <span className="text-gray-400">/</span>
                      <span className="text-red-600 dark:text-red-400">{offline}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Map */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="h-[600px] flex items-center justify-center">
              <div className="text-center">
                <LoadingSpinner size="lg" text="Loading map..." />
              </div>
            </div>
          ) : (
            <div className="h-[600px] relative">
              <MapContainer
                center={GEORGIA_CENTER}
                zoom={7}
                minZoom={6}
                maxZoom={19}
                className="h-full w-full rounded-lg"
                scrollWheelZoom={true}
                ref={mapRef as any}
              >
                {/* OpenStreetMap Tile Layer */}
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  maxZoom={19}
                />

                {/* Device Markers with Clustering */}
                <MarkerClusterGroup
                  chunkedLoading
                  maxClusterRadius={60}
                  spiderfyOnMaxZoom={true}
                  showCoverageOnHover={true}
                  zoomToBoundsOnClick={true}
                  iconCreateFunction={(cluster: any) => {
                    const markers = cluster.getAllChildMarkers()
                    const count = markers.length
                    const onlineCount = markers.filter((m: any) => {
                      const device = m.options.device
                      return device && (device.ping_status === 'Up' || device.available === 'Available')
                    }).length
                    const allOnline = onlineCount === count
                    const allOffline = onlineCount === 0

                    let backgroundColor = '#f59e0b' // mixed (orange)
                    if (allOnline) backgroundColor = '#10b981' // green
                    if (allOffline) backgroundColor = '#ef4444' // red

                    return L.divIcon({
                      html: `
                        <div style="
                          background: ${backgroundColor};
                          width: 40px;
                          height: 40px;
                          border-radius: 50%;
                          border: 3px solid white;
                          box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                          display: flex;
                          align-items: center;
                          justify-content: center;
                          color: white;
                          font-weight: bold;
                          font-size: 14px;
                        " title="${count} devices: ${onlineCount} online, ${count - onlineCount} offline">
                          ${count}
                        </div>
                      `,
                      className: '',
                      iconSize: [40, 40],
                      iconAnchor: [20, 20],
                    })
                  }}
                >
                  {deviceGroups.map((group, index) => {
                    const firstDevice = group[0]
                    if (!firstDevice.latitude || !firstDevice.longitude) return null

                    const onlineCount = group.filter(d =>
                      d.ping_status === 'Up' || d.available === 'Available'
                    ).length
                    const allOnline = onlineCount === group.length
                    const hasRecentlyDown = group.some(isRecentlyDown)

                    return (
                      <Marker
                        key={index}
                        position={[firstDevice.latitude, firstDevice.longitude]}
                        icon={createMarkerIcon(allOnline, group.length, hasRecentlyDown)}
                      >
                        <Popup maxWidth={400} maxHeight={450}>
                          <div className="p-2 bg-white dark:bg-gray-800">
                            <div className="border-b border-gray-200 dark:border-gray-700 pb-2 mb-3">
                              <h3 className="font-bold text-gray-900 dark:text-gray-100 text-lg">
                                {firstDevice.branch}
                              </h3>
                              <p className="text-sm text-gray-500 dark:text-gray-400">{firstDevice.region}</p>
                            </div>

                            {/* Stats */}
                            <div className="grid grid-cols-3 gap-3 mb-3">
                              <div className="text-center p-2 bg-gray-50 dark:bg-gray-900 rounded-lg">
                                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{group.length}</div>
                                <div className="text-xs text-gray-500 dark:text-gray-400">Total</div>
                              </div>
                              <div className="text-center p-2 bg-green-50 dark:bg-green-900/20 rounded-lg">
                                <div className="text-2xl font-bold text-green-600 dark:text-green-400">{onlineCount}</div>
                                <div className="text-xs text-gray-500 dark:text-gray-400">Online</div>
                              </div>
                              <div className="text-center p-2 bg-red-50 dark:bg-red-900/20 rounded-lg">
                                <div className="text-2xl font-bold text-red-600 dark:text-red-400">{group.length - onlineCount}</div>
                                <div className="text-xs text-gray-500 dark:text-gray-400">Offline</div>
                              </div>
                            </div>

                            {/* Device List */}
                            <div className="border-t border-gray-200 dark:border-gray-700 pt-2 max-h-48 overflow-y-auto">
                              <div className="space-y-2">
                                {group.map((device, idx) => {
                                  const isOnline = device.ping_status === 'Up' || device.available === 'Available'
                                  const isRecent = isRecentlyDown(device)
                                  return (
                                    <div
                                      key={idx}
                                      className={`flex items-start justify-between gap-2 text-sm p-2 rounded ${
                                        isRecent ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800' : ''
                                      }`}
                                    >
                                      <div className="flex-1 min-w-0">
                                        <div className="font-medium text-gray-900 dark:text-gray-100 truncate flex items-center gap-1">
                                          {device.display_name}
                                          {isRecent && <AlertCircle className="h-3 w-3 text-red-500" />}
                                        </div>
                                        <div className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                                          {device.ip}
                                        </div>
                                        {device.device_type && (
                                          <div className="text-xs text-gray-400 dark:text-gray-500">
                                            {device.device_type}
                                          </div>
                                        )}
                                      </div>
                                      <Badge
                                        variant={isOnline ? 'success' : 'danger'}
                                        size="sm"
                                        dot
                                      >
                                        {isOnline ? 'Up' : 'Down'}
                                      </Badge>
                                    </div>
                                  )
                                })}
                              </div>
                            </div>

                            {/* Actions */}
                            <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                              <Button
                                onClick={() => window.location.href = `/devices?search=${encodeURIComponent(firstDevice.branch)}`}
                                size="sm"
                                variant="outline"
                              >
                                View Devices
                              </Button>
                              <Button
                                onClick={() => window.location.href = `/monitor?region=${encodeURIComponent(firstDevice.region)}`}
                                size="sm"
                              >
                                Monitor Region
                              </Button>
                            </div>
                          </div>
                        </Popup>
                      </Marker>
                    )
                  })}
                </MarkerClusterGroup>

                {/* Auto-fit bounds */}
                <MapBounds devices={filteredDevices} filter={filter} searchQuery={searchQuery} />
              </MapContainer>

              {/* Enhanced Legend Overlay */}
              <div className="absolute bottom-4 left-4 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4 z-[1000] border border-gray-200 dark:border-gray-700">
                <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">Legend</div>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-green-500 border-2 border-white shadow"></div>
                    <span className="text-gray-700 dark:text-gray-300">Online Device ({devices.filter(d => d.ping_status === 'Up').length})</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-red-500 border-2 border-white shadow"></div>
                    <span className="text-gray-700 dark:text-gray-300">Offline Device ({devices.filter(d => d.ping_status === 'Down').length})</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded-full bg-orange-500 border-2 border-white shadow flex items-center justify-center text-white text-xs font-bold">
                      5
                    </div>
                    <span className="text-gray-700 dark:text-gray-300">Mixed Status Cluster</span>
                  </div>
                  <div className="flex items-center gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                    <div className="w-4 h-4 rounded-full bg-red-500 border-2 border-white shadow animate-pulse"></div>
                    <span className="text-gray-700 dark:text-gray-300">Recently Down (&lt;10m)</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
