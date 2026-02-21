import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { SectorAllocation } from '../../types';
import { getSectorColor } from '../../utils/colorScale';

interface Props {
  sectors: SectorAllocation[];
}

export default function AllocationChart({ sectors }: Props) {
  const data = sectors.map((s) => ({
    name: s.sector,
    value: Math.round(s.weight * 100 * 10) / 10,
    tickers: s.tickers,
    color: getSectorColor(s.sector),
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={100}
          paddingAngle={2}
          dataKey="value"
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            background: '#1e293b',
            border: '1px solid #475569',
            borderRadius: 6,
            fontSize: 12,
          }}
          formatter={(value, _name, props) => [
            `${(value as number).toFixed(1)}%`,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ((props as any).payload?.tickers as string[] | undefined)?.slice(0, 4).join(', ') ?? '',
          ]}
        />
        <Legend
          formatter={(value) => <span style={{ color: '#94a3b8', fontSize: 11 }}>{value}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
