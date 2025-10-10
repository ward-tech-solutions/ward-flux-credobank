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
    region: '',
    branch: '',
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
      region: device.region || '',
      branch: device.branch || '',
    })
    setEditModalOpen(true)
  }

  const handleSaveDeviceEdit = async () => {
    if (!editingDevice) return

    setSavingDevice(true)
    try {
      await devicesAPI.updateDevice(editingDevice.hostid, {
        region: editForm.region,
        branch: editForm.branch,
      })
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
        size="md"
      >
        {editingDevice && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Device Name
              </label>
              <Input
                value={editingDevice.display_name}
                disabled
                className="bg-gray-50 dark:bg-gray-900"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Read-only</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                IP Address
              </label>
              <Input
                value={editingDevice.ip}
                disabled
                className="bg-gray-50 dark:bg-gray-900 font-mono"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Read-only</p>
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
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Assign device to a region
              </p>
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
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Branch or city where the device is located
              </p>
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
          <div className="overflow-y-auto flex-1 pr-2 space-y-4">
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

            <Input
              label="SNMP Community"
              value={addDeviceForm.snmp_community}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAddDeviceForm({ ...addDeviceForm, snmp_community: e.target.value })}
              placeholder="public"
            />

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                SNMP Version
              </label>
              <select
                value={addDeviceForm.snmp_version}
                onChange={(e) => setAddDeviceForm({ ...addDeviceForm, snmp_version: e.target.value })}
                className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-ward-green"
              >
                <option value="1">SNMPv1</option>
                <option value="2c">SNMPv2c</option>
                <option value="3">SNMPv3</option>
              </select>
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
