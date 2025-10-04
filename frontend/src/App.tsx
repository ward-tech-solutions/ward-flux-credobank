import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ErrorBoundary } from './components/ErrorBoundary'
import { Dashboard } from './pages/Dashboard'
import { Devices } from './pages/Devices'
import { MapView } from './pages/MapView'
import { Topology } from './pages/Topology'
import { Reports } from './pages/Reports'
import { DeviceDetails } from './pages/DeviceDetails'
import { useWebSocket } from './hooks/useWebSocket'

function App() {
  // Connect to WebSocket for real-time updates
  useWebSocket()

  return (
    <ErrorBoundary>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/devices" element={<Devices />} />
          <Route path="/device/:hostid" element={<DeviceDetails />} />
          <Route path="/map" element={<MapView />} />
          <Route path="/topology" element={<Topology />} />
          <Route path="/reports" element={<Reports />} />
        </Routes>
      </Layout>
    </ErrorBoundary>
  )
}

export default App
