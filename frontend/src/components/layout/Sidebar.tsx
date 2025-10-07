import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Scan,
  Wifi,
  Activity,
  Map as MapIcon,
  Network,
  Stethoscope,
  BarChart3,
  MapPin,
  Settings
} from 'lucide-react'
import { cn } from '@/lib/utils.ts'
import { useAuth } from '@/contexts/AuthContext'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard, roles: ['admin', 'regional_manager', 'technician', 'viewer'] },
  { name: 'Discovery', href: '/discovery', icon: Scan, roles: ['admin', 'technician'] },
  { name: 'Devices', href: '/devices', icon: Wifi, roles: ['admin', 'regional_manager', 'technician', 'viewer'] },
  { name: 'Monitor', href: '/monitor', icon: Activity, roles: ['admin', 'regional_manager', 'technician'] },
  { name: 'Map', href: '/map', icon: MapIcon, roles: ['admin', 'regional_manager', 'technician', 'viewer'] },
  { name: 'Topology', href: '/topology', icon: Network, roles: ['admin', 'regional_manager', 'technician'] },
  { name: 'Diagnostics', href: '/diagnostics', icon: Stethoscope, roles: ['admin', 'regional_manager', 'technician'] },
  { name: 'Reports', href: '/reports', icon: BarChart3, roles: ['admin', 'regional_manager'] },
  { name: 'Regions', href: '/regions', icon: MapPin, roles: ['admin', 'regional_manager'] },
  { name: 'Settings', href: '/settings', icon: Settings, roles: ['admin'] },
]

export default function Sidebar() {
  const { user } = useAuth()
  return (
    <div className="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-72 lg:flex-col">
      <div className="flex grow flex-col gap-y-5 overflow-y-auto bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 px-6 pb-4">
        {/* Logo */}
        <div className="flex h-16 shrink-0 items-center">
          <img
            className="h-8 w-auto dark:invert"
            src="/logo-ward.svg"
            alt="WARD FLUX"
          />
          <span className="ml-3 text-xl font-bold text-gray-900 dark:text-white">
            FLUX
          </span>
        </div>

        {/* Navigation */}
        <nav className="flex flex-1 flex-col">
          <ul role="list" className="flex flex-1 flex-col gap-y-7">
            <li>
              <ul role="list" className="-mx-2 space-y-1">
                {navigation
                  .filter((item) => !user?.role || item.roles.includes(user.role))
                  .map((item) => (
                    <li key={item.name}>
                      <NavLink
                        to={item.href}
                        end={item.href === '/'}
                        className={({ isActive }) =>
                          cn(
                            'group flex gap-x-3 rounded-md p-2 text-sm font-semibold leading-6 transition-colors',
                            isActive
                              ? 'bg-ward-green text-white'
                              : 'text-gray-700 dark:text-gray-300 hover:text-ward-green dark:hover:text-ward-green hover:bg-gray-50 dark:hover:bg-gray-800'
                          )
                        }
                      >
                        {({ isActive }) => (
                          <>
                            <item.icon
                              className={cn(
                                'h-6 w-6 shrink-0',
                                isActive ? 'text-white' : 'text-gray-400 dark:text-gray-500 group-hover:text-ward-green'
                              )}
                              aria-hidden="true"
                            />
                            {item.name}
                          </>
                        )}
                      </NavLink>
                    </li>
                  ))}
              </ul>
            </li>
          </ul>
        </nav>

        {/* Footer */}
        <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            WARD FLUX v2.0
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
            © 2025 WARD Tech Solutions
          </p>
        </div>
      </div>
    </div>
  )
}
