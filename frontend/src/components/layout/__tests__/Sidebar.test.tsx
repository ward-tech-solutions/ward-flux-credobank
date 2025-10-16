import { describe, expect, it, vi, type Mock } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { render, screen } from '@testing-library/react'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

import { useAuth } from '@/contexts/AuthContext'
import Sidebar from '../Sidebar'

const authState = {
  isLoading: false,
  logout: vi.fn(),
  refreshUser: vi.fn(),
  userRegion: null,
}

function renderSidebar() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Sidebar />
    </MemoryRouter>
  )
}

describe('Sidebar navigation', () => {
  it('shows full navigation for admin users', () => {
    const mockedUseAuth = useAuth as unknown as Mock
    mockedUseAuth.mockReturnValue({
      ...authState,
      user: { role: 'admin' },
      isAdmin: true,
      isRegionalManager: false,
    })

    renderSidebar()

    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Discovery')).toBeInTheDocument()
    expect(screen.getByText('Monitor')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('hides restricted items for viewer users', () => {
    const mockedUseAuth = useAuth as unknown as Mock
    mockedUseAuth.mockReturnValue({
      ...authState,
      user: { role: 'viewer' },
      isAdmin: false,
      isRegionalManager: false,
    })

    renderSidebar()

    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Devices')).toBeInTheDocument()
    expect(screen.getByText('Map')).toBeInTheDocument()
    expect(screen.queryByText('Discovery')).not.toBeInTheDocument()
    expect(screen.queryByText('Settings')).not.toBeInTheDocument()
  })
})
