// -----------------------------------------------------------------------
// Bond arbitrage monitor — TypeScript interfaces
// Mirror of backend/models/bond_models.py Pydantic models
// -----------------------------------------------------------------------

export interface BondPairConfig {
  id: string;
  label: string;
  local_symbol: string;
  ny_symbol: string;
  description: string;
}

export interface RatioSnapshot {
  pair_id: string;
  timestamp: string;   // ISO UTC datetime
  local_price: number;
  ny_price: number;
  ratio: number;
}

export interface RatioStats {
  mean: number;
  std: number;
  z_score: number;
  upper_band: number;
  lower_band: number;
  upper_band_1sigma: number;
  lower_band_1sigma: number;
  window_size: number;
}

export interface CommissionInfo {
  roundtrip_cost_pct: number;    // total round-trip cost as % (e.g. 0.5)
  gross_spread_pct: number;      // |ratio - mean| / mean * 100
  net_spread_pct: number;        // gross - roundtrip_cost (as %)
  is_profitable: boolean;
  breakeven_ratio: number;
}

export type AlertDirection = 'LOCAL_CHEAP' | 'NY_CHEAP';

export interface ArbitrageAlert {
  pair_id: string;
  pair_label: string;
  timestamp: string;
  ratio: number;
  z_score: number;
  direction: AlertDirection;
  description: string;
  commission: CommissionInfo | null;
}

export type EodAction = 'hold' | 'close' | 'none';

export interface BondPairState {
  config: BondPairConfig;
  latest: RatioSnapshot | null;
  stats: RatioStats | null;
  alert: ArbitrageAlert | null;
  commission: CommissionInfo | null;
  history: RatioSnapshot[];
  last_fetch_error: string | null;
  eod_signal: boolean;
  eod_action: EodAction;  // 'hold' | 'close' | 'none'
}

export interface BondsStatusResponse {
  pairs: BondPairState[];
  last_refresh_at: string | null;
  next_refresh_at: string | null;
  refresh_running: boolean;
  iol_authenticated: boolean;
  market_open: boolean;
  eod_signal: boolean;
  commission_rate: number;  // total round-trip cost
}

export interface BondHistoryResponse {
  pair_id: string;
  pair_label: string;
  history: RatioSnapshot[];
  stats: RatioStats | null;
}

// ---------------------------------------------------------------------------
// Order types
// ---------------------------------------------------------------------------

export type OrderSide = 'buy' | 'sell';
export type OrderPlazo = 't0' | 't1' | 't2';

export interface BondOrderRequest {
  pair_id: string;
  symbol: string;
  side: OrderSide;
  quantity: number;
  price: number;
  plazo: OrderPlazo;
  sandbox: boolean;
}

export interface BondOrderResponse {
  success: boolean;
  order_id: string | null;
  message: string;
  sandbox: boolean;
  raw_response: Record<string, unknown> | null;
}

// ---------------------------------------------------------------------------
// Order log
// ---------------------------------------------------------------------------

export interface OrderLogEntry {
  id: string;
  timestamp: string;       // ISO UTC
  pair_id: string;
  pair_label: string;
  symbol: string;
  side: OrderSide;
  quantity: number;
  price: number;
  plazo: OrderPlazo;
  sandbox: boolean;
  success: boolean;
  order_id: string | null;
  message: string;
}

export interface OrderLogResponse {
  entries: OrderLogEntry[];
  total: number;
}
