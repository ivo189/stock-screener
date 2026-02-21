import { LineChart, Line, ReferenceLine, ResponsiveContainer, Tooltip } from 'recharts';
import type { WeeklyPrice } from '../../types';

interface Props {
  prices: WeeklyPrice[];
  low52w: number | null;
  maxPct: number;
}

export default function MiniChart({ prices, low52w, maxPct }: Props) {
  if (!prices || prices.length < 4) {
    return <div className="w-24 h-10 bg-slate-700 rounded opacity-30" />;
  }

  const data = prices.slice(-26); // last 26 weeks (6 months)
  const current = data[data.length - 1]?.close;
  const first = data[0]?.close;
  const isUp = current >= first;

  const threshold = low52w ? low52w * (1 + maxPct / 100) : null;

  return (
    <div className="w-24 h-10">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          {low52w && (
            <ReferenceLine
              y={low52w}
              stroke="#10b981"
              strokeDasharray="2 2"
              strokeWidth={1}
            />
          )}
          {threshold && (
            <ReferenceLine
              y={threshold}
              stroke="#f59e0b"
              strokeDasharray="2 2"
              strokeWidth={0.5}
            />
          )}
          <Line
            type="monotone"
            dataKey="close"
            dot={false}
            stroke={isUp ? '#34d399' : '#f87171'}
            strokeWidth={1.5}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              return (
                <div className="bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-white">
                  ${Number(payload[0].value).toFixed(2)}
                </div>
              );
            }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
