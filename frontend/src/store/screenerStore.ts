import { create } from 'zustand';
import type { SortColumn, SortDirection, WeightingMethod } from '../types';

export interface FilterState {
  universe: string[];
  max_pct_above_52w_low: number;
  max_trailing_pe: number;
  min_eps_cagr_5y: number;
  min_dividend_yield: number;
  require_both: boolean;
  // Moving average filters (null = disabled)
  enable_ma200d: boolean;
  max_pct_vs_ma200d: number;   // e.g. -10 means must be ≥10% below MA200
  enable_ma30w: boolean;
  max_pct_vs_ma30w: number;
}

const DEFAULT_FILTERS: FilterState = {
  universe: ['SP500', 'DJIA'],
  max_pct_above_52w_low: 15,
  max_trailing_pe: 20,
  min_eps_cagr_5y: 5,
  min_dividend_yield: 2,
  require_both: false,
  enable_ma200d: false,
  max_pct_vs_ma200d: -5,
  enable_ma30w: false,
  max_pct_vs_ma30w: -5,
};

interface ScreenerStore {
  filters: FilterState;
  selectedTickers: string[];
  sortColumn: SortColumn;
  sortDirection: SortDirection;
  showOnlyPassing: boolean;

  // Portfolio builder
  capital: number | undefined;
  weightingMethod: WeightingMethod;

  // Actions
  updateFilter: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
  resetFilters: () => void;
  toggleTicker: (ticker: string) => void;
  clearSelection: () => void;
  selectAll: (tickers: string[]) => void;
  setSort: (column: SortColumn) => void;
  setShowOnlyPassing: (v: boolean) => void;
  setCapital: (v: number | undefined) => void;
  setWeightingMethod: (v: WeightingMethod) => void;
}

export const useScreenerStore = create<ScreenerStore>((set) => ({
  filters: { ...DEFAULT_FILTERS },
  selectedTickers: [],
  sortColumn: 'quality_score' as SortColumn,
  sortDirection: 'desc',
  showOnlyPassing: true,
  capital: undefined,
  weightingMethod: 'risk_parity',

  updateFilter: (key, value) =>
    set((s) => ({ filters: { ...s.filters, [key]: value } })),

  resetFilters: () => set({ filters: { ...DEFAULT_FILTERS } }),

  toggleTicker: (ticker) =>
    set((s) => {
      const sel = new Set(s.selectedTickers);
      if (sel.has(ticker)) sel.delete(ticker);
      else sel.add(ticker);
      return { selectedTickers: Array.from(sel) };
    }),

  clearSelection: () => set({ selectedTickers: [] }),

  selectAll: (tickers) => set({ selectedTickers: tickers }),

  setSort: (column) =>
    set((s) => ({
      sortColumn: column,
      sortDirection:
        s.sortColumn === column && s.sortDirection === 'desc' ? 'asc' : 'desc',
    })),

  setShowOnlyPassing: (v) => set({ showOnlyPassing: v }),
  setCapital: (v) => set({ capital: v }),
  setWeightingMethod: (v) => set({ weightingMethod: v }),
}));
