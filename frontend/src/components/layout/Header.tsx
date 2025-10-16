import { Search, Bell, Moon, Sun, LogOut, User } from 'lucide-react'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

export default function Header() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode')
    return saved === 'true'
  })

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    localStorage.setItem('darkMode', darkMode.toString())
  }, [darkMode])

  const toggleDarkMode = () => {
    setDarkMode(!darkMode)
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const getRoleDisplay = (role: string) => {
    switch (role) {
      case 'admin': return 'Admin'
      case 'regional_manager': return 'Regional Manager'
      case 'technician': return 'Technician'
      case 'viewer': return 'Viewer'
      default: return role
    }
  }

  return (
    <div className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8">
      {/* Search */}
      <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
        <form className="relative flex flex-1" action="#" method="GET">
          <label htmlFor="search-field" className="sr-only">
            Search
          </label>
          <Search
            className="pointer-events-none absolute inset-y-0 left-0 h-full w-5 text-gray-400 dark:text-gray-500"
            aria-hidden="true"
          />
          <input
            id="search-field"
            className="block h-full w-full border-0 py-0 pl-8 pr-0 text-gray-900 dark:text-gray-100 dark:bg-gray-800 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:ring-0 sm:text-sm"
            placeholder="Search devices, alerts..."
            type="search"
            name="search"
          />
        </form>
      </div>

      <div className="flex items-center gap-x-4 lg:gap-x-6">
        {/* Dark mode toggle */}
        <button
          type="button"
          onClick={toggleDarkMode}
          className="p-2 text-gray-400 hover:text-gray-500 dark:text-gray-400 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <span className="sr-only">Toggle dark mode</span>
          {darkMode ? (
            <Sun className="h-6 w-6" aria-hidden="true" />
          ) : (
            <Moon className="h-6 w-6" aria-hidden="true" />
          )}
        </button>

        {/* Notifications */}
        <button
          type="button"
          className="relative p-2 text-gray-400 hover:text-gray-500 dark:text-gray-400 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <span className="sr-only">View notifications</span>
          <Bell className="h-6 w-6" aria-hidden="true" />
          <span className="absolute top-1 right-1 block h-2 w-2 rounded-full bg-red-400 ring-2 ring-white dark:ring-gray-800" />
        </button>

        {/* Separator */}
        <div className="hidden lg:block lg:h-6 lg:w-px lg:bg-gray-200 dark:bg-gray-700" aria-hidden="true" />

        {/* Profile dropdown */}
        <div className="relative flex items-center gap-x-2">
          <button
            type="button"
            className="flex items-center gap-x-2 rounded-lg p-2 text-sm font-semibold leading-6 text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            <div className="h-8 w-8 rounded-full bg-ward-green flex items-center justify-center text-white">
              <User className="h-5 w-5" />
            </div>
            <div className="hidden lg:flex lg:flex-col lg:items-start">
              <span className="text-sm font-semibold">{user?.username || 'User'}</span>
              <span className="text-xs text-gray-500 dark:text-gray-400">{user?.role ? getRoleDisplay(user.role) : ''}</span>
            </div>
          </button>
        </div>

        {/* Logout */}
        <button
          onClick={handleLogout}
          className="p-2 text-gray-400 hover:text-red-500 dark:text-gray-400 dark:hover:text-red-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <span className="sr-only">Logout</span>
          <LogOut className="h-6 w-6" />
        </button>
      </div>
    </div>
  )
}
