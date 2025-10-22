/**
 * API Client for WARD FLUX
 * Standalone monitoring system API
 */

import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

// Create axios instance with auth
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Types
export interface Trigger {
  triggerid: string
  description: string
  priority: string
  lastchange: string  // Unix timestamp when problem started
}

export interface Device {
  hostid: string
  hostname: string
  display_name: string
  name?: string
  branch: string  // City name
  region: string  // Region name
  ip: string
  device_type: string
  status: string  // "Enabled" or "Disabled"
  enabled?: boolean
  available: string  // "Available" or "Unavailable"
  ping_status: string  // "Up" or "Down"
  ping_response_time: number | null
  last_check: number
  down_since?: string  // ISO timestamp when device first went down
  groups: string[]
  problems: number
  triggers?: Trigger[]
  latitude: number
  longitude: number
  vendor?: string
  model?: string
  created_at?: string
  description?: string
  location?: string
  ssh_port?: number
  ssh_username?: string
  ssh_enabled?: boolean
  snmp_community?: string  // SNMP community string for monitoring
  snmp_version?: string    // SNMP version (1, 2c, or 3)
}

export interface User {
  id: number
  username: string
  email: string
  full_name: string
  role: string
  is_active: boolean
  region?: string
  branches?: string
}

export interface Stats {
  total_devices: number
  online_devices: number
  offline_devices: number
  warning_devices: number
  monitored_devices?: number
  uptime_percentage: number
  active_alerts: number
  critical_alerts: number
}

export interface DiscoveryRule {
  id: string
  name: string
  description: string
  network_ranges: string
  excluded_ips?: string
  enabled: boolean
  created_at: string
}

export interface DiscoveryResult {
  id: string
  ip: string
  hostname: string
  device_type: string
  discovered_at: string
}

// Auth
export const authAPI = {
  login: (username: string, password: string) => {
    // Use URLSearchParams for proper application/x-www-form-urlencoded format
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
  },
  logout: () => {
    localStorage.removeItem('token')
  },
  me: () => api.get<User>('/auth/me'),
  getCurrentUser: () => api.get<User>('/auth/me'),
  listUsers: () => api.get<User[]>('/users'),
  register: (user: any) => api.post<User>('/auth/register', user),
  updateUser: (id: number, user: any) => api.put<User>(`/users/${id}`, user),
  deleteUser: (id: number) => api.delete(`/users/${id}`),
}

// Devices - USE OLD WORKING ZABBIX API
export const devicesAPI = {
  // Main devices endpoint - returns ALL devices
  getAll: () => api.get<Device[]>('/devices'),

  // Get devices by region filter
  getByRegion: (region: string) => api.get<Device[]>(`/devices?region=${region}`),

  // Get devices by branch filter
  getByBranch: (branch: string) => api.get<Device[]>(`/devices?branch=${branch}`),

  // Get devices by type filter
  getByType: (type: string) => api.get<Device[]>(`/devices?device_type=${type}`),

  // Get single device details
  getById: (hostid: string) => api.get<Device>(`/devices/${hostid}`),

  // Update device (region/branch assignment)
  updateDevice: (hostid: string, data: {
    name?: string;
    ip?: string;
    hostname?: string;
    vendor?: string;
    device_type?: string;
    model?: string;
    location?: string;
    description?: string;
    region?: string;
    branch?: string;
    ssh_port?: number;
    ssh_username?: string;
    ssh_enabled?: boolean;
  }) =>
    api.put(`/devices/${hostid}`, data),

  // Get device ping history
  getHistory: (hostid: string, timeRange: '24h' | '7d' | '30d' = '24h') =>
    api.get(`/devices/${hostid}/history?time_range=${timeRange}`),

  // Ping device
  pingDevice: (hostid: string) =>
    api.post(`/devices/${hostid}/ping`),

  // Dashboard stats
  getStats: () => api.get<Stats>('/dashboard/stats'),

  // Get alerts from standalone monitoring
  getAlerts: (severity?: string, deviceId?: string) => {
    let params = '?'
    if (severity) params += `severity=${severity}&`
    if (deviceId) params += `device_id=${deviceId}&`
    params += 'status=active'
    return api.get(`/alerts${params}`)
  },

  // Get alert history for a specific device
  getDeviceAlerts: (deviceId: string, limit = 50) => {
    return api.get(`/alerts?device_id=${deviceId}&limit=${limit}`)
  },

  // Get real-time alerts based on actual ping status (shows ALL down devices)
  getRealtimeAlerts: () => {
    return api.get(`/alerts/realtime`)
  },

  // Standalone devices
  standalone: {
    list: () => api.get('/devices/standalone/list'),
    create: (device: any) => api.post('/devices/standalone', device),
    update: (id: string, device: any) => api.put(`/devices/standalone/${id}`, device),
    delete: (id: string) => api.delete(`/devices/standalone/${id}`),
  },

  // Create Standalone device
  createStandalone: (device: any) => api.post('/devices/standalone', device),
}

