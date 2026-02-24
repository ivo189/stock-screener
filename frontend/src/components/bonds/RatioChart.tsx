/**
 * Control chart for a single bond pair ratio.
 *
 * Shows up to 14 trading days of history with DYNAMIC (rolling) Bollinger bands:
 * - Each point's mean/±1σ/±2σ is computed from its own rolling window,
 *   so the bands move over time and reflect actual trend.
 * - Falls back to a flat line (last stats) if rolling data is not available.
 */
import { useState } from 'react';
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import type { BondHistoryResponse } from '../../types/bonds';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Props {
  data: BondHistoryResponse;
}

type ViewWindow = '1d' | '5d' | '14d' | 'all';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Label completo para el tooltip: dd/mm HH:MM */
function formatTs(iso: string): string {
  const d = new Date(iso.endsWith('Z') ? iso : iso + 'Z');
  return d.toLocaleString('es-AR', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

/** Label del eje X: siempre dd/mm HH:MM */
function formatXAxis(iso: string): string {
  const d = new Date(iso.endsWith('Z') ? iso : iso + 'Z');
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const hh = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${dd}/${mm} ${hh}:${min}`;
}

// Approx points per window: 4 refreshes/hr × 6h market × trading days
const POINTS_PER_DAY = 24; // 4 × 6
const WINDOW_POINTS: Record<ViewWindow, number> = {
  '1d': POINTS_PER_DAY,
  '5d': POINTS_PER_DAY * 5,
  '14d': POINTS_PER_DAY * 14,
  'all': Infinity,
};

// ---------------------------------------------------------------------------
// Custom tooltip
// ---------------------------------------------------------------------------

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const get = (key: string) => payload.find((p: any) => p.dataKey === key)?.value;
  const ratio = get('ratio');
  const mean = get('mean');
  const u2 = get('upper2');
  const l2 = get('lower2');
  const z = get('z_score');

  return (
    <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 text-xs shadow-xl min-w-[160px]">
      <p className="text-slate-400 mb-2">{label}</p>
      {ratio != null && <p className="text-emerald-300 font-mono">Ratio: {Number(ratio).toFixed(4)}</p>}
      {mean != null && <p className="text-sky-300 font-mono">Media: {Number(mean).toFixed(4)}</p>}
      {u2 != null && <p className="text-blue-400 font-mono">+2σ: {Number(u2).toFixed(4)}</p>}
      {l2 != null && <p className="text-blue-400 font-mono">−2σ: {Number(l2).toFixed(4)}</p>}
      {z != null && (
        <p className={`font-mono mt-1 font-semibold ${Math.abs(Number(z)) >= 2 ? 'text-orange-300' : 'text-slate-300'}`}>
          z: {Number(z) >= 0 ? '+' : ''}{Number(z).toFixed(2)}σ
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main chart
// ---------------------------------------------------------------------------

export default function RatioChart({ data }: Props) {
  const { history, stats } = data;
  const [view, setView] = useState<ViewWindow>('14d');

  // Filter to selected window
  const maxPoints = WINDOW_POINTS[view];
  const sliced = maxPoints === Infinity ? history : history.slice(-maxPoints);

  // Build chart data — use rolling stats from each snapshot if available,
  // fall back to current flat stats for older points without rolling data
  // Mostrar punto en ratio cuando hay <= 80 puntos (vista 1d o 5d con pocos datos)
  const showDots = sliced.length <= 80;

  const chartData = sliced.map((s) => ({
    ts: formatTs(s.timestamp),
    tsAxis: formatXAxis(s.timestamp),
    ratio: s.ratio,
    // Rolling (dynamic) values take priority; fall back to current flat stats
    mean:   s.mean   ?? stats?.mean,
    upper2: s.upper2 ?? stats?.upper_band,
    lower2: s.lower2 ?? stats?.lower_band,
    upper1: s.upper1 ?? stats?.upper_band_1sigma,
    lower1: s.lower1 ?? stats?.lower_band_1sigma,
    z_score: s.z_score,
  }));

  if (chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-500 text-sm">
        Sin datos históricos aún.
      </div>
    );
  }

  // Y axis domain: include all bands with small padding
  const allValues = chartData.flatMap(d => [
    d.ratio,
    d.upper2 ?? d.ratio,
    d.lower2 ?? d.ratio,
  ]).filter(Boolean) as number[];
  const minR = Math.min(...allValues) * 0.998;
  const maxR = Math.max(...allValues) * 1.002;

  return (
    <div className="space-y-2">
      {/* View selector */}
      <div className="flex items-center gap-1 justify-end">
        {(['1d', '5d', '14d', 'all'] as ViewWindow[]).map(w => (
          <button
            key={w}
            onClick={() => setView(w)}
            className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
              view === w
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
            }`}
          >
            {w === 'all' ? 'Todo' : w}
          </button>
        ))}
        <span className="text-slate-600 text-xs ml-2">
          {sliced.length} puntos
        </span>
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />

          <XAxis
            dataKey="tsAxis"
            tick={{ fontSize: 10, fill: '#64748b' }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[minR, maxR]}
            tick={{ fontSize: 10, fill: '#64748b' }}
            tickLine={false}
            tickFormatter={(v) => v.toFixed(4)}
            width={64}
          />

          <Tooltip content={<CustomTooltip />} />

          {/* ±2σ shaded band */}
          <Area
            type="monotone"
            dataKey="upper2"
            stroke="none"
            fill="#1e3a5f"
            fillOpacity={0.35}
            legendType="none"
            isAnimationActive={false}
            connectNulls
          />
          <Area
            type="monotone"
            dataKey="lower2"
            stroke="none"
            fill="#0f172a"
            fillOpacity={0.0}
            legendType="none"
            isAnimationActive={false}
            connectNulls
          />

          {/* ±1σ shaded band */}
          <Area
            type="monotone"
            dataKey="upper1"
            stroke="none"
            fill="#1e3a5f"
            fillOpacity={0.25}
            legendType="none"
            isAnimationActive={false}
            connectNulls
          />
          <Area
            type="monotone"
            dataKey="lower1"
            stroke="none"
            fill="#0f172a"
            fillOpacity={0.0}
            legendType="none"
            isAnimationActive={false}
            connectNulls
          />

          {/* ±2σ band lines (dynamic) */}
          <Line
            type="monotone"
            dataKey="upper2"
            stroke="#3b82f6"
            strokeWidth={1.5}
            dot={false}
            strokeDasharray="4 2"
            name="+2σ"
            isAnimationActive={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="lower2"
            stroke="#3b82f6"
            strokeWidth={1.5}
            dot={false}
            strokeDasharray="4 2"
            name="−2σ"
            isAnimationActive={false}
            connectNulls
          />

          {/* ±1σ band lines (dynamic) */}
          <Line
            type="monotone"
            dataKey="upper1"
            stroke="#6366f1"
            strokeWidth={1}
            dot={false}
            strokeDasharray="2 3"
            name="+1σ"
            isAnimationActive={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="lower1"
            stroke="#6366f1"
            strokeWidth={1}
            dot={false}
            strokeDasharray="2 3"
            name="−1σ"
            isAnimationActive={false}
            connectNulls
          />

          {/* Rolling mean (dynamic) */}
          <Line
            type="monotone"
            dataKey="mean"
            stroke="#38bdf8"
            strokeWidth={1.5}
            dot={false}
            strokeDasharray="6 3"
            name="Media"
            isAnimationActive={false}
            connectNulls
          />

          {/* Ratio line — con puntos cuando hay pocos datos */}
          <Line
            type="monotone"
            dataKey="ratio"
            stroke="#34d399"
            strokeWidth={2}
            dot={showDots ? { r: 3, fill: '#34d399', stroke: '#0f172a', strokeWidth: 1 } : false}
            activeDot={{ r: 5, fill: '#34d399', stroke: '#0f172a', strokeWidth: 1.5 }}
            name="Ratio"
            isAnimationActive={false}
          />

          <Legend
            wrapperStyle={{ fontSize: 11, color: '#64748b', paddingTop: 6 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
