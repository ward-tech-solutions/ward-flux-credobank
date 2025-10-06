import { useState, useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Loading'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Select from '@/components/ui/Select'
import Badge from '@/components/ui/Badge'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table'
import DeviceDetailsModal from '@/components/DeviceDetailsModal'
import SSHTerminalModal from '@/components/SSHTerminalModal'
import { devicesAPI } from '@/services/api'
import { Wifi, Search, List, Eye, LayoutGrid, Terminal } from 'lucide-react'

export default function Devices() {
  const [searchParams, setSearchParams] = useSearchParams()

  // Get initial view mode from localStorage or default to 'grid'
  const [viewMode, setViewMode] = useState<'grid' | 'list'>(() => {
    const saved = localStorage.getItem('devices-view-mode')
    return (saved === 'grid' || saved === 'list') ? saved : 'grid'
  })

  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '')
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '')
  const [typeFilter, setTypeFilter] = useState(searchParams.get('type') || '')
  const [regionFilter, setRegionFilter] = useState(searchParams.get('region') || '')

  // Modal states
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null)
  const [sshModalOpen, setSSHModalOpen] = useState(false)
  const [sshDeviceName, setSSHDeviceName] = useState('')
  const [sshDeviceIP, setSSHDeviceIP] = useState('')

  const { data: devices, isLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesAPI.getAll(),
  })

  // Save view mode to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('devices-view-mode', viewMode)
  }, [viewMode])

  // Get unique regions and device types from devices
  const { regions, deviceTypes } = useMemo(() => {
    if (!devices?.data) return { regions: [], deviceTypes: [] }

    const regionsSet = new Set<string>()
    const typesSet = new Set<string>()

    devices.data.forEach((device: any) => {
      if (device.region) regionsSet.add(device.region)
      if (device.device_type) typesSet.add(device.device_type)
    })

    return {
      regions: Array.from(regionsSet).sort(),
      deviceTypes: Array.from(typesSet).sort(),
    }
  }, [devices])

  // Filter devices based on all filters
  const filteredDevices = useMemo(() => {
    if (!devices?.data) return []

    return devices.data.filter((device: any) => {
      const name = device.display_name || device.hostname || ''
      const host = device.ip || ''
      const branch = device.branch || ''

      // Search filter
      const matchesSearch = !searchQuery ||
        name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        host.toLowerCase().includes(searchQuery.toLowerCase()) ||
        branch.toLowerCase().includes(searchQuery.toLowerCase())

      // Status filter
      const matchesStatus = !statusFilter || device.ping_status === statusFilter

      // Type filter
      const matchesType = !typeFilter || device.device_type === typeFilter

      // Region filter
      const matchesRegion = !regionFilter || device.region === regionFilter

      return matchesSearch && matchesStatus && matchesType && matchesRegion
    })
  }, [devices, searchQuery, statusFilter, typeFilter, regionFilter])

  const handleViewDevice = (hostid: string) => {
    setSelectedDeviceId(hostid)
  }

  const handleOpenSSH = (deviceName: string, deviceIP: string) => {
    setSSHDeviceName(deviceName)
    setSSHDeviceIP(deviceIP)
    setSSHModalOpen(true)
  }

  const handleClearFilters = () => {
    setSearchQuery('')
    setStatusFilter('')
    setTypeFilter('')
    setRegionFilter('')
    setSearchParams({})
  }

  const hasActiveFilters = searchQuery || statusFilter || typeFilter || regionFilter

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Devices</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Zabbix monitored devices ({filteredDevices.length}
            {filteredDevices.length !== devices?.data?.length && ` of ${devices?.data?.length}`} total)
          </p>
        </div>
      </div>

      {/* Filters and View Toggle */}
      <Card>
        <CardContent className="p-4">
          <div className="space-y-4">
            {/* Top row: Search and View Toggle */}
            <div className="flex items-center justify-between gap-4">
              <div className="flex-1 max-w-md">
                <Input
                  placeholder="Search devices by name, IP, or branch..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  icon={<Search className="h-5 w-5" />}
                />
              </div>
              <div className="flex items-center gap-2 border border-gray-200 dark:border-gray-700 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('grid')}
                  className={`p-2 rounded transition-colors ${
                    viewMode === 'grid'
                      ? 'bg-ward-green text-white'
                      : 'text-gray-600 dark:text-gray-400 hover:text-ward-green'
                  }`}
                  title="Grid View"
                >
                  <LayoutGrid className="h-5 w-5" />
                </button>
                <button
                  onClick={() => setViewMode('list')}
                  className={`p-2 rounded transition-colors ${
                    viewMode === 'list'
                      ? 'bg-ward-green text-white'
                      : 'text-gray-600 dark:text-gray-400 hover:text-ward-green'
                  }`}
                  title="Table View"
                >
                  <List className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Bottom row: Filter dropdowns */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <Select
                value={statusFilter}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setStatusFilter(e.target.value)}
                options={[
                  { value: '', label: 'All Status' },
                  { value: 'Up', label: 'Online' },
                  { value: 'Down', label: 'Offline' },
                  { value: 'Unknown', label: 'Unknown' },
                ]}
              />
              <Select
                value={typeFilter}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setTypeFilter(e.target.value)}
                options={[
                  { value: '', label: 'All Types' },
                  ...deviceTypes.map(type => ({ value: type, label: type })),
                ]}
              />
              <Select
                value={regionFilter}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setRegionFilter(e.target.value)}
                options={[
                  { value: '', label: 'All Regions' },
                  ...regions.map(region => ({ value: region, label: region })),
                ]}
              />
              {hasActiveFilters && (
                <Button
                  variant="outline"
                  onClick={handleClearFilters}
                  className="w-full"
                >
                  Clear Filters
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Devices Grid/List */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} variant="card" />
          ))}
        </div>
      ) : filteredDevices.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <Wifi className="h-16 w-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No devices found</h3>
              <p className="text-gray-500 dark:text-gray-400 mt-1 mb-4">
                {hasActiveFilters ? 'Try adjusting your filters' : 'No devices available from Zabbix'}
              </p>
              {hasActiveFilters && (
                <Button onClick={handleClearFilters} variant="outline">
                  Clear Filters
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredDevices.map((device: any) => {
            const isOnline = device.ping_status === 'Up' || device.available === 'Available'
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
                        <p className="text-sm text-gray-500 dark:text-gray-400 font-mono mt-1">{device.ip}</p>
                      </div>
                    </div>
                    <Badge variant={isOnline ? 'success' : 'danger'} dot>
                      {device.ping_status || 'Unknown'}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 mb-4">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500 dark:text-gray-400">Branch:</span>
                      <span className="text-gray-900 dark:text-gray-100 font-medium">{device.branch || '-'}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500 dark:text-gray-400">Type:</span>
                      <span className="text-gray-900 dark:text-gray-100 font-medium">{device.device_type || '-'}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500 dark:text-gray-400">Region:</span>
                      <span className="text-gray-900 dark:text-gray-100 font-medium">{device.region || '-'}</span>
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
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Status</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Branch</TableHead>
                  <TableHead>IP Address</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Region</TableHead>
                  <TableHead>Problems</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredDevices.map((device: any) => {
                  const isOnline = device.ping_status === 'Up' || device.available === 'Available'
                  return (
                    <TableRow key={device.hostid}>
                      <TableCell>
                        <Badge variant={isOnline ? 'success' : 'danger'} dot>
                          {device.ping_status || 'Unknown'}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium text-gray-900 dark:text-gray-100">{device.display_name}</TableCell>
                      <TableCell className="text-gray-700 dark:text-gray-300">{device.branch}</TableCell>
                      <TableCell className="font-mono text-sm text-gray-700 dark:text-gray-300">{device.ip}</TableCell>
                      <TableCell className="text-gray-700 dark:text-gray-300">{device.device_type || '-'}</TableCell>
                      <TableCell className="text-gray-700 dark:text-gray-300">{device.region || '-'}</TableCell>
                      <TableCell>
                        {device.problems > 0 ? (
                          <Badge variant="danger">{device.problems}</Badge>
                        ) : (
                          <span className="text-green-600">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleViewDevice(device.hostid)
                            }}
                            title="View Details"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleOpenSSH(device.display_name, device.ip)
                            }}
                            className="text-ward-green hover:text-ward-green/80"
                            title="SSH Access"
                          >
                            <Terminal className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
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
