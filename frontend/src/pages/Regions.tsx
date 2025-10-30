import { useState, useMemo, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Loading'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import Select from '@/components/ui/Select'
import Input from '@/components/ui/Input'
import DeviceDetailsModal from '@/components/DeviceDetailsModal'
import SSHTerminalModal from '@/components/SSHTerminalModal'
import { devicesAPI, Device } from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'
import { MapPin, ChevronRight, Wifi, Filter, Search, Eye, Terminal } from 'lucide-react'
import { toast } from 'sonner'

type RegionStats = {
  total: number
  online: number
  offline: number
}

type CityStats = {
  total: number
  online: number
  offline: number
  devices: Device[]
}

export default function Regions() {
  const navigate = useNavigate()
  const { user, isAdmin, isRegionalManager } = useAuth()
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null)
  const [selectedCity, setSelectedCity] = useState<string | null>(null)
  const [showAllDevicesInRegion, setShowAllDevicesInRegion] = useState(false)

  // RBAC: Only admins and regional managers can access Regions page
  useEffect(() => {
    if (!isAdmin && !isRegionalManager) {
      toast.error('Access Denied', {
        description: 'You do not have permission to access Regions. Admin or Regional Manager role required.',
      })
      navigate('/')
    }
  }, [isAdmin, isRegionalManager, navigate])

  // Show nothing while redirecting
  if (!isAdmin && !isRegionalManager) {
    return null
  }
  const [deviceTypeFilter, setDeviceTypeFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')

  // Modal states
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null)
  const [sshModalOpen, setSSHModalOpen] = useState(false)
  const [sshDeviceName, setSSHDeviceName] = useState('')
  const [sshDeviceIP, setSSHDeviceIP] = useState('')

  const { data: devicesResponse, isLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesAPI.getAll(),
  })

  const devices = devicesResponse?.data || []

  // Device type filters based on old UI
  const deviceTypes = ['all', 'ATM', 'Paybox', 'NVR', 'Biostar', 'Router', 'Switch', 'Access Point']

  // Group devices by region
  const regionStats = useMemo(() => {
    const stats: Record<string, RegionStats> = {}

    devices.forEach((device: Device) => {
      const region = device.region || 'Unknown'
      if (!stats[region]) {
        stats[region] = { total: 0, online: 0, offline: 0 }
      }

      stats[region].total++

      // Use old UI logic: ping_status === 'Up' OR available === 'Available'
      if (device.ping_status === 'Up' || device.available === 'Available') {
        stats[region].online++
      } else if (device.ping_status === 'Down' || device.available === 'Unavailable') {
        stats[region].offline++
      }
    })

    return stats
  }, [devices])

  // Group devices by city within selected region
  const cityStats = useMemo(() => {
    if (!selectedRegion) return {}

    const stats: Record<string, CityStats> = {}

    devices
      .filter((d: Device) => d.region === selectedRegion)
      .forEach((device: Device) => {
        const city = device.branch || 'Unknown'
        if (!stats[city]) {
          stats[city] = { total: 0, online: 0, offline: 0, devices: [] }
        }

        stats[city].total++
        stats[city].devices.push(device)

        // Use old UI logic: ping_status === 'Up' OR available === 'Available'
        if (device.ping_status === 'Up' || device.available === 'Available') {
          stats[city].online++
        } else if (device.ping_status === 'Down' || device.available === 'Unavailable') {
          stats[city].offline++
        }
      })

    return stats
  }, [devices, selectedRegion])

  // Get devices for selected city with type filter
  const cityDevices = useMemo(() => {
    if (!selectedCity || !cityStats[selectedCity]) return []

    let filtered = cityStats[selectedCity].devices

    if (deviceTypeFilter !== 'all') {
      filtered = filtered.filter((d: Device) => d.device_type === deviceTypeFilter)
    }

    return filtered
  }, [selectedCity, cityStats, deviceTypeFilter])

  // Get all devices in selected region with filters (for "All Devices" view)
  const allRegionDevices = useMemo(() => {
    if (!selectedRegion || !showAllDevicesInRegion) return []

    let filtered = devices.filter((d: Device) => d.region === selectedRegion)

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter((d: Device) =>
        d.display_name.toLowerCase().includes(query) ||
        d.ip.toLowerCase().includes(query) ||
        d.branch.toLowerCase().includes(query)
      )
    }

    // Apply device type filter
    if (deviceTypeFilter !== 'all') {
      filtered = filtered.filter((d: Device) => d.device_type === deviceTypeFilter)
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      if (statusFilter === 'online') {
        filtered = filtered.filter((d: Device) => d.ping_status === 'Up' || d.available === 'Available')
      } else if (statusFilter === 'offline') {
        filtered = filtered.filter((d: Device) => d.ping_status === 'Down' || d.available === 'Unavailable')
      }
    }

    return filtered
  }, [devices, selectedRegion, showAllDevicesInRegion, searchQuery, deviceTypeFilter, statusFilter])

  const handleViewDevice = (hostid: string) => {
    setSelectedDeviceId(hostid)
  }

  const handleOpenSSH = (deviceName: string, deviceIP: string) => {
    setSSHDeviceName(deviceName)
    setSSHDeviceIP(deviceIP)
    setSSHModalOpen(true)
  }

  const handleViewAllDevices = () => {
    setShowAllDevicesInRegion(true)
    setSelectedCity(null)
  }

  const handleBackToRegion = () => {
    setShowAllDevicesInRegion(false)
    setSelectedCity(null)
    setDeviceTypeFilter('all')
    setStatusFilter('all')
    setSearchQuery('')
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton variant="card" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} variant="card" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Regions</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            {selectedCity
              ? `Viewing devices in ${selectedCity}`
              : showAllDevicesInRegion
              ? `All devices in ${selectedRegion} (${allRegionDevices.length} devices)`
              : selectedRegion
              ? `Viewing cities in ${selectedRegion}`
              : 'View devices by region and city'}
          </p>
        </div>

        {/* Breadcrumb Navigation */}
        {(selectedRegion || selectedCity) && (
          <div className="flex items-center gap-2 text-sm">
            <button
              onClick={() => {
                setSelectedRegion(null)
                setSelectedCity(null)
                setShowAllDevicesInRegion(false)
                setDeviceTypeFilter('all')
                setStatusFilter('all')
                setSearchQuery('')
              }}
              className="text-ward-green hover:text-ward-green-dark font-medium"
            >
              All Regions
            </button>
            {selectedRegion && (
              <>
                <ChevronRight className="h-4 w-4 text-gray-400" />
                <button
                  onClick={handleBackToRegion}
                  className="text-ward-green hover:text-ward-green-dark font-medium"
                >
                  {selectedRegion}
                </button>
              </>
            )}
            {selectedCity && (
              <>
                <ChevronRight className="h-4 w-4 text-gray-400" />
                <span className="text-gray-900 dark:text-gray-100 font-medium">{selectedCity}</span>
              </>
            )}
            {showAllDevicesInRegion && !selectedCity && (
              <>
                <ChevronRight className="h-4 w-4 text-gray-400" />
                <span className="text-gray-900 dark:text-gray-100 font-medium">All Devices</span>
              </>
            )}
          </div>
        )}
      </div>

      {/* Filters (show when viewing city or all devices in region) */}
      {(selectedCity || showAllDevicesInRegion) && (
        <Card>
          <CardContent className="p-4">
            <div className="space-y-4">
              {/* Search and Status filter for All Devices view */}
              {showAllDevicesInRegion && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <Input
                    placeholder="Search by name, IP, or branch..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    icon={<Search className="h-5 w-5" />}
                  />
                  <Select
                    value={statusFilter}
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setStatusFilter(e.target.value)}
                    options={[
                      { value: 'all', label: 'All Status' },
                      { value: 'online', label: 'Online' },
                      { value: 'offline', label: 'Offline' },
                    ]}
                  />
                  <Select
                    value={deviceTypeFilter}
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setDeviceTypeFilter(e.target.value)}
                    options={[
                      { value: 'all', label: 'All Types' },
                      ...deviceTypes.filter(t => t !== 'all').map(type => ({ value: type, label: type })),
                    ]}
                  />
                </div>
              )}

              {/* Device type buttons for city view */}
              {selectedCity && !showAllDevicesInRegion && (
                <div className="flex items-center gap-4">
                  <Filter className="h-5 w-5 text-gray-500 dark:text-gray-400" />
                  <div className="flex gap-2 flex-wrap">
                    {deviceTypes.map((type) => (
                      <button
                        key={type}
                        onClick={() => setDeviceTypeFilter(type)}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                          deviceTypeFilter === type
                            ? 'bg-ward-green text-white'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600'
                        }`}
                      >
                        {type === 'all' ? 'All Types' : type}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Region List */}
      {!selectedRegion && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Object.entries(regionStats)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([region, stats]) => (
              <Card
                key={region}
                hover
                onClick={() => setSelectedRegion(region)}
                className="cursor-pointer"
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-3 bg-ward-green/10 rounded-lg">
                        <MapPin className="h-6 w-6 text-ward-green" />
                      </div>
                      <div>
                        <CardTitle className="text-lg">{region}</CardTitle>
                        <p className="text-sm text-gray-500 mt-1">{stats.total} devices</p>
                      </div>
                    </div>
                    <ChevronRight className="h-5 w-5 text-gray-400" />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex gap-4">
                    <div className="flex-1">
                      <div className="text-sm text-gray-500 mb-1">Online</div>
                      <div className="flex items-center gap-2">
                        <div className="text-2xl font-bold text-green-600">{stats.online}</div>
                        <Badge variant="success" dot>
                          {stats.total > 0 ? Math.round((stats.online / stats.total) * 100) : 0}%
                        </Badge>
                      </div>
                    </div>
                    <div className="flex-1">
                      <div className="text-sm text-gray-500 mb-1">Offline</div>
                      <div className="flex items-center gap-2">
                        <div className="text-2xl font-bold text-red-600">{stats.offline}</div>
                        <Badge variant="danger" dot>
                          {stats.total > 0 ? Math.round((stats.offline / stats.total) * 100) : 0}%
                        </Badge>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
        </div>
      )}

      {/* City List */}
      {selectedRegion && !selectedCity && !showAllDevicesInRegion && (
        <>
          {/* View All Devices Button */}
          <Card>
            <CardContent className="p-4">
              <Button
                onClick={handleViewAllDevices}
                className="w-full bg-ward-green hover:bg-ward-green/90"
              >
                <Wifi className="h-5 w-5 mr-2" />
                View All Devices in {selectedRegion} ({regionStats[selectedRegion]?.total || 0} devices)
              </Button>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Object.entries(cityStats)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([city, stats]) => (
              <Card
                key={city}
                hover
                onClick={() => setSelectedCity(city)}
                className="cursor-pointer"
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-3 bg-ward-green/10 rounded-lg">
                        <MapPin className="h-6 w-6 text-ward-green" />
                      </div>
                      <div>
                        <CardTitle className="text-lg">{city}</CardTitle>
                        <p className="text-sm text-gray-500 mt-1">{stats.total} devices</p>
                      </div>
                    </div>
                    <ChevronRight className="h-5 w-5 text-gray-400" />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex gap-4">
                    <div className="flex-1">
                      <div className="text-sm text-gray-500 mb-1">Online</div>
                      <div className="flex items-center gap-2">
                        <div className="text-2xl font-bold text-green-600">{stats.online}</div>
                        <Badge variant="success" dot>
                          {stats.total > 0 ? Math.round((stats.online / stats.total) * 100) : 0}%
                        </Badge>
                      </div>
                    </div>
                    <div className="flex-1">
                      <div className="text-sm text-gray-500 mb-1">Offline</div>
                      <div className="flex items-center gap-2">
                        <div className="text-2xl font-bold text-red-600">{stats.offline}</div>
                        <Badge variant="danger" dot>
                          {stats.total > 0 ? Math.round((stats.offline / stats.total) * 100) : 0}%
                        </Badge>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}

      {/* All Devices in Region View */}
      {showAllDevicesInRegion && !selectedCity && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {allRegionDevices.map((device: Device) => {
            const isOnline = device.ping_status === 'Up' || device.available === 'Available'
            const statusText = device.ping_status || device.available || 'Unknown'

            return (
              <Card key={device.hostid} hover>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-3 bg-ward-green/10 rounded-lg">
                        <Wifi className="h-6 w-6 text-ward-green" />
                      </div>
                      <div>
                        <CardTitle className="text-base">{device.display_name}</CardTitle>
                        <p className="text-sm text-gray-500 font-mono mt-1">{device.ip}</p>
                      </div>
                    </div>
                    <Badge variant={isOnline ? 'success' : 'danger'} dot>
                      {statusText}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 mb-4">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500 dark:text-gray-400">Type:</span>
                      <span className="text-gray-900 dark:text-gray-100 font-medium">{device.device_type}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500 dark:text-gray-400">Branch:</span>
                      <span className="text-gray-900 dark:text-gray-100 font-medium">{device.branch}</span>
                    </div>
                    {device.problems > 0 && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500 dark:text-gray-400">Problems:</span>
                        <Badge variant="danger">{device.problems}</Badge>
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => handleViewDevice(device.hostid)}
                    >
                      <Eye className="h-4 w-4" />
                      View
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="bg-ward-green/10 hover:bg-ward-green/20 border-ward-green text-ward-green"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleOpenSSH(device.display_name, device.ip)
                      }}
                      title="SSH Access"
                    >
                      <Terminal className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}

          {allRegionDevices.length === 0 && (
            <div className="col-span-full">
              <Card>
                <CardContent className="py-12">
                  <div className="text-center">
                    <Wifi className="h-16 w-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No devices found</h3>
                    <p className="text-gray-500 dark:text-gray-400 mt-1">
                      Try adjusting your filters
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* Device List (City View) */}
      {selectedCity && !showAllDevicesInRegion && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {cityDevices.map((device: Device) => {
            // Status logic: ping_status === 'Up' OR available === 'Available'
            const isOnline = device.ping_status === 'Up' || device.available === 'Available'
            const statusText = device.ping_status || device.available || 'Unknown'

            return (
              <Card key={device.hostid} hover>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-3 bg-ward-green/10 rounded-lg">
                        <Wifi className="h-6 w-6 text-ward-green" />
                      </div>
                      <div>
                        <CardTitle className="text-base">{device.display_name}</CardTitle>
                        <p className="text-sm text-gray-500 font-mono mt-1">{device.ip}</p>
                      </div>
                    </div>
                    <Badge variant={isOnline ? 'success' : 'danger'} dot>
                      {statusText}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500 dark:text-gray-400">Type:</span>
                      <span className="text-gray-900 dark:text-gray-100 font-medium">{device.device_type}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500 dark:text-gray-400">Branch:</span>
                      <span className="text-gray-900 dark:text-gray-100 font-medium">{device.branch}</span>
                    </div>
                    {device.problems > 0 && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500 dark:text-gray-400">Problems:</span>
                        <Badge variant="danger">{device.problems}</Badge>
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2 mt-4">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => handleViewDevice(device.hostid)}
                    >
                      <Eye className="h-4 w-4" />
                      View
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="bg-ward-green/10 hover:bg-ward-green/20 border-ward-green text-ward-green"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleOpenSSH(device.display_name, device.ip)
                      }}
                      title="SSH Access"
                    >
                      <Terminal className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}

          {cityDevices.length === 0 && (
            <div className="col-span-full">
              <Card>
                <CardContent className="py-12">
                  <div className="text-center">
                    <Wifi className="h-16 w-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No devices found</h3>
                    <p className="text-gray-500 dark:text-gray-400 mt-1">
                      No {deviceTypeFilter !== 'all' ? deviceTypeFilter : ''} devices in {selectedCity}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* Device Details Modal */}
      {selectedDeviceId && (
        <DeviceDetailsModal
          open={!!selectedDeviceId}
          onClose={() => setSelectedDeviceId(null)}
          hostid={selectedDeviceId}
          onOpenSSH={handleOpenSSH}
        />
      )}

      {/* SSH Terminal Modal */}
      <SSHTerminalModal
        open={sshModalOpen}
        onClose={() => setSSHModalOpen(false)}
        deviceName={sshDeviceName}
        deviceIP={sshDeviceIP}
      />
    </div>
  )
}
