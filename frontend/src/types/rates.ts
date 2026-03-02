// -----------------------------------------------------------------------
// Tasas ARS — TypeScript interfaces
// Mirror of backend/api/routes/rates.py Pydantic models
// -----------------------------------------------------------------------

export interface RatePoint {
  date: string;    // ISO date: "2025-01-15"
  tna: number;     // Tasa Nominal Anual (%)
  price: number;   // Raw IOL closing price
}

export interface LetraResult {
  data: RatePoint[];
  vencimiento: string | null;  // ISO date or null
  error: string | null;        // null if OK, error message otherwise
}

export interface RatesHistoryResponse {
  caucion_1d: RatePoint[];
  letras: Record<string, LetraResult>;
  fecha_desde: string;
  fecha_hasta: string;
}

// -----------------------------------------------------------------------
// UI-specific types
// -----------------------------------------------------------------------

export type RangeOption = '1M' | '3M' | '6M' | '1Y' | 'custom';

export interface RatesFilters {
  range: RangeOption;
  fechaDesde: string;   // ISO date
  fechaHasta: string;   // ISO date
  letras: string[];     // symbol list e.g. ["S17A6", "S30A6"]
}

/** A single series item for Recharts, keyed by symbol or "caucion_1d" */
export interface ChartDataPoint {
  date: string;
  caucion_1d?: number;
  [letraSymbol: string]: number | string | undefined;
}
