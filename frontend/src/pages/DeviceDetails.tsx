import { useParams } from 'react-router-dom'

export const DeviceDetails = () => {
  const { hostid } = useParams()
  return <div>Device Details for {hostid} - Coming Soon</div>
}
