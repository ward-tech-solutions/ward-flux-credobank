import { beforeEach, describe, expect, it, vi, type Mock } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api')
  return {
    ...actual,
    authAPI: {
      ...actual.authAPI,
      login: vi.fn(),
    },
  }
})

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

import { authAPI } from '@/services/api'
import { toast } from 'sonner'
import Login from '../Login'

function renderLogin() {
  const queryClient = new QueryClient()
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <QueryClientProvider client={queryClient}>
        <Login />
      </QueryClientProvider>
    </MemoryRouter>
  )
}

describe('Login page', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('authenticates the user and stores the token on success', async () => {
    const user = userEvent.setup()
    const mockedLogin = authAPI.login as unknown as Mock
    mockedLogin.mockResolvedValue({
      data: { access_token: 'token-123' },
    })

    renderLogin()

    await user.type(screen.getByPlaceholderText(/username/i), 'admin')
    await user.type(screen.getByPlaceholderText(/password/i), 'Ward@2025!')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(authAPI.login).toHaveBeenCalledWith('admin', 'Ward@2025!')
    })

    expect(localStorage.getItem('token')).toBe('token-123')
    expect(toast.success).toHaveBeenCalledWith('Login successful')
  })

  it('shows an error toast when authentication fails', async () => {
    const user = userEvent.setup()
    const mockedLogin = authAPI.login as unknown as Mock
    mockedLogin.mockRejectedValue(new Error('Invalid credentials'))

    renderLogin()

    await user.type(screen.getByPlaceholderText(/username/i), 'admin')
    await user.type(screen.getByPlaceholderText(/password/i), 'wrong')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Invalid username or password')
    })

    expect(localStorage.getItem('token')).toBeNull()
  })
})
