import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import clsx from 'clsx'

interface LayoutProps {
  children: ReactNode
}

export const Layout = ({ children }: LayoutProps) => {
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  return (
    <>
      <nav className="topnav">
        <div className="topnav-left">
          <div className="logo">
            <i className="fas fa-network-wired"></i>
            <span>Network Monitor</span>
          </div>
        </div>

        <div className="topnav-center">
          <Link
            to="/"
            className={clsx('nav-item', { active: isActive('/') })}
          >
            <i className="fas fa-tachometer-alt"></i>
            Dashboard
          </Link>
          <Link
            to="/devices"
            className={clsx('nav-item', { active: isActive('/devices') })}
          >
            <i className="fas fa-server"></i>
            Devices
          </Link>
          <Link
            to="/map"
            className={clsx('nav-item', { active: isActive('/map') })}
          >
            <i className="fas fa-map-marked-alt"></i>
            Map
          </Link>
          <Link
            to="/topology"
            className={clsx('nav-item', { active: isActive('/topology') })}
          >
            <i className="fas fa-project-diagram"></i>
            Topology
          </Link>
          <Link
            to="/reports"
            className={clsx('nav-item', { active: isActive('/reports') })}
          >
            <i className="fas fa-chart-bar"></i>
            Reports
          </Link>
        </div>

        <div className="topnav-right">
          <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.875rem' }}>
            v2.0.0
          </span>
        </div>
      </nav>

      <main className="main-container">
        <div className="main-content no-sidebar">{children}</div>
      </main>
    </>
  )
}
