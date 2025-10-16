import axios from 'axios'

const API_BASE = '/api/v1'

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error
      console.error('API Error:', error.response.status, error.response.data)
    } else if (error.request) {
      // Request made but no response
      console.error('Network Error:', error.message)
    } else {
      // Something else happened
      console.error('Error:', error.message)
    }
    return Promise.reject(error)
  }
)

// API functions
export const api = {
  // Dashboard
  getDashboardStats: (region?: string) =>
    apiClient.get('/dashboard/stats', { params: { region } }),

  // Devices
  getDevices: (filters?: {
    region?: string
    branch?: string
    device_type?: string
  }) => apiClient.get('/devices', { params: filters }),

  getDeviceDetails: (hostid: string) => apiClient.get(`/devices/${hostid}`),

  searchDevices: (params: {
    q?: string
    region?: string
    branch?: string
    device_type?: string
    status?: string
  }) => apiClient.get('/search', { params }),

  // Alerts
  getAlerts: () => apiClient.get('/alerts'),

  // MTTR
  getMTTRStats: () => apiClient.get('/mttr/stats'),

  // Groups and Templates
  getGroups: () => apiClient.get('/groups'),
  getTemplates: () => apiClient.get('/templates'),

  // Host Management
  createHost: (data: {
    hostname: string
    visible_name: string
    ip_address: string
    group_ids: string[]
    template_ids: string[]
  }) => apiClient.post('/hosts', data),

  updateHost: (hostid: string, data: any) =>
    apiClient.put(`/hosts/${hostid}`, data),

  deleteHost: (hostid: string) => apiClient.delete(`/hosts/${hostid}`),

  // Reports
  getDowntimeReport: (params: {
    period?: string
    region?: string
    device_type?: string
  }) => apiClient.get('/reports/downtime', { params }),

  getMTTRExtended: () => apiClient.get('/reports/mttr-extended'),

  // Topology
  getTopology: (params: { view?: string; limit?: number; region?: string }) =>
    apiClient.get('/topology', { params }),

  // Health
  health: () => apiClient.get('/health'),
}
