import { TrendingUp, RefreshCw } from 'lucide-react';
import { useUniverseStats, useRefreshTrigger } from '../../hooks/useScreener';
import { formatAge } from '../../utils/formatters';

export default function Navbar() {
  const { data: stats } = useUniverseStats();
  const refresh = useRefreshTrigger();

  const isStale = stats?.is_stale;
  const isRunning = stats?.refresh_running || refresh.isPending;

  return (
    <nav className="bg-slate-900 border-b border-slate-700 px-4 py-3 flex items-center justify-between sticky top-0 z-50">
      <div className="flex items-center gap-2">
        <TrendingUp className="text-indigo-400" size={22} />
        <span className="font-bold text-lg text-white tracking-tight">Stock Screener de Ivo</span>
        <span className="text-xs text-slate-400 ml-2 hidden sm:block">S&P 500 · DJIA · Nasdaq 100</span>
      </div>

      <div className="flex items-center gap-4">
        {stats && (
          <div className="text-xs text-slate-400 hidden md:flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full inline-block ${
                isRunning ? 'bg-yellow-400 animate-pulse' : isStale ? 'bg-red-400' : 'bg-emerald-400'
              }`}
            />
            {isRunning
              ? 'Updating data...'
              : `${stats.total_tickers} tickers · ${formatAge(stats.cache_age_seconds)}`}
          </div>
        )}
        <button
          onClick={() => refresh.mutate()}
          disabled={isRunning}
          title="Trigger data refresh"
          className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-md bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-slate-200"
        >
          <RefreshCw size={12} className={isRunning ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>
    </nav>
  );
}
