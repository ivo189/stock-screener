import client from './client';

export type HighRef = 'ath' | '52w' | '26w' | '13w';

export interface ScanParams {
  high_ref: HighRef;
  max_dist_pct: number;
  min_vol_pct: number;
  min_traded_musd: number;
  top: number;
  force?: boolean;
}

export interface UnderlyingRow {
  ticker: string;
  close: number;
  high_ref: number;
  dist_pct: number;
  rv21: number;
  max_move_pct: number;
  sigma15_pct: number;
  traded_musd: number;
  score: number;
  last_date: string;
  earnings_date: string | null;
  days_to_earnings: number | null;
}

export interface SpreadParams {
  x: number;
  y: number;
  min_dte: number;
  max_dte: number;
  min_credit: number;
  max_otm_long_pct: number;
  max_otm_short_pct: number;
  min_open_interest: number;
}

export interface SpreadRow {
  expiration: string;
  dte: number;
  k_long: number;
  k_short: number;
  premium_long: number;
  premium_short: number;
  net_credit: number; // USD por combo (x100)
  max_profit: number;
  upper_breakeven: number | null;
  upper_breakeven_pct: number | null;
  naked: number;
  iv_long: number | null;
  iv_short: number | null;
  payoff: { spot: number; pnl: number }[];
}

export interface SpreadsResponse {
  ticker: string;
  spot: number;
  x: number;
  y: number;
  spreads: SpreadRow[];
}

export async function scanUnderlyings(p: ScanParams): Promise<{ count: number; results: UnderlyingRow[] }> {
  const res = await client.get('/options/scan', { params: p });
  return res.data;
}

export async function fetchRatioSpreads(ticker: string, p: SpreadParams): Promise<SpreadsResponse> {
  const res = await client.get(`/options/ratio-spreads/${ticker}`, { params: p });
  return res.data;
}
