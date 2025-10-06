import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import MarkerClusterGroup from 'react-leaflet-cluster'
import L from 'leaflet'
import { useQuery } from '@tanstack/react-query'
import { devicesAPI } from '@/services/api'
import { Card, CardContent } from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import { MapPin, Globe, CheckCircle, XCircle } from 'lucide-react'
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
}

// Component to fit map bounds to markers
function MapBounds({ devices, filter }: { devices: Device[]; filter: string }) {
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
  }, [devices, filter, map])

  return null
}

export default function Map() {
  const [filter, setFilter] = useState<'all' | 'online' | 'offline'>('all')
  const [selectedRegion, setSelectedRegion] = useState<string>('')

  const { data: devicesResponse, isLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesAPI.getAll(),
    refetchInterval: 30000, // Auto-refresh every 30 seconds
  })

  const devices: Device[] = devicesResponse?.data || []

  // Apply filters
  const filteredDevices = devices.filter(device => {
    // Region filter
    if (selectedRegion && device.region !== selectedRegion) return false

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
    total: devices.length,
    online: devices.filter(d => d.ping_status === 'Up' || d.available === 'Available').length,
    offline: devices.filter(d => d.ping_status === 'Down' || d.available === 'Unavailable').length,
  }

  // Create custom marker icon
  const createMarkerIcon = (isOnline: boolean, count: number = 1) => {
    const color = isOnline ? '#10b981' : '#ef4444' // green-500 : red-500
    return L.divIcon({
      html: `
        <div style="
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

      {/* Region Selector */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Jump to region:</label>
            <select
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
              className="flex-1 max-w-xs px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-ward-green focus:border-transparent"
            >
              <option value="">All Regions</option>
              {regions.map(region => (
                <option key={region} value={region}>{region}</option>
              ))}
            </select>
            {selectedRegion && (
              <button
                onClick={() => setSelectedRegion('')}
                className="px-4 py-2 text-sm font-medium text-ward-green hover:bg-ward-green/10 rounded-lg transition-colors"
              >
                Reset View
              </button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Map */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="h-[600px] flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-ward-green mx-auto mb-4"></div>
                <p className="text-gray-500 dark:text-gray-400">Loading map...</p>
              </div>
            </div>
          ) : (
            <div className="h-[600px] relative">
              <MapContainer
                center={GEORGIA_CENTER}
                zoom={7}
                minZoom={6}
                maxZoom={18}
                className="h-full w-full rounded-lg"
                scrollWheelZoom={true}
              >
                {/* Tile Layers */}
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                  url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                  maxZoom={18}
                />

                {/* Device Markers with Clustering */}
                <MarkerClusterGroup
                  chunkedLoading
                  maxClusterRadius={60}
                  spiderfyOnMaxZoom={true}
                  showCoverageOnHover={false}
                  zoomToBoundsOnClick={true}
                  iconCreateFunction={(cluster) => {
                    const markers = cluster.getAllChildMarkers()
                    const count = markers.length
                    const onlineCount = markers.filter((m: any) => {
                      const device = m.options.device
                      return device.ping_status === 'Up' || device.available === 'Available'
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
                        ">
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

                    return (
                      <Marker
                        key={index}
                        position={[firstDevice.latitude, firstDevice.longitude]}
                        icon={createMarkerIcon(allOnline, group.length)}
                        device={firstDevice} // Pass device data for clustering
                      >
                        <Popup maxWidth={350} maxHeight={400}>
                          <div className="p-2 bg-white dark:bg-gray-800">
                            <div className="border-b border-gray-200 dark:border-gray-700 pb-2 mb-3">
                              <h3 className="font-bold text-gray-900 dark:text-gray-100 text-lg">
                                {firstDevice.branch}
                              </h3>
                              <p className="text-sm text-gray-500 dark:text-gray-400">{firstDevice.region}</p>
                            </div>

                            {/* Stats */}
                            <div className="grid grid-cols-3 gap-3 mb-3">
                              <div className="text-center">
                                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{group.length}</div>
                                <div className="text-xs text-gray-500 dark:text-gray-400">Total</div>
                              </div>
                              <div className="text-center">
                                <div className="text-2xl font-bold text-green-600 dark:text-green-400">{onlineCount}</div>
                                <div className="text-xs text-gray-500 dark:text-gray-400">Online</div>
                              </div>
                              <div className="text-center">
                                <div className="text-2xl font-bold text-red-600 dark:text-red-400">{group.length - onlineCount}</div>
                                <div className="text-xs text-gray-500 dark:text-gray-400">Offline</div>
                              </div>
                            </div>

                            {/* Device List */}
                            <div className="border-t border-gray-200 dark:border-gray-700 pt-2 max-h-48 overflow-y-auto">
                              <div className="space-y-2">
                                {group.map((device, idx) => {
                                  const isOnline = device.ping_status === 'Up' || device.available === 'Available'
                                  return (
                                    <div key={idx} className="flex items-start justify-between gap-2 text-sm">
                                      <div className="flex-1 min-w-0">
                                        <div className="font-medium text-gray-900 dark:text-gray-100 truncate">
                                          {device.display_name}
                                        </div>
                                        <div className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                                          {device.ip}
                                        </div>
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

                            {/* View Devices Button */}
                            <button
                              onClick={() => window.location.href = `/devices?search=${encodeURIComponent(firstDevice.branch)}`}
                              className="mt-3 w-full px-3 py-2 bg-ward-green text-white rounded-lg hover:bg-ward-green-dark transition-colors text-sm font-medium"
                            >
                              View Devices
                            </button>
                          </div>
                        </Popup>
                      </Marker>
                    )
                  })}
                </MarkerClusterGroup>

                {/* Auto-fit bounds */}
                <MapBounds devices={filteredDevices} filter={filter} />
              </MapContainer>

              {/* Legend Overlay */}
              <div className="absolute bottom-4 left-4 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4 z-[1000] border border-gray-200 dark:border-gray-700">
                <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">Legend</div>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-green-500 border-2 border-white shadow"></div>
                    <span className="text-gray-700 dark:text-gray-300">Online Device</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-red-500 border-2 border-white shadow"></div>
                    <span className="text-gray-700 dark:text-gray-300">Offline Device</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded-full bg-orange-500 border-2 border-white shadow flex items-center justify-center text-white text-xs font-bold">
                      5
                    </div>
                    <span className="text-gray-700 dark:text-gray-300">Device Cluster</span>
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
