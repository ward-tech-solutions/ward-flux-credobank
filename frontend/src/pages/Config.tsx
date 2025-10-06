import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Server, RefreshCw, Save, MapPin } from 'lucide-react'
import api from '@/services/api'

interface HostGroup {
  groupid: string
  name: string
  display_name?: string
  is_active?: boolean
}

interface City {
  id: number
  name_en: string
  latitude: number
  longitude: number
  region_name: string
}

export default function Config() {
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [allGroups, setAllGroups] = useState<HostGroup[]>([])
  const [selectedGroups, setSelectedGroups] = useState<Set<string>>(new Set())
  const [cities, setCities] = useState<City[]>([])

  useEffect(() => {
    loadMonitoredGroups()
    loadCities()
  }, [])

  const loadMonitoredGroups = async () => {
    try {
      const response = await api.get('/config/monitored-hostgroups')
      const monitoredGroupIds = new Set<string>(response.data.monitored_groups.map((g: any) => g.groupid as string))
      setSelectedGroups(monitoredGroupIds)
    } catch (error) {
      console.error('Failed to load monitored groups:', error)
    }
  }

  const loadZabbixGroups = async () => {
    setLoading(true)
    try {
      const response = await api.get('/config/zabbix-hostgroups')
      setAllGroups(response.data.hostgroups || [])
    } catch (error) {
      console.error('Failed to load Zabbix host groups:', error)
      alert('Failed to fetch host groups from Zabbix. Please check your Zabbix configuration.')
    } finally {
      setLoading(false)
    }
  }

  const loadCities = async () => {
    try {
      const response = await api.get('/config/georgian-cities')
      setCities(response.data.cities || [])
    } catch (error) {
      console.error('Failed to load cities:', error)
    }
  }

  const toggleGroup = (groupId: string) => {
    const newSelected = new Set<string>(selectedGroups)
    if (newSelected.has(groupId)) {
      newSelected.delete(groupId)
    } else {
      newSelected.add(groupId)
    }
    setSelectedGroups(newSelected)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const groups = allGroups
        .filter(g => selectedGroups.has(g.groupid))
        .map(g => ({
          groupid: g.groupid,
          name: g.name,
          display_name: g.name
        }))

      await api.post('/config/monitored-hostgroups', { groups })
      alert('Configuration saved successfully!')
    } catch (error) {
      console.error('Failed to save configuration:', error)
      alert('Failed to save configuration')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Host Group Configuration</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Select host groups to monitor from Zabbix</p>
      </div>

      {/* Host Groups Configuration */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-ward-green/10 rounded-lg">
                <Server className="h-6 w-6 text-ward-green" />
              </div>
              <div>
                <CardTitle>Select Host Groups to Monitor</CardTitle>
                {selectedGroups.size > 0 && (
                  <Badge variant="default" className="mt-1">
                    {selectedGroups.size} selected
                  </Badge>
                )}
              </div>
            </div>
            <Button onClick={loadZabbixGroups} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Fetch from Zabbix
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {allGroups.length === 0 ? (
            <div className="text-center py-12">
              <Server className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500 dark:text-gray-400">
                Click "Fetch from Zabbix" to load available host groups
              </p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-h-[500px] overflow-y-auto p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                {allGroups.map((group) => (
                  <label
                    key={group.groupid}
                    className={`flex items-start gap-3 p-4 rounded-lg border-2 cursor-pointer transition-all ${
                      selectedGroups.has(group.groupid)
                        ? 'border-ward-green bg-ward-green/5'
                        : 'border-gray-200 dark:border-gray-700 hover:border-ward-green/50'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedGroups.has(group.groupid)}
                      onChange={() => toggleGroup(group.groupid)}
                      className="mt-1 rounded border-gray-300 text-ward-green focus:ring-ward-green w-5 h-5"
                    />
                    <div className="flex-1">
                      <p className="font-medium text-gray-900 dark:text-gray-100">{group.name}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">ID: {group.groupid}</p>
                    </div>
                  </label>
                ))}
              </div>

              <div className="flex justify-end mt-6">
                <Button onClick={handleSave} disabled={saving || selectedGroups.size === 0}>
                  <Save className="h-4 w-4 mr-2" />
                  {saving ? 'Saving...' : 'Save Configuration'}
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* City-Region Mapping */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-ward-green/10 rounded-lg">
              <MapPin className="h-6 w-6 text-ward-green" />
            </div>
            <div>
              <CardTitle>City-Region Mapping</CardTitle>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Configured cities with coordinates for map visualization
              </p>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {cities.length === 0 ? (
            <div className="text-center py-12">
              <MapPin className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500 dark:text-gray-400">Loading cities...</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {cities.map((city) => (
                <div
                  key={city.id}
                  className="p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-gray-900 dark:text-gray-100">{city.name_en}</p>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                        <Badge variant="default">{city.region_name}</Badge>
                      </p>
                    </div>
                    <MapPin className="h-5 w-5 text-ward-green" />
                  </div>
                  <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <p className="text-gray-500 dark:text-gray-400">Latitude</p>
                        <p className="font-mono text-gray-900 dark:text-gray-100">{city.latitude.toFixed(4)}</p>
                      </div>
                      <div>
                        <p className="text-gray-500 dark:text-gray-400">Longitude</p>
                        <p className="font-mono text-gray-900 dark:text-gray-100">{city.longitude.toFixed(4)}</p>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
