/**
 * Regional Access Control
 * Device naming format: "City - Type - IP" (e.g., "Sagarejo - SW - 192.168.200.77")
 * Extract city and map to region for filtering
 */

// City to Region mapping for Georgia
export const CITY_TO_REGION: Record<string, string> = {
  // Kakheti Region
  'Sagarejo': 'Kakheti',
  'Telavi': 'Kakheti',
  'Gurjaani': 'Kakheti',
  'Sighnaghi': 'Kakheti',
  'Dedoplistskaro': 'Kakheti',
  'Lagodekhi': 'Kakheti',
  'Akhmeta': 'Kakheti',
  'Kvareli': 'Kakheti',
  'Kabali': 'Kakheti',

  // Tbilisi
  'Tbilisi': 'Tbilisi',

  // Imereti Region
  'Kutaisi': 'Imereti',
  'Zestaponi': 'Imereti',
  'Chiatura': 'Imereti',
  'Khoni': 'Imereti',
  'Sachkhere': 'Imereti',
  'Samtredia': 'Imereti',
  'Terjola': 'Imereti',
  'Vani': 'Imereti',
  'Baghdati': 'Imereti',
  'Kharagauli': 'Imereti',

  // Adjara Region
  'Batumi': 'Adjara',
  'Kobuleti': 'Adjara',
  'Khelvachauri': 'Adjara',
  'Shuakhevi': 'Adjara',
  'Keda': 'Adjara',
  'Khulo': 'Adjara',

  // Kvemo Kartli
  'Rustavi': 'Kvemo Kartli',
  'Marneuli': 'Kvemo Kartli',
  'Gardabani': 'Kvemo Kartli',
  'Bolnisi': 'Kvemo Kartli',
  'Dmanisi': 'Kvemo Kartli',
  'Tsalka': 'Kvemo Kartli',
  'Tetritskaro': 'Kvemo Kartli',

  // Shida Kartli
  'Gori': 'Shida Kartli',
  'Kaspi': 'Shida Kartli',
  'Kareli': 'Shida Kartli',
  'Khashuri': 'Shida Kartli',

  // Samtskhe-Javakheti
  'Akhaltsikhe': 'Samtskhe-Javakheti',
  'Borjomi': 'Samtskhe-Javakheti',
  'Akhalkalaki': 'Samtskhe-Javakheti',
  'Adigeni': 'Samtskhe-Javakheti',
  'Aspindza': 'Samtskhe-Javakheti',
  'Ninotsminda': 'Samtskhe-Javakheti',

  // Mtskheta-Mtianeti
  'Mtskheta': 'Mtskheta-Mtianeti',
  'Dusheti': 'Mtskheta-Mtianeti',
  'Tianeti': 'Mtskheta-Mtianeti',
  'Akhalgori': 'Mtskheta-Mtianeti',

  // Racha-Lechkhumi and Kvemo Svaneti
  'Ambrolauri': 'Racha-Lechkhumi',
  'Lentekhi': 'Racha-Lechkhumi',
  'Oni': 'Racha-Lechkhumi',
  'Tsageri': 'Racha-Lechkhumi',

  // Samegrelo-Zemo Svaneti
  'Zugdidi': 'Samegrelo-Zemo Svaneti',
  'Poti': 'Samegrelo-Zemo Svaneti',
  'Senaki': 'Samegrelo-Zemo Svaneti',
  'Mestia': 'Samegrelo-Zemo Svaneti',
  'Abasha': 'Samegrelo-Zemo Svaneti',
  'Martvili': 'Samegrelo-Zemo Svaneti',
  'Chkhorotsku': 'Samegrelo-Zemo Svaneti',
  'Khobi': 'Samegrelo-Zemo Svaneti',
  'Tsalenjikha': 'Samegrelo-Zemo Svaneti',

  // Guria
  'Ozurgeti': 'Guria',
  'Lanchkhuti': 'Guria',
  'Chokhatauri': 'Guria',
}

// All unique regions
export const REGIONS = Array.from(new Set(Object.values(CITY_TO_REGION))).sort()

/**
 * Extract city from device name
 * Supports two formats:
 * - Standalone: "City - DeviceType - IP" (e.g., "Sagarejo - SW - 192.168.200.77")
 * - Zabbix: "City - IP" (e.g., "Sagarejo - 192.168.200.77")
 * Both extract "Sagarejo" as the city name
 */
export function extractCityFromDeviceName(deviceName: string): string | null {
  if (!deviceName || typeof deviceName !== 'string') return null

  const parts = deviceName.split('-').map(p => p?.trim()).filter(p => p)
  if (parts.length >= 1 && parts[0]) {
    // First part is always the city name
    return parts[0]
  }

  return null
}

/**
 * Get region from device name
 * Example: "Sagarejo - SW - 192.168.200.77" -> "Kakheti"
 */
export function getRegionFromDeviceName(deviceName: string): string | null {
  if (!deviceName || typeof deviceName !== 'string') return null

  const city = extractCityFromDeviceName(deviceName)
  if (!city || typeof city !== 'string') return null

  return CITY_TO_REGION[city] || null
}

/**
 * Filter devices by region
 */
export function filterDevicesByRegion(devices: any[], region: string): any[] {
  if (!region || region === 'all') return devices

  return devices.filter(device => {
    const deviceRegion = getRegionFromDeviceName(device.name || device.host || '')
    return deviceRegion === region
  })
}

/**
 * Get device type from name
 * Standalone format: "City - Type - IP" (e.g., "Sagarejo - SW - 192.168.200.77")
 * Zabbix format: "City - IP" (e.g., "Sagarejo - 192.168.200.77")
 * Returns device type (SW, RT, etc.) or null for Zabbix devices
 */
export function getDeviceTypeFromName(deviceName: string): string | null {
  if (!deviceName) return null

  const parts = deviceName.split('-').map(p => p.trim())

  // If we have 3 parts, it's standalone format with device type
  if (parts.length >= 3) {
    return parts[1]
  }

  // If we have 2 parts, it's Zabbix format (City - IP), no device type
  return null
}

/**
 * Check if user has access to a device based on their region
 */
export function hasAccessToDevice(device: any, userRegion: string | null, userRole: string): boolean {
  // Admins have access to all devices
  if (userRole === 'admin') return true

  // If no user region, deny access (regional managers must have a region)
  if (!userRegion) return false

  // Get device region
  const deviceRegion = getRegionFromDeviceName(device.name || device.host || '')

  // Regional manager can only see devices from their region
  return deviceRegion === userRegion
}
