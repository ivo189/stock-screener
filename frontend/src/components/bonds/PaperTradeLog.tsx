/**
 * Paper Trade Log — shows open positions and closed trades with P&L.
 * Trades are opened/closed automatically by the backend on each refresh.
 */
import { useQuery } from '@tanstack/react-query';
import { TrendingUp, TrendingDown, Clock, CheckCircle, BarChart2, RefreshCw } from 'lucide-react';
import { fetchPaperTrades } from '../../api/bonds';
import type { PaperTrade, PaperTradeStats } from '../../types/bonds';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmt(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso.endsWith('Z') ? iso : iso + 'Z');
  return d.toLocaleString('es-AR', {
    day: '2-digit', month: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  });
}

function fmtPct(v: number | null | undefined, decimals = 3): string {
  if (v == null) return '—';
  return `${v >= 0 ? '+' : ''}${(v * 100).toFixed(decimals)}%`;
}

function fmtArs(v: number | null | undefined): string {
  if (v == null) return '—';
  return (v >= 0 ? '+' : '') + v.toLocaleString('es-AR', {
    style: 'currency', currency: 'ARS', minimumFractionDigits: 0, maximumFractionDigits: 0,
  });
}

function durationStr(openedAt: string, closedAt: string | null): string {
  const open = new Date(openedAt.endsWith('Z') ? openedAt : openedAt + 'Z');
  const close = closedAt ? new Date(closedAt.endsWith('Z') ? closedAt : closedAt + 'Z') : new Date();
  const hours = (close.getTime() - open.getTime()) / 3_600_000;
  if (hours < 1) return `${Math.round(hours * 60)}m`;
  if (hours < 24) return `${hours.toFixed(1)}h`;
  return `${(hours / 24).toFixed(1)}d`;
}

function closeReasonLabel(reason: string | null): string {
  if (reason === 'convergence') return 'Convergencia';
  if (reason === 'eod_close') return 'Cierre EOD';
  if (reason === 'manual') return 'Manual';
  return reason ?? '—';
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatsBar({ stats }: { stats: PaperTradeStats; notional: number }) {
  const netColor = stats.total_net_pnl_ars >= 0 ? 'text-emerald-400' : 'text-red-400';
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 text-center">
      {[
        { label: 'Trades', value: stats.total_trades.toString() },
        { label: 'Win rate', value: `${stats.win_rate_pct.toFixed(0)}%` },
        { label: 'Ganadoras', value: stats.winning_trades.toString(), color: 'text-emerald-400' },
        { label: 'Perdedoras', value: stats.losing_trades.toString(), color: 'text-red-400' },
        { label: 'P&L bruto promedio', value: fmtPct(stats.avg_gross_pnl_pct / 100, 3) },
        { label: 'P&L neto promedio', value: fmtPct(stats.avg_net_pnl_pct / 100, 3) },
        { label: 'P&L neto total', value: fmtArs(stats.total_net_pnl_ars), color: netColor },
        { label: 'Duración media', value: `${stats.avg_duration_hours.toFixed(1)}h` },
      ].map(({ label, value, color }) => (
        <div key={label} className="bg-slate-700/50 rounded-lg p-2">
          <p className="text-slate-400 text-xs">{label}</p>
          <p className={`font-mono text-xs font-semibold mt-0.5 ${color ?? 'text-white'}`}>{value}</p>
        </div>
      ))}
    </div>
  );
}

function SlippageBadge({ slippage }: { slippage: number | null }) {
  if (slippage == null) return <span className="text-slate-600">—</span>;
  const pct = slippage * 100;
  const color = pct >= 0 ? 'text-emerald-400' : 'text-red-400';
  return (
    <span className={`font-mono ${color}`} title="Slippage vs. último precio">
      {pct >= 0 ? '+' : ''}{pct.toFixed(3)}%
    </span>
  );
}

function ExecRatioBadge({ execRatio, lastRatio }: { execRatio: number | null; lastRatio: number }) {
  if (execRatio == null) return <span className="text-slate-400 font-mono">{lastRatio.toFixed(4)}</span>;
  return (
    <span className="font-mono text-slate-200" title={`Ratio ejecutado con puntas (bid/ask). Último: ${lastRatio.toFixed(4)}`}>
      {execRatio.toFixed(4)}
    </span>
  );
}

