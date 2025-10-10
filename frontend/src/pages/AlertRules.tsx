import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tantml:invoke>
<parameter name="Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { LoadingSpinner } from '@/components/ui/Loading'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Badge from '@/components/ui/Badge'
import { Modal, ModalHeader, ModalTitle, ModalContent, ModalFooter } from '@/components/ui/Modal'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table'
import { alertRulesAPI } from '@/services/api'
import { Bell, Plus, Edit, Trash2, Power, AlertTriangle } from 'lucide-react'
import { toast } from 'sonner'

interface AlertRule {
  id: string
  name: string
  description?: string
  expression: string
  severity: string
  enabled: boolean
  device_id?: string
  created_at: string
  updated_at: string
}

export default function AlertRules() {
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null)

  const [ruleForm, setRuleForm] = useState({
    name: '',
    description: '',
    expression: 'ping_unreachable >= 3',
    severity: 'warning',
    enabled: true,
  })

  const { data: rulesData, isLoading } = useQuery({
    queryKey: ['alert-rules'],
    queryFn: () => alertRulesAPI.getRules(),
  })

  const createMutation = useMutation({
    mutationFn: alertRulesAPI.createRule,
    onSuccess: () => {
      toast.success('Alert rule created')
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
      toast.success('Alert rule updated')
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
      toast.success('Alert rule toggled')
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
    })
  }

  const openCreateModal = () => {
    resetForm()
    setEditingRule(null)
    setModalOpen(true)
  }

  const openEditModal = (rule: AlertRule) => {
    setRuleForm({
      name: rule.name,
      description: rule.description || '',
      expression: rule.expression,
      severity: rule.severity,
      enabled: rule.enabled,
    })
    setEditingRule(rule)
    setModalOpen(true)
  }

  const handleSubmit = () => {
    if (editingRule) {
      updateMutation.mutate({ id: editingRule.id, ...ruleForm })
    } else {
      createMutation.mutate(ruleForm)
    }
  }

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this alert rule?')) {
      deleteMutation.mutate(id)
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

  const rules = rulesData?.rules || []

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Bell className="h-8 w-8 text-primary" />
            Alert Rules Management
          </h1>
          <p className="text-muted-foreground mt-1">
            Configure alert rules for device monitoring
          </p>
        </div>
        <Button onClick={openCreateModal}>
          <Plus className="h-4 w-4 mr-2" />
          Create Alert Rule
        </Button>
      </div>

      {/* Alert Rules Table */}
      <Card>
        <CardHeader>
          <CardTitle>Alert Rules ({rules.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner />
            </div>
          ) : rules.length === 0 ? (
            <div className="text-center py-12">
              <AlertTriangle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No Alert Rules</h3>
              <p className="text-muted-foreground mb-4">
                Create your first alert rule to monitor devices
              </p>
              <Button onClick={openCreateModal}>
                <Plus className="h-4 w-4 mr-2" />
                Create Alert Rule
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Expression</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rules.map((rule: AlertRule) => (
                  <TableRow key={rule.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{rule.name}</div>
                        {rule.description && (
                          <div className="text-sm text-muted-foreground">
                            {rule.description}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <code className="text-sm bg-muted px-2 py-1 rounded">
                        {rule.expression}
                      </code>
                    </TableCell>
                    <TableCell>
                      <Badge variant={getSeverityColor(rule.severity) as any}>
                        {rule.severity}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={rule.enabled ? 'success' : 'secondary'}>
                        {rule.enabled ? 'Enabled' : 'Disabled'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleMutation.mutate(rule.id)}
                          title={rule.enabled ? 'Disable' : 'Enable'}
                        >
                          <Power className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openEditModal(rule)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(rule.id)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Modal */}
      <Modal open={modalOpen} onOpenChange={setModalOpen}>
        <ModalHeader>
          <ModalTitle>
            {editingRule ? 'Edit Alert Rule' : 'Create Alert Rule'}
          </ModalTitle>
        </ModalHeader>
        <ModalContent>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Name *</label>
              <Input
                value={ruleForm.name}
                onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })}
                placeholder="High Ping Alert"
              />
            </div>

            <div>
              <label className="text-sm font-medium">Description</label>
              <Input
                value={ruleForm.description}
                onChange={(e) => setRuleForm({ ...ruleForm, description: e.target.value })}
                placeholder="Alert when device ping exceeds threshold"
              />
            </div>

            <div>
              <label className="text-sm font-medium">Expression *</label>
              <Input
                value={ruleForm.expression}
                onChange={(e) => setRuleForm({ ...ruleForm, expression: e.target.value })}
                placeholder="ping_unreachable >= 3"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Examples: ping_unreachable &gt;= 3, avg_ping_ms &gt; 200, packet_loss &gt; 10
              </p>
            </div>

            <div>
              <label className="text-sm font-medium">Severity *</label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={ruleForm.severity}
                onChange={(e) => setRuleForm({ ...ruleForm, severity: e.target.value })}
              >
                <option value="info">Info</option>
                <option value="low">Low</option>
                <option value="warning">Warning</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="enabled"
                checked={ruleForm.enabled}
                onChange={(e) => setRuleForm({ ...ruleForm, enabled: e.target.checked })}
                className="h-4 w-4 rounded border-gray-300"
              />
              <label htmlFor="enabled" className="text-sm font-medium">
                Enable rule immediately
              </label>
            </div>
          </div>
        </ModalContent>
        <ModalFooter>
          <Button variant="ghost" onClick={() => setModalOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!ruleForm.name || !ruleForm.expression}
          >
            {editingRule ? 'Update' : 'Create'} Rule
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  )
}
