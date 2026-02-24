/**
 * Card showing the current state of one bond pair.
 * Expandable: shows control chart, Bollinger stats, and commission P&L breakdown.
 */
import { useState } from 'react';
import { ChevronDown, ChevronUp, AlertTriangle, CheckCircle, Loader2, TrendingDown, TrendingUp, Moon, LogOut } from 'lucide-react';
import type { BondPairState, BondHistoryResponse, CommissionInfo, EodAction } from '../../types/bonds';
import RatioChart from './RatioChart';

interface Props {
  state: BondPairState;
  historyData: BondHistoryResponse | null;
  onOpenOrder: (pairId: string) => void;
  isLoadingHistory: boolean;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ZScoreBadge({ z }: { z: number }) {
  const abs = Math.abs(z);
  const color =
    abs >= 2.5
      ? 'bg-red-500/20 text-red-300 border-red-500/40'
      : abs >= 2.0
      ? 'bg-orange-500/20 text-orange-300 border-orange-500/40'
      : abs >= 1.0
      ? 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40'
      : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-mono ${color}`}>
      z = {z >= 0 ? '+' : ''}{z.toFixed(2)}σ
    </span>
  );
}

function CommissionPanel({ comm, direction }: { comm: CommissionInfo; direction?: string }) {
  const netColor = comm.is_profitable ? 'text-emerald-300' : 'text-red-300';
  const netBg = comm.is_profitable ? 'bg-emerald-900/20 border-emerald-700/30' : 'bg-red-900/20 border-red-700/30';

  return (
    <div className={`rounded-lg border p-3 ${netBg}`}>
      <p className="text-slate-300 text-xs font-medium mb-2 flex items-center gap-1.5">
        {direction === 'LOCAL_CHEAP' ? <TrendingDown size={12} className="text-emerald-400" /> : <TrendingUp size={12} className="text-orange-400" />}
        Análisis de rentabilidad (intradiario)
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
        <div className="bg-slate-800/60 rounded p-1.5">
          <p className="text-slate-500 text-xs">Spread bruto</p>
          <p className="text-white font-mono text-xs mt-0.5">{comm.gross_spread_pct.toFixed(3)}%</p>
        </div>
        <div className="bg-slate-800/60 rounded p-1.5">
          <p className="text-slate-500 text-xs">Comisión total</p>
          <p className="text-red-300 font-mono text-xs mt-0.5">−{comm.roundtrip_cost_pct.toFixed(2)}%</p>
          <p className="text-slate-600 text-xs">round-trip</p>
        </div>
        <div className="bg-slate-800/60 rounded p-1.5">
          <p className="text-slate-500 text-xs">Spread neto</p>
          <p className={`font-mono text-xs mt-0.5 font-semibold ${netColor}`}>
            {comm.net_spread_pct >= 0 ? '+' : ''}{comm.net_spread_pct.toFixed(3)}%
          </p>
        </div>
        <div className="bg-slate-800/60 rounded p-1.5">
          <p className="text-slate-500 text-xs">Breakeven ratio</p>
          <p className="text-slate-200 font-mono text-xs mt-0.5">{comm.breakeven_ratio.toFixed(4)}</p>
        </div>
      </div>
      {!comm.is_profitable && (
        <p className="text-red-400 text-xs mt-2">
          El spread bruto ({comm.gross_spread_pct.toFixed(3)}%) no cubre la comisión ({comm.roundtrip_cost_pct.toFixed(2)}%). Operar con pérdida.
        </p>
      )}
    </div>
  );
}

function formatPrice(v: number | null | undefined) {
  if (v == null) return '—';
  return v.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ---------------------------------------------------------------------------
// Main card
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// EOD banner component
// ---------------------------------------------------------------------------

function EodBanner({ action }: { action: EodAction }) {
  if (action === 'none') return null;

  if (action === 'hold') {
    return (
      <div className="px-4 py-2 bg-blue-900/30 border-t border-blue-500/30 flex items-start gap-2">
        <Moon size={14} className="text-blue-400 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-blue-200 text-xs font-semibold">Cierre próximo — Mantener posición</p>
          <p className="text-blue-300/70 text-xs mt-0.5">
            El desarbitraje persiste (z &gt; 1σ). Conviene mantener la posición overnight — el spread puede cerrar mañana.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 py-2 bg-yellow-900/30 border-t border-yellow-600/30 flex items-start gap-2">
      <LogOut size={14} className="text-yellow-400 flex-shrink-0 mt-0.5" />
      <div>
        <p className="text-yellow-200 text-xs font-semibold">Cierre próximo — Cerrar posición</p>
        <p className="text-yellow-300/70 text-xs mt-0.5">
          El spread convergió (z &lt; 1σ). El arbitraje se realizó — conviene salir antes del cierre.
        </p>
      </div>
    </div>
  );
}

export default function PairCard({ state, historyData, onOpenOrder, isLoadingHistory }: Props) {
  const [expanded, setExpanded] = useState(false);
  const { config, latest, stats, alert, commission, last_fetch_error, eod_signal, eod_action } = state;

  const hasAlert = !!alert;
  const cardBorder = eod_signal
    ? 'border-yellow-500/50'
    : hasAlert
    ? 'border-orange-500/50'
    : last_fetch_error
    ? 'border-red-500/30'
    : 'border-slate-700';

  return (
    <div className={`bg-slate-800 rounded-xl border ${cardBorder} overflow-hidden transition-colors`}>
      {/* Header row */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-slate-700/50 transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-center gap-3 min-w-0">
          {eod_signal ? (
            <AlertTriangle size={16} className="text-yellow-400 flex-shrink-0" />
          ) : hasAlert ? (
            <AlertTriangle size={16} className="text-orange-400 flex-shrink-0" />
          ) : last_fetch_error ? (
            <AlertTriangle size={16} className="text-red-400 flex-shrink-0" />
          ) : (
            <CheckCircle size={16} className="text-emerald-400 flex-shrink-0" />
          )}

          <div className="min-w-0">
            <p className="font-semibold text-white text-sm">{config.label}</p>
            <p className="text-slate-400 text-xs truncate">{config.description}</p>
          </div>
        </div>

        {/* Right side: prices + ratio + z-score */}
        <div className="flex items-center gap-3 flex-shrink-0">
          {latest ? (
            <>
              <div className="text-right hidden sm:block">
                <p className="text-xs text-slate-500">{config.local_symbol}</p>
                <p className="font-mono text-slate-300 text-xs">{formatPrice(latest.local_price)}</p>
              </div>
              <div className="text-right hidden sm:block">
                <p className="text-xs text-slate-500">{config.ny_symbol}</p>
                <p className="font-mono text-slate-300 text-xs">{formatPrice(latest.ny_price)}</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-slate-500">Ratio</p>
                <p className="font-mono text-white text-sm">{latest.ratio.toFixed(4)}</p>
              </div>
              {/* Net spread pill — always visible when we have commission data */}
              {commission && (
                <span className={`hidden sm:inline-flex items-center px-2 py-0.5 rounded border text-xs font-mono ${
                  commission.is_profitable
                    ? 'bg-emerald-500/10 text-emerald-300 border-emerald-600/30'
                    : 'bg-slate-700/50 text-slate-400 border-slate-600/30'
                }`}>
                  {commission.net_spread_pct >= 0 ? '+' : ''}{commission.net_spread_pct.toFixed(2)}% neto
                </span>
              )}
              {stats && <ZScoreBadge z={stats.z_score} />}
            </>
          ) : last_fetch_error ? (
            <span className="text-red-400 text-xs max-w-[180px] truncate">{last_fetch_error}</span>
          ) : (
            <span className="text-slate-500 text-xs">Sin datos</span>
          )}
          {expanded ? (
            <ChevronUp size={16} className="text-slate-400" />
          ) : (
            <ChevronDown size={16} className="text-slate-400" />
          )}
        </div>
      </div>

      {/* EOD banner — smart: hold or close based on z-score */}
      {eod_signal && <EodBanner action={eod_action ?? 'none'} />}

      {/* Alert banner (only when profitable) */}
      {hasAlert && !eod_signal && (
        <div className="px-4 py-2 bg-orange-900/30 border-t border-orange-500/30 flex items-start gap-2">
          <AlertTriangle size={14} className="text-orange-400 flex-shrink-0 mt-0.5" />
          <p className="text-orange-200 text-xs">{alert!.description}</p>
        </div>
      )}

      {/* Expanded section */}
      {expanded && (
        <div className="border-t border-slate-700 px-4 py-4 space-y-4">
          {/* Commission P&L breakdown — shown always */}
          {commission && (
            <CommissionPanel
              comm={commission}
              direction={alert?.direction}
            />
          )}

          {/* Bollinger stats */}
          {stats && (
            <div className="grid grid-cols-3 sm:grid-cols-5 gap-3 text-center">
              {[
                { label: 'Media', value: stats.mean.toFixed(4) },
                { label: 'Desv. Est.', value: stats.std.toFixed(4) },
                { label: '+2σ', value: stats.upper_band.toFixed(4) },
                { label: '−2σ', value: stats.lower_band.toFixed(4) },
                { label: 'Ventana', value: `${stats.window_size} obs.` },
              ].map(({ label, value }) => (
                <div key={label} className="bg-slate-700/50 rounded-lg p-2">
                  <p className="text-slate-400 text-xs">{label}</p>
                  <p className="text-white font-mono text-xs mt-0.5">{value}</p>
                </div>
              ))}
            </div>
          )}

          {/* Chart */}
          <div>
            <p className="text-slate-400 text-xs mb-2">
              Historial de ratio con bandas de Bollinger (±1σ, ±2σ)
            </p>
            {isLoadingHistory ? (
              <div className="flex items-center justify-center h-48 text-slate-500">
                <Loader2 size={20} className="animate-spin" />
              </div>
            ) : historyData ? (
              <RatioChart data={historyData} />
            ) : (
              <div className="flex items-center justify-center h-48 text-slate-500 text-sm">
                Sin historial disponible.
              </div>
            )}
          </div>

          {/* Order button */}
          {latest && (
            <div className="flex justify-end">
              <button
                onClick={(e) => { e.stopPropagation(); onOpenOrder(config.id); }}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
              >
                Simular orden
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
