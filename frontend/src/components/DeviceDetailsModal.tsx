import { useState, useEffect, useMemo, type ReactNode } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Modal, ModalHeader, ModalTitle, ModalContent } from '@/components/ui/Modal'
import { Skeleton } from '@/components/ui/Loading'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import { devicesAPI } from '@/services/api'
import {
  Globe,
  Copy,
  MapPin,
  RefreshCw,
  Wrench,
  Terminal,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Activity,
  Info,
  Network,
  Edit3,
  Save,
  X as XIcon,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface DeviceDetailsModalProps {
  open: boolean
  onClose: () => void
  hostid: string
  onOpenSSH?: (deviceName: string, deviceIP: string) => void
}

const getDeviceIcon = (deviceType: string) => {
  const iconMap: Record<string, any> = {
    'Paybox': '💳',
    'ATM': '🏧',
    'NVR': '📹',
    'Access Point': '📡',
    'Switch': '🔀',
    'Router': '🌐',
    'Core Router': '🖥️',
    'Biostar': '👆',
    'Disaster Recovery': '🛡️',
  }
  return iconMap[deviceType] || '📦'
}

const getSeverityName = (priority: number) => {
  const severities = ['Not classified', 'Information', 'Warning', 'Average', 'High', 'Disaster']
  return severities[priority] || 'Unknown'
}

const getSeverityVariant = (priority: number): 'default' | 'success' | 'warning' | 'danger' => {
  if (priority >= 4) return 'danger'
  if (priority === 3) return 'warning'
  if (priority === 2) return 'warning'
  return 'default'
}

const formatDuration = (ms: number) => {
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 0) return `${days}d ${hours % 24}h`
  if (hours > 0) return `${hours}h ${minutes % 60}m`
  if (minutes > 0) return `${minutes}m`
  return `${seconds}s`
}

// Generate simulated historical data for 24h status chart
const generateStatusHistory = (isOnline: boolean) => {
  const data = []
  const now = Date.now()
  const points = 24 // Last 24 hours

  for (let i = points; i >= 0; i--) {
    const timestamp = now - (i * 60 * 60 * 1000) // Hourly intervals
    const hour = new Date(timestamp).getHours()

    // Simulate realistic patterns
    let status = 1 // Up
    let responseTime = 5 + Math.random() * 15 // 5-20ms for normal

    // If currently offline, make recent hours offline
    if (!isOnline && i < 2) {
      status = 0
      responseTime = 0
    } else if (Math.random() < 0.05) {
      // 5% chance of historical downtime
      status = 0
      responseTime = 0
    } else if (hour >= 2 && hour <= 5) {
      // Better performance during night hours
      responseTime = 3 + Math.random() * 8
    }

    data.push({
      time: new Date(timestamp).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      }),
      status,
      responseTime: status === 1 ? responseTime : 0,
    })
  }

  return data
}

const buildEditFormState = (deviceData: any) => ({
  name: deviceData?.display_name || deviceData?.name || '',
  ip: deviceData?.ip || '',
  hostname: deviceData?.hostname || '',
  vendor: deviceData?.vendor || '',
  device_type: deviceData?.device_type || '',
  model: deviceData?.model || '',
  location: deviceData?.location || '',
  description: deviceData?.description || '',
  ssh_port: deviceData?.ssh_port ?? 22,
  ssh_username: deviceData?.ssh_username || '',
  ssh_enabled: deviceData?.ssh_enabled !== false,
})