// Discovery
export const discoveryAPI = {
  getRules: () => api.get<DiscoveryRule[]>('/discovery/rules'),
  createRule: (rule: Partial<DiscoveryRule>) => api.post<DiscoveryRule>('/discovery/rules', rule),
  deleteRule: (id: string) => api.delete(`/discovery/rules/${id}`),
  getResults: () => api.get<DiscoveryResult[]>('/discovery/results'),
  scanNow: (ruleId: string) => api.post(`/discovery/rules/${ruleId}/scan`),
  quickScan: (params: { network_ranges: string[]; excluded_ips: string[]; use_ping: boolean; use_snmp: boolean }) =>
    api.post('/discovery/scan', params),
  importDevices: (deviceIds: string[]) => api.post('/discovery/import', { device_ids: deviceIds }),
}

// Alert Rules
export const alertRulesAPI = {
  getRules: () => api.get('/alert-rules'),
  createRule: (rule: {
    name: string
    description?: string
    expression: string
    severity: string
    enabled?: boolean
    device_id?: string
  }) => api.post('/alert-rules', rule),
  updateRule: (id: string, rule: Partial<{
    name: string
    description: string
    expression: string
    severity: string
    enabled: boolean
  }>) => api.put(`/alert-rules/${id}`, rule),
  deleteRule: (id: string) => api.delete(`/alert-rules/${id}`),
  toggleRule: (id: string) => api.post(`/alert-rules/${id}/toggle`),
}

// Branches
export const branchesAPI = {
  getAll: (params?: { region?: string; is_active?: boolean; search?: string }) => {
    const query = new URLSearchParams(params as any).toString()
    return api.get(`/branches${query ? `?${query}` : ''}`)
  },
  getById: (id: string) => api.get(`/branches/${id}`),
  getDevices: (id: string) => api.get(`/branches/${id}/devices`),
  getStats: () => api.get('/branches/stats'),
  create: (data: {
    name: string
    display_name: string
    region?: string
    branch_code?: string
    address?: string
    is_active?: boolean
  }) => api.post('/branches', data),
  update: (id: string, data: Partial<{
    name: string
    display_name: string
    region: string
    branch_code: string
    address: string
    is_active: boolean
  }>) => api.put(`/branches/${id}`, data),
  delete: (id: string, force?: boolean) => api.delete(`/branches/${id}${force ? '?force=true' : ''}`),
}

// Reports
export const reportsAPI = {
  getDowntime: (params?: { period?: string; region?: string }) => {
    const query = new URLSearchParams(params as any).toString()
    return api.get(`/reports/downtime${query ? `?${query}` : ''}`)
  },
  getMTTR: (params?: { period?: string; region?: string }) => {
    const query = new URLSearchParams(params as any).toString()
    return api.get(`/reports/mttr${query ? `?${query}` : ''}`)
  },
}


// Config
export const configAPI = {
  getMonitoredGroups: () => api.get('/config/monitored-hostgroups'),
  getCities: () => api.get('/config/georgian-cities'),
  saveMonitoredGroups: (groupIds: string[]) => api.post('/config/monitored-hostgroups', { groupids: groupIds }),
}


// Diagnostics
export const diagnosticsAPI = {
  ping: (ip: string, count = 5) =>
    api.post('/diagnostics/ping', null, { params: { ip, count } }),
  traceroute: (ip: string, maxHops = 30) =>
    api.post('/diagnostics/traceroute', null, { params: { ip, max_hops: maxHops } }),
  mtr: (ip: string, count = 10) =>
    api.post('/diagnostics/mtr', null, { params: { ip, count } }),
  dnsLookup: (hostname: string) =>
    api.post('/diagnostics/dns/lookup', null, { params: { hostname } }),
  portScan: (ip: string, ports: string) =>
    api.post('/diagnostics/portscan', null, { params: { ip, ports } }),
  summary: () => api.get('/diagnostics/dashboard/summary'),
  tracerouteMap: (ip: string) => api.get('/diagnostics/traceroute/map', { params: { ip } }),
}

// SSH Terminal
export const sshAPI = {
  connect: (params: { host: string; username: string; password: string; port?: number }) =>
    api.post('/ssh/connect', params),
}

// Settings
export const settingsAPI = {
  getFeatureToggles: () => api.get('/settings/features'),
  saveFeatureToggles: (features: Record<string, boolean>) => api.post('/settings/features', features),
}

export default api
