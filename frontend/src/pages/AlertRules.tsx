import { useState, useMemo, type ChangeEvent } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { LoadingSpinner } from '@/components/ui/Loading'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Badge from '@/components/ui/Badge'
import Select from '@/components/ui/Select'
import MultiSelect from '@/components/ui/MultiSelect'
import Switch from '@/components/ui/Switch'
import { Modal, ModalHeader, ModalTitle, ModalContent, ModalFooter } from '@/components/ui/Modal'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table'
import { alertRulesAPI, devicesAPI, branchesAPI } from '@/services/api'
import {
  Bell, Plus, Edit, Trash2, Power, AlertTriangle, Search,
  AlertCircle, AlertOctagon, Info, Zap, Activity, Clock, MapPin, Building2
} from 'lucide-react'
import { toast } from 'sonner'
import { formatDistanceToNow } from 'date-fns'

interface AlertRule {
  id: string
  name: string
  description?: string
  expression: string
  severity: string
  enabled: boolean
  device_id?: string
  branch_id?: string
  created_at: string
  updated_at: string
}

const EXPRESSION_TEMPLATES = [
  { label: 'Device Unreachable (3 min)', value: 'ping_unreachable >= 3' },
  { label: 'Device Unreachable (5 min)', value: 'ping_unreachable >= 5' },
  { label: 'High Ping (>200ms)', value: 'avg_ping_ms > 200' },
  { label: 'High Ping (>500ms)', value: 'avg_ping_ms > 500' },
  { label: 'Packet Loss (>10%)', value: 'packet_loss > 10' },
  { label: 'Packet Loss (>25%)', value: 'packet_loss > 25' },
  { label: 'Custom Expression', value: 'custom' },
]

const SEVERITY_CONFIG = {
  critical: { icon: AlertOctagon, color: 'text-red-600', bgColor: 'bg-red-100', label: 'Critical' },
  high: { icon: AlertCircle, color: 'text-orange-600', bgColor: 'bg-orange-100', label: 'High' },
  warning: { icon: AlertTriangle, color: 'text-yellow-600', bgColor: 'bg-yellow-100', label: 'Warning' },
  medium: { icon: Zap, color: 'text-blue-600', bgColor: 'bg-blue-100', label: 'Medium' },
  low: { icon: Info, color: 'text-gray-600', bgColor: 'bg-gray-100', label: 'Low' },
  info: { icon: Info, color: 'text-gray-500', bgColor: 'bg-gray-50', label: 'Info' },
}

