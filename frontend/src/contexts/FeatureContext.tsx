import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { settingsAPI } from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'

export interface FeatureFlags {
  discovery: boolean
  topology: boolean
  diagnostics: boolean
  reports: boolean
  map: boolean
  regions: boolean
}

const DEFAULT_FEATURES: FeatureFlags = {
  discovery: true,
  topology: true,
  diagnostics: true,
  reports: true,
  map: true,
  regions: true,
}

interface FeatureContextType {
  features: FeatureFlags
  toggleFeature: (feature: keyof FeatureFlags) => void
  resetFeatures: () => void
  isLoading: boolean
}

const FeatureContext = createContext<FeatureContextType | undefined>(undefined)

export function FeatureProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const [features, setFeatures] = useState<FeatureFlags>(DEFAULT_FEATURES)

  // Fetch feature toggles from API (system-wide settings) - only when authenticated
  const { data, isLoading } = useQuery({
    queryKey: ['feature-toggles'],
    queryFn: () => settingsAPI.getFeatureToggles(),
    staleTime: 30_000, // Cache for 30 seconds
    refetchOnWindowFocus: true,
    enabled: !!user, // Only fetch when user is authenticated
  })

  // Update local state when API data changes
  useEffect(() => {
    if (data?.data) {
      setFeatures({ ...DEFAULT_FEATURES, ...data.data })
    }
  }, [data])

  // Mutation to save feature toggles (admin only)
  const updateFeaturesMutation = useMutation({
    mutationFn: (newFeatures: FeatureFlags) => settingsAPI.saveFeatureToggles(newFeatures),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feature-toggles'] })
    },
  })

  const toggleFeature = (feature: keyof FeatureFlags) => {
    const newFeatures = {
      ...features,
      [feature]: !features[feature],
    }
    setFeatures(newFeatures)
    updateFeaturesMutation.mutate(newFeatures)
  }

  const resetFeatures = () => {
    setFeatures(DEFAULT_FEATURES)
    updateFeaturesMutation.mutate(DEFAULT_FEATURES)
  }

  return (
    <FeatureContext.Provider value={{ features, toggleFeature, resetFeatures, isLoading }}>
      {children}
    </FeatureContext.Provider>
  )
}

export function useFeatures() {
  const context = useContext(FeatureContext)
  if (context === undefined) {
    throw new Error('useFeatures must be used within a FeatureProvider')
  }
  return context
}
