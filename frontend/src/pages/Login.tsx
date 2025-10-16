import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Card, CardContent } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { authAPI } from '@/services/api'
import { Lock, User } from 'lucide-react'
import { toast } from 'sonner'

export default function Login() {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  })

  const loginMutation = useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      authAPI.login(username, password),
    onSuccess: (response) => {
      localStorage.setItem('token', response.data.access_token)
      toast.success('Login successful')
      navigate('/')
    },
    onError: () => {
      toast.error('Invalid username or password')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    loginMutation.mutate({ username: formData.username, password: formData.password })
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-ward-green to-ward-green-dark flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-10"></div>

      <Card className="w-full max-w-md relative z-10 shadow-2xl">
        <CardContent className="p-8">
          {/* Logo and Title */}
          <div className="text-center mb-8">
            <div className="flex justify-center mb-4">
              <div className="p-4 bg-ward-green/10 rounded-full">
                <img src="/logo-ward.svg" alt="WARD FLUX" className="h-16 w-16" />
              </div>
            </div>
            <h1 className="text-3xl font-bold text-gray-900">WARD FLUX</h1>
            <p className="text-gray-500 mt-2">Network Monitoring Platform</p>
          </div>

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            <Input
              label="Username"
              type="text"
              placeholder="Enter your username"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              icon={<User className="h-5 w-5" />}
              required
            />

            <Input
              label="Password"
              type="password"
              placeholder="Enter your password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              icon={<Lock className="h-5 w-5" />}
              required
            />

            <Button
              type="submit"
              className="w-full"
              size="lg"
              loading={loginMutation.isPending}
            >
              Sign In
            </Button>
          </form>

          {/* Demo Credentials */}
          <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <p className="text-sm font-medium text-blue-900 mb-2">Demo Credentials:</p>
            <div className="text-xs text-blue-700 space-y-1">
              <p>Username: <span className="font-mono bg-blue-100 px-2 py-0.5 rounded">admin</span></p>
              <p>Password: <span className="font-mono bg-blue-100 px-2 py-0.5 rounded">admin</span></p>
            </div>
          </div>

          {/* Footer */}
          <div className="mt-8 text-center">
            <p className="text-xs text-gray-500">
              © 2025 WARD Tech Solutions. All rights reserved.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Decorative Elements */}
      <div className="absolute top-10 left-10 w-20 h-20 bg-white/20 rounded-full blur-xl"></div>
      <div className="absolute bottom-10 right-10 w-32 h-32 bg-white/20 rounded-full blur-2xl"></div>
      <div className="absolute top-1/2 left-1/4 w-16 h-16 bg-white/10 rounded-full blur-lg"></div>
    </div>
  )
}