export default function AlertRules() {
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [severityFilter, setSeverityFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [selectedTemplate, setSelectedTemplate] = useState('ping_unreachable >= 3')

  const [ruleForm, setRuleForm] = useState({
    name: '',
    description: '',
    expression: 'ping_unreachable >= 3',
    severity: 'warning',
    enabled: true,
    device_id: '',
    branch_id: '',
    scope: 'global', // 'global', 'branch', or 'device'
  })

  const { data: rulesData, isLoading } = useQuery({
    queryKey: ['alert-rules'],
    queryFn: async () => {
      const response = await alertRulesAPI.getRules()
      return response.data
    },
  })

  const { data: devicesData } = useQuery({
    queryKey: ['devices'],
    queryFn: async () => {
      const response = await devicesAPI.getAll()
      return response.data
    },
  })

  const { data: branchesData } = useQuery({
    queryKey: ['branches'],
    queryFn: async () => {
      const response = await branchesAPI.getAll()
      return response.data
    },
  })

  const createMutation = useMutation({
    mutationFn: alertRulesAPI.createRule,
    onSuccess: () => {
      toast.success('Alert rule created successfully')
      setModalOpen(false)
      resetForm()
      queryClient.invalidateQueries({ queryKey: ['alert-rules'] })
    },
    onError: () => {
      toast.error('Failed to create alert rule')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, ...data }: { id: string } & any) => alertRulesAPI.updateRule(id, data),
    onSuccess: () => {
      toast.success('Alert rule updated successfully')
      setModalOpen(false)
      setEditingRule(null)
      resetForm()
      queryClient.invalidateQueries({ queryKey: ['alert-rules'] })
    },
    onError: () => {
      toast.error('Failed to update alert rule')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: alertRulesAPI.deleteRule,
    onSuccess: () => {
      toast.success('Alert rule deleted')
      queryClient.invalidateQueries({ queryKey: ['alert-rules'] })
    },
    onError: () => {
      toast.error('Failed to delete alert rule')
    },
  })

  const toggleMutation = useMutation({
    mutationFn: alertRulesAPI.toggleRule,
    onSuccess: () => {
      toast.success('Alert rule status toggled')
      queryClient.invalidateQueries({ queryKey: ['alert-rules'] })
    },
    onError: () => {
      toast.error('Failed to toggle alert rule')
    },
  })

  const resetForm = () => {
    setRuleForm({
      name: '',
      description: '',
      expression: 'ping_unreachable >= 3',
      severity: 'warning',
      enabled: true,
      device_id: '',
      branch_id: '',
      scope: 'global',
    })
    setSelectedTemplate('ping_unreachable >= 3')
  }

  const openCreateModal = () => {
    resetForm()
    setEditingRule(null)
    setModalOpen(true)
  }

  const openEditModal = (rule: AlertRule) => {
    // Determine scope from rule
    const scope = rule.branch_id ? 'branch' : rule.device_id ? 'device' : 'global'

    setRuleForm({
      name: rule.name,
      description: rule.description || '',
      expression: rule.expression,
      severity: rule.severity,
      enabled: rule.enabled,
      device_id: rule.device_id || '',
      branch_id: rule.branch_id || '',
      scope: scope,
    })
    setSelectedTemplate('custom')
    setEditingRule(rule)
    setModalOpen(true)
  }

  const handleSubmit = () => {
    // Prepare data based on scope
    const submitData: any = {
      name: ruleForm.name,
      description: ruleForm.description,
      expression: ruleForm.expression,
      severity: ruleForm.severity,
      enabled: ruleForm.enabled,
    }

    // Set device_id or branch_id based on scope
    if (ruleForm.scope === 'device') {
      submitData.device_id = ruleForm.device_id || null
      submitData.branch_id = null
    } else if (ruleForm.scope === 'branch') {
      submitData.branch_id = ruleForm.branch_id || null
      submitData.device_id = null
    } else {
      // Global rule
      submitData.device_id = null
      submitData.branch_id = null
    }

    if (editingRule) {
      updateMutation.mutate({ id: editingRule.id, ...submitData })
    } else {
      createMutation.mutate(submitData)
    }
  }

  const handleDelete = (id: string, name: string) => {
    if (confirm(`Are you sure you want to delete "${name}"?`)) {
      deleteMutation.mutate(id)
    }
  }

  const handleTemplateChange = (template: string) => {
    setSelectedTemplate(template)
    if (template !== 'custom') {
      setRuleForm({ ...ruleForm, expression: template })
    }
  }

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      critical: 'destructive',
      high: 'destructive',
      warning: 'warning',
      medium: 'warning',
      low: 'secondary',
      info: 'default',
    }
    return colors[severity.toLowerCase()] || 'default'
  }

  const getSeverityIcon = (severity: string) => {
    const config = SEVERITY_CONFIG[severity.toLowerCase() as keyof typeof SEVERITY_CONFIG]
    if (!config) return Info
    return config.icon
  }

  const rules = rulesData?.rules || []
  const devices = devicesData || []
  const branches = branchesData?.branches || []

  const branchOptions = useMemo(
    () =>
      branches.map((branch: any) => ({
        value: branch.id,
        label: `${branch.display_name}${branch.region ? ` (${branch.region})` : ''}`,
      })),
    [branches],
  )

  const deviceOptions = useMemo(
    () =>
      devices.map((device: any) => ({
        value: device.hostid,
        label: `${device.display_name || device.hostname || device.name || 'Device'} (${device.ip})`,
      })),
    [devices],
  )

  // Filter and search rules
  const filteredRules = useMemo(() => {
    return rules.filter((rule: AlertRule) => {
      const matchesSearch = rule.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           rule.description?.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesSeverity = severityFilter === 'all' || rule.severity === severityFilter
      const matchesStatus = statusFilter === 'all' ||
                           (statusFilter === 'enabled' && rule.enabled) ||
                           (statusFilter === 'disabled' && !rule.enabled)
      return matchesSearch && matchesSeverity && matchesStatus
    })
  }, [rules, searchQuery, severityFilter, statusFilter])

  // Calculate stats
  const stats = useMemo(() => {
    const total = rules.length
    const enabled = rules.filter((r: AlertRule) => r.enabled).length
    const critical = rules.filter((r: AlertRule) => r.severity === 'critical').length
    const high = rules.filter((r: AlertRule) => r.severity === 'high').length
    return { total, enabled, disabled: total - enabled, critical, high }
  }, [rules])

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Bell className="h-8 w-8 text-ward-green" />
            Alert Rules Management
          </h1>
          <p className="text-muted-foreground mt-1">
            Configure and manage alert rules for device monitoring
          </p>
        </div>
        <Button onClick={openCreateModal} className="bg-ward-green hover:bg-ward-green/90">
          <Plus className="h-4 w-4 mr-2" />
          Create Alert Rule
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card variant="glass" hover>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Rules</p>
                <p className="text-2xl font-bold">{stats.total}</p>
              </div>
              <Activity className="h-8 w-8 text-ward-green" />
            </div>
          </CardContent>
        </Card>
        <Card variant="glass" hover>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Enabled</p>
                <p className="text-2xl font-bold text-green-600">{stats.enabled}</p>
              </div>
              <Power className="h-8 w-8 text-green-600" />
            </div>
          </CardContent>
        </Card>
        <Card variant="glass" hover>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Critical</p>
                <p className="text-2xl font-bold text-red-600">{stats.critical}</p>
              </div>
              <AlertOctagon className="h-8 w-8 text-red-600" />
            </div>
          </CardContent>
        </Card>
        <Card variant="glass" hover>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">High Priority</p>
                <p className="text-2xl font-bold text-orange-600">{stats.high}</p>
              </div>
              <AlertCircle className="h-8 w-8 text-orange-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card variant="glass">
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search alert rules..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select
              value={severityFilter}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setSeverityFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Severities' },
                { value: 'critical', label: 'Critical' },
                { value: 'high', label: 'High' },
                { value: 'warning', label: 'Warning' },
                { value: 'low', label: 'Low' },
                { value: 'info', label: 'Info' },
              ]}
            />
            <Select
              value={statusFilter}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setStatusFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Status' },
                { value: 'enabled', label: 'Enabled' },
                { value: 'disabled', label: 'Disabled' },
              ]}
            />
          </div>
        </CardContent>
      </Card>

      {/* Alert Rules Table */}
      <Card variant="glass">
        <CardHeader>
          <CardTitle>
            Alert Rules ({filteredRules.length}{filteredRules.length !== rules.length && ` of ${rules.length}`})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner />
            </div>
          ) : filteredRules.length === 0 ? (
            <div className="text-center py-12">
              <AlertTriangle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">
                {rules.length === 0 ? 'No Alert Rules' : 'No Matching Rules'}
              </h3>
              <p className="text-muted-foreground mb-4">
                {rules.length === 0
                  ? 'Create your first alert rule to monitor devices'
                  : 'Try adjusting your filters or search query'}
              </p>
              {rules.length === 0 && (
                <Button onClick={openCreateModal} className="bg-ward-green hover:bg-ward-green/90">
                  <Plus className="h-4 w-4 mr-2" />
                  Create Alert Rule
                </Button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[50px]"></TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Scope/Target</TableHead>
                    <TableHead>Expression</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Updated</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRules.map((rule: AlertRule) => {
                    const SeverityIcon = getSeverityIcon(rule.severity)
                    const severityConfig = SEVERITY_CONFIG[rule.severity.toLowerCase() as keyof typeof SEVERITY_CONFIG]

                    // Determine scope and target
                    const branch = rule.branch_id ? branches.find((b: any) => b.id === rule.branch_id) : null
                    const device = rule.device_id ? devices.find((d: any) => d.hostid === rule.device_id) : null

                    return (
                      <TableRow key={rule.id}>
                        <TableCell>
                          <div className={`p-2 rounded-full ${severityConfig?.bgColor || 'bg-gray-100'}`}>
                            <SeverityIcon className={`h-4 w-4 ${severityConfig?.color || 'text-gray-600'}`} />
                          </div>
                        </TableCell>
                        <TableCell>
                          <div>
                            <div className="font-medium">{rule.name}</div>
                            {rule.description && (
                              <div className="text-sm text-muted-foreground mt-0.5">
                                {rule.description}
                              </div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {rule.branch_id ? (
                              <>
                                <MapPin className="h-4 w-4 text-blue-600" />
                                <div>
                                  <div className="text-sm font-medium">{branch?.display_name || 'Branch'}</div>
                                  <div className="text-xs text-muted-foreground">
                                    {branch?.device_count || 0} devices
                                  </div>
                                </div>
                              </>
                            ) : rule.device_id ? (
                              <>
                                <Building2 className="h-4 w-4 text-purple-600" />
                                <div>
                                  <div className="text-sm font-medium">{device?.name || 'Device'}</div>
                                  <div className="text-xs text-muted-foreground">{device?.ip}</div>
                                </div>
                              </>
                            ) : (
                              <>
                                <Activity className="h-4 w-4 text-gray-600" />
                                <div className="text-sm font-medium text-muted-foreground">Global (All Devices)</div>
                              </>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <code className="text-xs bg-muted px-2 py-1 rounded font-mono">
                            {rule.expression}
                          </code>
                        </TableCell>
                        <TableCell>
                          <Badge variant={getSeverityColor(rule.severity) as any}>
                            {rule.severity.toUpperCase()}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={rule.enabled ? 'success' : 'default'}>
                            {rule.enabled ? 'Enabled' : 'Disabled'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1 text-sm text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            {formatDistanceToNow(new Date(rule.updated_at), { addSuffix: true })}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => toggleMutation.mutate(rule.id)}
                              title={rule.enabled ? 'Disable' : 'Enable'}
                              className="h-8 w-8 p-0"
                            >
                              <Power className={`h-4 w-4 ${rule.enabled ? 'text-green-600' : 'text-gray-400'}`} />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openEditModal(rule)}
                              className="h-8 w-8 p-0"
                              title="Edit"
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDelete(rule.id, rule.name)}
                              className="h-8 w-8 p-0"
                              title="Delete"
                            >
                              <Trash2 className="h-4 w-4 text-red-600 hover:text-red-700" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Modal */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)}>
        <ModalHeader onClose={() => setModalOpen(false)}>
          <ModalTitle>
            {editingRule ? 'Edit Alert Rule' : 'Create Alert Rule'}
          </ModalTitle>
        </ModalHeader>
        <ModalContent>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium block mb-2">Rule Name *</label>
              <Input
                value={ruleForm.name}
                onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })}
                placeholder="e.g., High Ping Alert"
              />
            </div>

            <div>
              <label className="text-sm font-medium block mb-2">Description</label>
              <Input
                value={ruleForm.description}
                onChange={(e) => setRuleForm({ ...ruleForm, description: e.target.value })}
                placeholder="Optional description"
              />
            </div>

            <Select
              label="Expression Template"
              value={selectedTemplate}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => handleTemplateChange(e.target.value)}
              options={EXPRESSION_TEMPLATES}
              fullWidth
            />

            <div>
              <label className="text-sm font-medium block mb-2">Expression *</label>
              <Input
                value={ruleForm.expression}
                onChange={(e) => setRuleForm({ ...ruleForm, expression: e.target.value })}
                placeholder="ping_unreachable >= 3"
                disabled={selectedTemplate !== 'custom'}
              />
              <p className="text-xs text-muted-foreground mt-1">
                Available metrics: ping_unreachable, avg_ping_ms, packet_loss
              </p>
            </div>

            <Select
              label="Severity *"
              value={ruleForm.severity}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setRuleForm({ ...ruleForm, severity: e.target.value })}
              options={[
                { value: 'info', label: 'Info - Informational messages' },
                { value: 'low', label: 'Low - Minor issues' },
                { value: 'warning', label: 'Warning - Potential problems' },
                { value: 'high', label: 'High - Serious issues' },
                { value: 'critical', label: 'Critical - Urgent attention needed' },
              ]}
              fullWidth
            />

            <Select
              label="Alert Scope *"
              value={ruleForm.scope}
              onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                setRuleForm({ ...ruleForm, scope: e.target.value, device_id: '', branch_id: '' })
              }
              options={[
                { value: 'global', label: 'Global - All Devices' },
                { value: 'branch', label: 'Branch - Devices in a Branch' },
                { value: 'device', label: 'Device - Specific Device' },
              ]}
              helperText={
                ruleForm.scope === 'global'
                  ? 'This rule will apply to all devices in the system.'
                  : ruleForm.scope === 'branch'
                  ? 'Applies to every device assigned to the selected branch.'
                  : 'Applies only to the device you select below.'
              }
              fullWidth
            />

            {ruleForm.scope === 'branch' && (
              <div>
                <label className="text-sm font-medium block mb-2 flex items-center gap-2">
                  <MapPin className="h-4 w-4" />
                  Select Branch *
                </label>
                <MultiSelect
                  options={branchOptions}
                  selected={ruleForm.branch_id ? [ruleForm.branch_id] : []}
                  onChange={(values) => setRuleForm({ ...ruleForm, branch_id: values[0] ?? '' })}
                  placeholder="Select a branch..."
                  helperText="Choose the branch whose devices should inherit this rule."
                  maxSelected={1}
                />
              </div>
            )}

            {ruleForm.scope === 'device' && (
              <div>
                <label className="text-sm font-medium block mb-2 flex items-center gap-2">
                  <Building2 className="h-4 w-4" />
                  Select Device *
                </label>
                <MultiSelect
                  options={deviceOptions}
                  selected={ruleForm.device_id ? [ruleForm.device_id] : []}
                  onChange={(values) => setRuleForm({ ...ruleForm, device_id: values[0] ?? '' })}
                  placeholder="Select a device..."
                  helperText="Pick the device that should trigger this rule."
                  maxSelected={1}
                />
              </div>
            )}

            <Switch
              checked={ruleForm.enabled}
              onClick={() => setRuleForm(prev => ({ ...prev, enabled: !prev.enabled }))}
              label="Enable rule immediately"
              helperText="Enabled rules start evaluating as soon as you save."
            />
          </div>
        </ModalContent>
        <ModalFooter>
          <Button variant="ghost" onClick={() => setModalOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={
              !ruleForm.name ||
              !ruleForm.expression ||
              (ruleForm.scope === 'branch' && !ruleForm.branch_id) ||
              (ruleForm.scope === 'device' && !ruleForm.device_id)
            }
            className="bg-ward-green hover:bg-ward-green/90"
          >
            {editingRule ? 'Update' : 'Create'} Rule
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  )
}
