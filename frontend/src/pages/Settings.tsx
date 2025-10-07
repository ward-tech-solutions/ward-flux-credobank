import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Select from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/Loading'
import { Modal } from '@/components/ui/Modal'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table'
import { Server, Bell, Mail, Shield, Database, Users as UsersIcon, Plus, Edit2, Trash2, Search, Eye, EyeOff, Wrench, RefreshCw, Save, MapPin } from 'lucide-react'
import api, { authAPI } from '@/services/api'

interface User {
  id: string | number
  username: string
  email: string
  full_name: string
  role: 'admin' | 'regional_manager' | 'technician' | 'viewer'
  region?: string | null
  is_active: boolean
  created_at?: string
}

interface HostGroup {
  groupid: string
  name: string
  display_name?: string
  is_active?: boolean
}

interface City {
  id: number
  name_en: string
  latitude: number
  longitude: number
  region_name: string
}

export default function Settings() {
  const [saving, setSaving] = useState(false)
  const [activeSection, setActiveSection] = useState('zabbix')
  const [zabbixSettings, setZabbixSettings] = useState({
    url: '',
    username: '',
    password: '',
  })
  const [emailSettings, setEmailSettings] = useState({
    smtp_server: '',
    smtp_port: '587',
    smtp_user: '',
    smtp_password: '',
    from_email: '',
  })
  const [notificationSettings, setNotificationSettings] = useState({
    email_enabled: true,
    slack_enabled: false,
    slack_webhook: '',
  })

  // Password visibility toggles
  const [showZabbixPassword, setShowZabbixPassword] = useState(false)
  const [showEmailPassword, setShowEmailPassword] = useState(false)

  // Config state
  const [loadingGroups, setLoadingGroups] = useState(false)
  const [savingConfig, setSavingConfig] = useState(false)
  const [allGroups, setAllGroups] = useState<HostGroup[]>([])
  const [selectedGroups, setSelectedGroups] = useState<Set<string>>(new Set())
  const [cities, setCities] = useState<City[]>([])

  // Users management state
  const [users, setUsers] = useState<User[]>([])
  const [loadingUsers, setLoadingUsers] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [userForm, setUserForm] = useState({
    username: '',
    email: '',
    full_name: '',
    password: '',
    role: 'technician' as 'admin' | 'regional_manager' | 'technician' | 'viewer',
    region: '',
  })


  useEffect(() => {
    if (activeSection === 'users') {
      loadUsers()
    } else if (activeSection === 'config') {
      loadMonitoredGroups()
      loadCities()
    }
  }, [activeSection])

  const loadUsers = async () => {
    try {
      setLoadingUsers(true)
      const response = await authAPI.listUsers()
      setUsers(response.data as User[])
    } catch (error) {
      console.error('Failed to load users:', error)
    } finally {
      setLoadingUsers(false)
    }
  }

  const handleAddUser = async () => {
    try {
      await authAPI.register(userForm)
      setShowAddModal(false)
      resetUserForm()
      loadUsers()
    } catch (error) {
      console.error('Failed to add user:', error)
    }
  }

  const handleEditUser = async () => {
    if (!selectedUser) return
    try {
      const updateData = userForm.password
        ? userForm
        : {
            username: userForm.username,
            email: userForm.email,
            full_name: userForm.full_name,
            role: userForm.role,
            region: userForm.region,
          }
      await authAPI.updateUser(Number(selectedUser.id), updateData)
      setShowEditModal(false)
      resetUserForm()
      setSelectedUser(null)
      loadUsers()
    } catch (error) {
      console.error('Failed to update user:', error)
    }
  }

  const handleDeleteUser = async (userId: string | number) => {
    if (!confirm('Are you sure you want to delete this user?')) return
    try {
      await authAPI.deleteUser(Number(userId))
      loadUsers()
    } catch (error) {
      console.error('Failed to delete user:', error)
    }
  }

  const resetUserForm = () => {
    setUserForm({
      username: '',
      email: '',
      full_name: '',
      password: '',
      role: 'technician',
      region: '',
    })
  }

  const openEditModal = (user: User) => {
    setSelectedUser(user)
    setUserForm({
      username: user.username,
      email: user.email,
      full_name: user.full_name,
      password: '',
      role: user.role,
      region: user.region || '',
    })
    setShowEditModal(true)
  }

  const filteredUsers = users.filter(user => {
    const username = (user.username || '').toLowerCase()
    const email = (user.email || '').toLowerCase()
    const fullName = (user.full_name || '').toLowerCase()
    const query = searchQuery.toLowerCase()
    return username.includes(query) || email.includes(query) || fullName.includes(query)
  })

  const getRoleBadgeVariant = (role: string) => {
    switch (role) {
      case 'admin':
        return 'danger'
      case 'regional_manager':
        return 'warning'
      case 'technician':
        return 'default'
      default:
        return 'default'
    }
  }

  const getRoleDisplayName = (role: string) => {
    switch (role) {
      case 'admin':
        return 'ADMIN'
      case 'regional_manager':
        return 'REGIONAL MANAGER'
      case 'technician':
        return 'TECHNICIAN'
      case 'viewer':
        return 'VIEWER'
      default:
        return role.toUpperCase()
    }
  }

  const handleSaveZabbix = async () => {
    setSaving(true)
    try {
      await api.post('/settings/zabbix', zabbixSettings)
      alert('Zabbix settings saved successfully!')
    } catch (error) {
      console.error('Failed to save Zabbix settings:', error)
      alert('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleTestZabbix = async () => {
    try {
      const response = await api.post('/settings/test-zabbix', zabbixSettings)
      if (response.data.success) {
        alert(`Connection successful! Zabbix version: ${response.data.version || 'Unknown'}`)
      } else {
        alert(`Connection failed: ${response.data.error || 'Unknown error'}`)
      }
    } catch (error: any) {
      alert(`Connection failed: ${error.message}`)
    }
  }

  // Config functions
  const loadMonitoredGroups = async () => {
    try {
      const response = await api.get('/config/monitored-hostgroups')
      const monitoredGroupIds = new Set<string>(response.data.monitored_groups.map((g: any) => g.groupid as string))
      setSelectedGroups(monitoredGroupIds)
    } catch (error) {
      console.error('Failed to load monitored groups:', error)
    }
  }

  const loadZabbixGroups = async () => {
    setLoadingGroups(true)
    try {
      const response = await api.get('/config/zabbix-hostgroups')
      setAllGroups(response.data.hostgroups || [])
    } catch (error) {
      console.error('Failed to load Zabbix host groups:', error)
      alert('Failed to fetch host groups from Zabbix. Please check your Zabbix configuration.')
    } finally {
      setLoadingGroups(false)
    }
  }

  const loadCities = async () => {
    try {
      const response = await api.get('/config/georgian-cities')
      setCities(response.data.cities || [])
    } catch (error) {
      console.error('Failed to load cities:', error)
    }
  }

  const toggleGroup = (groupId: string) => {
    const newSelected = new Set<string>(selectedGroups)
    if (newSelected.has(groupId)) {
      newSelected.delete(groupId)
    } else {
      newSelected.add(groupId)
    }
    setSelectedGroups(newSelected)
  }

  const handleSaveConfig = async () => {
    setSavingConfig(true)
    try {
      const groups = allGroups
        .filter(g => selectedGroups.has(g.groupid))
        .map(g => ({
          groupid: g.groupid,
          name: g.name,
          display_name: g.name
        }))

      await api.post('/config/monitored-hostgroups', { groups })
      alert('Configuration saved successfully!')
    } catch (error) {
      console.error('Failed to save configuration:', error)
      alert('Failed to save configuration')
    } finally {
      setSavingConfig(false)
    }
  }


  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Settings</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Configure system settings and integrations</p>
      </div>

      {/* Settings Navigation */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setActiveSection('zabbix')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeSection === 'zabbix'
                  ? 'bg-ward-green text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              <Server className="h-4 w-4 inline-block mr-2" />
              Zabbix
            </button>
            <button
              onClick={() => setActiveSection('notifications')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeSection === 'notifications'
                  ? 'bg-ward-green text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              <Bell className="h-4 w-4 inline-block mr-2" />
              Notifications
            </button>
            <button
              onClick={() => setActiveSection('email')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeSection === 'email'
                  ? 'bg-ward-green text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              <Mail className="h-4 w-4 inline-block mr-2" />
              Email
            </button>
            <button
              onClick={() => setActiveSection('security')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeSection === 'security'
                  ? 'bg-ward-green text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              <Shield className="h-4 w-4 inline-block mr-2" />
              Security
            </button>
            <button
              onClick={() => setActiveSection('users')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeSection === 'users'
                  ? 'bg-ward-green text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              <UsersIcon className="h-4 w-4 inline-block mr-2" />
              Users
            </button>
            <button
              onClick={() => setActiveSection('config')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeSection === 'config'
                  ? 'bg-ward-green text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              <Wrench className="h-4 w-4 inline-block mr-2" />
              Config
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Zabbix Configuration */}
      {activeSection === 'zabbix' && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-ward-green/10 rounded-lg">
                <Server className="h-6 w-6 text-ward-green" />
              </div>
              <div>
                <CardTitle>Zabbix Configuration</CardTitle>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  Configure connection to your Zabbix monitoring server
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <Input
              label="Zabbix API URL"
              placeholder="http://192.168.200.178:8080/api_jsonrpc.php"
              value={zabbixSettings.url}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setZabbixSettings({ ...zabbixSettings, url: e.target.value })}
              helperText="Full URL to Zabbix API endpoint"
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="Username"
                placeholder="admin"
                value={zabbixSettings.username}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setZabbixSettings({ ...zabbixSettings, username: e.target.value })}
              />

              <div className="w-full">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showZabbixPassword ? 'text' : 'password'}
                    placeholder="Enter password"
                    value={zabbixSettings.password}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setZabbixSettings({ ...zabbixSettings, password: e.target.value })}
                    autoComplete="new-password"
                    className="w-full px-4 py-2 pr-12 rounded-lg border transition-all duration-200 text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-ward-green focus:border-transparent border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowZabbixPassword(!showZabbixPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                  >
                    {showZabbixPassword ? (
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                </div>
              </div>
            </div>

            <div className="flex gap-3 pt-4">
              <Button variant="outline" onClick={handleTestZabbix}>
                <Database className="h-4 w-4 mr-2" />
                Test Connection
              </Button>
              <Button onClick={handleSaveZabbix} disabled={saving}>
                {saving ? 'Saving...' : 'Save Configuration'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Notifications */}
      {activeSection === 'notifications' && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-ward-green/10 rounded-lg">
                <Bell className="h-6 w-6 text-ward-green" />
              </div>
              <div>
                <CardTitle>Notification Settings</CardTitle>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  Configure alert notifications and channels
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-4">
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={notificationSettings.email_enabled}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNotificationSettings({ ...notificationSettings, email_enabled: e.target.checked })}
                  className="rounded border-gray-300 text-ward-green focus:ring-ward-green w-5 h-5"
                />
                <div>
                  <p className="font-medium text-gray-900 dark:text-gray-100">Email Notifications</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Receive alerts via email</p>
                </div>
              </label>

              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={notificationSettings.slack_enabled}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNotificationSettings({ ...notificationSettings, slack_enabled: e.target.checked })}
                  className="rounded border-gray-300 text-ward-green focus:ring-ward-green w-5 h-5"
                />
                <div>
                  <p className="font-medium text-gray-900 dark:text-gray-100">Slack Notifications</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Send alerts to Slack channel</p>
                </div>
              </label>
            </div>

            {notificationSettings.slack_enabled && (
              <Input
                label="Slack Webhook URL"
                placeholder="https://hooks.slack.com/services/..."
                value={notificationSettings.slack_webhook}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNotificationSettings({ ...notificationSettings, slack_webhook: e.target.value })}
              />
            )}

            <Button>Save Notification Settings</Button>
          </CardContent>
        </Card>
      )}

      {/* Email Configuration */}
      {activeSection === 'email' && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-ward-green/10 rounded-lg">
                <Mail className="h-6 w-6 text-ward-green" />
              </div>
              <div>
                <CardTitle>Email Configuration</CardTitle>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  Configure SMTP server for email notifications
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-2">
                <Input
                  label="SMTP Server"
                  placeholder="smtp.gmail.com"
                  value={emailSettings.smtp_server}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmailSettings({ ...emailSettings, smtp_server: e.target.value })}
                />
              </div>
              <Input
                label="Port"
                placeholder="587"
                value={emailSettings.smtp_port}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmailSettings({ ...emailSettings, smtp_port: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="SMTP Username"
                placeholder="your-email@example.com"
                value={emailSettings.smtp_user}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmailSettings({ ...emailSettings, smtp_user: e.target.value })}
              />

              <div className="w-full">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  SMTP Password
                </label>
                <div className="relative">
                  <input
                    type={showEmailPassword ? 'text' : 'password'}
                    placeholder="Enter password"
                    value={emailSettings.smtp_password}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmailSettings({ ...emailSettings, smtp_password: e.target.value })}
                    autoComplete="new-password"
                    className="w-full px-4 py-2 pr-12 rounded-lg border transition-all duration-200 text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-ward-green focus:border-transparent border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowEmailPassword(!showEmailPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                  >
                    {showEmailPassword ? (
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                </div>
              </div>
            </div>

            <Input
              label="From Email"
              placeholder="noreply@wardops.com"
              value={emailSettings.from_email}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmailSettings({ ...emailSettings, from_email: e.target.value })}
            />

            <Button>Save Email Settings</Button>
          </CardContent>
        </Card>
      )}

      {/* Security */}
      {activeSection === 'security' && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-ward-green/10 rounded-lg">
                <Shield className="h-6 w-6 text-ward-green" />
              </div>
              <div>
                <CardTitle>Security Settings</CardTitle>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  Manage authentication and access control
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-4">
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  defaultChecked
                  className="rounded border-gray-300 text-ward-green focus:ring-ward-green w-5 h-5"
                />
                <div>
                  <p className="font-medium text-gray-900 dark:text-gray-100">Enforce Password Complexity</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Require strong passwords for all users</p>
                </div>
              </label>

              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  defaultChecked
                  className="rounded border-gray-300 text-ward-green focus:ring-ward-green w-5 h-5"
                />
                <div>
                  <p className="font-medium text-gray-900 dark:text-gray-100">Enable Session Timeout</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Auto-logout after 30 minutes of inactivity</p>
                </div>
              </label>

              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-ward-green focus:ring-ward-green w-5 h-5"
                />
                <div>
                  <p className="font-medium text-gray-900 dark:text-gray-100">Enable Two-Factor Authentication</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Require 2FA for admin users</p>
                </div>
              </label>
            </div>

            <Button>Save Security Settings</Button>
          </CardContent>
        </Card>
      )}

      {/* Users Management */}
      {activeSection === 'users' && (
        <>
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">User Management</h2>
              <p className="text-gray-500 dark:text-gray-400 mt-1">Manage system users and permissions</p>
            </div>
            <Button onClick={() => setShowAddModal(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add User
            </Button>
          </div>

          {/* Search */}
          <Card>
            <CardContent className="py-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <Input
                  type="text"
                  placeholder="Search users..."
                  value={searchQuery}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </CardContent>
          </Card>

          {/* Users Table */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <UsersIcon className="h-5 w-5 text-ward-green" />
                <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">System Users</h3>
              </div>
            </CardHeader>
            <CardContent>
              {loadingUsers ? (
                <div className="text-center py-12">
                  <LoadingSpinner size="lg" text="Loading users..." />
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Username</TableHead>
                        <TableHead>Full Name</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead>Role</TableHead>
                        <TableHead>Region</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredUsers.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={7} className="text-center py-12">
                            <UsersIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                            <p className="text-gray-500 dark:text-gray-400">No users found</p>
                          </TableCell>
                        </TableRow>
                      ) : (
                        filteredUsers.map((user) => (
                          <TableRow key={user.id}>
                            <TableCell className="font-medium">
                              <div className="flex items-center gap-2">
                                {user.role === 'admin' && <Shield className="h-4 w-4 text-red-500" />}
                                {user.username}
                              </div>
                            </TableCell>
                            <TableCell>{user.full_name}</TableCell>
                            <TableCell>{user.email}</TableCell>
                            <TableCell>
                              <Badge variant={getRoleBadgeVariant(user.role)}>
                                {getRoleDisplayName(user.role)}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              {user.region ? (
                                <Badge variant="default">{user.region}</Badge>
                              ) : (
                                <span className="text-gray-400">All Regions</span>
                              )}
                            </TableCell>
                            <TableCell>
                              <Badge variant={user.is_active ? 'success' : 'default'}>
                                {user.is_active ? 'Active' : 'Inactive'}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center justify-end gap-2">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => openEditModal(user)}
                                >
                                  <Edit2 className="h-4 w-4" />
                                </Button>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleDeleteUser(user.id)}
                                >
                                  <Trash2 className="h-4 w-4 text-red-500" />
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Add User Modal */}
          <Modal
            open={showAddModal}
            onClose={() => {
              setShowAddModal(false)
              resetUserForm()
            }}
            title="Add New User"
          >
            <div className="space-y-4">
              <Input
                label="Username"
                value={userForm.username}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUserForm({ ...userForm, username: e.target.value })}
                placeholder="Enter username"
                required
              />
              <Input
                label="Full Name"
                value={userForm.full_name}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUserForm({ ...userForm, full_name: e.target.value })}
                placeholder="Enter full name"
                required
              />
              <Input
                label="Email"
                type="email"
                value={userForm.email}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUserForm({ ...userForm, email: e.target.value })}
                placeholder="Enter email"
                required
              />
              <Input
                label="Password"
                type="password"
                value={userForm.password}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUserForm({ ...userForm, password: e.target.value })}
                placeholder="Enter password"
                autoComplete="new-password"
                required
              />
              <Select
                label="Role"
                value={userForm.role}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setUserForm({ ...userForm, role: e.target.value as any })}
                options={[
                  { value: 'technician', label: 'Technician' },
                  { value: 'regional_manager', label: 'Regional Manager' },
                  { value: 'admin', label: 'Administrator' },
                  { value: 'viewer', label: 'Viewer' },
                ]}
              />
              {userForm.role === 'regional_manager' && (
                <Select
                  label="Region"
                  value={userForm.region}
                  onChange={(e) => setUserForm({ ...userForm, region: e.target.value })}
                  helperText="Regional managers only see devices in their region"
                >
                  <option value="">Select a region</option>
                  <option value="Tbilisi">Tbilisi</option>
                  <option value="Kvemo Kartli">Kvemo Kartli</option>
                  <option value="Kakheti">Kakheti</option>
                  <option value="Mtskheta-Mtianeti">Mtskheta-Mtianeti</option>
                  <option value="Samtskhe-Javakheti">Samtskhe-Javakheti</option>
                  <option value="Shida Kartli">Shida Kartli</option>
                  <option value="Imereti">Imereti</option>
                  <option value="Samegrelo">Samegrelo</option>
                  <option value="Guria">Guria</option>
                  <option value="Achara">Achara</option>
                  <option value="Racha-Lechkhumi">Racha-Lechkhumi</option>
                  <option value="Kvemo Svaneti">Kvemo Svaneti</option>
                </Select>
              )}
              <div className="flex gap-3 pt-4">
                <Button onClick={handleAddUser} className="flex-1">
                  Add User
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowAddModal(false)
                    resetUserForm()
                  }}
                  className="flex-1"
                >
                  Cancel
                </Button>
              </div>
            </div>
          </Modal>

          {/* Edit User Modal */}
          <Modal
            open={showEditModal}
            onClose={() => {
              setShowEditModal(false)
              resetUserForm()
              setSelectedUser(null)
            }}
            title="Edit User"
          >
            <div className="space-y-4">
              <Input
                label="Username"
                value={userForm.username}
                disabled
                className="bg-gray-50 dark:bg-gray-900"
              />
              <Input
                label="Full Name"
                value={userForm.full_name}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUserForm({ ...userForm, full_name: e.target.value })}
                placeholder="Enter full name"
              />
              <Input
                label="Email"
                type="email"
                value={userForm.email}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUserForm({ ...userForm, email: e.target.value })}
                placeholder="Enter email"
              />
              <Input
                label="New Password (leave empty to keep current)"
                type="password"
                value={userForm.password}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUserForm({ ...userForm, password: e.target.value })}
                placeholder="Enter new password"
                autoComplete="new-password"
              />
              <Select
                label="Role"
                value={userForm.role}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setUserForm({ ...userForm, role: e.target.value as any })}
                options={[
                  { value: 'technician', label: 'Technician' },
                  { value: 'regional_manager', label: 'Regional Manager' },
                  { value: 'admin', label: 'Administrator' },
                  { value: 'viewer', label: 'Viewer' },
                ]}
              />
              {userForm.role === 'regional_manager' && (
                <Select
                  label="Region"
                  value={userForm.region}
                  onChange={(e) => setUserForm({ ...userForm, region: e.target.value })}
                  helperText="Regional managers only see devices in their region"
                >
                  <option value="">Select a region</option>
                  <option value="Tbilisi">Tbilisi</option>
                  <option value="Kvemo Kartli">Kvemo Kartli</option>
                  <option value="Kakheti">Kakheti</option>
                  <option value="Mtskheta-Mtianeti">Mtskheta-Mtianeti</option>
                  <option value="Samtskhe-Javakheti">Samtskhe-Javakheti</option>
                  <option value="Shida Kartli">Shida Kartli</option>
                  <option value="Imereti">Imereti</option>
                  <option value="Samegrelo">Samegrelo</option>
                  <option value="Guria">Guria</option>
                  <option value="Achara">Achara</option>
                  <option value="Racha-Lechkhumi">Racha-Lechkhumi</option>
                  <option value="Kvemo Svaneti">Kvemo Svaneti</option>
                </Select>
              )}
              <div className="flex gap-3 pt-4">
                <Button onClick={handleEditUser} className="flex-1">
                  Save Changes
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowEditModal(false)
                    resetUserForm()
                    setSelectedUser(null)
                  }}
                  className="flex-1"
                >
                  Cancel
                </Button>
              </div>
            </div>
          </Modal>
        </>
      )}

      {/* Config Section */}
      {activeSection === 'config' && (
        <>
          {/* Host Groups Configuration */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-ward-green/10 rounded-lg">
                    <Server className="h-6 w-6 text-ward-green" />
                  </div>
                  <div>
                    <CardTitle>Select Host Groups to Monitor</CardTitle>
                    {selectedGroups.size > 0 && (
                      <Badge variant="default" className="mt-1">
                        {selectedGroups.size} selected
                      </Badge>
                    )}
                  </div>
                </div>
                <Button onClick={loadZabbixGroups} disabled={loadingGroups}>
                  <RefreshCw className={`h-4 w-4 mr-2 ${loadingGroups ? 'animate-spin' : ''}`} />
                  Fetch from Zabbix
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {allGroups.length === 0 ? (
                <div className="text-center py-12">
                  <Server className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500 dark:text-gray-400">
                    Click "Fetch from Zabbix" to load available host groups
                  </p>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-h-[500px] overflow-y-auto p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                    {allGroups.map((group) => (
                      <label
                        key={group.groupid}
                        className={`flex items-start gap-3 p-4 rounded-lg border-2 cursor-pointer transition-all ${
                          selectedGroups.has(group.groupid)
                            ? 'border-ward-green bg-ward-green/5'
                            : 'border-gray-200 dark:border-gray-700 hover:border-ward-green/50'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={selectedGroups.has(group.groupid)}
                          onChange={() => toggleGroup(group.groupid)}
                          className="mt-1 rounded border-gray-300 text-ward-green focus:ring-ward-green w-5 h-5"
                        />
                        <div className="flex-1">
                          <p className="font-medium text-gray-900 dark:text-gray-100">{group.name}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">ID: {group.groupid}</p>
                        </div>
                      </label>
                    ))}
                  </div>

                  <div className="flex justify-end mt-6">
                    <Button onClick={handleSaveConfig} disabled={savingConfig || selectedGroups.size === 0}>
                      <Save className="h-4 w-4 mr-2" />
                      {savingConfig ? 'Saving...' : 'Save Configuration'}
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* City-Region Mapping */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-ward-green/10 rounded-lg">
                  <MapPin className="h-6 w-6 text-ward-green" />
                </div>
                <div>
                  <CardTitle>City-Region Mapping</CardTitle>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    Configured cities with coordinates for map visualization
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {cities.length === 0 ? (
                <div className="text-center py-12">
                  <MapPin className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500 dark:text-gray-400">Loading cities...</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {cities.map((city) => (
                    <div
                      key={city.id}
                      className="p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-medium text-gray-900 dark:text-gray-100">{city.name_en}</p>
                          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            <Badge variant="default">{city.region_name}</Badge>
                          </p>
                        </div>
                        <MapPin className="h-5 w-5 text-ward-green" />
                      </div>
                      <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div>
                            <p className="text-gray-500 dark:text-gray-400">Latitude</p>
                            <p className="font-mono text-gray-900 dark:text-gray-100">{city.latitude.toFixed(4)}</p>
                          </div>
                          <div>
                            <p className="text-gray-500 dark:text-gray-400">Longitude</p>
                            <p className="font-mono text-gray-900 dark:text-gray-100">{city.longitude.toFixed(4)}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

    </div>
  )
}
