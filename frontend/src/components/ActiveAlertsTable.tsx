import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown, ChevronRight, MapPin, Clock, AlertCircle } from 'lucide-react'

interface Alert {
  id: string
  device_id: string
  device_name: string
  device_ip: string
  device_type?: string
  device_location: string
  branch_id?: string
  branch_name: string
  branch_code?: string
  branch_region: string
  rule_name: string
  severity: string
  message: string
  value?: string
  threshold?: string
  triggered_at: string
  resolved_at?: string
  duration_seconds?: number
  acknowledged: boolean
  acknowledged_by?: string
  acknowledged_at?: string
}

interface BranchGroup {
  branch_id: string
  branch_name: string
  branch_code?: string
  branch_region: string
  alerts: Alert[]
  critical_count: number
  warning_count: number
  info_count: number
}

interface ActiveAlertsTableProps {
  alerts: Alert[]
  isLoading?: boolean
}

export default function ActiveAlertsTable({ alerts, isLoading }: ActiveAlertsTableProps) {
  const [expandedBranches, setExpandedBranches] = useState<Set<string>>(new Set())

  // Group alerts by branch
  const branchGroups = useMemo(() => {
    const groups = new Map<string, BranchGroup>()

    alerts.forEach((alert) => {
      const branchKey = alert.branch_id || 'unknown'

      if (!groups.has(branchKey)) {
        groups.set(branchKey, {
          branch_id: branchKey,
          branch_name: alert.branch_name,
          branch_code: alert.branch_code,
          branch_region: alert.branch_region,
          alerts: [],
          critical_count: 0,
          warning_count: 0,
          info_count: 0,
        })
      }

      const group = groups.get(branchKey)!
      group.alerts.push(alert)

      // Count by severity
      const severity = alert.severity.toUpperCase()
      if (severity === 'CRITICAL') {
        group.critical_count++
      } else if (severity === 'WARNING' || severity === 'MEDIUM' || severity === 'HIGH') {
        group.warning_count++
      } else {
        group.info_count++
      }
    })

    // Sort by total alert count (descending)
    return Array.from(groups.values()).sort((a, b) => b.alerts.length - a.alerts.length)
  }, [alerts])

  const toggleBranch = (branchId: string) => {
    setExpandedBranches((prev) => {
      const next = new Set(prev)
      if (next.has(branchId)) {
        next.delete(branchId)
      } else {
        next.add(branchId)
      }
      return next
    })
  }

  const expandAll = () => {
    setExpandedBranches(new Set(branchGroups.map((g) => g.branch_id)))
  }

  const collapseAll = () => {
    setExpandedBranches(new Set())
  }

  const getSeverityColor = (severity: string) => {
    const sev = severity.toUpperCase()
    if (sev === 'CRITICAL') return 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'
    if (sev === 'WARNING' || sev === 'HIGH' || sev === 'MEDIUM')
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400'
    return 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400'
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A'

    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)

    if (hours > 0) {
      return `${hours}h ${minutes}m`
    }
    return `${minutes}m`
  }

  const formatTimestamp = (timestamp?: string) => {
    if (!timestamp) return 'N/A'

    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`

    return date.toLocaleDateString()
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ward-green"></div>
      </div>
    )
  }

  if (alerts.length === 0) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No active alerts</h3>
        <p className="text-gray-500 dark:text-gray-400 mt-1">All systems are operating normally</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Expand/Collapse Controls */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-600 dark:text-gray-400">
          {branchGroups.length} {branchGroups.length === 1 ? 'branch' : 'branches'} with alerts
        </div>
        <div className="flex gap-2">
          <button
            onClick={expandAll}
            className="text-xs px-3 py-1 rounded-md bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
          >
            Expand All
          </button>
          <button
            onClick={collapseAll}
            className="text-xs px-3 py-1 rounded-md bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
          >
            Collapse All
          </button>
        </div>
      </div>

      {/* Branch Groups */}
      <div className="space-y-2">
        {branchGroups.map((group) => {
          const isExpanded = expandedBranches.has(group.branch_id)

          return (
            <div
              key={group.branch_id}
              className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
            >
              {/* Branch Header - Clickable */}
              <button
                onClick={() => toggleBranch(group.branch_id)}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  {isExpanded ? (
                    <ChevronDown className="h-5 w-5 text-gray-500" />
                  ) : (
                    <ChevronRight className="h-5 w-5 text-gray-500" />
                  )}

                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-gray-400" />
                    <span className="font-medium text-gray-900 dark:text-gray-100">
                      {group.branch_name}
                    </span>
                    {group.branch_code && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        ({group.branch_code})
                      </span>
                    )}
                  </div>

                  {/* Alert Count Badges */}
                  <div className="flex items-center gap-2 ml-4">
                    {group.critical_count > 0 && (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400">
                        {group.critical_count} Critical
                      </span>
                    )}
                    {group.warning_count > 0 && (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400">
                        {group.warning_count} Warning
                      </span>
                    )}
                    {group.info_count > 0 && (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400">
                        {group.info_count} Info
                      </span>
                    )}
                  </div>
                </div>

                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {group.alerts.length} {group.alerts.length === 1 ? 'alert' : 'alerts'}
                </div>
              </button>

              {/* Branch Alerts Table */}
              {isExpanded && (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-100 dark:bg-gray-800 border-y border-gray-200 dark:border-gray-700">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                          Severity
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                          Device
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                          Alert
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                          Duration
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                          Triggered
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-950">
                      {group.alerts.map((alert) => {
                        // Calculate duration for active alerts
                        let duration = alert.duration_seconds
                        if (!alert.resolved_at && alert.triggered_at) {
                          const now = new Date()
                          const triggered = new Date(alert.triggered_at)
                          duration = Math.floor((now.getTime() - triggered.getTime()) / 1000)
                        }

                        return (
                          <tr
                            key={alert.id}
                            className="hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
                          >
                            <td className="px-4 py-3 whitespace-nowrap">
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(alert.severity)}`}>
                                {alert.severity}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <Link
                                to={`/devices/${alert.device_id}`}
                                className="text-ward-green hover:text-ward-green-dark hover:underline font-medium transition-colors"
                              >
                                <div className="font-medium">{alert.device_name}</div>
                                <div className="text-xs text-gray-500 dark:text-gray-400">
                                  {alert.device_ip} {alert.device_type && `• ${alert.device_type}`}
                                </div>
                              </Link>
                            </td>
                            <td className="px-4 py-3">
                              <div className="font-medium text-gray-900 dark:text-gray-100">
                                {alert.rule_name}
                              </div>
                              <div className="text-sm text-gray-600 dark:text-gray-400">
                                {alert.message}
                              </div>
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap">
                              <div className="flex items-center gap-1 text-sm text-gray-700 dark:text-gray-300">
                                <Clock className="h-3.5 w-3.5 text-gray-400" />
                                {formatDuration(duration)}
                              </div>
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">
                              {formatTimestamp(alert.triggered_at)}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
