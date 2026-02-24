import { TrendingUp, RefreshCw, Activity } from 'lucide-react';
import { useUniverseStats, useRefreshTrigger } from '../../hooks/useScreener';
import type { AppTab } from '../../App';

function formatLocalDateTime(isoUtc: string | null | undefined): string {
  if (!isoUtc) return '—';
  try {
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

interface Props {
  activeTab: AppTab;
  onTabChange: (tab: AppTab) => void;
}

const TABS: { id: AppTab; label: string }[] = [
  { id: 'screener', label: 'Screener' },
  { id: 'bonds', label: 'Bonos AR' },
];

export default function Navbar({ activeTab, onTabChange }: Props) {
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
    <nav className="bg-slate-900 border-b border-slate-700 px-4 flex items-stretch justify-between sticky top-0 z-50" style={{ minHeight: 48 }}>
      {/* Left: brand + tabs */}
      <div className="flex items-stretch gap-0">
        {/* Brand */}
        <div className="flex items-center gap-2 pr-4 mr-2 border-r border-slate-700">
          <TrendingUp className="text-indigo-400" size={20} />
          <span className="font-bold text-base text-white tracking-tight hidden sm:block">Screener de Ivo</span>
        </div>

        {/* Navigation tabs */}
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`flex items-center gap-1.5 px-4 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-indigo-400 text-indigo-300'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-500'
            }`}
          >
            {tab.id === 'bonds' && <Activity size={13} />}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Right: status + refresh (screener tab only) */}
      <div className="flex items-center gap-3">
        {activeTab === 'screener' && stats && (
          <div className="hidden md:flex items-center gap-2 text-xs text-slate-400">
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

        {activeTab === 'screener' && (
          <button
            onClick={() => refresh.mutate()}
            disabled={isRunning}
            title="Forzar actualización de datos"
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-slate-200 flex-shrink-0"
          >
            <RefreshCw size={12} className={isRunning ? 'animate-spin' : ''} />
            <span className="hidden sm:inline">Actualizar</span>
          </button>
        )}
      </div>
    </nav>
  );
}
