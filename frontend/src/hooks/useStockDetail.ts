import { useQuery } from '@tanstack/react-query';
import { fetchStockDetail } from '../api/stocks';

export function useStockDetail(ticker: string | null) {
  return useQuery({
    queryKey: ['stock', ticker],
    queryFn: () => fetchStockDetail(ticker!),
    enabled: !!ticker,
    staleTime: 15 * 60 * 1000,
  });
}