function TradeRow({ trade, isOpen }: { trade: PaperTrade; isOpen: boolean }) {
  const isWin = (trade.net_pnl_ars ?? 0) >= 0;
  const netColor = isOpen ? 'text-slate-400' : isWin ? 'text-emerald-400' : 'text-red-400';
  const dirIcon = trade.direction === 'LOCAL_CHEAP'
    ? <TrendingDown size={12} className="text-emerald-400 flex-shrink-0" />
    : <TrendingUp size={12} className="text-orange-400 flex-shrink-0" />;
  const dirLabel = trade.direction === 'LOCAL_CHEAP' ? 'Local barato' : 'NY barato';

  // Show exec ratio when available; otherwise fall back to last price
  const hasExecOpen  = trade.open_exec_ratio  != null;
  const hasExecClose = trade.close_exec_ratio != null;

  return (
    <tr className="border-t border-slate-700/50 hover:bg-slate-700/20 transition-colors">
      <td className="px-3 py-2 text-xs text-slate-300 font-medium">{trade.pair_label}</td>
      <td className="px-3 py-2">
        <span className="flex items-center gap-1 text-xs text-slate-400">
          {dirIcon}{dirLabel}
        </span>
      </td>
      {/* Entrada: ratio último + exec + slippage */}
      <td className="px-3 py-2 text-xs">
        <div className="flex flex-col gap-0.5">
          <ExecRatioBadge execRatio={trade.open_exec_ratio} lastRatio={trade.open_ratio} />
          {hasExecOpen && (
            <span className="text-slate-500 font-mono text-[10px]">
              último: {trade.open_ratio.toFixed(4)}
            </span>
          )}
        </div>
      </td>
      <td className="px-3 py-2 text-xs font-mono text-slate-400">
        {trade.open_z_score >= 0 ? '+' : ''}{trade.open_z_score.toFixed(2)}σ
      </td>
      {/* Slippage entrada */}
      <td className="px-3 py-2 text-xs">
        <SlippageBadge slippage={trade.open_slippage_pct} />
      </td>
      <td className="px-3 py-2 text-xs text-slate-400">{fmt(trade.opened_at)}</td>
      {/* Salida: ratio último + exec + slippage */}
      <td className="px-3 py-2 text-xs">
        {trade.close_ratio != null ? (
          <div className="flex flex-col gap-0.5">
            <ExecRatioBadge execRatio={trade.close_exec_ratio} lastRatio={trade.close_ratio} />
            {hasExecClose && (
              <span className="text-slate-500 font-mono text-[10px]">
                último: {trade.close_ratio.toFixed(4)}
              </span>
            )}
          </div>
        ) : '—'}
      </td>
      {/* Slippage salida */}
      <td className="px-3 py-2 text-xs">
        {!isOpen && trade.close_slippage_pct != null
          ? <SlippageBadge slippage={trade.close_slippage_pct} />
          : <span className="text-slate-600">—</span>
        }
      </td>
      <td className="px-3 py-2 text-xs text-slate-400">
        {isOpen ? (
          <span className="flex items-center gap-1 text-sky-400">
            <Clock size={11} /> Abierto · {durationStr(trade.opened_at, null)}
          </span>
        ) : (
          <span className="text-slate-500">{closeReasonLabel(trade.close_reason)}</span>
        )}
      </td>
      <td className="px-3 py-2 text-xs font-mono text-slate-400">
        {isOpen ? '—' : fmtPct(trade.gross_pnl_pct)}
      </td>
      <td className={`px-3 py-2 text-xs font-mono font-semibold ${netColor}`}>
        {isOpen ? '—' : fmtArs(trade.net_pnl_ars)}
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function PaperTradeLog() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['paperTrades'],
    queryFn: () => fetchPaperTrades(100),
    refetchInterval: 5 * 60 * 1000,
    refetchIntervalInBackground: true,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 gap-2 text-slate-400">
        <RefreshCw size={16} className="animate-spin" />
        <span className="text-sm">Cargando paper trades...</span>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="text-center py-12 text-slate-500 text-sm">
        No se pudo cargar el registro de paper trades.
      </div>
    );
  }

  const { open_trades, closed_trades, stats, notional_ars } = data;
  const allEmpty = open_trades.length === 0 && closed_trades.length === 0;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <BarChart2 size={14} className="text-indigo-400" />
        <h2 className="text-slate-300 text-xs font-medium uppercase tracking-wider">
          Paper Trading — Registro automático
        </h2>
        <span className="text-slate-500 text-xs font-normal normal-case tracking-normal">
          · Nocional ARS {notional_ars.toLocaleString('es-AR')} por trade
        </span>
      </div>

      {/* Stats bar */}
      {stats && (
        <div>
          <p className="text-slate-500 text-xs mb-2">Estadísticas acumuladas ({stats.total_trades} trades cerrados)</p>
          <StatsBar stats={stats} notional={notional_ars} />
        </div>
      )}

      {/* Metodología */}
      <div className="rounded-lg bg-slate-800/50 border border-slate-700/60 px-4 py-3 text-xs text-slate-400 space-y-1">
        <p className="text-slate-300 font-medium">Metodología de ejecución</p>
        <p>• <span className="text-slate-200">Ratio entrada/salida</span>: precio ejecutado usando <span className="text-yellow-300">puntas reales (bid/ask)</span> de IOL, no el último precio.</p>
        <p>• <span className="text-slate-200">Slippage</span>: diferencia entre el último precio y el precio de punta. Negativo = pagamos más / recibimos menos que el último.</p>
        <p>• <span className="text-slate-200">P&L calculado sobre exec ratios</span>. Si puntas no disponibles, se usa último precio como fallback.</p>
        <p className="text-slate-500">Señal de apertura: |z| ≥ {'>'}1σ · Señal de cierre: |z| ≤ 0.5σ · Nocional: ARS 100.000 por trade.</p>
      </div>

      {allEmpty && (
        <div className="text-center py-10 text-slate-500 text-sm">
          <p>Sin trades registrados aún.</p>
          <p className="text-xs mt-1 text-slate-600">
            Los trades se abren automáticamente cuando el z-score supera {'>'}1σ y se cierran al volver a ±0.5σ.
          </p>
        </div>
      )}

      {/* Open positions */}
      {open_trades.length > 0 && (
        <div>
          <p className="text-sky-400 text-xs font-medium mb-2 flex items-center gap-1.5">
            <Clock size={12} />
            Posiciones abiertas ({open_trades.length})
          </p>
          <div className="overflow-x-auto rounded-lg border border-slate-700">
            <TradeTable trades={open_trades} isOpen />
          </div>
        </div>
      )}

      {/* Closed trades */}
      {closed_trades.length > 0 && (
        <div>
          <p className="text-slate-400 text-xs font-medium mb-2 flex items-center gap-1.5">
            <CheckCircle size={12} />
            Trades cerrados ({closed_trades.length})
          </p>
          <div className="overflow-x-auto rounded-lg border border-slate-700">
            <TradeTable trades={closed_trades} isOpen={false} />
          </div>
        </div>
      )}
    </div>
  );
}

function TradeTable({ trades, isOpen }: { trades: PaperTrade[]; isOpen: boolean }) {
  const headers = [
    'Par',
    'Dirección',
    'Entrada (exec)',
    'Z entrada',
    'Slip. entrada',
    'Apertura',
    'Salida (exec)',
    'Slip. salida',
    isOpen ? 'Estado' : 'Cierre',
    'P&L bruto',
    'P&L neto (ARS)',
  ];
  return (
    <table className="w-full text-left">
      <thead>
        <tr className="bg-slate-800/80">
          {headers.map(h => (
            <th key={h} className="px-3 py-2 text-xs text-slate-500 font-medium whitespace-nowrap">{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {trades.map(t => <TradeRow key={t.id} trade={t} isOpen={isOpen} />)}
      </tbody>
    </table>
  );
}
