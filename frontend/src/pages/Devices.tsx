import { useState, useEffect, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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
import { devicesAPI, branchesAPI } from '@/services/api'
import { Wifi, Search, List, Eye, LayoutGrid, Terminal, Edit, Plus, MapPin, Info, Activity, Trash2 } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { toast } from 'sonner'

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
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [deviceToDelete, setDeviceToDelete] = useState<any>(null)
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

  const queryClient = useQueryClient()

  const { data: devices, isLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesAPI.getAll(),
  })

  // Fetch available regions from database
  const { data: regionsData} = useQuery({
    queryKey: ['regions'],
    queryFn: async () => {
      const response = await branchesAPI.getRegions()
      return response.data
    },
  })

  // Delete device mutation
  const deleteMutation = useMutation({
    mutationFn: (deviceId: string) => devicesAPI.standalone.delete(deviceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['devices'] })
      toast.success('Device deleted successfully')
      setDeleteModalOpen(false)
      setDeviceToDelete(null)
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to delete device'
      toast.error(message)
    }
  })

  const availableRegions = regionsData?.regions || []

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
      toast.success('Device updated successfully!')
      setEditModalOpen(false)
      setEditingDevice(null)
      // Refresh the devices list
      queryClient.invalidateQueries({ queryKey: ['devices'] })
    } catch (error: any) {
      console.error('Failed to update device:', error)
      const message = error.response?.data?.detail || 'Failed to update device'
      toast.error(message)
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
      toast.error('Please fill in all required fields')
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
      toast.success('Device added successfully!')

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
      queryClient.invalidateQueries({ queryKey: ['devices'] })
    } catch (error: any) {
      console.error('Failed to add device:', error)
      const message = error.response?.data?.detail || 'Failed to add device. Please check the form and try again.'
      toast.error(message)
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
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200"
                      onClick={(e) => {
                        e.stopPropagation()
                        setDeviceToDelete(device)
                        setDeleteModalOpen(true)
                      }}
                      title="Delete Device"
                    >
                      <Trash2 className="h-4 w-4" />
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
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation()
                              setDeviceToDelete(device)
                              setDeleteModalOpen(true)
                            }}
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            title="Delete Device"
                          >
                            <Trash2 className="h-4 w-4" />
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
        size="xl"
      >
        {editingDevice && (
          <div className="flex flex-col" style={{ minHeight: '600px', maxHeight: 'calc(85vh - 120px)' }}>
            {/* Scrollable Body */}
            <div className="overflow-y-auto flex-1 pr-3" style={{ paddingBottom: '1rem' }}>
              <div className="space-y-5">
                {/* Basic Information Section */}
                <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-md rounded-2xl p-5 border border-gray-200/50 dark:border-gray-700/50 shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="p-1.5 rounded-lg bg-gradient-to-br from-blue-400 to-indigo-500">
                      <Wifi className="h-4 w-4 text-white" />
                    </div>
                    <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">Basic Information</h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Input
                      label="Device Name"
                      value={editForm.name}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, name: e.target.value })}
                      placeholder="Enter device name"
                    />

                    <Input
                      label="IP Address"
                      value={editForm.ip}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, ip: e.target.value })}
                      placeholder="192.168.1.1"
                      className="font-mono"
                    />

                    <Input
                      label="Hostname"
                      value={editForm.hostname}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, hostname: e.target.value })}
                      placeholder="Enter hostname"
                    />

                    <Input
                      label="Vendor"
                      value={editForm.vendor}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, vendor: e.target.value })}
                      placeholder="e.g., Cisco, Fortinet"
                    />

                    <Input
                      label="Device Type"
                      value={editForm.device_type}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, device_type: e.target.value })}
                      placeholder="Biostar"
                    />

                    <Input
                      label="Model"
                      value={editForm.model}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, model: e.target.value })}
                      placeholder="Device model"
                    />
                  </div>
                </div>

                {/* Location Section */}
                <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-md rounded-2xl p-5 border border-gray-200/50 dark:border-gray-700/50 shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="p-1.5 rounded-lg bg-gradient-to-br from-green-400 to-emerald-500">
                      <MapPin className="h-4 w-4 text-white" />
                    </div>
                    <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">Location</h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                        Region
                      </label>
                      <select
                        value={editForm.region}
                        onChange={(e) => setEditForm({ ...editForm, region: e.target.value })}
                        className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-ward-green focus:border-transparent transition-colors"
                      >
                        <option value="">Select Region</option>
                        {availableRegions.map((region) => (
                          <option key={region} value={region}>{region}</option>
                        ))}
                      </select>
                    </div>

                    <Input
                      label="Branch (City)"
                      value={editForm.branch}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, branch: e.target.value })}
                      placeholder="Enter branch/city name"
                    />

                    <div className="md:col-span-2">
                      <Input
                        label="Location"
                        value={editForm.location}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, location: e.target.value })}
                        placeholder="Physical location"
                      />
                    </div>
                  </div>
                </div>

                {/* Description Section */}
                <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-md rounded-2xl p-5 border border-gray-200/50 dark:border-gray-700/50 shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="p-1.5 rounded-lg bg-gradient-to-br from-purple-400 to-pink-500">
                      <Info className="h-4 w-4 text-white" />
                    </div>
                    <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">Description</h3>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                      Device Description
                    </label>
                    <textarea
                      value={editForm.description}
                      onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                      className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-ward-green focus:border-transparent transition-colors resize-none"
                      rows={3}
                      placeholder="Device description"
                    />
                  </div>
                </div>

                {/* SSH Configuration Section */}
                <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-md rounded-2xl p-5 border border-gray-200/50 dark:border-gray-700/50 shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="p-1.5 rounded-lg bg-gradient-to-br from-orange-400 to-red-500">
                      <Terminal className="h-4 w-4 text-white" />
                    </div>
                    <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">SSH Configuration</h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Input
                      label="SSH Port"
                      type="number"
                      value={editForm.ssh_port}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, ssh_port: parseInt(e.target.value) || 22 })}
                      placeholder="22"
                    />

                    <Input
                      label="SSH Username"
                      value={editForm.ssh_username}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm({ ...editForm, ssh_username: e.target.value })}
                      placeholder="admin"
                    />

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
              </div>
            </div>

            {/* Fixed Footer */}
            <div className="flex gap-3 pt-4 mt-4 border-t border-gray-200 dark:border-gray-700 flex-shrink-0">
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
              <Button
                onClick={handleSaveDeviceEdit}
                disabled={savingDevice}
                className="flex-1 bg-ward-green hover:bg-ward-green-dark"
              >
                {savingDevice ? 'Saving...' : 'Save Changes'}
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
        size="xl"
      >
        <div className="flex flex-col" style={{ minHeight: '500px', maxHeight: 'calc(85vh - 120px)' }}>
          {/* Scrollable Body */}
          <div className="overflow-y-auto flex-1 pr-3" style={{ paddingBottom: '1rem' }}>
            <div className="space-y-5">
              {/* Basic Information Section */}
              <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-md rounded-2xl p-5 border border-gray-200/50 dark:border-gray-700/50 shadow-sm hover:shadow-md transition-shadow">
                <div className="flex items-center gap-2 mb-4">
                  <div className="p-1.5 rounded-lg bg-gradient-to-br from-blue-400 to-indigo-500">
                    <Wifi className="h-4 w-4 text-white" />
                  </div>
                  <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">Basic Information</h3>
                </div>

                <div className="space-y-4">
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
              </div>

              {/* Location Section */}
              <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-md rounded-2xl p-5 border border-gray-200/50 dark:border-gray-700/50 shadow-sm hover:shadow-md transition-shadow">
                <div className="flex items-center gap-2 mb-4">
                  <div className="p-1.5 rounded-lg bg-gradient-to-br from-green-400 to-emerald-500">
                    <MapPin className="h-4 w-4 text-white" />
                  </div>
                  <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">Location</h3>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                      Region
                    </label>
                    <select
                      value={addDeviceForm.region}
                      onChange={(e) => setAddDeviceForm({ ...addDeviceForm, region: e.target.value })}
                      className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-ward-green focus:border-transparent transition-colors"
                    >
                      <option value="">Select Region</option>
                      {availableRegions.map((region) => (
                        <option key={region} value={region}>{region}</option>
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
                      <p className="text-xs text-green-600 dark:text-green-400 mt-1.5 flex items-center gap-1">
                        <span className="text-green-500">✓</span> Auto-extracted from hostname
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* Monitoring Configuration Section */}
              <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-md rounded-2xl p-5 border border-gray-200/50 dark:border-gray-700/50 shadow-sm hover:shadow-md transition-shadow">
                <div className="flex items-center gap-2 mb-4">
                  <div className="p-1.5 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-500">
                    <Info className="h-4 w-4 text-white" />
                  </div>
                  <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">Monitoring Configuration</h3>
                </div>

                <div className="space-y-4">
                  {/* Monitoring Type Info */}
                  <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-4">
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 mt-0.5">
                        <svg className="h-5 w-5 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <div className="text-sm text-blue-800 dark:text-blue-200">
                        <p className="font-semibold mb-2">Monitoring Types:</p>
                        <ul className="space-y-1.5">
                          <li className="flex items-start gap-2">
                            <span className="text-blue-600 dark:text-blue-400 mt-0.5">•</span>
                            <span><strong className="font-semibold">ICMP (Ping)</strong> - Always enabled for all devices</span>
                          </li>
                          <li className="flex items-start gap-2">
                            <span className="text-blue-600 dark:text-blue-400 mt-0.5">•</span>
                            <span><strong className="font-semibold">SNMP</strong> - Optional, enter community string below to enable</span>
                          </li>
                        </ul>
                      </div>
                    </div>
                  </div>

                  <Input
                    label="SNMP Community String (Optional)"
                    value={addDeviceForm.snmp_community}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAddDeviceForm({ ...addDeviceForm, snmp_community: e.target.value })}
                    placeholder="Leave empty for ICMP-only monitoring"
                  />

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                      SNMP Version
                    </label>
                    <select
                      value={addDeviceForm.snmp_version}
                      onChange={(e) => setAddDeviceForm({ ...addDeviceForm, snmp_version: e.target.value })}
                      className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-ward-green focus:border-transparent transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      disabled={!addDeviceForm.snmp_community}
                    >
                      <option value="1">SNMPv1</option>
                      <option value="2c">SNMPv2c</option>
                      <option value="3">SNMPv3</option>
                    </select>
                    {!addDeviceForm.snmp_community && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1.5">
                        Enter SNMP community string to enable version selection
                      </p>
                    )}
                  </div>
                </div>
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
              className="flex-1 bg-ward-green hover:bg-ward-green-dark"
            >
              {addingDevice ? 'Adding...' : 'Add Device'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Delete Confirmation Modal */}
      {deleteModalOpen && deviceToDelete && (
        <Modal
          open={deleteModalOpen}
          onClose={() => {
            setDeleteModalOpen(false)
            setDeviceToDelete(null)
          }}
          title="Delete Device"
        >
          <div className="space-y-4">
            <p className="text-gray-600 dark:text-gray-300">
              Are you sure you want to delete <strong>{deviceToDelete.name || deviceToDelete.display_name}</strong>?
              This action cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setDeleteModalOpen(false)
                  setDeviceToDelete(null)
                }}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={() => deleteMutation.mutate(deviceToDelete.hostid || deviceToDelete.id)}
                disabled={deleteMutation.isPending}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
