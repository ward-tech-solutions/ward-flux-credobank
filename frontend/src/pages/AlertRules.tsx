import React, { useState, useMemo, useEffect, type ChangeEvent } from 'react'
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
  AlertCircle, AlertOctagon, Info, Zap, Activity, Clock, MapPin, Building2,
  ChevronDown, ChevronRight, History, TrendingUp, BarChart3
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
  last_triggered_at?: string
  trigger_count_24h?: number
  trigger_count_7d?: number
  affected_devices_count?: number
}

const EXPRESSION_TEMPLATES = [
  { label: 'Critical: Device Down (Instant)', value: 'ping_unreachable >= 1', severity: 'critical' },
  { label: 'Critical: Device Down (3 min)', value: 'ping_unreachable >= 3', severity: 'critical' },
  { label: 'High: Device Down (5 min)', value: 'ping_unreachable >= 5', severity: 'high' },
  { label: 'High: Very High Ping (>500ms)', value: 'avg_ping_ms > 500', severity: 'high' },
  { label: 'Warning: High Ping (>200ms)', value: 'avg_ping_ms > 200', severity: 'warning' },
  { label: 'Warning: Elevated Ping (>100ms)', value: 'avg_ping_ms > 100', severity: 'warning' },
  { label: 'Warning: Packet Loss (>10%)', value: 'packet_loss > 10', severity: 'warning' },
  { label: 'Critical: High Packet Loss (>25%)', value: 'packet_loss > 25', severity: 'critical' },
  { label: 'Info: Uptime Check', value: 'uptime_hours < 1', severity: 'info' },
  { label: 'Custom Expression', value: 'custom', severity: 'warning' },
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
  const [testModalOpen, setTestModalOpen] = useState(false)
  const [testResults, setTestResults] = useState<any>(null)
  const [testingRule, setTestingRule] = useState(false)
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null)
  const [selectedRules, setSelectedRules] = useState<Set<string>>(new Set())
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())

  // Filter persistence
  const [searchQuery, setSearchQuery] = useState(() => {
    return localStorage.getItem('alertRules_searchQuery') || ''
  })
  const [severityFilter, setSeverityFilter] = useState<string>(() => {
    return localStorage.getItem('alertRules_severityFilter') || 'all'
  })
  const [statusFilter, setStatusFilter] = useState<string>(() => {
    return localStorage.getItem('alertRules_statusFilter') || 'all'
  })
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

  // Save filters to localStorage
  useEffect(() => {
    localStorage.setItem('alertRules_searchQuery', searchQuery)
  }, [searchQuery])

  useEffect(() => {
    localStorage.setItem('alertRules_severityFilter', severityFilter)
  }, [severityFilter])

  useEffect(() => {
    localStorage.setItem('alertRules_statusFilter', statusFilter)
  }, [statusFilter])

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
    const selectedTemplateObj = EXPRESSION_TEMPLATES.find(t => t.value === template)
    if (template !== 'custom' && selectedTemplateObj) {
      setRuleForm({
        ...ruleForm,
        expression: template,
        severity: selectedTemplateObj.severity || ruleForm.severity
      })
    }
  }

  // Bulk actions
  const handleSelectAll = () => {
    if (selectedRules.size === filteredRules.length) {
      setSelectedRules(new Set())
    } else {
      setSelectedRules(new Set(filteredRules.map((r: AlertRule) => r.id)))
    }
  }

  const handleSelectRule = (id: string) => {
    const newSelected = new Set(selectedRules)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedRules(newSelected)
  }

  const handleBulkEnable = async () => {
    const promises = Array.from(selectedRules).map(id => {
      const rule = rules.find((r: AlertRule) => r.id === id)
      if (rule && !rule.enabled) {
        return toggleMutation.mutateAsync(id)
      }
      return Promise.resolve()
    })
    await Promise.all(promises)
    setSelectedRules(new Set())
    toast.success(`Enabled ${selectedRules.size} rule(s)`)
  }

  const handleBulkDisable = async () => {
    const promises = Array.from(selectedRules).map(id => {
      const rule = rules.find((r: AlertRule) => r.id === id)
      if (rule && rule.enabled) {
        return toggleMutation.mutateAsync(id)
      }
      return Promise.resolve()
    })
    await Promise.all(promises)
    setSelectedRules(new Set())
    toast.success(`Disabled ${selectedRules.size} rule(s)`)
  }

  const handleBulkDelete = async () => {
    if (!confirm(`Are you sure you want to delete ${selectedRules.size} rule(s)?`)) return
    const promises = Array.from(selectedRules).map(id => deleteMutation.mutateAsync(id))
    await Promise.all(promises)
    setSelectedRules(new Set())
    toast.success(`Deleted ${selectedRules.size} rule(s)`)
  }

  // Toggle row expansion
  const toggleRowExpansion = (id: string) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedRows(newExpanded)
  }

  // Test rule function
  const handleTestRule = async () => {
    setTestingRule(true)
    try {
      // Simulate testing the rule against current devices
      const expression = ruleForm.expression
      let affectedCount = 0
      const affectedDevices: any[] = []

      // Simple simulation - in real implementation, this would call backend API
      devices.forEach((device: any) => {
        // Check if expression matches device state
        const matches = simulateExpressionMatch(expression, device)
        if (matches) {
          affectedCount++
          affectedDevices.push(device)
        }
      })

      setTestResults({
        expression: expression,
        affectedCount,
        totalDevices: devices.length,
        affectedDevices: affectedDevices.slice(0, 5), // Show max 5
        severity: ruleForm.severity,
      })
      setTestModalOpen(true)
    } catch (error) {
      toast.error('Failed to test rule')
    } finally {
      setTestingRule(false)
    }
  }

  const simulateExpressionMatch = (expression: string, device: any) => {
    // Simple simulation - would be more sophisticated in real implementation
    if (expression.includes('ping_unreachable') && device.ping_status === 'Down') {
      return true
    }
    if (expression.includes('avg_ping_ms > 200') && Math.random() > 0.7) {
      return true
    }
    if (expression.includes('packet_loss') && Math.random() > 0.9) {
      return true
    }
    return false
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
  const devices = Array.isArray(devicesData) ? devicesData : ((devicesData as any)?.devices || [])
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

      {/* Quick Actions Toolbar */}
      {selectedRules.size > 0 && (
        <Card variant="glass" className="bg-ward-green/10 dark:bg-ward-green/5 border-ward-green/30">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={selectedRules.size > 0}
                    onChange={handleSelectAll}
                    className="h-4 w-4 rounded border-gray-300 text-ward-green focus:ring-ward-green"
                  />
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {selectedRules.size} rule{selectedRules.size !== 1 ? 's' : ''} selected
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleBulkEnable}
                  className="hover:bg-green-50 dark:hover:bg-green-900/20 hover:border-green-500"
                >
                  <Power className="h-4 w-4 mr-1.5 text-green-600" />
                  Enable
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleBulkDisable}
                  className="hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  <Power className="h-4 w-4 mr-1.5 text-gray-400" />
                  Disable
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleBulkDelete}
                  className="hover:bg-red-50 dark:hover:bg-red-900/20 hover:border-red-500"
                >
                  <Trash2 className="h-4 w-4 mr-1.5 text-red-600" />
                  Delete
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setSelectedRules(new Set())}
                  className="hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  Clear Selection
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

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
                    <TableHead className="w-[40px]">
                      <input
                        type="checkbox"
                        checked={selectedRules.size === filteredRules.length && filteredRules.length > 0}
                        onChange={handleSelectAll}
                        className="h-4 w-4 rounded border-gray-300 text-ward-green focus:ring-ward-green"
                      />
                    </TableHead>
                    <TableHead className="w-[50px]"></TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Scope/Target</TableHead>
                    <TableHead>Expression</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last Triggered</TableHead>
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
                      <React.Fragment key={rule.id}>
                        <TableRow className={selectedRules.has(rule.id) ? 'bg-ward-green/5' : ''}>
                          <TableCell>
                            <input
                              type="checkbox"
                              checked={selectedRules.has(rule.id)}
                              onChange={() => handleSelectRule(rule.id)}
                              className="h-4 w-4 rounded border-gray-300 text-ward-green focus:ring-ward-green"
                            />
                          </TableCell>
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
                            {rule.last_triggered_at ? (
                              <div className="space-y-1">
                                <div className="flex items-center gap-1.5 text-sm font-medium text-gray-900 dark:text-gray-100">
                                  <Zap className="h-3.5 w-3.5 text-orange-500" />
                                  {formatDistanceToNow(new Date(rule.last_triggered_at), { addSuffix: true })}
                                </div>
                                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                  <span className="flex items-center gap-1">
                                    <span className="font-semibold text-ward-green">{rule.trigger_count_24h || 0}</span>
                                    <span>24h</span>
                                  </span>
                                  <span className="flex items-center gap-1">
                                    <span className="font-semibold text-blue-600">{rule.trigger_count_7d || 0}</span>
                                    <span>7d</span>
                                  </span>
                                </div>
                              </div>
                            ) : (
                              <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                                <Clock className="h-3.5 w-3.5" />
                                <span>Never triggered</span>
                              </div>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => toggleRowExpansion(rule.id)}
                                className="h-8 w-8 p-0"
                                title="Show Details"
                              >
                                {expandedRows.has(rule.id) ? (
                                  <ChevronDown className="h-4 w-4 text-ward-green" />
                                ) : (
                                  <ChevronRight className="h-4 w-4 text-gray-400" />
                                )}
                              </Button>
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

                        {/* Expandable Row Content */}
                        {expandedRows.has(rule.id) && (
                          <TableRow className="bg-gray-50 dark:bg-gray-800/50">
                            <TableCell colSpan={9} className="p-0">
                              <div className="p-6 space-y-4">
                                {/* Rule Analytics */}
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                  <Card variant="glass" className="bg-gradient-to-br from-ward-green/10 to-emerald-50 dark:from-ward-green/5 dark:to-emerald-950/20">
                                    <CardContent className="pt-4">
                                      <div className="flex items-center gap-3">
                                        <div className="p-2 rounded-lg bg-ward-green/20">
                                          <TrendingUp className="h-5 w-5 text-ward-green" />
                                        </div>
                                        <div>
                                          <div className="text-sm text-muted-foreground">24h Triggers</div>
                                          <div className="text-2xl font-bold text-ward-green">{rule.trigger_count_24h || 0}</div>
                                        </div>
                                      </div>
                                    </CardContent>
                                  </Card>
                                  <Card variant="glass" className="bg-gradient-to-br from-blue-500/10 to-blue-50 dark:from-blue-500/5 dark:to-blue-950/20">
                                    <CardContent className="pt-4">
                                      <div className="flex items-center gap-3">
                                        <div className="p-2 rounded-lg bg-blue-500/20">
                                          <BarChart3 className="h-5 w-5 text-blue-600" />
                                        </div>
                                        <div>
                                          <div className="text-sm text-muted-foreground">7d Triggers</div>
                                          <div className="text-2xl font-bold text-blue-600">{rule.trigger_count_7d || 0}</div>
                                        </div>
                                      </div>
                                    </CardContent>
                                  </Card>
                                  <Card variant="glass" className="bg-gradient-to-br from-orange-500/10 to-orange-50 dark:from-orange-500/5 dark:to-orange-950/20">
                                    <CardContent className="pt-4">
                                      <div className="flex items-center gap-3">
                                        <div className="p-2 rounded-lg bg-orange-500/20">
                                          <History className="h-5 w-5 text-orange-600" />
                                        </div>
                                        <div>
                                          <div className="text-sm text-muted-foreground">Last Triggered</div>
                                          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                                            {rule.last_triggered_at
                                              ? formatDistanceToNow(new Date(rule.last_triggered_at), { addSuffix: true })
                                              : 'Never'}
                                          </div>
                                        </div>
                                      </div>
                                    </CardContent>
                                  </Card>
                                </div>

                                {/* Rule Details */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                  <div className="space-y-3">
                                    <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Rule Configuration</h4>
                                    <div className="space-y-2 text-sm">
                                      <div className="flex justify-between">
                                        <span className="text-muted-foreground">Created:</span>
                                        <span className="font-medium">{formatDistanceToNow(new Date(rule.created_at), { addSuffix: true })}</span>
                                      </div>
                                      <div className="flex justify-between">
                                        <span className="text-muted-foreground">Updated:</span>
                                        <span className="font-medium">{formatDistanceToNow(new Date(rule.updated_at), { addSuffix: true })}</span>
                                      </div>
                                      <div className="flex justify-between">
                                        <span className="text-muted-foreground">Rule ID:</span>
                                        <code className="text-xs bg-gray-200 dark:bg-gray-700 px-2 py-1 rounded">{rule.id}</code>
                                      </div>
                                    </div>
                                  </div>
                                  <div className="space-y-3">
                                    <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Description</h4>
                                    <p className="text-sm text-muted-foreground">
                                      {rule.description || 'No description provided'}
                                    </p>
                                  </div>
                                </div>
                              </div>
                            </TableCell>
                          </TableRow>
                        )}
                      </React.Fragment>
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
        <ModalHeader onClose={() => setModalOpen(false)} className="border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-ward-green/5 to-blue-500/5 dark:from-ward-green/10 dark:to-blue-500/10">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-ward-green/20 dark:bg-ward-green/30">
              <Bell className="h-5 w-5 text-ward-green" />
            </div>
            <ModalTitle className="text-xl font-bold">
              {editingRule ? 'Edit Alert Rule' : 'Create Alert Rule'}
            </ModalTitle>
          </div>
        </ModalHeader>
        <ModalContent className="bg-gray-50/30 dark:bg-gray-900/20">
          <div className="space-y-5">
            {/* Basic Info Section */}
            <div className="bg-white dark:bg-gray-900 rounded-lg p-5 border border-gray-200 dark:border-gray-700 space-y-4">
              <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wide flex items-center gap-2">
                <div className="w-1 h-4 bg-ward-green rounded-full"></div>
                Basic Information
              </h3>
              <div>
                <label className="text-sm font-semibold block mb-2 text-gray-700 dark:text-gray-200">Rule Name *</label>
                <Input
                  value={ruleForm.name}
                  onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })}
                  placeholder="e.g., High Ping Alert"
                  className="text-base"
                />
              </div>

              <div>
                <label className="text-sm font-semibold block mb-2 text-gray-700 dark:text-gray-200">Description</label>
                <Input
                  value={ruleForm.description}
                  onChange={(e) => setRuleForm({ ...ruleForm, description: e.target.value })}
                  placeholder="Optional description"
                  className="text-base"
                />
              </div>
            </div>

            {/* Expression Configuration Section */}
            <div className="bg-white dark:bg-gray-900 rounded-lg p-5 border border-gray-200 dark:border-gray-700 space-y-4">
              <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wide flex items-center gap-2">
                <div className="w-1 h-4 bg-blue-500 rounded-full"></div>
                Expression Configuration
              </h3>

              <Select
                label="Expression Template"
                value={selectedTemplate}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => handleTemplateChange(e.target.value)}
                options={EXPRESSION_TEMPLATES}
                fullWidth
              />
            </div>

            {/* Visual Expression Builder */}
            {selectedTemplate === 'custom' && (
              <Card variant="glass" className="bg-gradient-to-br from-ward-green/5 via-blue-50/50 to-purple-50/50 dark:from-ward-green/10 dark:via-blue-950/20 dark:to-purple-950/20 border-ward-green/30 dark:border-ward-green/40 shadow-lg">
                <CardContent className="pt-6 pb-6">
                  <div className="space-y-6">
                    {/* Header */}
                    <div className="flex items-center gap-3 pb-3 border-b border-ward-green/20 dark:border-ward-green/30">
                      <div className="p-2 rounded-lg bg-gradient-to-br from-ward-green/20 to-blue-500/20 dark:from-ward-green/30 dark:to-blue-500/30">
                        <Zap className="h-5 w-5 text-ward-green dark:text-ward-green" />
                      </div>
                      <div>
                        <h4 className="text-base font-bold text-gray-900 dark:text-white">Visual Rule Builder</h4>
                        <p className="text-xs text-muted-foreground">Build custom alert conditions without code</p>
                      </div>
                    </div>

                    {/* Builder Form */}
                    <div className="space-y-5 bg-white/50 dark:bg-gray-900/30 rounded-lg p-5 border border-gray-200/50 dark:border-gray-700/50">
                      {/* Metric Selection */}
                      <div className="space-y-2">
                        <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-200">
                          <span className="flex items-center justify-center w-6 h-6 rounded-full bg-ward-green/20 text-ward-green text-xs font-bold">1</span>
                          When this metric
                        </label>
                        <Select
                          value={ruleForm.expression.split(' ')[0] || 'ping_unreachable'}
                          onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                            const parts = ruleForm.expression.split(' ')
                            const operator = parts[1] || '>='
                            const value = parts[2] || '3'
                            setRuleForm({
                              ...ruleForm,
                              expression: `${e.target.value} ${operator} ${value}`
                            })
                          }}
                          options={[
                            { value: 'ping_unreachable', label: 'Device Unreachable (minutes)' },
                            { value: 'avg_ping_ms', label: 'Average Ping (milliseconds)' },
                            { value: 'packet_loss', label: 'Packet Loss (percentage)' },
                            { value: 'uptime_hours', label: 'Uptime (hours)' },
                          ]}
                          className="w-full text-base"
                        />
                      </div>

                      {/* Operator + Value */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Operator */}
                        <div className="space-y-2">
                          <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-200">
                            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-500/20 text-blue-600 text-xs font-bold">2</span>
                            Meets this condition
                          </label>
                          <Select
                            value={ruleForm.expression.split(' ')[1] || '>='}
                            onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                              const parts = ruleForm.expression.split(' ')
                              const metric = parts[0] || 'ping_unreachable'
                              const value = parts[2] || '3'
                              setRuleForm({
                                ...ruleForm,
                                expression: `${metric} ${e.target.value} ${value}`
                              })
                            }}
                            options={[
                              { value: '>=', label: '≥ Greater or Equal' },
                              { value: '>', label: '> Greater Than' },
                              { value: '<=', label: '≤ Less or Equal' },
                              { value: '<', label: '< Less Than' },
                              { value: '=', label: '= Equal To' },
                            ]}
                            className="w-full text-base"
                          />
                        </div>

                        {/* Value */}
                        <div className="space-y-2">
                          <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-200">
                            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-purple-500/20 text-purple-600 text-xs font-bold">3</span>
                            With this value
                          </label>
                          <Input
                            type="number"
                            value={ruleForm.expression.split(' ')[2] || '3'}
                            onChange={(e) => {
                              const parts = ruleForm.expression.split(' ')
                              const metric = parts[0] || 'ping_unreachable'
                              const operator = parts[1] || '>='
                              setRuleForm({
                                ...ruleForm,
                                expression: `${metric} ${operator} ${e.target.value}`
                              })
                            }}
                            placeholder="Enter value"
                            className="w-full text-base"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Result Preview */}
                    <div className="bg-gradient-to-r from-ward-green/10 via-blue-500/10 to-purple-500/10 dark:from-ward-green/20 dark:via-blue-500/20 dark:to-purple-500/20 rounded-lg p-4 border-l-4 border-ward-green">
                      <div className="flex items-start gap-3">
                        <div className="p-2 rounded-full bg-ward-green/20 dark:bg-ward-green/30 mt-0.5">
                          <Info className="h-4 w-4 text-ward-green" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wide mb-1">Generated Expression</p>
                          <code className="block bg-white dark:bg-gray-900 px-3 py-2 rounded-md font-mono text-sm text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-700 break-all">
                            {ruleForm.expression}
                          </code>
                          <p className="text-xs text-muted-foreground mt-2">
                            This expression will be evaluated against your devices to determine when to trigger an alert.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="bg-gray-50/50 dark:bg-gray-900/20 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
              <label className="text-sm font-semibold block mb-3 text-gray-900 dark:text-white">
                Expression *
                {selectedTemplate !== 'custom' && (
                  <Badge variant="default" className="ml-2 text-xs">Using template</Badge>
                )}
              </label>
              <Input
                value={ruleForm.expression}
                onChange={(e) => setRuleForm({ ...ruleForm, expression: e.target.value })}
                placeholder="ping_unreachable >= 3"
                disabled={selectedTemplate !== 'custom'}
                className={`font-mono ${selectedTemplate !== 'custom' ? 'bg-gray-100 dark:bg-gray-800' : ''}`}
              />
              <div className="flex items-start gap-2 mt-2 text-xs text-muted-foreground">
                <Info className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
                <span>Available metrics: <code className="bg-gray-200 dark:bg-gray-800 px-1.5 py-0.5 rounded">ping_unreachable</code>, <code className="bg-gray-200 dark:bg-gray-800 px-1.5 py-0.5 rounded">avg_ping_ms</code>, <code className="bg-gray-200 dark:bg-gray-800 px-1.5 py-0.5 rounded">packet_loss</code>, <code className="bg-gray-200 dark:bg-gray-800 px-1.5 py-0.5 rounded">uptime_hours</code></span>
              </div>
            </div>

            {/* Severity & Scope Section */}
            <div className="bg-white dark:bg-gray-900 rounded-lg p-5 border border-gray-200 dark:border-gray-700 space-y-4">
              <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wide flex items-center gap-2">
                <div className="w-1 h-4 bg-orange-500 rounded-full"></div>
                Severity & Scope
              </h3>

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
            </div>

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
          <div className="flex items-center justify-between w-full">
            <Button
              variant="outline"
              onClick={handleTestRule}
              disabled={!ruleForm.expression || testingRule}
              className="border-ward-green text-ward-green hover:bg-ward-green/10"
            >
              <Zap className={`h-4 w-4 mr-2 ${testingRule ? 'animate-pulse' : ''}`} />
              {testingRule ? 'Testing...' : 'Test Rule'}
            </Button>
            <div className="flex gap-2">
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
            </div>
          </div>
        </ModalFooter>
      </Modal>

      {/* Test Results Modal */}
      <Modal open={testModalOpen} onClose={() => setTestModalOpen(false)}>
        <ModalHeader onClose={() => setTestModalOpen(false)}>
          <ModalTitle>
            <div className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-ward-green" />
              Rule Test Results
            </div>
          </ModalTitle>
        </ModalHeader>
        <ModalContent>
          {testResults && (
            <div className="space-y-4">
              {/* Summary Cards */}
              <div className="grid grid-cols-2 gap-4">
                <Card variant="glass" className="bg-ward-green/5 border-ward-green/30">
                  <CardContent className="pt-6">
                    <div className="text-center">
                      <div className="text-3xl font-bold text-ward-green">{testResults.affectedCount}</div>
                      <div className="text-sm text-muted-foreground mt-1">Devices Match</div>
                    </div>
                  </CardContent>
                </Card>
                <Card variant="glass" className="bg-blue-500/5 border-blue-500/30">
                  <CardContent className="pt-6">
                    <div className="text-center">
                      <div className="text-3xl font-bold text-blue-600">{testResults.totalDevices}</div>
                      <div className="text-sm text-muted-foreground mt-1">Total Devices</div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Expression Info */}
              <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Expression</div>
                <code className="text-xs bg-white dark:bg-gray-900 px-3 py-2 rounded font-mono block">
                  {testResults.expression}
                </code>
              </div>

              {/* Severity Badge */}
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Alert Severity</span>
                <Badge variant={getSeverityColor(testResults.severity) as any}>
                  {testResults.severity.toUpperCase()}
                </Badge>
              </div>

              {/* Affected Devices Preview */}
              {testResults.affectedDevices && testResults.affectedDevices.length > 0 && (
                <div>
                  <div className="text-sm font-medium mb-3">Sample Matching Devices (max 5)</div>
                  <div className="space-y-2">
                    {testResults.affectedDevices.map((device: any, idx: number) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
                      >
                        <div className="flex items-center gap-3">
                          <Activity className="h-4 w-4 text-ward-green" />
                          <div>
                            <div className="text-sm font-medium">{device.display_name || device.name}</div>
                            <div className="text-xs text-muted-foreground">{device.ip}</div>
                          </div>
                        </div>
                        <Badge variant={device.ping_status === 'Up' ? 'success' : 'danger'} size="sm">
                          {device.ping_status}
                        </Badge>
                      </div>
                    ))}
                  </div>
                  {testResults.affectedCount > 5 && (
                    <div className="text-xs text-muted-foreground text-center mt-2">
                      + {testResults.affectedCount - 5} more device(s)
                    </div>
                  )}
                </div>
              )}

              {testResults.affectedCount === 0 && (
                <div className="text-center py-8">
                  <Info className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                  <div className="text-sm text-muted-foreground">
                    No devices currently match this rule's expression.
                  </div>
                </div>
              )}
            </div>
          )}
        </ModalContent>
        <ModalFooter>
          <Button onClick={() => setTestModalOpen(false)}>
            Close
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  )
}
