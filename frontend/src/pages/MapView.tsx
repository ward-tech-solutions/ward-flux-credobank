import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/Loading'
import { Map, MapPin, Globe } from 'lucide-react'
import { devicesAPI } from '@/services/api'

interface Device {
  id: string
  name: string
  ip: string
  status: 'online' | 'offline'
  region: string
  latitude?: number
  longitude?: number
}

export default function MapView() {
  const [devices, setDevices] = useState<Device[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'online' | 'offline'>('all')
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null)

  useEffect(() => {
    loadDevices()
  }, [])

  const loadDevices = async () => {
    try {
      setLoading(true)
      const response = await devicesAPI.getAll()
      // Mock coordinates for demo
      const devicesWithCoords: Device[] = response.data.map((device: any, index: number) => ({
        id: device.id?.toString() || index.toString(),
        name: device.name || `Device ${index}`,
        ip: device.ip || 'N/A',
        status: device.enabled ? 'online' : 'offline',
        region: device.region || 'Unknown',
        // Mock Georgia coordinates (Tbilisi area)
        latitude: 41.7151 + (Math.random() - 0.5) * 2,
        longitude: 44.8271 + (Math.random() - 0.5) * 3,
      }))
      setDevices(devicesWithCoords)
    } catch (error) {
      console.error('Failed to load devices:', error)
    } finally {
      setLoading(false)
    }
  }

  const filteredDevices = devices.filter(device => {
    if (filter === 'all') return true
    return device.status === filter
  })

  const stats = {
    total: devices.length,
    online: devices.filter(d => d.status === 'online').length,
    offline: devices.filter(d => d.status === 'offline').length,
  }

  // Calculate map bounds
  const mapBounds = {
    minLat: Math.min(...filteredDevices.map(d => d.latitude || 0)),
    maxLat: Math.max(...filteredDevices.map(d => d.latitude || 0)),
    minLng: Math.min(...filteredDevices.map(d => d.longitude || 0)),
    maxLng: Math.max(...filteredDevices.map(d => d.longitude || 0)),
  }

  const centerLat = (mapBounds.minLat + mapBounds.maxLat) / 2 || 41.7151
  const centerLng = (mapBounds.minLng + mapBounds.maxLng) / 2 || 44.8271

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Network Map</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Geographical view of network devices</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              filter === 'all'
                ? 'bg-ward-green text-white'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
            }`}
          >
            <Globe className="h-4 w-4 inline-block mr-2" />
            All ({stats.total})
          </button>
          <button
            onClick={() => setFilter('online')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              filter === 'online'
                ? 'bg-green-500 text-white'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
            }`}
          >
            Online ({stats.online})
          </button>
          <button
            onClick={() => setFilter('offline')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              filter === 'offline'
                ? 'bg-red-500 text-white'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
            }`}
          >
            Offline ({stats.offline})
          </button>
        </div>
      </div>

      {/* Map Container */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <Card className="lg:col-span-3">
          <CardContent className="p-6">
            {loading ? (
              <div className="flex items-center justify-center h-[600px]">
                <LoadingSpinner size="lg" />
              </div>
            ) : (
              <div className="relative bg-gray-100 dark:bg-gray-900 rounded-lg h-[600px] overflow-hidden">
                {/* Placeholder map background with Georgia outline */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="text-center">
                    <Map className="h-24 w-24 text-gray-300 dark:text-gray-700 mx-auto mb-4" />
                    <p className="text-gray-400 dark:text-gray-600 font-medium">Georgia Network Map</p>
                    <p className="text-sm text-gray-400 dark:text-gray-600 mt-2">
                      Center: {centerLat.toFixed(4)}, {centerLng.toFixed(4)}
                    </p>
                  </div>
                </div>

                {/* Device Markers */}
                {filteredDevices.map((device) => {
                  // Calculate position as percentage
                  const x = ((device.longitude! - mapBounds.minLng) / (mapBounds.maxLng - mapBounds.minLng)) * 100
                  const y = ((mapBounds.maxLat - device.latitude!) / (mapBounds.maxLat - mapBounds.minLat)) * 100

                  return (
                    <div
                      key={device.id}
                      className={`absolute cursor-pointer transition-transform hover:scale-125 ${
                        selectedDevice?.id === device.id ? 'z-10 scale-125' : 'z-0'
                      }`}
                      style={{
                        left: `${x}%`,
                        top: `${y}%`,
                        transform: 'translate(-50%, -50%)',
                      }}
                      onClick={() => setSelectedDevice(device)}
                      title={device.name}
                    >
                      <div className={`relative`}>
                        <MapPin
                          className={`h-8 w-8 ${
                            device.status === 'online' ? 'text-green-500' : 'text-red-500'
                          } drop-shadow-lg`}
                          fill="currentColor"
                        />
                        {selectedDevice?.id === device.id && (
                          <div className="absolute top-full left-1/2 transform -translate-x-1/2 mt-2 bg-white dark:bg-gray-800 rounded-lg shadow-xl p-3 min-w-[200px] border border-gray-200 dark:border-gray-700">
                            <p className="font-semibold text-gray-900 dark:text-gray-100">{device.name}</p>
                            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{device.ip}</p>
                            <div className="mt-2">
                              <Badge variant={device.status === 'online' ? 'success' : 'danger'} dot>
                                {device.status.toUpperCase()}
                              </Badge>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Legend and Info */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Legend</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-2">
                <MapPin className="h-6 w-6 text-green-500" fill="currentColor" />
                <span className="text-sm text-gray-700 dark:text-gray-300">Online Device</span>
              </div>
              <div className="flex items-center gap-2">
                <MapPin className="h-6 w-6 text-red-500" fill="currentColor" />
                <span className="text-sm text-gray-700 dark:text-gray-300">Offline Device</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Statistics</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500 dark:text-gray-400">Total Devices</span>
                <span className="font-semibold text-gray-900 dark:text-gray-100">{stats.total}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500 dark:text-gray-400">Online</span>
                <Badge variant="success">{stats.online}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500 dark:text-gray-400">Offline</span>
                <Badge variant="danger">{stats.offline}</Badge>
              </div>
              <div className="flex items-center justify-between pt-3 border-t border-gray-200 dark:border-gray-700">
                <span className="text-sm text-gray-500 dark:text-gray-400">Availability</span>
                <span className="font-semibold text-ward-green">
                  {stats.total > 0 ? ((stats.online / stats.total) * 100).toFixed(1) : 0}%
                </span>
              </div>
            </CardContent>
          </Card>

          {selectedDevice && (
            <Card>
              <CardHeader>
                <CardTitle>Selected Device</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Name</p>
                  <p className="font-semibold text-gray-900 dark:text-gray-100 mt-1">{selectedDevice.name}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">IP Address</p>
                  <p className="font-mono text-sm text-gray-900 dark:text-gray-100 mt-1">{selectedDevice.ip}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Region</p>
                  <p className="text-sm text-gray-900 dark:text-gray-100 mt-1">{selectedDevice.region}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Status</p>
                  <div className="mt-1">
                    <Badge variant={selectedDevice.status === 'online' ? 'success' : 'danger'} dot>
                      {selectedDevice.status.toUpperCase()}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
