export interface WeeklyPrice {
  date: string;
  close: number;
}

export interface StockMetrics {
  ticker: string;
  name: string | null;
  sector: string | null;
  industry: string | null;
  index_membership: string[];
  current_price: number | null;
  price_52w_high: number | null;
  price_52w_low: number | null;
  pct_above_52w_low: number | null;
  ma_200d: number | null;
  ma_30w: number | null;
  pct_vs_ma200d: number | null;
  pct_vs_ma30w: number | null;
  trailing_pe: number | null;
  forward_pe: number | null;
  market_cap: number | null;
  dividend_yield: number | null;
  eps_ttm: number | null;
  eps_cagr_5y: number | null;
  beta: number | null;
  price_volatility_1y: number | null;
  weekly_prices: WeeklyPrice[];
  last_updated: string | null;
  data_quality_score: number;
  quality_score: number | null;
}

export interface StockSummary {
  ticker: string;
  name: string | null;
  sector: string | null;
  index_membership: string[];
  current_price: number | null;
  pct_above_52w_low: number | null;
  trailing_pe: number | null;
  eps_cagr_5y: number | null;
  dividend_yield: number | null;
  beta: number | null;
  market_cap: number | null;
  price_52w_low: number | null;
  price_52w_high: number | null;
  ma_200d: number | null;
  ma_30w: number | null;
  pct_vs_ma200d: number | null;
  pct_vs_ma30w: number | null;
  data_quality_score: number;
  quality_score: number | null;
  passes_filter: boolean;
  last_updated: string | null;
}

export interface ScreenerFilters {
  universe: string[];
  max_pct_above_52w_low: number;
  max_trailing_pe: number;
  min_eps_cagr_5y: number;
  min_dividend_yield: number;
  require_both_income_filters: boolean;
}

export interface ScreenerResponse {
  filters_applied: ScreenerFilters;
  total_universe_count: number;
  passed_count: number;
  results: StockSummary[];
  cache_age_seconds: number | null;
  generated_at: string;
}

export interface PortfolioRequest {
  tickers: string[];
  total_capital?: number;
  max_sector_weight?: number;
  max_single_stock_weight?: number;
  weighting_method?: 'equal' | 'risk_parity' | 'market_cap';
}

export interface PortfolioPosition {
  ticker: string;
  name: string | null;
  sector: string | null;
  target_weight: number;
  target_amount: number | null;
  target_shares: number | null;
  current_price: number | null;
  beta: number | null;
  volatility: number | null;
  quality_score: number | null;
  pct_above_52w_low: number | null;
  dividend_yield: number | null;
  trailing_pe: number | null;
}

export interface SectorAllocation {
  sector: string;
  weight: number;
  tickers: string[];
}

export interface PortfolioResponse {
  positions: PortfolioPosition[];
  sector_allocations: SectorAllocation[];
  portfolio_beta: number;
  portfolio_volatility: number;
  diversification_score: number;
  total_positions: number;
  weighting_method: string;
  total_capital: number | null;
  warnings: string[];
}

export interface UniverseStats {
  total_tickers: number;
  sectors: Record<string, number>;
  cache_age_seconds: number | null;
  is_stale: boolean;
  refresh_running: boolean;
}

export interface MonteCarloSummary {
  mean_final: number;
  median_final: number;
  p10_final: number;
  p90_final: number;
  prob_profit: number;
  prob_loss_20pct: number;
  annualized_return_median: number;
  mu_weekly: number;
  sigma_weekly: number;
  n_simulations: number;
  n_weeks: number;
}

export interface SimulationResult {
  weeks: string[];
  paths: { p10: number[]; p25: number[]; p50: number[]; p75: number[]; p90: number[] };
  initial_capital: number;
  summary: MonteCarloSummary;
  error?: string;
}

export interface MonteCarloResult {
  weeks: string[];
  paths: { p10: number[]; p25: number[]; p50: number[]; p75: number[]; p90: number[] };
  initial_capital: number;
  summary: MonteCarloSummary;
  portfolio_positions: number;
  missing_tickers: string[];
  error?: string;
  monte_carlo?: SimulationResult;
  bootstrap?: SimulationResult;
}

export type SortDirection = 'asc' | 'desc';
export type SortColumn = keyof StockSummary;
export type WeightingMethod = 'equal' | 'risk_parity' | 'market_cap';
