export interface User {
  id: string
  username: string
  email: string
  full_name: string
  role: 'admin' | 'manager' | 'technician' | 'viewer'
  is_active: boolean
  created_at: string
}

export interface Device {
  id: string
  name: string
  ip: string
  vendor?: string
  device_type?: string
  model?: string
  enabled: boolean
  status?: 'online' | 'offline' | 'warning'
  uptime?: number
  last_seen?: string
  created_at: string
}

export interface DiscoveryRule {
  id: string
  name: string
  description?: string
  enabled: boolean
  network_ranges: string[]
  excluded_ips?: string[]
  use_ping: boolean
  use_snmp: boolean
  schedule_enabled: boolean
  schedule_cron?: string
  auto_import: boolean
  created_at: string
}

export interface DiscoveryResult {
  id: string
  ip: string
  hostname?: string
  vendor?: string
  device_type?: string
  sys_descr?: string
  ping_responsive: boolean
  ping_latency_ms?: number
  snmp_responsive: boolean
  snmp_version?: string
  status: 'discovered' | 'imported' | 'ignored' | 'failed'
  discovered_at: string
}

export interface DiscoveryJob {
  id: string
  rule_id: string
  status: 'running' | 'completed' | 'failed' | 'cancelled'
  total_ips: number
  scanned_ips: number
  discovered_devices: number
  started_at: string
  completed_at?: string
  duration_seconds?: number
}

export interface Alert {
  id: string
  device_id: string
  device_name: string
  severity: 'critical' | 'warning' | 'info'
  message: string
  timestamp: string
  acknowledged: boolean
}

export interface Stats {
  total_devices: number
  online_devices: number
  offline_devices: number
  warning_devices: number
  monitored_devices: number
  uptime_percentage: number
  total_traffic: number
  active_alerts: number
}

export interface Template {
  id: string
  name: string
  vendor?: string
  device_types?: string[]
  is_default: boolean
  items: TemplateItem[]
  triggers: TemplateTrigger[]
}

export interface TemplateItem {
  name: string
  oid: string
  value_type: string
  units?: string
  description?: string
}

export interface TemplateTrigger {
  name: string
  expression: string
  severity: 'critical' | 'warning' | 'info'
  description?: string
}
