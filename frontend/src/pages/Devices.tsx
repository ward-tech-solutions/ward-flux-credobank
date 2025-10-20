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
import { Wifi, Search, List, Eye, LayoutGrid, Terminal, Edit, Plus } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'

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
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editingDevice, setEditingDevice] = useState<any>(null)
  const [editForm, setEditForm] = useState({
    name: '',
    ip: '',
    hostname: '',
    vendor: '',
    device_type: '',
    model: '',
    location: '',
    description: '',
    region: '',
    branch: '',
    ssh_port: 22,
    ssh_username: '',
    ssh_enabled: true,
  })
  const [savingDevice, setSavingDevice] = useState(false)

  // Add Device modal states
  const [addDeviceModalOpen, setAddDeviceModalOpen] = useState(false)
  const [addDeviceForm, setAddDeviceForm] = useState({
    hostname: '',
    ip: '',
    region: '',
    branch: '',
    snmp_community: '',
    snmp_version: '2c',
  })
  const [addingDevice, setAddingDevice] = useState(false)

  // Helper function to extract city from hostname
  const extractCityFromHostname = (hostname: string): string => {
    if (!hostname) return ''

    // Remove IP if present: "Batumi-ATM 10.199.96.163" -> "Batumi-ATM"
    const name = hostname.split(' ')[0]

    // Handle special prefixes: "PING-Kabali-AP" -> skip "PING", use "Kabali"
    const parts = name.split('-')

    // Skip common prefixes (PING, TEST, PROD, DEV, SW, RTR)
    const commonPrefixes = ['PING', 'TEST', 'PROD', 'DEV', 'SW', 'RTR']
    let city = ''

    if (parts.length > 1 && commonPrefixes.includes(parts[0].toUpperCase())) {
      city = parts[1]  // Use second part as city
    } else {
      city = parts[0]  // Use first part as city
    }

    // Remove numbers: "Batumi1" -> "Batumi"
    city = city.split('').filter(c => isNaN(parseInt(c))).join('')

    return city.trim()
  }

  const { data: devices, isLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesAPI.getAll(),
  })

  // Save view mode to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('devices-view-mode', viewMode)
  }, [viewMode])

  // Auto-extract city/branch from hostname
  useEffect(() => {
    if (addDeviceForm.hostname && !addDeviceForm.branch) {
      const extractedCity = extractCityFromHostname(addDeviceForm.hostname)
      if (extractedCity) {
        setAddDeviceForm(prev => ({ ...prev, branch: extractedCity }))
      }
    }
  }, [addDeviceForm.hostname])

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

  const handleEditDevice = (device: any) => {
    setEditingDevice(device)
    setEditForm({
      name: device.display_name || device.name || '',
      ip: device.ip || '',
      hostname: device.hostname || '',
      vendor: device.vendor || '',
      device_type: device.device_type || '',
      model: device.model || '',
      location: device.location || '',
      description: device.description || '',
      region: device.region || '',
      branch: device.branch || '',
      ssh_port: device.ssh_port || 22,
      ssh_username: device.ssh_username || '',
      ssh_enabled: device.ssh_enabled !== false,
    })
    setEditModalOpen(true)
  }

  const handleSaveDeviceEdit = async () => {
    if (!editingDevice) return

    setSavingDevice(true)
    try {
      await devicesAPI.updateDevice(editingDevice.hostid, editForm)
      alert('Device updated successfully!')
      setEditModalOpen(false)
      setEditingDevice(null)
      // Refresh the devices list
      window.location.reload()
    } catch (error) {
      console.error('Failed to update device:', error)
      alert('Failed to update device')
    } finally {
      setSavingDevice(false)
    }
  }

  const handleClearFilters = () => {
    setSearchQuery('')
    setStatusFilter('')
    setTypeFilter('')
    setRegionFilter('')
    setSearchParams({})
  }

  const handleAddDevice = async () => {
    if (!addDeviceForm.hostname || !addDeviceForm.ip) {
      alert('Please fill in all required fields')
      return
    }

    setAddingDevice(true)
    try {
      // Call standalone API
      await devicesAPI.createStandalone({
        name: addDeviceForm.hostname,
        ip: addDeviceForm.ip,
        hostname: addDeviceForm.hostname,
        location: addDeviceForm.region,
        custom_fields: {
          branch: addDeviceForm.branch,
          snmp_community: addDeviceForm.snmp_community,
          snmp_version: addDeviceForm.snmp_version,
        }
      })
      alert('Device added successfully!')

      setAddDeviceModalOpen(false)
      setAddDeviceForm({
        hostname: '',
        ip: '',
        region: '',
        branch: '',
        snmp_community: '',
        snmp_version: '2c',
      })
      // Refresh the devices list
      window.location.reload()
    } catch (error) {
      console.error('Failed to add device:', error)
      alert('Failed to add device. Please check the form and try again.')
    } finally {
      setAddingDevice(false)
    }
  }

  const handleAddDeviceModalClose = () => {
    setAddDeviceModalOpen(false)
    setAddDeviceForm({
      hostname: '',
      ip: '',
      region: '',
      branch: '',
      snmp_community: '',
      snmp_version: '2c',
    })
  }

  const hasActiveFilters = searchQuery || statusFilter || typeFilter || regionFilter

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Devices</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Standalone Devices ({filteredDevices.length}
            {filteredDevices.length !== devices?.data?.length && ` of ${devices?.data?.length}`} total)
          </p>
        </div>
        <Button onClick={() => setAddDeviceModalOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Device
        </Button>
      </div>

      {/* Device Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Total Devices</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {devices?.data?.length || 0}
                </p>
              </div>
              <Wifi className="h-8 w-8 text-gray-400" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Up</p>
                <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {devices?.data?.filter((d: any) => d.ping_status === 'Up').length || 0}
                </p>
              </div>
              <div className="h-8 w-8 rounded-full bg-green-100 dark:bg-green-900/20 flex items-center justify-center">
                <div className="h-4 w-4 rounded-full bg-green-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Down</p>
                <p className="text-2xl font-bold text-red-600 dark:text-red-400">
                  {devices?.data?.filter((d: any) => d.ping_status === 'Down').length || 0}
                </p>
              </div>
              <div className="h-8 w-8 rounded-full bg-red-100 dark:bg-red-900/20 flex items-center justify-center">
                <div className="h-4 w-4 rounded-full bg-red-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Unknown</p>
                <p className="text-2xl font-bold text-gray-600 dark:text-gray-400">
                  {devices?.data?.filter((d: any) => !d.ping_status || d.ping_status === 'Unknown').length || 0}
                </p>
              </div>
              <div className="h-8 w-8 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                <div className="h-4 w-4 rounded-full bg-gray-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters and View Toggle */}
      <Card>
        <CardContent className="p-4">
          <div className="space-y-4">
            {/* Top row: Search and View Toggle */}
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div className="w-full md:max-w-md">
                <Input
                  label="Search"
                  placeholder="Search devices by name, IP, or branch..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  icon={<Search className="h-5 w-5" />}
                />
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant={viewMode === 'grid' ? 'primary' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('grid')}
                  aria-pressed={viewMode === 'grid'}
                  title="Grid View"
                  className="px-3 py-1.5"
                  icon={<LayoutGrid className="h-4 w-4" />}
                >
                  <span className="hidden sm:inline">Grid</span>
                </Button>
                <Button
                  variant={viewMode === 'list' ? 'primary' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('list')}
                  aria-pressed={viewMode === 'list'}
                  title="Table View"
                  className="px-3 py-1.5"
                  icon={<List className="h-4 w-4" />}
                >
                  <span className="hidden sm:inline">Table</span>
                </Button>
              </div>
            </div>

            {/* Bottom row: Filter dropdowns */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <Select
                label="Status"
                value={statusFilter}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setStatusFilter(e.target.value)}
                options={[
                  { value: '', label: 'All Status' },
                  { value: 'Up', label: 'Online' },
                  { value: 'Down', label: 'Offline' },
                  { value: 'Unknown', label: 'Unknown' },
                ]}
                fullWidth
              />
              <Select
                label="Type"
                value={typeFilter}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setTypeFilter(e.target.value)}
                options={[
                  { value: '', label: 'All Types' },
                  ...deviceTypes.map(type => ({ value: type, label: type })),
                ]}
                fullWidth
              />
              <Select
                label="Region"
                value={regionFilter}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setRegionFilter(e.target.value)}
                options={[
                  { value: '', label: 'All Regions' },
                  ...regions.map(region => ({ value: region, label: region })),
                ]}
                fullWidth
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
                {hasActiveFilters ? 'Try adjusting your filters' : 'No devices available'}
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
                      onClick={(e) => {
                        e.stopPropagation()
                        handleEditDevice(device)
                      }}
                      title="Edit Device"
                    >
                      <Edit className="h-4 w-4" />
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
                    <TableRow
                      key={device.hostid}
                      className={!isOnline ? 'bg-red-50 dark:bg-red-900/10 hover:bg-red-100 dark:hover:bg-red-900/20' : ''}
                    >
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
                              handleEditDevice(device)
                            }}
                            title="Edit Device"
                          >
                            <Edit className="h-4 w-4" />
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

      {/* Edit Device Modal */}
      <Modal
        open={editModalOpen}
        onClose={() => {
          setEditModalOpen(false)
          setEditingDevice(null)
        }}
        title="Edit Device"
        size="lg"
      >
        {editingDevice && (
          <div className="space-y-4 max-h-[70vh] overflow-y-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Device Name
                </label>
                <Input
                  value={editForm.name}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, name: e.target.value })}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  IP Address
                </label>
                <Input
                  value={editForm.ip}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, ip: e.target.value })}
                  className="font-mono"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Hostname
                </label>
                <Input
                  value={editForm.hostname}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, hostname: e.target.value })}
                  placeholder="Enter hostname"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Vendor
                </label>
                <Input
                  value={editForm.vendor}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, vendor: e.target.value })}
                  placeholder="e.g., Cisco, Fortinet"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Device Type
                </label>
                <Input
                  value={editForm.device_type}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, device_type: e.target.value })}
                  placeholder="e.g., Switch, Router, Paybox"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Model
                </label>
                <Input
                  value={editForm.model}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, model: e.target.value })}
                  placeholder="Device model"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Location
                </label>
                <Input
                  value={editForm.location}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, location: e.target.value })}
                  placeholder="Physical location"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Region
                </label>
                <select
                  value={editForm.region}
                  onChange={(e) => setEditForm({ ...editForm, region: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-ward-green"
                >
                  <option value="">Select Region</option>
                  {regions.map((region) => (
                    <option key={region} value={region}>
                      {region}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Branch (City)
                </label>
                <Input
                  value={editForm.branch}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, branch: e.target.value })}
                  placeholder="Enter branch/city name"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Description
                </label>
                <textarea
                  value={editForm.description}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-ward-green"
                  rows={3}
                  placeholder="Device description"
                />
              </div>
            </div>

            <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4">
              <h4 className="text-md font-semibold mb-3 text-gray-900 dark:text-gray-100">SSH Configuration</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    SSH Port
                  </label>
                  <Input
                    type="number"
                    value={editForm.ssh_port}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, ssh_port: parseInt(e.target.value) || 22 })}
                    placeholder="22"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    SSH Username
                  </label>
                  <Input
                    value={editForm.ssh_username}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, ssh_username: e.target.value })}
                    placeholder="admin"
                  />
                </div>

                <div className="flex items-end pb-2">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={editForm.ssh_enabled}
                      onChange={(e) => setEditForm({ ...editForm, ssh_enabled: e.target.checked })}
                      className="h-4 w-4 rounded border-gray-300 text-ward-green focus:ring-ward-green"
                    />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      SSH Enabled
                    </span>
                  </label>
                </div>
              </div>
            </div>

            <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <Button
                onClick={handleSaveDeviceEdit}
                disabled={savingDevice}
                className="flex-1"
              >
                {savingDevice ? 'Saving...' : 'Save Changes'}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setEditModalOpen(false)
                  setEditingDevice(null)
                }}
                disabled={savingDevice}
                className="flex-1"
              >
                Cancel
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Add Device Modal */}
      <Modal
        open={addDeviceModalOpen}
        onClose={handleAddDeviceModalClose}
        title="Add New Device"
        size="md"
      >
        <div className="flex flex-col" style={{ maxHeight: 'calc(90vh - 200px)' }}>
          {/* Scrollable Body */}
          <div className="overflow-y-auto flex-1 pr-2 space-y-6">
            {/* Basic Information Section */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 pb-2 border-b border-gray-200 dark:border-gray-700">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Basic Information</h3>
              </div>

              <Input
                label="Hostname"
                value={addDeviceForm.hostname}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAddDeviceForm({ ...addDeviceForm, hostname: e.target.value })}
                placeholder="Enter device hostname"
                required
              />

              <Input
                label="IP Address"
                value={addDeviceForm.ip}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAddDeviceForm({ ...addDeviceForm, ip: e.target.value })}
                placeholder="192.168.1.1"
                required
              />
            </div>

            {/* Location Section */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 pb-2 border-b border-gray-200 dark:border-gray-700">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Location</h3>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Region
                </label>
                <select
                  value={addDeviceForm.region}
                  onChange={(e) => setAddDeviceForm({ ...addDeviceForm, region: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-ward-green"
                >
                  <option value="">Select Region</option>
                  {regions.map((region) => (
                    <option key={region} value={region}>
                      {region}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <Input
                  label="Branch (City)"
                  value={addDeviceForm.branch}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAddDeviceForm({ ...addDeviceForm, branch: e.target.value })}
                  placeholder="Enter branch/city name"
                />
                {addDeviceForm.hostname && addDeviceForm.branch && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Auto-extracted from hostname
                  </p>
                )}
              </div>
            </div>

            {/* Monitoring Configuration Section */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 pb-2 border-b border-gray-200 dark:border-gray-700">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Monitoring Configuration</h3>
              </div>

              {/* Monitoring Type Info */}
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
                <div className="flex items-start gap-2">
                  <div className="flex-shrink-0 mt-0.5">
                    <span className="text-blue-600 dark:text-blue-400">ℹ️</span>
                  </div>
                  <div className="text-xs text-blue-800 dark:text-blue-300">
                    <p className="font-medium mb-1">Monitoring Types:</p>
                    <ul className="space-y-1 list-disc list-inside">
                      <li><strong>ICMP (Ping)</strong> - Always enabled for all devices</li>
                      <li><strong>SNMP</strong> - Optional, enter community string below to enable</li>
                    </ul>
                  </div>
                </div>
              </div>

              <Input
                label="SNMP Community (Optional)"
                value={addDeviceForm.snmp_community}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAddDeviceForm({ ...addDeviceForm, snmp_community: e.target.value })}
                placeholder="public"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 -mt-2">
                Leave empty for ICMP-only monitoring
              </p>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  SNMP Version
                </label>
                <select
                  value={addDeviceForm.snmp_version}
                  onChange={(e) => setAddDeviceForm({ ...addDeviceForm, snmp_version: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-ward-green"
                  disabled={!addDeviceForm.snmp_community}
                >
                  <option value="1">SNMPv1</option>
                  <option value="2c">SNMPv2c</option>
                  <option value="3">SNMPv3</option>
                </select>
                {!addDeviceForm.snmp_community && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Enter SNMP community to enable SNMP version selection
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Fixed Footer */}
          <div className="flex gap-3 pt-4 mt-4 border-t border-gray-200 dark:border-gray-700 flex-shrink-0">
            <Button
              variant="outline"
              onClick={handleAddDeviceModalClose}
              className="flex-1"
              disabled={addingDevice}
            >
              Cancel
            </Button>
            <Button
              onClick={handleAddDevice}
              disabled={addingDevice}
              className="flex-1"
            >
              {addingDevice ? 'Adding...' : 'Add Device'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
