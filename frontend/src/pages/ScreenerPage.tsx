import { useState, useMemo } from 'react';
import FilterPanel from '../components/screener/FilterPanel';
import StockTable from '../components/screener/StockTable';
import LoadingSpinner from '../components/common/LoadingSpinner';
import PortfolioBuilder from '../components/portfolio/PortfolioBuilder';
import { useScreener } from '../hooks/useScreener';
import { useScreenerStore } from '../store/screenerStore';
import { formatAge } from '../utils/formatters';
import { BarChart3, AlertCircle, Info } from 'lucide-react';
import type { WeeklyPrice } from '../types';

export default function ScreenerPage() {
  const { filters, selectedTickers, showOnlyPassing } = useScreenerStore();
  const [showPortfolio, setShowPortfolio] = useState(false);

  const params = {
    universe: filters.universe,
    max_pct_above_52w_low: filters.max_pct_above_52w_low,
    max_trailing_pe: filters.max_trailing_pe,
    min_eps_cagr_5y: filters.min_eps_cagr_5y,
    min_dividend_yield: filters.min_dividend_yield,
    require_both: filters.require_both,
    max_pct_vs_ma200d: filters.enable_ma200d ? filters.max_pct_vs_ma200d : null,
    max_pct_vs_ma30w: filters.enable_ma30w ? filters.max_pct_vs_ma30w : null,
  };

  const { data, isLoading, isError, error, isFetching } = useScreener(params);

  const displayedStocks = useMemo(() => {
    if (!data) return [];
    return showOnlyPassing ? data.results.filter((s) => s.passes_filter) : data.results;
  }, [data, showOnlyPassing]);

  // Build weekly price map from any cached data (via screener results that include it)
  const weeklyPrices: Record<string, WeeklyPrice[]> = {};

  const passCount = data?.passed_count ?? 0;
  const totalCount = data?.total_universe_count ?? 0;

  return (
    <div className="flex h-[calc(100vh-53px)]">
      <FilterPanel passCount={passCount} totalCount={totalCount} />

      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <div className="border-b border-slate-700 px-4 py-2 flex items-center justify-between bg-slate-800/50 shrink-0">
          <div className="flex items-center gap-3">
            {isFetching && !isLoading && (
              <span className="text-xs text-slate-400 animate-pulse">Updating...</span>
            )}
            {data && (
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Info size={12} />
                Data from {formatAge(data.cache_age_seconds)}
              </span>
            )}
          </div>

          {selectedTickers.length >= 2 && (
            <button
              onClick={() => setShowPortfolio(true)}
              className="flex items-center gap-2 px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
            >
              <BarChart3 size={14} />
              Build Portfolio ({selectedTickers.length})
            </button>
          )}
        </div>

        {/* Content */}
        {isLoading ? (
          <LoadingSpinner />
        ) : isError ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-red-400">
            <AlertCircle size={32} />
            <p className="text-sm">{(error as Error).message}</p>
            <p className="text-xs text-slate-500">
              Make sure the backend is running on port 8000.
            </p>
          </div>
        ) : (
          <StockTable stocks={displayedStocks} weeklyPrices={weeklyPrices} />
        )}
      </main>

      {showPortfolio && <PortfolioBuilder onClose={() => setShowPortfolio(false)} />}
    </div>
  );
}
