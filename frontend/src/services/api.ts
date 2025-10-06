/**
 * API Client for WARD FLUX
 * Uses the proven old backend logic for Zabbix integration
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
  branch: string  // City name
  region: string  // Region name
  ip: string
  device_type: string
  status: string  // "Enabled" or "Disabled"
  available: string  // "Available" or "Unavailable"
  ping_status: string  // "Up" or "Down"
  ping_response_time: number | null
  last_check: number
  groups: string[]
  problems: number
  triggers?: Trigger[]
  latitude: number
  longitude: number
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
  // Main devices endpoint - returns ALL Zabbix devices
  getAll: () => api.get<Device[]>('/devices'),

  // Get devices by region filter
  getByRegion: (region: string) => api.get<Device[]>(`/devices?region=${region}`),

  // Get devices by branch filter
  getByBranch: (branch: string) => api.get<Device[]>(`/devices?branch=${branch}`),

  // Get devices by type filter
  getByType: (type: string) => api.get<Device[]>(`/devices?device_type=${type}`),

  // Get single device details
  getById: (hostid: string) => api.get<Device>(`/devices/${hostid}`),

  // Dashboard stats
  getStats: () => api.get<Stats>('/dashboard/stats'),

  // Get alerts
  getAlerts: (severity?: string) => {
    const params = severity ? `?severity=${severity}` : ''
    return api.get(`/alerts${params}`)
  },

  // Standalone devices (separate from Zabbix)
  standalone: {
    list: () => api.get('/devices/standalone/list'),
    create: (device: any) => api.post('/devices/standalone', device),
    update: (id: string, device: any) => api.put(`/devices/standalone/${id}`, device),
    delete: (id: string) => api.delete(`/devices/standalone/${id}`),
  }
}

// Discovery
export const discoveryAPI = {
  getRules: () => api.get<DiscoveryRule[]>('/discovery/rules'),
  createRule: (rule: Partial<DiscoveryRule>) => api.post<DiscoveryRule>('/discovery/rules', rule),
  deleteRule: (id: string) => api.delete(`/discovery/rules/${id}`),
  getResults: () => api.get<DiscoveryResult[]>('/discovery/results'),
  scanNow: (ruleId: string) => api.post(`/discovery/rules/${ruleId}/scan`),
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

// Zabbix
export const zabbixAPI = {
  getGroups: () => api.get('/zabbix/groups'),
  getTemplates: () => api.get('/zabbix/templates'),
  createHost: (host: any) => api.post('/zabbix/hosts', host),
  updateHost: (hostid: string, host: any) => api.put(`/zabbix/hosts/${hostid}`, host),
  deleteHost: (hostid: string) => api.delete(`/zabbix/hosts/${hostid}`),
  getAlerts: (params?: any) => {
    const query = new URLSearchParams(params).toString()
    return api.get(`/zabbix/alerts${query ? `?${query}` : ''}`)
  },
}

// Config
export const configAPI = {
  getMonitoredGroups: () => api.get('/config/monitored-hostgroups'),
  getCities: () => api.get('/config/georgian-cities'),
  saveMonitoredGroups: (groupIds: string[]) => api.post('/config/monitored-hostgroups', { groupids: groupIds }),
}

// Settings
export const settingsAPI = {
  getZabbix: () => api.get('/settings/zabbix'),
  saveZabbix: (settings: any) => api.post('/settings/zabbix', settings),
  testZabbix: (settings: any) => api.post('/settings/test-zabbix', settings),
}

// Diagnostics
export const diagnosticsAPI = {
  ping: (host: string) => api.post('/diagnostics/ping', { host }),
  traceroute: (host: string) => api.post('/diagnostics/traceroute', { host }),
  dnsLookup: (host: string) => api.post('/diagnostics/dns-lookup', { host }),
  portScan: (host: string, ports: string) => api.post('/diagnostics/port-scan', { host, ports }),
}

// SSH Terminal
export const sshAPI = {
  connect: (params: { host: string; username: string; password: string; port?: number }) =>
    api.post('/ssh/connect', params),
}

export default api