export default function DeviceDetailsModal({ open, onClose, hostid, onOpenSSH }: DeviceDetailsModalProps) {
  const [copiedIP, setCopiedIP] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState<any>({ ssh_port: 22, ssh_enabled: true })
  const queryClient = useQueryClient()

  const { data: device, isLoading, refetch } = useQuery({
    queryKey: ['device', hostid],
    queryFn: () => devicesAPI.getById(hostid),
    enabled: open && !!hostid,
  })

  const updateMutation = useMutation({
    mutationFn: (data: any) => devicesAPI.updateDevice(hostid, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['device', hostid] })
      queryClient.invalidateQueries({ queryKey: ['devices'] })
      setIsEditing(false)
      refetch()
    },
  })

  useEffect(() => {
    if (open && hostid) {
      refetch()
    }
  }, [open, hostid, refetch])

  const deviceData = device?.data

  useEffect(() => {
    if (deviceData && isEditing) {
      setEditForm(buildEditFormState(deviceData))
    }
  }, [isEditing, deviceData])

  const isOnline = deviceData?.ping_status === 'Up' || deviceData?.available === 'Available'
  const statusText = deviceData?.ping_status || deviceData?.available || 'Unknown'

  // Generate status history data
  const statusHistory = useMemo(() => {
    if (!deviceData) return []
    return generateStatusHistory(isOnline)
  }, [deviceData, isOnline])

  const copyIP = () => {
    if (deviceData?.ip) {
      navigator.clipboard.writeText(deviceData.ip)
      setCopiedIP(true)
      setTimeout(() => setCopiedIP(false), 2000)
    }
  }

  const openWebUI = () => {
    if (deviceData?.ip) {
      window.open(`http://${deviceData.ip}`, '_blank')
    }
  }

  const handleRefresh = () => {
    refetch()
  }

  const handleSSH = () => {
    if (deviceData && onOpenSSH) {
      const port = deviceData.ssh_port || 22
      onOpenSSH(deviceData.display_name, `${deviceData.ip}:${port}`)
      onClose()
    }
  }

  const handleSave = () => {
    updateMutation.mutate(editForm)
  }

  const handleCancel = () => {
    setIsEditing(false)
    setEditForm({ ssh_port: 22, ssh_enabled: true })
  }

  const handleEditToggle = () => {
    if (!isEditing && deviceData) {
      setEditForm(buildEditFormState(deviceData))
    }
    setIsEditing(!isEditing)
  }

  return (
    <Modal open={open} onClose={onClose} size="xl">
      <ModalHeader onClose={onClose}>
        <div className="flex items-center justify-between w-full pr-8">
          <ModalTitle className="flex items-center gap-2">
            {deviceData && <span className="text-2xl">{getDeviceIcon(deviceData.device_type)}</span>}
            {deviceData?.display_name || 'Device Details'}
          </ModalTitle>
          <div className="flex items-center gap-2">
            {isEditing ? (
              <>
                <Button
                  onClick={handleCancel}
                  variant="outline"
                  size="sm"
                  className="flex items-center gap-2"
                >
                  <XIcon className="h-4 w-4" />
                  Cancel
                </Button>
                <Button
                  onClick={handleSave}
                  size="sm"
                  className="flex items-center gap-2 bg-ward-green hover:bg-ward-green-dark"
                  disabled={updateMutation.isPending}
                >
                  <Save className="h-4 w-4" />
                  {updateMutation.isPending ? 'Saving...' : 'Save'}
                </Button>
              </>
            ) : (
              <Button
                onClick={handleEditToggle}
                variant="outline"
                size="sm"
                className="flex items-center gap-2"
              >
                <Edit3 className="h-4 w-4" />
                Edit Device
              </Button>
            )}
          </div>
        </div>
      </ModalHeader>
      <ModalContent className="max-h-[80vh] overflow-y-auto">
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton variant="card" />
            <Skeleton variant="card" />
            <Skeleton variant="card" />
          </div>
        ) : deviceData ? (
          <div className="space-y-6">
            {/* Status Banner */}
            <div
              className={`rounded-xl p-6 ${
                isOnline
                  ? 'bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border border-green-200 dark:border-green-800'
                  : 'bg-gradient-to-r from-red-50 to-rose-50 dark:from-red-900/20 dark:to-rose-900/20 border border-red-200 dark:border-red-800'
              }`}
            >
              <div className="flex items-start gap-4">
                <div className={`p-3 rounded-full ${isOnline ? 'bg-green-100 dark:bg-green-900/40' : 'bg-red-100 dark:bg-red-900/40'}`}>
                  {isOnline ? (
                    <CheckCircle className="h-8 w-8 text-green-600 dark:text-green-400" />
                  ) : (
                    <XCircle className="h-8 w-8 text-red-600 dark:text-red-400" />
                  )}
                </div>
                <div className="flex-1">
                  <h3 className={`text-xl font-semibold ${isOnline ? 'text-green-900 dark:text-green-100' : 'text-red-900 dark:text-red-100'}`}>
                    {statusText}
                  </h3>
                  <p className={`mt-1 ${isOnline ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'}`}>
                    {isOnline ? 'Device is responding normally' : 'Device is not responding'}
                  </p>
                </div>
              </div>
            </div>

            {/* Action Bar */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              {onOpenSSH && (
                <Button
                  onClick={handleSSH}
                  variant="outline"
                  className="flex flex-col items-center gap-2 h-auto py-3 bg-ward-green/10 hover:bg-ward-green/20 border-ward-green text-ward-green"
                >
                  <Terminal className="h-5 w-5" />
                  <span className="text-xs font-medium">SSH</span>
                </Button>
              )}
              <Button
                onClick={openWebUI}
                variant="outline"
                className="flex flex-col items-center gap-2 h-auto py-3"
              >
                <Globe className="h-5 w-5" />
                <span className="text-xs font-medium">Web UI</span>
              </Button>
              <Button
                onClick={copyIP}
                variant="outline"
                className="flex flex-col items-center gap-2 h-auto py-3"
              >
                <Copy className="h-5 w-5" />
                <span className="text-xs font-medium">{copiedIP ? 'Copied!' : 'Copy IP'}</span>
              </Button>
              <Button
                onClick={handleRefresh}
                variant="outline"
                className="flex flex-col items-center gap-2 h-auto py-3"
              >
                <RefreshCw className="h-5 w-5" />
                <span className="text-xs font-medium">Refresh</span>
              </Button>
              <Button
                onClick={() => window.location.href = `/devices?branch=${deviceData.branch}`}
                variant="outline"
                className="flex flex-col items-center gap-2 h-auto py-3"
              >
                <MapPin className="h-5 w-5" />
                <span className="text-xs font-medium">Branch</span>
              </Button>
              {(deviceData.device_type?.toLowerCase().includes('router') ||
                deviceData.device_type?.toLowerCase().includes('switch')) && (
                <Button
                  onClick={() => {
                    window.location.href = `/topology?deviceId=${deviceData.hostid}&deviceName=${encodeURIComponent(deviceData.display_name)}`
                  }}
                  variant="outline"
                  className="flex flex-col items-center gap-2 h-auto py-3"
                >
                  <Network className="h-5 w-5" />
                  <span className="text-xs font-medium">Topology</span>
                </Button>
              )}
              <Button
                variant="outline"
                className="flex flex-col items-center gap-2 h-auto py-3"
              >
                <Wrench className="h-5 w-5" />
                <span className="text-xs font-medium">Maintain</span>
              </Button>
            </div>

            {/* Status History */}
            <div>
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-gray-100">
                <Activity className="h-5 w-5 text-ward-green" />
                Status History (Last 24 Hours)
              </h3>

              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700 mb-4">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Availability Timeline
                </h4>
                <ResponsiveContainer width="100%" height={180}>
                  <AreaChart data={statusHistory}>
                    <defs>
                      <linearGradient id="statusGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0.1}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.1} />
                    <XAxis
                      dataKey="time"
                      stroke="#6b7280"
                      tick={{ fill: '#6b7280', fontSize: 11 }}
                      tickFormatter={(value, index) => {
                        // Show fewer labels
                        if (index % 4 !== 0) return ''
                        return value
                      }}
                    />
                    <YAxis
                      stroke="#6b7280"
                      tick={{ fill: '#6b7280', fontSize: 11 }}
                      domain={[0, 1]}
                      ticks={[0, 1]}
                      tickFormatter={(value) => value === 1 ? 'Up' : 'Down'}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1f2937',
                        border: '1px solid #374151',
                        borderRadius: '8px',
                        color: '#f3f4f6',
                        fontSize: '12px'
                      }}
                      formatter={(value: any) => [value === 1 ? 'Online' : 'Offline', 'Status']}
                    />
                    <Area
                      type="stepAfter"
                      dataKey="status"
                      stroke="#10b981"
                      strokeWidth={2}
                      fill="url(#statusGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Response Time (ms)
                </h4>
                <ResponsiveContainer width="100%" height={180}>
                  <AreaChart data={statusHistory}>
                    <defs>
                      <linearGradient id="responseGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#5EBBA8" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="#5EBBA8" stopOpacity={0.1}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.1} />
                    <XAxis
                      dataKey="time"
                      stroke="#6b7280"
                      tick={{ fill: '#6b7280', fontSize: 11 }}
                      tickFormatter={(value, index) => {
                        if (index % 4 !== 0) return ''
                        return value
                      }}
                    />
                    <YAxis
                      stroke="#6b7280"
                      tick={{ fill: '#6b7280', fontSize: 11 }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1f2937',
                        border: '1px solid #374151',
                        borderRadius: '8px',
                        color: '#f3f4f6',
                        fontSize: '12px'
                      }}
                      formatter={(value: any) => [`${value.toFixed(2)} ms`, 'Response Time']}
                    />
                    <Area
                      type="monotone"
                      dataKey="responseTime"
                      stroke="#5EBBA8"
                      strokeWidth={2}
                      fill="url(#responseGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Device Information */}
            <div>
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-gray-100">
                <Info className="h-5 w-5 text-ward-green" />
                Device Information
              </h3>
              {isEditing ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <InputField label="Device Name" value={editForm.name || ''} onChange={(v) => setEditForm({...editForm, name: v})} />
                    <InputField label="IP Address" value={editForm.ip || ''} onChange={(v) => setEditForm({...editForm, ip: v})} />
                    <InputField label="Hostname" value={editForm.hostname || ''} onChange={(v) => setEditForm({...editForm, hostname: v})} />
                    <InputField label="Vendor" value={editForm.vendor || ''} onChange={(v) => setEditForm({...editForm, vendor: v})} />
                    <InputField label="Device Type" value={editForm.device_type || ''} onChange={(v) => setEditForm({...editForm, device_type: v})} />
                    <InputField label="Model" value={editForm.model || ''} onChange={(v) => setEditForm({...editForm, model: v})} />
                    <InputField label="Location" value={editForm.location || ''} onChange={(v) => setEditForm({...editForm, location: v})} />
                    <InputField label="Description" value={editForm.description || ''} onChange={(v) => setEditForm({...editForm, description: v})} />
                  </div>
                  <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4">
                    <h4 className="text-md font-semibold mb-3 text-gray-900 dark:text-gray-100">SSH Configuration</h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <InputField label="SSH Port" type="number" value={editForm.ssh_port || 22} onChange={(v) => setEditForm({...editForm, ssh_port: parseInt(v) || 22})} />
                      <InputField label="SSH Username" value={editForm.ssh_username || ''} onChange={(v) => setEditForm({...editForm, ssh_username: v})} />
                      <div className="flex items-center gap-2 pt-6">
                        <input
                          type="checkbox"
                          id="ssh_enabled"
                          checked={editForm.ssh_enabled}
                          onChange={(e) => setEditForm({...editForm, ssh_enabled: e.target.checked})}
                          className="h-4 w-4 rounded border-gray-300 text-ward-green focus:ring-ward-green"
                        />
                        <label htmlFor="ssh_enabled" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                          SSH Enabled
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <InfoRow label="Branch Location" value={deviceData.branch} />
                  <InfoRow label="Region" value={deviceData.region} />
                  <InfoRow label="IP Address" value={deviceData.ip} />
                  <InfoRow label="Device Type" value={deviceData.device_type} />
                  <InfoRow label="Hostname" value={deviceData.hostname} />
                  <InfoRow label="Vendor" value={deviceData.vendor || 'Not set'} />
                  <InfoRow label="Model" value={deviceData.model || 'Not set'} />
                  <InfoRow label="Location" value={deviceData.location || 'Not set'} />
                  <InfoRow label="SSH Port" value={deviceData.ssh_port?.toString() || '22'} />
                  <InfoRow label="SSH Username" value={deviceData.ssh_username || 'Not set'} />
                  <InfoRow label="Available" value={deviceData.available} />
                </div>
              )}
            </div>

            {/* Active Problems */}
            {deviceData.triggers && deviceData.triggers.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-gray-100">
                  <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
                  Active Problems ({deviceData.triggers.length})
                </h3>
                <div className="space-y-3">
                  {deviceData.triggers.map((trigger: any, index: number) => {
                    const startTime = parseInt(trigger.lastchange) * 1000
                    const duration = formatDuration(Date.now() - startTime)
                    return (
                      <div
                        key={index}
                        className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow bg-white dark:bg-gray-800"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <Badge variant={getSeverityVariant(parseInt(trigger.priority))}>
                                {getSeverityName(parseInt(trigger.priority))}
                              </Badge>
                            </div>
                            <p className="text-gray-900 dark:text-gray-100 font-medium">{trigger.description}</p>
                            <div className="flex items-center gap-4 mt-2 text-sm text-gray-600 dark:text-gray-400">
                              <span className="flex items-center gap-1">
                                <Clock className="h-4 w-4" />
                                {new Date(startTime).toLocaleString()}
                              </span>
                              <span className="flex items-center gap-1">
                                <Activity className="h-4 w-4" />
                                {duration}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-12">
            <AlertTriangle className="h-16 w-16 text-red-500 mx-auto mb-4" />
            <p className="text-gray-900 font-medium">Failed to load device information</p>
          </div>
        )}
      </ModalContent>
    </Modal>
  )
}

function InfoRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-gray-100 dark:border-gray-700">
      <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
      <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{value}</span>
    </div>
  )
}

function InputField({ label, value, onChange, type = 'text' }: { label: string; value: string | number; onChange: (value: string) => void; type?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-ward-green focus:border-transparent"
      />
    </div>
  )
}
