/**
 * Bond Arbitrage Monitor page — intraday edition.
 *
 * Polls every 5 min. Shows market status, EOD signal, per-pair cards
 * with commission-aware P&L, control charts, and sandbox order panel.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Activity,
  RefreshCw,
  Shield,
  AlertTriangle,
  Wifi,
  WifiOff,
  Clock,
  Moon,
} from 'lucide-react';
import { fetchBondsStatus, fetchPairHistory, triggerBondRefresh } from '../api/bonds';
import type { BondPairState } from '../types/bonds';
import PairCard from '../components/bonds/PairCard';
import AlertSummary from '../components/bonds/AlertSummary';
import OrderPanel from '../components/bonds/OrderPanel';

const POLL_INTERVAL_MS = 5 * 60 * 1000;

function formatLocalTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso.endsWith('Z') ? iso : iso + 'Z');
    if (isNaN(d.getTime())) return '—';
    return d.toLocaleString('es-AR', {
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

export default function BondMonitorPage() {
  const queryClient = useQueryClient();
  const [orderPairId, setOrderPairId] = useState<string | null>(null);
  const [expandedPairId, setExpandedPairId] = useState<string | null>(null);

  const {
    data: status,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['bondsStatus'],
    queryFn: fetchBondsStatus,
    refetchInterval: POLL_INTERVAL_MS,
    refetchIntervalInBackground: true,
  });

  const { data: historyData, isLoading: isLoadingHistory } = useQuery({
    queryKey: ['bondHistory', expandedPairId],
    queryFn: () => fetchPairHistory(expandedPairId!, 200),
    enabled: !!expandedPairId,
    staleTime: 2 * 60 * 1000,
  });

  const refreshMutation = useMutation({
    mutationFn: triggerBondRefresh,
    onSuccess: () => {
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['bondsStatus'] });
        if (expandedPairId) {
          queryClient.invalidateQueries({ queryKey: ['bondHistory', expandedPairId] });
        }
      }, 3000);
    },
  });

  const isRefreshing = status?.refresh_running || refreshMutation.isPending;
  const activeAlerts = (status?.pairs ?? []).filter((p) => p.alert !== null).length;

  const orderPairState = orderPairId
    ? status?.pairs.find((p) => p.config.id === orderPairId) ?? null
    : null;

  function handleToggleExpand(pairId: string) {
    setExpandedPairId((current) => (current === pairId ? null : pairId));
  }

  return (
    <div className="flex-1 overflow-y-auto">
      {/* Page header */}
      <div className="sticky top-0 z-10 bg-slate-900 border-b border-slate-700 px-6 py-3">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <Activity size={18} className="text-indigo-400" />
            <div>
              <h1 className="text-white font-semibold text-sm">Monitor de Arbitraje — Bonos Soberanos AR</h1>
              <p className="text-slate-400 text-xs">
                Ley local vs Ley Nueva York · Actualización cada 15 min en horario de mercado (11:00–17:00 ART)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Market status */}
            {status && (
              <div className="flex items-center gap-1.5 text-xs">
                {status.eod_signal ? (
                  <>
                    <Moon size={12} className="text-yellow-400" />
                    <span className="text-yellow-400 font-medium">Cierre próximo — ir a cash</span>
                  </>
                ) : status.market_open ? (
                  <>
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="text-emerald-400">Mercado abierto</span>
                  </>
                ) : (
                  <>
                    <Clock size={12} className="text-slate-500" />
                    <span className="text-slate-500">Mercado cerrado</span>
                  </>
                )}
              </div>
            )}

            {/* IOL auth */}
            {status && (
              <div className="flex items-center gap-1.5 text-xs">
                {status.iol_authenticated ? (
                  <>
                    <Wifi size={12} className="text-emerald-400" />
                    <span className="text-emerald-400 hidden sm:inline">IOL conectado</span>
                  </>
                ) : (
                  <>
                    <WifiOff size={12} className="text-red-400" />
                    <span className="text-red-400 hidden sm:inline">IOL sin autenticar</span>
                  </>
                )}
              </div>
            )}

            {/* Timestamps */}
            {status && (
              <div className="hidden md:flex flex-col items-end text-xs text-slate-400 leading-tight">
                <span>
                  <span className="text-slate-500">Última:&nbsp;</span>
                  <span className="text-slate-200">{formatLocalTime(status.last_refresh_at)}</span>
                </span>
              </div>
            )}

            <button
              onClick={() => refreshMutation.mutate()}
              disabled={isRefreshing}
              title="Forzar actualización de precios IOL"
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-slate-200"
            >
              <RefreshCw size={12} className={isRefreshing ? 'animate-spin' : ''} />
              <span className="hidden sm:inline">Actualizar</span>
            </button>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="px-6 py-6 max-w-5xl mx-auto space-y-5">
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-20 gap-3 text-slate-400">
            <RefreshCw size={28} className="animate-spin" />
            <p className="text-sm">Cargando datos de bonos...</p>
          </div>
        )}

        {isError && (
          <div className="flex flex-col items-center justify-center py-20 gap-3 text-red-400">
            <AlertTriangle size={28} />
            <p className="text-sm">{(error as Error).message}</p>
            <p className="text-xs text-slate-500">
              Verificá que el backend esté corriendo y que las credenciales de IOL estén configuradas en .env
            </p>
          </div>
        )}

        {status && (
          <>
            {/* Global EOD banner */}
            {status.eod_signal && (
              <div className="flex items-center gap-3 px-4 py-3 bg-yellow-900/30 border border-yellow-600/40 rounded-lg">
                <Moon size={18} className="text-yellow-400 flex-shrink-0" />
                <div>
                  <p className="text-yellow-200 text-sm font-semibold">Señal de cierre diario activa</p>
                  <p className="text-yellow-300/70 text-xs mt-0.5">
                    El mercado cierra en menos de 10 minutos. Liquidar todas las posiciones abiertas y volver a cash.
                  </p>
                </div>
              </div>
            )}

            {/* Commission config info */}
            <div className="flex items-center gap-2 px-3 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-xs text-slate-400">
              <Shield size={12} className="flex-shrink-0" />
              <span>
                Costo round-trip total:{' '}
                <span className="text-orange-300 font-medium">{(status.commission_rate * 100).toFixed(2)}%</span>
                {' · '}
                Las alertas se disparan por z-score — la comisión se muestra como referencia
                {' · '}
                <span className="text-slate-500">Configurable en .env (IOL_ROUNDTRIP_COMMISSION)</span>
              </span>
            </div>

            {/* Alert summary */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Shield size={13} className="text-slate-400" />
                <h2 className="text-slate-300 text-xs font-medium uppercase tracking-wider">
                  Estado del monitor
                  {activeAlerts > 0 && (
                    <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-300 text-xs font-normal normal-case tracking-normal">
                      {activeAlerts} {activeAlerts === 1 ? 'alerta rentable' : 'alertas rentables'}
                    </span>
                  )}
                </h2>
              </div>
              <AlertSummary pairs={status.pairs} />
            </div>

            {/* Pair cards */}
            <div>
              <h2 className="text-slate-300 text-xs font-medium uppercase tracking-wider mb-3 flex items-center gap-2">
                <Activity size={13} className="text-slate-400" />
                Pares monitoreados ({status.pairs.length})
              </h2>
              <div className="space-y-3">
                {status.pairs.map((pairState: BondPairState) => (
                  <div
                    key={pairState.config.id}
                    onClick={() => handleToggleExpand(pairState.config.id)}
                  >
                    <PairCard
                      state={pairState}
                      historyData={
                        expandedPairId === pairState.config.id ? historyData ?? null : null
                      }
                      onOpenOrder={(id) => { setOrderPairId(id); }}
                      isLoadingHistory={
                        expandedPairId === pairState.config.id && isLoadingHistory
                      }
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Legend */}
            <div className="bg-slate-800/50 rounded-lg px-4 py-3 border border-slate-700 text-xs text-slate-400 space-y-1">
              <p className="font-medium text-slate-300">Guía de lectura</p>
              <p>• <span className="text-emerald-400">Línea verde</span>: ratio actual (precio ley local / precio ley NY)</p>
              <p>• <span className="text-sky-400">Línea azul punteada</span>: media móvil (ventana 20 períodos de 15 min)</p>
              <p>• <span className="text-blue-400">Bandas ±2σ</span>: zona de alerta estadística</p>
              <p>• <span className="text-orange-300">Alerta</span>: z-score ≥ 2.0 (anomalía estadística) — la comisión se muestra como referencia</p>
              <p>• <span className="text-yellow-400">Señal EOD</span>: 10 min antes del cierre → liquidar posiciones</p>
            </div>
          </>
        )}
      </div>

      {/* Order modal */}
      {orderPairState && (
        <OrderPanel
          pairState={orderPairState}
          onClose={() => setOrderPairId(null)}
        />
      )}
    </div>
  );
}
