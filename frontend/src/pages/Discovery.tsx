import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { LoadingSpinner, Skeleton } from '@/components/ui/Loading'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Badge from '@/components/ui/Badge'
import { Modal, ModalHeader, ModalTitle, ModalContent, ModalFooter } from '@/components/ui/Modal'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table'
import { discoveryAPI } from '@/services/api'
import { Scan, Play, Wifi, Clock, Download, Settings } from 'lucide-react'
import { toast } from 'sonner'

export default function Discovery() {
  const queryClient = useQueryClient()
  const [scanModalOpen, setScanModalOpen] = useState(false)
  const [ruleModalOpen, setRuleModalOpen] = useState(false)
  const [selectedResults, setSelectedResults] = useState<string[]>([])

  const [scanForm, setScanForm] = useState({
    network_range: '192.168.1.0/24',
    excluded_ips: '',
    use_ping: true,
    use_snmp: true,
  })

  const [ruleForm, setRuleForm] = useState({
    name: '',
    description: '',
    network_ranges: '',
    excluded_ips: '',
    use_ping: true,
    use_snmp: true,
    schedule_enabled: false,
    schedule_cron: '0 */6 * * *',
    auto_import: false,
  })

  const { data: rules, isLoading: rulesLoading } = useQuery({
    queryKey: ['discovery-rules'],
    queryFn: () => discoveryAPI.getRules(),
  })

  const { data: results, isLoading: resultsLoading } = useQuery({
    queryKey: ['discovery-results'],
    queryFn: () => discoveryAPI.getResults(),
  })

  const scanMutation = useMutation({
    mutationFn: discoveryAPI.quickScan,
    onSuccess: () => {
      toast.success('Network scan started')
      setScanModalOpen(false)
      queryClient.invalidateQueries({ queryKey: ['discovery-results'] })
    },
    onError: () => {
      toast.error('Failed to start scan')
    },
  })

  const createRuleMutation = useMutation({
    mutationFn: discoveryAPI.createRule,
    onSuccess: () => {
      toast.success('Discovery rule created')
      setRuleModalOpen(false)
      queryClient.invalidateQueries({ queryKey: ['discovery-rules'] })
    },
    onError: () => {
      toast.error('Failed to create rule')
    },
  })

  const importMutation = useMutation({
    mutationFn: discoveryAPI.importDevices,
    onSuccess: () => {
      toast.success('Devices imported successfully')
      setSelectedResults([])
      queryClient.invalidateQueries({ queryKey: ['devices'] })
    },
    onError: () => {
      toast.error('Failed to import devices')
    },
  })

  const handleQuickScan = () => {
    const networkRanges = scanForm.network_range.split(',').map(r => r.trim())
    const excludedIps = scanForm.excluded_ips ? scanForm.excluded_ips.split(',').map(ip => ip.trim()) : []

    scanMutation.mutate({
      network_ranges: networkRanges,
      excluded_ips: excludedIps,
      use_ping: scanForm.use_ping,
      use_snmp: scanForm.use_snmp,
    })
  }

  const handleCreateRule = () => {
    const networkRanges = ruleForm.network_ranges.split(',').map(r => r.trim())
    const excludedIps = ruleForm.excluded_ips ? ruleForm.excluded_ips.split(',').map(ip => ip.trim()) : []

    createRuleMutation.mutate({
      ...ruleForm,
      network_ranges: networkRanges,
      excluded_ips: excludedIps,
    })
  }

  const handleImportSelected = () => {
    if (selectedResults.length === 0) {
      toast.error('Please select devices to import')
      return
    }
    importMutation.mutate(selectedResults)
  }

  const toggleSelectResult = (id: string) => {
    setSelectedResults(prev =>
      prev.includes(id) ? prev.filter(r => r !== id) : [...prev, id]
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Network Discovery</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Scan and discover devices on your network</p>
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            icon={<Settings className="h-5 w-5" />}
            onClick={() => setRuleModalOpen(true)}
          >
            Create Rule
          </Button>
          <Button
            icon={<Play className="h-5 w-5" />}
            onClick={() => setScanModalOpen(true)}
          >
            Quick Scan
          </Button>
        </div>
      </div>

      {/* Discovery Rules */}
      <Card>
        <CardHeader>
          <CardTitle>Discovery Rules</CardTitle>
        </CardHeader>
        <CardContent>
          {rulesLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => <Skeleton key={i} variant="rect" />)}
            </div>
          ) : rules?.data?.length === 0 ? (
            <div className="text-center py-12">
              <Scan className="h-16 w-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No discovery rules</h3>
              <p className="text-gray-500 dark:text-gray-400 mt-1 mb-4">Create a rule to automate network scanning</p>
              <Button onClick={() => setRuleModalOpen(true)}>Create First Rule</Button>
            </div>
          ) : (
            <div className="space-y-3">
              {rules?.data?.map((rule: any) => (
                <div key={rule.id} className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-ward-green transition-colors">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100">{rule.name}</h3>
                      <Badge variant={rule.enabled ? 'success' : 'default'} dot>
                        {rule.enabled ? 'Active' : 'Disabled'}
                      </Badge>
                      {rule.schedule_enabled && (
                        <Badge variant="info">
                          <Clock className="h-3 w-3" />
                          Scheduled
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{rule.description || 'No description'}</p>
                    <div className="flex gap-4 mt-2">
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        Networks: {rule.network_ranges?.join(', ')}
                      </span>
                      {rule.schedule_cron && (
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          Schedule: {rule.schedule_cron}
                        </span>
                      )}
                    </div>
                  </div>
                  <Button variant="ghost" size="sm">
                    Run Now
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Discovery Results */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Discovery Results</CardTitle>
            {selectedResults.length > 0 && (
              <Button
                size="sm"
                icon={<Download className="h-4 w-4" />}
                onClick={handleImportSelected}
                loading={importMutation.isPending}
              >
                Import Selected ({selectedResults.length})
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {resultsLoading ? (
            <LoadingSpinner size="lg" text="Loading results..." />
          ) : results?.data?.length === 0 ? (
            <div className="text-center py-12">
              <Wifi className="h-16 w-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No results yet</h3>
              <p className="text-gray-500 dark:text-gray-400 mt-1 mb-4">Start a scan to discover devices</p>
              <Button onClick={() => setScanModalOpen(true)}>Start Quick Scan</Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>
                    <input
                      type="checkbox"
                      className="rounded border-gray-300 text-ward-green focus:ring-ward-green"
                      checked={selectedResults.length === results?.data?.length}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedResults(results?.data?.map((r: any) => r.id) || [])
                        } else {
                          setSelectedResults([])
                        }
                      }}
                    />
                  </TableHead>
                  <TableHead>IP Address</TableHead>
                  <TableHead>Hostname</TableHead>
                  <TableHead>Vendor</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Discovered</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {results?.data?.map((result: any) => (
                  <TableRow key={result.id}>
                    <TableCell>
                      <input
                        type="checkbox"
                        className="rounded border-gray-300 text-ward-green focus:ring-ward-green"
                        checked={selectedResults.includes(result.id)}
                        onChange={() => toggleSelectResult(result.id)}
                      />
                    </TableCell>
                    <TableCell className="font-mono text-gray-900 dark:text-gray-100">{result.ip}</TableCell>
                    <TableCell className="text-gray-900 dark:text-gray-100">{result.hostname || '-'}</TableCell>
                    <TableCell className="text-gray-900 dark:text-gray-100">{result.vendor || '-'}</TableCell>
                    <TableCell className="text-gray-900 dark:text-gray-100">{result.device_type || '-'}</TableCell>
                    <TableCell>
                      <Badge variant={result.responsive ? 'success' : 'danger'} dot>
                        {result.responsive ? 'Responsive' : 'Unresponsive'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-gray-500 dark:text-gray-400">
                      {new Date(result.discovered_at).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => importMutation.mutate([result.id])}
                      >
                        Import
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Quick Scan Modal */}
      <Modal open={scanModalOpen} onClose={() => setScanModalOpen(false)} size="lg">
        <ModalHeader onClose={() => setScanModalOpen(false)}>
          <ModalTitle>Quick Network Scan</ModalTitle>
        </ModalHeader>
        <ModalContent>
          <div className="space-y-4">
            <Input
              label="Network Range (CIDR)"
              placeholder="192.168.1.0/24, 10.0.0.0/24"
              value={scanForm.network_range}
              onChange={(e) => setScanForm({ ...scanForm, network_range: e.target.value })}
              helperText="Comma-separated list of CIDR ranges"
            />
            <Input
              label="Excluded IPs (Optional)"
              placeholder="192.168.1.1, 192.168.1.254"
              value={scanForm.excluded_ips}
              onChange={(e) => setScanForm({ ...scanForm, excluded_ips: e.target.value })}
              helperText="IPs to skip during scan"
            />
            <div className="flex gap-6">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={scanForm.use_ping}
                  onChange={(e) => setScanForm({ ...scanForm, use_ping: e.target.checked })}
                  className="rounded border-gray-300 text-ward-green focus:ring-ward-green"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Use ICMP Ping</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={scanForm.use_snmp}
                  onChange={(e) => setScanForm({ ...scanForm, use_snmp: e.target.checked })}
                  className="rounded border-gray-300 text-ward-green focus:ring-ward-green"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Use SNMP Discovery</span>
              </label>
            </div>
          </div>
        </ModalContent>
        <ModalFooter>
          <Button variant="ghost" onClick={() => setScanModalOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleQuickScan} loading={scanMutation.isPending}>
            Start Scan
          </Button>
        </ModalFooter>
      </Modal>

      {/* Create Rule Modal */}
      <Modal open={ruleModalOpen} onClose={() => setRuleModalOpen(false)} size="lg">
        <ModalHeader onClose={() => setRuleModalOpen(false)}>
          <ModalTitle>Create Discovery Rule</ModalTitle>
        </ModalHeader>
        <ModalContent>
          <div className="space-y-4">
            <Input
              label="Rule Name"
              placeholder="Office Network Scan"
              value={ruleForm.name}
              onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })}
            />
            <Input
              label="Description (Optional)"
              placeholder="Scans office network every 6 hours"
              value={ruleForm.description}
              onChange={(e) => setRuleForm({ ...ruleForm, description: e.target.value })}
            />
            <Input
              label="Network Ranges (CIDR)"
              placeholder="192.168.1.0/24, 10.0.0.0/24"
              value={ruleForm.network_ranges}
              onChange={(e) => setRuleForm({ ...ruleForm, network_ranges: e.target.value })}
              helperText="Comma-separated list"
            />
            <Input
              label="Excluded IPs (Optional)"
              placeholder="192.168.1.1, 192.168.1.254"
              value={ruleForm.excluded_ips}
              onChange={(e) => setRuleForm({ ...ruleForm, excluded_ips: e.target.value })}
            />
            <div className="space-y-3">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={ruleForm.schedule_enabled}
                  onChange={(e) => setRuleForm({ ...ruleForm, schedule_enabled: e.target.checked })}
                  className="rounded border-gray-300 text-ward-green focus:ring-ward-green"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Enable Scheduled Scanning</span>
              </label>
              {ruleForm.schedule_enabled && (
                <Input
                  label="Cron Schedule"
                  placeholder="0 */6 * * *"
                  value={ruleForm.schedule_cron}
                  onChange={(e) => setRuleForm({ ...ruleForm, schedule_cron: e.target.value })}
                  helperText="Cron expression (e.g., 0 */6 * * * = every 6 hours)"
                />
              )}
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={ruleForm.auto_import}
                  onChange={(e) => setRuleForm({ ...ruleForm, auto_import: e.target.checked })}
                  className="rounded border-gray-300 text-ward-green focus:ring-ward-green"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Auto-import discovered devices</span>
              </label>
            </div>
          </div>
        </ModalContent>
        <ModalFooter>
          <Button variant="ghost" onClick={() => setRuleModalOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleCreateRule} loading={createRuleMutation.isPending}>
            Create Rule
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  )
}
