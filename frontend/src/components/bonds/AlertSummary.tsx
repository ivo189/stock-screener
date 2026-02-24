/**
 * Top-level alert summary bar: shows active arbitrage opportunities.
 */
import { AlertTriangle, TrendingDown, TrendingUp } from 'lucide-react';
import type { BondPairState } from '../../types/bonds';

interface Props {
  pairs: BondPairState[];
}

export default function AlertSummary({ pairs }: Props) {
  const activeAlerts = pairs.filter((p) => p.alert !== null);

  if (activeAlerts.length === 0) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 bg-emerald-900/20 border border-emerald-700/30 rounded-lg text-emerald-300 text-xs">
        <span className="w-2 h-2 rounded-full bg-emerald-400" />
        Sin anomalías detectadas — todos los ratios dentro de bandas normales.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {activeAlerts.map((p) => {
        const alert = p.alert!;
        const isLocalCheap = alert.direction === 'LOCAL_CHEAP';
        return (
          <div
            key={p.config.id}
            className="flex items-start gap-3 px-4 py-2.5 bg-orange-900/30 border border-orange-500/40 rounded-lg"
          >
            <AlertTriangle size={16} className="text-orange-400 flex-shrink-0 mt-0.5" />
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-orange-200 font-medium text-xs">{alert.pair_label}</span>
                <span className="flex items-center gap-1 text-xs font-mono text-orange-300">
                  {isLocalCheap ? (
                    <TrendingDown size={12} />
                  ) : (
                    <TrendingUp size={12} />
                  )}
                  z = {alert.z_score >= 0 ? '+' : ''}{alert.z_score.toFixed(2)}σ
                </span>
              </div>
              <p className="text-orange-100/70 text-xs mt-0.5">{alert.description}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
