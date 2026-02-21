import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchScreenerResults, fetchUniverseStats, triggerRefresh } from '../api/screener';
import type { ScreenerParams } from '../api/screener';

export function useScreener(params: ScreenerParams) {
  return useQuery({
    queryKey: ['screener', params],
    queryFn: () => fetchScreenerResults(params),
    staleTime: 5 * 60 * 1000,
    placeholderData: (prev) => prev,
    retry: 2,
  });
}

export function useUniverseStats() {
  return useQuery({
    queryKey: ['universe-stats'],
    queryFn: fetchUniverseStats,
    staleTime: 60 * 1000,
    refetchInterval: 60 * 1000,
  });
}

export function useRefreshTrigger() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: triggerRefresh,
    onSuccess: () => {
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ['screener'] });
        qc.invalidateQueries({ queryKey: ['universe-stats'] });
      }, 5000);
    },
  });
}
