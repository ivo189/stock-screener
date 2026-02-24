/**
 * Control chart for a single bond pair ratio.
 * Shows ratio history with Bollinger bands (±1σ and ±2σ) and mean line.
 */
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

interface Props {
  data: BondHistoryResponse;
}

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

// Custom tooltip
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const ratio = payload.find((p: any) => p.dataKey === 'ratio')?.value;
  const mean = payload.find((p: any) => p.dataKey === 'mean')?.value;
  return (
    <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 text-xs shadow-xl">
      <p className="text-slate-400 mb-1">{label}</p>
      {ratio != null && (
        <p className="text-emerald-300 font-mono">Ratio: {Number(ratio).toFixed(4)}</p>
      )}
      {mean != null && (
        <p className="text-sky-300 font-mono">Media: {Number(mean).toFixed(4)}</p>
      )}
    </div>
  );
}

export default function RatioChart({ data }: Props) {
  const { history, stats } = data;

  const chartData = history.map((s) => ({
    ts: formatTs(s.timestamp),
    ratio: s.ratio,
    mean: stats?.mean,
    upper2: stats?.upper_band,
    lower2: stats?.lower_band,
    upper1: stats?.upper_band_1sigma,
    lower1: stats?.lower_band_1sigma,
  }));

  if (chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-500 text-sm">
        Sin datos históricos aún.
      </div>
    );
  }

  const allRatios = history.map((s) => s.ratio);
  const minR = Math.min(...allRatios, stats?.lower_band ?? Infinity) * 0.998;
  const maxR = Math.max(...allRatios, stats?.upper_band ?? -Infinity) * 1.002;

  return (
    <ResponsiveContainer width="100%" height={240}>
      <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />

        <XAxis
          dataKey="ts"
          tick={{ fontSize: 10, fill: '#94a3b8' }}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          domain={[minR, maxR]}
          tick={{ fontSize: 10, fill: '#94a3b8' }}
          tickLine={false}
          tickFormatter={(v) => v.toFixed(4)}
          width={62}
        />

        <Tooltip content={<CustomTooltip />} />

        {/* ±2σ band (outer) */}
        {stats && (
          <Area
            type="monotone"
            dataKey="upper2"
            stroke="none"
            fill="#1e3a5f"
            fillOpacity={0.4}
            legendType="none"
            isAnimationActive={false}
          />
        )}
        {stats && (
          <Area
            type="monotone"
            dataKey="lower2"
            stroke="none"
            fill="#1e3a5f"
            fillOpacity={0}
            legendType="none"
            isAnimationActive={false}
          />
        )}

        {/* ±1σ band (inner) */}
        {stats && (
          <Area
            type="monotone"
            dataKey="upper1"
            stroke="none"
            fill="#1e3a5f"
            fillOpacity={0.3}
            legendType="none"
            isAnimationActive={false}
          />
        )}
        {stats && (
          <Area
            type="monotone"
            dataKey="lower1"
            stroke="none"
            fill="#1e3a5f"
            fillOpacity={0}
            legendType="none"
            isAnimationActive={false}
          />
        )}

        {/* Bollinger band lines */}
        {stats && (
          <Line
            type="monotone"
            dataKey="upper2"
            stroke="#3b82f6"
            strokeWidth={1}
            dot={false}
            strokeDasharray="4 2"
            name="+2σ"
            isAnimationActive={false}
          />
        )}
        {stats && (
          <Line
            type="monotone"
            dataKey="lower2"
            stroke="#3b82f6"
            strokeWidth={1}
            dot={false}
            strokeDasharray="4 2"
            name="−2σ"
            isAnimationActive={false}
          />
        )}

        {/* Mean line */}
        {stats && (
          <Line
            type="monotone"
            dataKey="mean"
            stroke="#38bdf8"
            strokeWidth={1.5}
            dot={false}
            strokeDasharray="6 3"
            name="Media"
            isAnimationActive={false}
          />
        )}

        {/* Actual ratio */}
        <Line
          type="monotone"
          dataKey="ratio"
          stroke="#34d399"
          strokeWidth={2}
          dot={false}
          name="Ratio"
          isAnimationActive={false}
        />

        <Legend
          wrapperStyle={{ fontSize: 11, color: '#94a3b8', paddingTop: 4 }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
