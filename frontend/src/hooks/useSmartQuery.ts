import { useQuery, useQueryClient, type UseQueryOptions, type UseQueryResult } from '@tanstack/react-query'

/**
 * Enhanced query hook with smart caching and surgical updates
 *
 * Benefits:
 * - Shows cached data immediately (0ms perceived load time)
 * - Updates in background without loading spinner
 * - Only refetches when window regains focus
 * - Automatically stale after 30 seconds
 *
 * Usage:
 *   const { data, isLoading } = useSmartQuery({
 *     queryKey: ['devices'],
 *     queryFn: () => devicesAPI.getAll(),
 *   })
 */
export function useSmartQuery<TData = unknown, TError = unknown>(
  options: UseQueryOptions<TData, TError>
): UseQueryResult<TData, TError> {
  return useQuery({
    ...options,
    // Show cached data immediately while fetching fresh data
    placeholderData: (previousData) => previousData,

    // Cache data for 5 minutes
    staleTime: 5 * 60 * 1000,

    // Keep unused data in cache for 10 minutes
    gcTime: 10 * 60 * 1000,

    // Refetch when window regains focus
    refetchOnWindowFocus: true,

    // Don't refetch on mount if data is fresh
    refetchOnMount: false,

    // Retry failed requests 2 times
    retry: 2,

    // Exponential backoff: 1s, 2s, 4s
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  })
}

/**
 * Hook for surgical cache updates - update specific item without refetching all
 *
 * Usage:
 *   const updateDevice = useCacheUpdate()
 *
 *   // Update single device in cache
 *   updateDevice(['devices'], (devices) =>
 *     devices.map(d => d.id === deviceId ? { ...d, status: 'down' } : d)
 *   )
 */
export function useCacheUpdate() {
  const queryClient = useQueryClient()

  return <TData = unknown>(
    queryKey: any[],
    updater: (oldData: TData) => TData
  ) => {
    queryClient.setQueryData<TData>(queryKey, (old) => {
      if (!old) return old
      return updater(old)
    })
  }
}

/**
 * Hook for optimistic updates - update UI immediately, rollback on error
 *
 * Usage:
 *   const acknowledge = useMutation({
 *     mutationFn: alertsAPI.acknowledge,
 *     ...useOptimisticUpdate(['alerts'], (alerts, alertId) =>
 *       alerts.map(a => a.id === alertId ? { ...a, acknowledged: true } : a)
 *     )
 *   })
 */
export function useOptimisticUpdate<TData = unknown, TVariables = unknown>(
  queryKey: any[],
  updater: (oldData: TData, variables: TVariables) => TData
) {
  const queryClient = useQueryClient()

  return {
    onMutate: async (variables: TVariables) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey })

      // Snapshot previous value
      const previousData = queryClient.getQueryData<TData>(queryKey)

      // Optimistically update
      queryClient.setQueryData<TData>(queryKey, (old) => {
        if (!old) return old
        return updater(old, variables)
      })

      // Return context with snapshot
      return { previousData }
    },

    onError: (_err: any, _variables: TVariables, context: any) => {
      // Rollback on error
      if (context?.previousData) {
        queryClient.setQueryData(queryKey, context.previousData)
      }
    },

    onSettled: () => {
      // Refetch to ensure we're in sync with server
      queryClient.invalidateQueries({ queryKey })
    },
  }
}
