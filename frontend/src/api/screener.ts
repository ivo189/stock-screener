import client from './client';
import type { ScreenerResponse, UniverseStats } from '../types';

export interface ScreenerParams {
  universe?: string[];
  max_pct_above_52w_low?: number;
  max_trailing_pe?: number;
  min_eps_cagr_5y?: number;
  min_dividend_yield?: number;
  require_both?: boolean;
  max_pct_vs_ma200d?: number | null;
  max_pct_vs_ma30w?: number | null;
}

export async function fetchScreenerResults(params: ScreenerParams): Promise<ScreenerResponse> {
  const searchParams = new URLSearchParams();
  if (params.universe) params.universe.forEach((u) => searchParams.append('universe', u));
  if (params.max_pct_above_52w_low !== undefined)
    searchParams.set('max_pct_above_52w_low', String(params.max_pct_above_52w_low));
  if (params.max_trailing_pe !== undefined)
    searchParams.set('max_trailing_pe', String(params.max_trailing_pe));
  if (params.min_eps_cagr_5y !== undefined)
    searchParams.set('min_eps_cagr_5y', String(params.min_eps_cagr_5y));
  if (params.min_dividend_yield !== undefined)
    searchParams.set('min_dividend_yield', String(params.min_dividend_yield));
  if (params.require_both !== undefined)
    searchParams.set('require_both', String(params.require_both));
  if (params.max_pct_vs_ma200d != null)
    searchParams.set('max_pct_vs_ma200d', String(params.max_pct_vs_ma200d));
  if (params.max_pct_vs_ma30w != null)
    searchParams.set('max_pct_vs_ma30w', String(params.max_pct_vs_ma30w));

  const res = await client.get<ScreenerResponse>(`/screener?${searchParams.toString()}`);
  return res.data;
}

export async function fetchUniverseStats(): Promise<UniverseStats> {
  const res = await client.get<UniverseStats>('/screener/universe');
  return res.data;
}

export async function triggerRefresh(): Promise<{ message: string }> {
  const res = await client.post<{ message: string }>('/screener/refresh');
  return res.data;
}
