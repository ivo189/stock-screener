import { TrendingUp, RefreshCw } from 'lucide-react';
import { useUniverseStats, useRefreshTrigger } from '../../hooks/useScreener';

function formatLocalDateTime(isoUtc: string | null | undefined): string {
  if (!isoUtc) return '—';
  try {
    // The backend returns UTC without 'Z', so we append it for correct parsing
    const d = new Date(isoUtc.endsWith('Z') ? isoUtc : isoUtc + 'Z');
    if (isNaN(d.getTime())) return '—';
    return d.toLocaleString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  } catch {
    return '—';
  }
}

export default function Navbar() {
  const { data: stats } = useUniverseStats();
  const refresh = useRefreshTrigger();

  const isRunning = stats?.refresh_running || refresh.isPending;
  const isStale = stats?.is_stale;

  const dotColor = isRunning
    ? 'bg-yellow-400 animate-pulse'
    : isStale
    ? 'bg-red-400'
    : 'bg-emerald-400';

  return (
    <nav className="bg-slate-900 border-b border-slate-700 px-4 py-3 flex items-center justify-between sticky top-0 z-50">
      {/* Left: brand */}
      <div className="flex items-center gap-2">
        <TrendingUp className="text-indigo-400" size={22} />
        <span className="font-bold text-lg text-white tracking-tight">Stock Screener de Ivo</span>
        <span className="text-xs text-slate-400 ml-2 hidden sm:block">S&P 500 · DJIA · Nasdaq 100</span>
      </div>

      {/* Right: status info + refresh button */}
      <div className="flex items-center gap-3">
        {stats && (
          <div className="hidden md:flex items-center gap-2 text-xs text-slate-400">
            {/* Status dot */}
            <span className={`w-2 h-2 rounded-full inline-block flex-shrink-0 ${dotColor}`} />

            {isRunning ? (
              <span className="text-yellow-300">Actualizando datos...</span>
            ) : (
              <div className="flex flex-col items-end gap-0.5 leading-tight">
                <span>
                  <span className="text-slate-500">Actualizado:&nbsp;</span>
                  <span className="text-slate-200">
                    {stats.last_updated_at ? formatLocalDateTime(stats.last_updated_at) : '—'}
                  </span>
                </span>
                <span>
                  <span className="text-slate-500">Próximo auto:&nbsp;</span>
                  <span className="text-slate-200">
                    {formatLocalDateTime(stats.next_refresh_at)}
                  </span>
                </span>
              </div>
            )}
          </div>
        )}

        <button
          onClick={() => refresh.mutate()}
          disabled={isRunning}
          title="Forzar actualización de datos"
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-slate-200 flex-shrink-0"
        >
          <RefreshCw size={12} className={isRunning ? 'animate-spin' : ''} />
          <span className="hidden sm:inline">Actualizar</span>
        </button>
      </div>
    </nav>
  );
}
