import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/Loading'
import { Modal } from '@/components/ui/Modal'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table'
import { Users as UsersIcon, Plus, Edit2, Trash2, Shield, Search, AlertCircle, X } from 'lucide-react'
import { authAPI } from '@/services/api'
import axios from 'axios'

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

export default function Users() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
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
    region: '',
  })

  useEffect(() => {
    loadUsers()
  }, [])

  const loadUsers = async () => {
    try {
      setLoading(true)
      const response = await authAPI.listUsers()
      setUsers(response.data as User[])
    } catch (error) {
      console.error('Failed to load users:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAddUser = async () => {
    try {
      setErrorMessage('')
      await authAPI.register(userForm)
      setShowAddModal(false)
      resetForm()
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
      // Only include password in update if it's been changed (non-empty)
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
      resetForm()
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

  const resetForm = () => {
    setUserForm({
      username: '',
      email: '',
      full_name: '',
      password: '',
      role: 'technician',
      region: '',
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">User Management</h1>
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
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">System Users</h2>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
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
          resetForm()
        }}
        title="Add New User"
      >
        <div className="space-y-4">
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
            required
          />
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Role
            </label>
            <select
              value={userForm.role}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setUserForm({ ...userForm, role: e.target.value as any })}
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              <option value="technician">Technician</option>
              <option value="regional_manager">Regional Manager</option>
              <option value="admin">Administrator</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>
          {userForm.role === 'regional_manager' && (
            <Input
              label="Region"
              value={userForm.region}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUserForm({ ...userForm, region: e.target.value })}
              placeholder="Enter region (e.g., Kakheti)"
              helperText="Regional managers only see devices in their region"
            />
          )}
          <div className="flex gap-3 pt-4">
            <Button onClick={handleAddUser} className="flex-1">
              Add User
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                setShowAddModal(false)
                resetForm()
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
          resetForm()
          setSelectedUser(null)
        }}
        title="Edit User"
      >
        <div className="space-y-4">
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
          />
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Role
            </label>
            <select
              value={userForm.role}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setUserForm({ ...userForm, role: e.target.value as any })}
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              <option value="technician">Technician</option>
              <option value="regional_manager">Regional Manager</option>
              <option value="admin">Administrator</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>
          {userForm.role === 'regional_manager' && (
            <Input
              label="Region"
              value={userForm.region}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUserForm({ ...userForm, region: e.target.value })}
              placeholder="Enter region (e.g., Kakheti)"
              helperText="Regional managers only see devices in their region"
            />
          )}
          <div className="flex gap-3 pt-4">
            <Button onClick={handleEditUser} className="flex-1">
              Save Changes
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                setShowEditModal(false)
                resetForm()
                setSelectedUser(null)
              }}
              className="flex-1"
            >
              Cancel
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
