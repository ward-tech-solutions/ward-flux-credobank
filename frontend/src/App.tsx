import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import Discovery from './pages/Discovery'
import Devices from './pages/Devices'
import DeviceDetails from './pages/DeviceDetails'
import Monitor from './pages/Monitor'
import Map from './pages/Map'
import Topology from './pages/Topology'
import Diagnostics from './pages/Diagnostics'
import Reports from './pages/Reports'
import Regions from './pages/Regions'
import Settings from './pages/Settings'
import Login from './pages/Login'

function App() {
  const isAuthenticated = localStorage.getItem('token')

  if (!isAuthenticated && window.location.pathname !== '/login') {
    return <Navigate to="/login" />
  }

  if (isAuthenticated && window.location.pathname === '/login') {
    return <Navigate to="/" />
  }

  return (
    <>
      <Toaster position="top-right" richColors />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="discovery" element={<Discovery />} />
          <Route path="devices" element={<Devices />} />
          <Route path="devices/:id" element={<DeviceDetails />} />
          <Route path="monitor" element={<Monitor />} />
          <Route path="map" element={<Map />} />
          <Route path="topology" element={<Topology />} />
          <Route path="diagnostics" element={<Diagnostics />} />
          <Route path="reports" element={<Reports />} />
          <Route path="regions" element={<Regions />} />
          <Route path="users" element={<Navigate to="/settings" replace />} />
          <Route path="settings" element={<Settings />} />
          <Route path="config" element={<Navigate to="/settings" replace />} />
        </Route>
      </Routes>
    </>
  )
}

export default App
