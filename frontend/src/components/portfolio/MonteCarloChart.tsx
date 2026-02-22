import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { runMonteCarlo } from '../../api/portfolio';
import type { PortfolioRequest, MonteCarloResult, SimulationResult } from '../../types';
import { formatCurrency } from '../../utils/formatters';
import { TrendingUp, AlertTriangle } from 'lucide-react';

interface Props {
  request: PortfolioRequest;
}

const WEEK_OPTIONS = [
  { label: '6 meses', weeks: 26 },
  { label: '1 año', weeks: 52 },
  { label: '2 años', weeks: 104 },
  { label: '3 años', weeks: 156 },
];

function StatCard({ label, value, sub = '', color = 'text-white' }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="bg-slate-700 rounded-lg p-3 text-center">
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className={`text-base font-bold font-mono ${color}`}>{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-0.5">{sub}</p>}
    </div>
  );
}

function SimChart({ sim, initialCapital }: { sim: SimulationResult; initialCapital: number }) {
  const chartData = sim.weeks.map((w, i) => ({
    week: w,
    p10: sim.paths.p10[i],
    p25: sim.paths.p25[i],
    p50: sim.paths.p50[i],
    p75: sim.paths.p75[i],
    p90: sim.paths.p90[i],
  }));
  const s = sim.summary;

  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 mb-5">
        <StatCard
          label="Mediana final"
          value={formatCurrency(s.median_final, 0)}
          sub={`${s.annualized_return_median > 0 ? '+' : ''}${s.annualized_return_median.toFixed(1)}% anual`}
          color={s.median_final >= initialCapital ? 'text-emerald-400' : 'text-red-400'}
        />
        <StatCard label="Peor 10%" value={formatCurrency(s.p10_final, 0)} color="text-red-400" />
        <StatCard label="Mejor 10%" value={formatCurrency(s.p90_final, 0)} color="text-emerald-400" />
        <StatCard
          label="Prob. ganancia"
          value={`${s.prob_profit.toFixed(1)}%`}
          color={s.prob_profit >= 60 ? 'text-emerald-400' : s.prob_profit >= 45 ? 'text-yellow-400' : 'text-red-400'}
        />
        <StatCard
          label="Prob. pérdida >20%"
          value={`${s.prob_loss_20pct.toFixed(1)}%`}
          color={s.prob_loss_20pct <= 10 ? 'text-emerald-400' : s.prob_loss_20pct <= 25 ? 'text-yellow-400' : 'text-red-400'}
        />
        <StatCard label="Vol. semanal" value={`${s.sigma_weekly.toFixed(2)}%`} />
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="week" tick={{ fill: '#94a3b8', fontSize: 9 }} interval={Math.floor(chartData.length / 6)} />
          <YAxis
            tick={{ fill: '#94a3b8', fontSize: 10 }}
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
            width={52}
          />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #475569', borderRadius: 6, fontSize: 11 }}
            formatter={(v: number | undefined, name: string | undefined) => [v != null ? formatCurrency(v, 0) : '—', name ?? '']}
          />
          <Legend formatter={(v) => <span style={{ color: '#94a3b8', fontSize: 10 }}>{v}</span>} />
          <ReferenceLine
            y={initialCapital}
            stroke="#64748b"
            strokeDasharray="4 3"
            label={{ value: 'Capital inicial', fill: '#64748b', fontSize: 9 }}
          />
          <Line type="monotone" dataKey="p10" stroke="#ef4444" strokeWidth={1} dot={false} name="P10 (peor 10%)" strokeDasharray="3 2" />
          <Line type="monotone" dataKey="p25" stroke="#f97316" strokeWidth={1} dot={false} name="P25" strokeDasharray="2 2" />
          <Line type="monotone" dataKey="p50" stroke="#818cf8" strokeWidth={2.5} dot={false} name="Mediana (P50)" />
          <Line type="monotone" dataKey="p75" stroke="#34d399" strokeWidth={1} dot={false} name="P75" strokeDasharray="2 2" />
          <Line type="monotone" dataKey="p90" stroke="#10b981" strokeWidth={1} dot={false} name="P90 (mejor 10%)" strokeDasharray="3 2" />
        </LineChart>
      </ResponsiveContainer>
    </>
  );
}

