import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Select from '@/components/ui/Select'
import MultiSelect from '@/components/ui/MultiSelect'
import { Badge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/Loading'
import { Modal, ModalHeader, ModalTitle, ModalContent, ModalFooter } from '@/components/ui/Modal'
import Switch from '@/components/ui/Switch'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table'
import { Server, Bell, Mail, Shield, Users as UsersIcon, Plus, Edit2, Trash2, Search, Eye, EyeOff, Wrench, Save, MapPin, ToggleLeft, Scan, Map as MapIcon, Network, Stethoscope, BarChart3, AlertCircle, X } from 'lucide-react'
import api, { authAPI } from '@/services/api'
import { useFeatures } from '@/contexts/FeatureContext'
import axios from 'axios'

interface User {
  id: string | number
  username: string
  email: string
  full_name: string
  role: 'admin' | 'regional_manager' | 'technician' | 'viewer'
  regions?: string[]
  region?: string | null  // Keep for backward compatibility
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

// Georgian regions list
const GEORGIAN_REGIONS = [
  'Tbilisi',
  'Kvemo Kartli',
  'Kakheti',
  'Mtskheta-Mtianeti',
  'Samtskhe-Javakheti',
  'Shida Kartli',
  'Imereti',
  'Samegrelo',
  'Guria',
  'Achara',
  'Racha-Lechkhumi',
  'Kvemo Svaneti'
]

export default function Settings() {
  const { features, toggleFeature, resetFeatures } = useFeatures()
  const [activeSection, setActiveSection] = useState('notifications')
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
  const [showEmailPassword, setShowEmailPassword] = useState(false)

  // Config state
  const [savingConfig, setSavingConfig] = useState(false)
  const [allGroups] = useState<HostGroup[]>([])
  const [selectedGroups, setSelectedGroups] = useState<Set<string>>(new Set())
  const [cities, setCities] = useState<City[]>([])

  // Users management state
  const [users, setUsers] = useState<User[]>([])
  const [loadingUsers, setLoadingUsers] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [errorMessage, setErrorMessage] = useState('')
  const [userForm, setUserForm] = useState({
    username: '',
    email: '',
    full_name: '',
    password: '',
    role: 'technician' as 'admin' | 'regional_manager' | 'technician' | 'viewer',
    regions: [] as string[],
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
      // Parse regions from JSON string to array
      const usersWithParsedRegions = response.data.map((user: any) => ({
        ...user,
        regions: user.regions ? (typeof user.regions === 'string' ? JSON.parse(user.regions) : user.regions) : []
      }))
      setUsers(usersWithParsedRegions as User[])
    } catch (error) {
      console.error('Failed to load users:', error)
    } finally {
      setLoadingUsers(false)
    }
  }

  const handleAddUser = async () => {
    try {
      setErrorMessage('')
      const userData = {
        ...userForm,
        regions: userForm.regions.length > 0 ? JSON.stringify(userForm.regions) : null
      }
      await authAPI.register(userData)
      setShowAddModal(false)
      resetUserForm()
      loadUsers()
    } catch (error) {
      console.error('Failed to add user:', error)
      if (axios.isAxiosError(error) && error.response?.data?.detail) {
        setErrorMessage(error.response.data.detail)
      } else {
        setErrorMessage('Failed to create user. Please try again.')
      }
    }
  }

  const handleEditUser = async () => {
    if (!selectedUser) return
    try {
      setErrorMessage('')
      const updateData = userForm.password
        ? {
            ...userForm,
            regions: userForm.regions.length > 0 ? JSON.stringify(userForm.regions) : null
          }
        : {
            username: userForm.username,
            email: userForm.email,
            full_name: userForm.full_name,
            role: userForm.role,
            regions: userForm.regions.length > 0 ? JSON.stringify(userForm.regions) : null,
          }
      await authAPI.updateUser(Number(selectedUser.id), updateData)
      setShowEditModal(false)
      resetUserForm()
      setSelectedUser(null)
      loadUsers()
    } catch (error) {
      console.error('Failed to update user:', error)
      if (axios.isAxiosError(error) && error.response?.data?.detail) {
        setErrorMessage(error.response.data.detail)
      } else {
        setErrorMessage('Failed to update user. Please try again.')
      }
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
      regions: [],
    })
    setErrorMessage('')
  }

  const openEditModal = (user: User) => {
    setSelectedUser(user)
    setUserForm({
      username: user.username,
      email: user.email,
      full_name: user.full_name,
      password: '',
      role: user.role,
      regions: user.regions || (user.region ? [user.region] : []),
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
            <button
              onClick={() => setActiveSection('features')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeSection === 'features'
                  ? 'bg-ward-green text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              <ToggleLeft className="h-4 w-4 inline-block mr-2" />
              Features
            </button>
          </div>
        </CardContent>
      </Card>


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
                              {user.regions && user.regions.length > 0 ? (
                                <div className="flex flex-wrap gap-1">
                                  {user.regions.map((region) => (
                                    <Badge key={region} variant="default" size="sm">{region}</Badge>
                                  ))}
                                </div>
                              ) : user.region ? (
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
            size="lg"
          >
            <ModalHeader onClose={() => { setShowAddModal(false); resetUserForm(); }} className="bg-gradient-to-r from-ward-green/10 to-emerald-50 dark:from-ward-green/20 dark:to-emerald-900/20">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-xl bg-gradient-to-br from-ward-green to-emerald-600 shadow-lg">
                  <UsersIcon className="h-6 w-6 text-white" />
                </div>
                <div>
                  <ModalTitle className="text-2xl">Add New User</ModalTitle>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Create a new system user with assigned role and permissions</p>
                </div>
              </div>
            </ModalHeader>
            <ModalContent className="bg-gray-50/50 dark:bg-gray-900/20">
              <div className="space-y-6">
                {/* Error Alert */}
                {errorMessage && (
                  <div className="flex items-start gap-3 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                    <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-red-800 dark:text-red-200">
                        {errorMessage}
                      </p>
                    </div>
                    <button
                      onClick={() => setErrorMessage('')}
                      className="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200"
                    >
                      <X className="h-5 w-5" />
                    </button>
                  </div>
                )}
                {/* Basic Information Section */}
                <div className="bg-white dark:bg-gray-900 rounded-lg p-5 border border-gray-200 dark:border-gray-700 space-y-4">
                  <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wide flex items-center gap-2">
                    <div className="w-1 h-4 bg-ward-green rounded-full"></div>
                    Basic Information
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                  </div>
                  <Input
                    label="Email Address"
                    type="email"
                    value={userForm.email}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUserForm({ ...userForm, email: e.target.value })}
                    placeholder="user@example.com"
                    required
                  />
                </div>

                {/* Security Section */}
                <div className="bg-white dark:bg-gray-900 rounded-lg p-5 border border-gray-200 dark:border-gray-700 space-y-4">
                  <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wide flex items-center gap-2">
                    <div className="w-1 h-4 bg-blue-500 rounded-full"></div>
                    Security
                  </h3>
                  <Input
                    label="Password"
                    type="password"
                    value={userForm.password}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUserForm({ ...userForm, password: e.target.value })}
                    placeholder="Enter a strong password"
                    autoComplete="new-password"
                    helperText="Minimum 8 characters recommended"
                    required
                  />
                </div>

                {/* Permissions Section */}
                <div className="bg-white dark:bg-gray-900 rounded-lg p-5 border border-gray-200 dark:border-gray-700 space-y-4">
                  <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wide flex items-center gap-2">
                    <div className="w-1 h-4 bg-orange-500 rounded-full"></div>
                    Permissions & Access
                  </h3>
                  <Select
                    label="User Role"
                    value={userForm.role}
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setUserForm({ ...userForm, role: e.target.value as any })}
                    options={[
                      { value: 'technician', label: 'Technician - Standard access to monitoring and diagnostics' },
                      { value: 'regional_manager', label: 'Regional Manager - Regional oversight and reporting' },
                      { value: 'admin', label: 'Administrator - Full system access' },
                      { value: 'viewer', label: 'Viewer - Read-only access' },
                    ]}
                  />
                  {userForm.role === 'regional_manager' && (
                    <MultiSelect
                      label="Assigned Regions"
                      options={GEORGIAN_REGIONS}
                      selected={userForm.regions}
                      onChange={(selected) => setUserForm({ ...userForm, regions: selected })}
                      placeholder="Select regions"
                      helperText="Regional managers will only see devices in their assigned regions"
                    />
                  )}
                </div>
              </div>
            </ModalContent>
            <ModalFooter className="bg-gray-50/50 dark:bg-gray-900/20">
              <Button
                variant="outline"
                onClick={() => {
                  setShowAddModal(false)
                  resetUserForm()
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleAddUser}
                className="bg-gradient-to-r from-ward-green to-emerald-600 hover:from-emerald-600 hover:to-ward-green"
                disabled={!userForm.username || !userForm.email || !userForm.password || !userForm.full_name}
              >
                <Plus className="h-4 w-4 mr-2" />
                Create User
              </Button>
            </ModalFooter>
          </Modal>

          {/* Edit User Modal */}
          <Modal
            open={showEditModal}
            onClose={() => {
              setShowEditModal(false)
              resetUserForm()
              setSelectedUser(null)
            }}
            size="lg"
          >
            <ModalHeader onClose={() => { setShowEditModal(false); resetUserForm(); setSelectedUser(null); }} className="bg-gradient-to-r from-blue-500/10 to-blue-50 dark:from-blue-500/20 dark:to-blue-900/20">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 shadow-lg">
                  <Edit2 className="h-6 w-6 text-white" />
                </div>
                <div>
                  <ModalTitle className="text-2xl">Edit User</ModalTitle>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Update user information and permissions</p>
                </div>
              </div>
            </ModalHeader>
            <ModalContent className="bg-gray-50/50 dark:bg-gray-900/20">
              <div className="space-y-6">
                {/* Error Alert */}
                {errorMessage && (
                  <div className="flex items-start gap-3 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                    <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-red-800 dark:text-red-200">
                        {errorMessage}
                      </p>
                    </div>
                    <button
                      onClick={() => setErrorMessage('')}
                      className="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200"
                    >
                      <X className="h-5 w-5" />
                    </button>
                  </div>
                )}
                {/* Basic Information Section */}
                <div className="bg-white dark:bg-gray-900 rounded-lg p-5 border border-gray-200 dark:border-gray-700 space-y-4">
                  <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wide flex items-center gap-2">
                    <div className="w-1 h-4 bg-ward-green rounded-full"></div>
                    Basic Information
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Input
                      label="Username"
                      value={userForm.username}
                      disabled
                      className="bg-gray-50 dark:bg-gray-900"
                      helperText="Username cannot be changed"
                    />
                    <Input
                      label="Full Name"
                      value={userForm.full_name}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUserForm({ ...userForm, full_name: e.target.value })}
                      placeholder="Enter full name"
                    />
                  </div>
                  <Input
                    label="Email Address"
                    type="email"
                    value={userForm.email}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUserForm({ ...userForm, email: e.target.value })}
                    placeholder="user@example.com"
                  />
                </div>

                {/* Security Section */}
                <div className="bg-white dark:bg-gray-900 rounded-lg p-5 border border-gray-200 dark:border-gray-700 space-y-4">
                  <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wide flex items-center gap-2">
                    <div className="w-1 h-4 bg-blue-500 rounded-full"></div>
                    Security
                  </h3>
                  <Input
                    label="New Password"
                    type="password"
                    value={userForm.password}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUserForm({ ...userForm, password: e.target.value })}
                    placeholder="Leave empty to keep current password"
                    autoComplete="new-password"
                    helperText="Only fill this if you want to change the password"
                  />
                </div>

                {/* Permissions Section */}
                <div className="bg-white dark:bg-gray-900 rounded-lg p-5 border border-gray-200 dark:border-gray-700 space-y-4">
                  <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wide flex items-center gap-2">
                    <div className="w-1 h-4 bg-orange-500 rounded-full"></div>
                    Permissions & Access
                  </h3>
                  <Select
                    label="User Role"
                    value={userForm.role}
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setUserForm({ ...userForm, role: e.target.value as any })}
                    options={[
                      { value: 'technician', label: 'Technician - Standard access to monitoring and diagnostics' },
                      { value: 'regional_manager', label: 'Regional Manager - Regional oversight and reporting' },
                      { value: 'admin', label: 'Administrator - Full system access' },
                      { value: 'viewer', label: 'Viewer - Read-only access' },
                    ]}
                  />
                  {userForm.role === 'regional_manager' && (
                    <MultiSelect
                      label="Assigned Regions"
                      options={GEORGIAN_REGIONS}
                      selected={userForm.regions}
                      onChange={(selected) => setUserForm({ ...userForm, regions: selected })}
                      placeholder="Select regions"
                      helperText="Regional managers will only see devices in their assigned regions"
                    />
                  )}
                </div>
              </div>
            </ModalContent>
            <ModalFooter className="bg-gray-50/50 dark:bg-gray-900/20">
              <Button
                variant="outline"
                onClick={() => {
                  setShowEditModal(false)
                  resetUserForm()
                  setSelectedUser(null)
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleEditUser}
                className="bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-500"
                disabled={!userForm.full_name || !userForm.email}
              >
                <Save className="h-4 w-4 mr-2" />
                Save Changes
              </Button>
            </ModalFooter>
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
              </div>
            </CardHeader>
            <CardContent>
              {allGroups.length === 0 ? (
                <div className="text-center py-12">
                  <Server className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500 dark:text-gray-400">
                    No host groups available
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

      {/* Feature Toggles */}
      {activeSection === 'features' && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-ward-green/10 rounded-lg">
                <ToggleLeft className="h-6 w-6 text-ward-green" />
              </div>
              <div>
                <CardTitle>Feature Toggles</CardTitle>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  System-wide feature toggles (affects all users) - Admin only
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Feature Toggle Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Discovery Feature */}
              <Card variant="glass" className={features.discovery ? 'border-ward-green/50 bg-ward-green/5' : 'border-gray-200 dark:border-gray-700'}>
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-lg ${features.discovery ? 'bg-ward-green/20' : 'bg-gray-100 dark:bg-gray-800'}`}>
                        <Scan className={`h-5 w-5 ${features.discovery ? 'text-ward-green' : 'text-gray-400'}`} />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900 dark:text-gray-100">Discovery</h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                          Network discovery and device scanning tools
                        </p>
                      </div>
                    </div>
                    <Switch
                      checked={features.discovery}
                      onClick={() => toggleFeature('discovery')}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Topology Feature */}
              <Card variant="glass" className={features.topology ? 'border-ward-green/50 bg-ward-green/5' : 'border-gray-200 dark:border-gray-700'}>
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-lg ${features.topology ? 'bg-ward-green/20' : 'bg-gray-100 dark:bg-gray-800'}`}>
                        <Network className={`h-5 w-5 ${features.topology ? 'text-ward-green' : 'text-gray-400'}`} />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900 dark:text-gray-100">Topology</h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                          Network topology visualization and mapping
                        </p>
                      </div>
                    </div>
                    <Switch
                      checked={features.topology}
                      onClick={() => toggleFeature('topology')}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Diagnostics Feature */}
              <Card variant="glass" className={features.diagnostics ? 'border-ward-green/50 bg-ward-green/5' : 'border-gray-200 dark:border-gray-700'}>
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-lg ${features.diagnostics ? 'bg-ward-green/20' : 'bg-gray-100 dark:bg-gray-800'}`}>
                        <Stethoscope className={`h-5 w-5 ${features.diagnostics ? 'text-ward-green' : 'text-gray-400'}`} />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900 dark:text-gray-100">Diagnostics</h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                          Advanced network diagnostics and troubleshooting
                        </p>
                      </div>
                    </div>
                    <Switch
                      checked={features.diagnostics}
                      onClick={() => toggleFeature('diagnostics')}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Reports Feature */}
              <Card variant="glass" className={features.reports ? 'border-ward-green/50 bg-ward-green/5' : 'border-gray-200 dark:border-gray-700'}>
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-lg ${features.reports ? 'bg-ward-green/20' : 'bg-gray-100 dark:bg-gray-800'}`}>
                        <BarChart3 className={`h-5 w-5 ${features.reports ? 'text-ward-green' : 'text-gray-400'}`} />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900 dark:text-gray-100">Reports</h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                          Generate and view detailed reports and analytics
                        </p>
                      </div>
                    </div>
                    <Switch
                      checked={features.reports}
                      onClick={() => toggleFeature('reports')}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Map Feature */}
              <Card variant="glass" className={features.map ? 'border-ward-green/50 bg-ward-green/5' : 'border-gray-200 dark:border-gray-700'}>
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-lg ${features.map ? 'bg-ward-green/20' : 'bg-gray-100 dark:bg-gray-800'}`}>
                        <MapIcon className={`h-5 w-5 ${features.map ? 'text-ward-green' : 'text-gray-400'}`} />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900 dark:text-gray-100">Map</h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                          Geographic map view of devices and branches
                        </p>
                      </div>
                    </div>
                    <Switch
                      checked={features.map}
                      onClick={() => toggleFeature('map')}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Regions Feature */}
              <Card variant="glass" className={features.regions ? 'border-ward-green/50 bg-ward-green/5' : 'border-gray-200 dark:border-gray-700'}>
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-lg ${features.regions ? 'bg-ward-green/20' : 'bg-gray-100 dark:bg-gray-800'}`}>
                        <MapPin className={`h-5 w-5 ${features.regions ? 'text-ward-green' : 'text-gray-400'}`} />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900 dark:text-gray-100">Regions</h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                          Manage regions and geographic organization
                        </p>
                      </div>
                    </div>
                    <Switch
                      checked={features.regions}
                      onClick={() => toggleFeature('regions')}
                    />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Reset Button */}
            <div className="flex items-center justify-between pt-6 border-t border-gray-200 dark:border-gray-700">
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">Reset to Defaults</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Enable all features and restore default settings
                </p>
              </div>
              <Button onClick={resetFeatures} variant="outline">
                Reset Features
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

    </div>
  )
}
