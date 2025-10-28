import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import Select from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/Loading'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table'
import {
  BarChart3,
  Clock,
  Wrench,
  TrendingUp,
  TrendingDown,
  Download,
  Calendar,
  Server,
  Percent,
  AlertTriangle,
  FileDown
} from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import api from '@/services/api'
import { PDFExportService } from '@/services/pdfExport'

type ReportTab = 'downtime' | 'mttr' | 'sla'

interface DowntimeReport {
  period: string
  generated_at: string
  total_devices: number
  summary: {
    total_downtime_hours: number
    average_availability: number
    devices_with_downtime: number
  }
  devices: Array<{
    hostid: string
    name: string
    region: string
    branch: string
    device_type: string
    downtime_hours: number
    availability_percent: number
    incidents: number
  }>
}

interface MTTRReport {
  avg_mttr_minutes: number
  total_incidents: number
  top_problem_devices: Array<{
    name: string
    hostid: string
    region: string
    downtime_minutes: number
    incident_count: number
  }>
  trends: {
    improving: boolean
    recommendation: string
  }
}

export default function Reports() {
  const [activeTab, setActiveTab] = useState<ReportTab>('downtime')
  const [period, setPeriod] = useState('weekly')
  const [region, setRegion] = useState('')
  const [loading, setLoading] = useState(false)
  const [downtimeReport, setDowntimeReport] = useState<DowntimeReport | null>(null)
  const [mttrReport, setMTTRReport] = useState<MTTRReport | null>(null)

  useEffect(() => {
    if (activeTab === 'downtime') {
      loadDowntimeReport()
    } else if (activeTab === 'mttr') {
      loadMTTRReport()
    }
  }, [activeTab, period, region])

  const loadDowntimeReport = async () => {
    setLoading(true)
    try {
      const response = await api.get('/reports/downtime', {
        params: { period, region: region || undefined }
      })
      setDowntimeReport(response.data)
    } catch (error) {
      console.error('Failed to load downtime report:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadMTTRReport = async () => {
    setLoading(true)
    try {
      const response = await api.get('/reports/mttr-extended')
      setMTTRReport(response.data)
    } catch (error) {
      console.error('Failed to load MTTR report:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleExportCSV = () => {
    if (!downtimeReport) return

    const csvContent = [
      ['Device', 'Region', 'Type', 'Availability %', 'Downtime Hours', 'Incidents'],
      ...downtimeReport.devices.map(d => [
        d.name,
        d.region,
        d.device_type,
        d.availability_percent.toString(),
        d.downtime_hours.toString(),
        d.incidents.toString()
      ])
    ].map(row => row.join(',')).join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `downtime_report_${new Date().toISOString().split('T')[0]}.csv`
    a.click()
  }

  // Sample data for charts
  const downtimeChartData = downtimeReport?.devices.slice(0, 10).map(d => ({
    name: d.name.length > 15 ? d.name.substring(0, 15) + '...' : d.name,
    downtime: d.downtime_hours,
    availability: d.availability_percent
  })) || []

  const mttrChartData = mttrReport?.top_problem_devices.slice(0, 8).map(d => ({
    name: d.name.length > 15 ? d.name.substring(0, 15) + '...' : d.name,
    downtime: d.downtime_minutes,
    incidents: d.incident_count
  })) || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Reports & Analytics</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Comprehensive network performance reports</p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            onClick={() => {
              const date = new Date().toISOString().split('T')[0]
              const filename = `ward-${activeTab}-report-${period}-${date}.pdf`
              PDFExportService.exportToPDF('report-content', filename)
            }}
            className="bg-ward-green hover:bg-ward-green-dark"
          >
            <FileDown className="h-4 w-4 mr-2" />
            Export PDF
          </Button>
          <Button onClick={loadDowntimeReport} variant="outline">
            <Clock className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Report Tabs */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setActiveTab('downtime')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === 'downtime'
                  ? 'bg-ward-green text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              <Clock className="h-4 w-4 inline-block mr-2" />
              Downtime Report
            </button>
            <button
              onClick={() => setActiveTab('mttr')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === 'mttr'
                  ? 'bg-ward-green text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              <Wrench className="h-4 w-4 inline-block mr-2" />
              MTTR Trends
            </button>
            <button
              onClick={() => setActiveTab('sla')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === 'sla'
                  ? 'bg-ward-green text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              <BarChart3 className="h-4 w-4 inline-block mr-2" />
              SLA Compliance
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Report Content Wrapper for PDF Export */}
      <div id="report-content">
        {/* Downtime Report */}
        {activeTab === 'downtime' && (
          <>
          {/* Filters */}
          <Card>
            <CardContent className="py-4">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-gray-500" />
                  <Select
                    value={period}
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setPeriod(e.target.value)}
                    options={[
                      { value: 'weekly', label: 'Last 7 Days' },
                      { value: 'monthly', label: 'Last 30 Days' },
                      { value: 'quarterly', label: 'Last 90 Days' },
                    ]}
                  />
                </div>

                <Select
                  value={region}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setRegion(e.target.value)}
                  options={[
                    { value: '', label: 'All Regions' },
                    { value: 'Tbilisi', label: 'Tbilisi' },
                    { value: 'Kakheti', label: 'Kakheti' },
                    { value: 'Adjara', label: 'Adjara' },
                  ]}
                />

                <div className="ml-auto">
                  <Button variant="outline" onClick={handleExportCSV}>
                    <Download className="h-4 w-4 mr-2" />
                    Export CSV
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <Card>
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Total Devices</p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      {downtimeReport?.total_devices || 0}
                    </p>
                  </div>
                  <Server className="h-8 w-8 text-ward-green" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Avg Availability</p>
                    <p className="text-2xl font-bold text-green-600">
                      {downtimeReport?.summary.average_availability.toFixed(1) || 0}%
                    </p>
                  </div>
                  <Percent className="h-8 w-8 text-green-500" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Total Downtime</p>
                    <p className="text-2xl font-bold text-red-600">
                      {downtimeReport?.summary.total_downtime_hours.toFixed(1) || 0}h
                    </p>
                  </div>
                  <Clock className="h-8 w-8 text-red-500" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Devices w/ Issues</p>
                    <p className="text-2xl font-bold text-orange-600">
                      {downtimeReport?.summary.devices_with_downtime || 0}
                    </p>
                  </div>
                  <AlertTriangle className="h-8 w-8 text-orange-500" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Downtime Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Top 10 Devices by Downtime</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center h-[300px]">
                  <LoadingSpinner size="lg" />
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={downtimeChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" className="dark:stroke-gray-700" />
                    <XAxis dataKey="name" stroke="#9ca3af" className="dark:stroke-gray-500" />
                    <YAxis stroke="#9ca3af" className="dark:stroke-gray-500" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'rgb(31 41 55)',
                        border: '1px solid rgb(75 85 99)',
                        borderRadius: '8px',
                        color: 'rgb(243 244 246)'
                      }}
                      labelStyle={{ color: 'rgb(243 244 246)' }}
                    />
                    <Bar dataKey="downtime" fill="#ef4444" radius={[8, 8, 0, 0]} name="Downtime (hours)" />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>

          {/* Detailed Table */}
          <Card>
            <CardHeader>
              <CardTitle>Device Availability Report</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-center py-12">
                  <LoadingSpinner size="lg" text="Loading report..." />
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Device Name</TableHead>
                        <TableHead>Region</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Availability</TableHead>
                        <TableHead>Downtime</TableHead>
                        <TableHead>Incidents</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {downtimeReport?.devices.map((device) => (
                        <TableRow key={device.hostid}>
                          <TableCell className="font-medium text-gray-900 dark:text-gray-100">{device.name}</TableCell>
                          <TableCell>
                            <Badge variant="default">{device.region}</Badge>
                          </TableCell>
                          <TableCell className="text-gray-900 dark:text-gray-100">{device.device_type}</TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Badge variant={device.availability_percent >= 99 ? 'success' : device.availability_percent >= 95 ? 'warning' : 'danger'}>
                                {device.availability_percent.toFixed(1)}%
                              </Badge>
                            </div>
                          </TableCell>
                          <TableCell className="text-gray-900 dark:text-gray-100">{device.downtime_hours.toFixed(2)}h</TableCell>
                          <TableCell className="text-gray-900 dark:text-gray-100">{device.incidents}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* MTTR Report */}
      {activeTab === 'mttr' && (
        <>
          {/* MTTR Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card>
              <CardContent className="py-6">
                <div className="text-center">
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Overall MTTR</p>
                  <p className="text-4xl font-bold text-ward-green">{mttrReport?.avg_mttr_minutes || 0}</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">minutes</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="py-6">
                <div className="text-center">
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Total Incidents</p>
                  <p className="text-4xl font-bold text-orange-600">{mttrReport?.total_incidents || 0}</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">this period</p>
                </div>
              </CardContent>
            </Card>

            <Card className={mttrReport?.trends.improving ? 'border-green-500 dark:border-green-600' : 'border-orange-500 dark:border-orange-600'}>
              <CardContent className="py-6">
                <div className="text-center">
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Trend</p>
                  <div className="flex items-center justify-center gap-2">
                    {mttrReport?.trends.improving ? (
                      <TrendingDown className="h-8 w-8 text-green-500" />
                    ) : (
                      <TrendingUp className="h-8 w-8 text-orange-500" />
                    )}
                  </div>
                  <p className={`text-sm mt-1 font-medium ${mttrReport?.trends.improving ? 'text-green-600' : 'text-orange-600'}`}>
                    {mttrReport?.trends.improving ? 'Improving' : 'Needs Attention'}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* MTTR Chart */}
          <Card>
            <CardHeader>
              <CardTitle>MTTR by Device</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={mttrChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" className="dark:stroke-gray-700" />
                  <XAxis dataKey="name" stroke="#9ca3af" className="dark:stroke-gray-500" />
                  <YAxis stroke="#9ca3af" className="dark:stroke-gray-500" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgb(31 41 55)',
                      border: '1px solid rgb(75 85 99)',
                      borderRadius: '8px',
                      color: 'rgb(243 244 246)'
                    }}
                    labelStyle={{ color: 'rgb(243 244 246)' }}
                  />
                  <Legend wrapperStyle={{ color: 'rgb(156 163 175)' }} />
                  <Bar dataKey="downtime" fill="#5EBBA8" name="Downtime (min)" radius={[8, 8, 0, 0]} />
                  <Bar dataKey="incidents" fill="#f59e0b" name="Incidents" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Top Problem Devices */}
          <Card>
            <CardHeader>
              <CardTitle>Top 10 Devices Requiring Attention</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>#</TableHead>
                      <TableHead>Device</TableHead>
                      <TableHead>Region</TableHead>
                      <TableHead>Incidents</TableHead>
                      <TableHead>Total Downtime</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mttrReport?.top_problem_devices.map((device, index) => (
                      <TableRow key={device.hostid}>
                        <TableCell>
                          <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-ward-green text-white font-semibold text-sm">
                            {index + 1}
                          </span>
                        </TableCell>
                        <TableCell className="font-medium text-gray-900 dark:text-gray-100">{device.name}</TableCell>
                        <TableCell>
                          <Badge variant="default">{device.region}</Badge>
                        </TableCell>
                        <TableCell className="text-gray-900 dark:text-gray-100">{device.incident_count}</TableCell>
                        <TableCell className="text-gray-900 dark:text-gray-100">{device.downtime_minutes} min</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* SLA Compliance */}
      {activeTab === 'sla' && (
        <Card>
          <CardHeader>
            <CardTitle>SLA Compliance Dashboard</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="p-6 rounded-lg border-2 border-green-500 dark:border-green-600 bg-green-50 dark:bg-green-900/20">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">99.9% SLA</h3>
                <p className="text-3xl font-bold text-green-600 dark:text-green-400 mb-1">85%</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">Devices Meeting SLA</p>
              </div>

              <div className="p-6 rounded-lg border-2 border-yellow-500 dark:border-yellow-600 bg-yellow-50 dark:bg-yellow-900/20">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">99.5% SLA</h3>
                <p className="text-3xl font-bold text-yellow-600 dark:text-yellow-400 mb-1">92%</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">Devices Meeting SLA</p>
              </div>

              <div className="p-6 rounded-lg border-2 border-red-500 dark:border-red-600 bg-red-50 dark:bg-red-900/20">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">Below Target</h3>
                <p className="text-3xl font-bold text-red-600 dark:text-red-400 mb-1">12</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">Devices Need Attention</p>
              </div>
            </div>

            <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-blue-900 dark:text-blue-100">Information</p>
                  <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                    SLA tracking requires historical data. This feature will be enhanced once connected to monitoring history API.
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
      </div>
      {/* End Report Content Wrapper */}
    </div>
  )
}