export default function MonteCarloChart({ request }: Props) {
  const [nWeeks, setNWeeks] = useState(52);
  const [result, setResult] = useState<MonteCarloResult | null>(null);
  const [activeTab, setActiveTab] = useState<'mc' | 'bootstrap'>('mc');

  const { mutate, isPending, isError, error } = useMutation({
    mutationFn: () => runMonteCarlo(request, nWeeks),
    onSuccess: (data) => setResult(data),
  });

  const activeSim: SimulationResult | null = result
    ? activeTab === 'mc'
      ? (result.monte_carlo ?? { weeks: result.weeks, paths: result.paths, initial_capital: result.initial_capital, summary: result.summary })
      : (result.bootstrap ?? null)
    : null;

  return (
    <div className="mt-6 border-t border-slate-700 pt-6">
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp className="text-indigo-400" size={18} />
        <h3 className="text-sm font-semibold text-white">Simulación de Escenarios</h3>
        <span className="text-xs text-slate-500">(500 escenarios · retornos totales con dividendos)</span>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <p className="text-xs text-slate-400">Horizonte:</p>
        {WEEK_OPTIONS.map((opt) => (
          <button
            key={opt.weeks}
            onClick={() => { setNWeeks(opt.weeks); setResult(null); }}
            className={`text-xs px-3 py-1 rounded-md border transition-colors ${
              nWeeks === opt.weeks
                ? 'bg-indigo-600 border-indigo-500 text-white'
                : 'bg-slate-700 border-slate-600 text-slate-400 hover:border-indigo-500'
            }`}
          >
            {opt.label}
          </button>
        ))}
        <button
          onClick={() => mutate()}
          disabled={isPending}
          className="ml-auto text-xs px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-md transition-colors font-medium"
        >
          {isPending ? 'Simulando...' : result ? 'Re-simular' : 'Simular'}
        </button>
      </div>

      {isError && (
        <div className="flex gap-2 bg-red-900/30 border border-red-700/50 rounded-lg p-3 mb-4 text-xs text-red-300">
          <AlertTriangle size={14} className="shrink-0 mt-0.5" />
          {(error as Error).message}
        </div>
      )}

      {!result && !isPending && (
        <p className="text-xs text-slate-500 text-center py-8">
          Presioná "Simular" para proyectar la evolución del patrimonio basándose en retornos históricos con dividendos reinvertidos.
        </p>
      )}

      {isPending && (
        <div className="flex items-center justify-center py-12 gap-3">
          <div className="w-6 h-6 border-2 border-slate-600 border-t-indigo-400 rounded-full animate-spin" />
          <p className="text-xs text-slate-400">Corriendo 500 simulaciones...</p>
        </div>
      )}

      {result && activeSim && (
        <>
          {/* Method tabs */}
          <div className="flex gap-1 mb-5 border-b border-slate-700">
            <button
              onClick={() => setActiveTab('mc')}
              className={`text-xs px-4 py-2 font-medium transition-colors border-b-2 -mb-px ${
                activeTab === 'mc'
                  ? 'border-indigo-500 text-indigo-300'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Monte Carlo
              <span className="ml-1.5 text-slate-500 font-normal">distribución normal</span>
            </button>
            <button
              onClick={() => setActiveTab('bootstrap')}
              className={`text-xs px-4 py-2 font-medium transition-colors border-b-2 -mb-px ${
                activeTab === 'bootstrap'
                  ? 'border-emerald-500 text-emerald-300'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Bootstrap Histórico
              <span className="ml-1.5 text-slate-500 font-normal">retornos reales</span>
            </button>
          </div>

          <SimChart sim={activeSim} initialCapital={result.initial_capital} />

          <p className="text-xs text-slate-500 mt-3 text-center">
            {activeTab === 'mc'
              ? 'Monte Carlo paramétrico: asume retornos con distribución normal. Incluye dividendos reinvertidos.'
              : 'Bootstrap histórico: resamplea retornos reales. Captura colas gordas y asimetrías del mercado. Incluye dividendos reinvertidos.'}
            {' '}No es predicción. Resultados pasados no garantizan rendimientos futuros.
          </p>
        </>
      )}
    </div>
  );
}
