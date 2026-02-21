import { X } from 'lucide-react';
import { useStockDetail } from '../../hooks/useStockDetail';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  ReferenceArea,
} from 'recharts';
import { formatCurrency, formatPercent, formatNumber, formatMarketCap } from '../../utils/formatters';
import { peColor, cagColor, divColor, proximityColor } from '../../utils/colorScale';

interface Props {
  ticker: string | null;
  onClose: () => void;
}

function Metric({ label, value, color = '' }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-slate-700 rounded-lg p-3">
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className={`text-base font-bold font-mono ${color || 'text-white'}`}>{value}</p>
    </div>
  );
}

export default function StockDetailDrawer({ ticker, onClose }: Props) {
  const { data, isLoading } = useStockDetail(ticker);

  if (!ticker) return null;

  const threshold = data?.price_52w_low
    ? data.price_52w_low * (1 + 0.15)
    : undefined;

  return (
    <div className="fixed inset-0 z-50 flex justify-end" onClick={onClose}>
      <div
        className="w-full max-w-2xl bg-slate-900 border-l border-slate-700 h-full overflow-y-auto shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-slate-900 border-b border-slate-700 px-6 py-4 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold text-white font-mono">{ticker}</h2>
            {data && <p className="text-sm text-slate-400">{data.name}</p>}
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>

        <div className="p-6">
          {isLoading && (
            <p className="text-slate-400 text-center py-8">Loading...</p>
          )}

          {data && (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-6">
                <Metric label="Price" value={formatCurrency(data.current_price)} />
                <Metric
                  label="% above 52w Low"
                  value={data.pct_above_52w_low != null ? `+${data.pct_above_52w_low.toFixed(1)}%` : '—'}
                  color={proximityColor(data.pct_above_52w_low)}
                />
                <Metric label="52w Low" value={formatCurrency(data.price_52w_low)} />
                <Metric label="52w High" value={formatCurrency(data.price_52w_high)} />
                <Metric label="Trailing P/E" value={`${formatNumber(data.trailing_pe, 1)}x`} color={peColor(data.trailing_pe)} />
                <Metric label="Forward P/E" value={`${formatNumber(data.forward_pe, 1)}x`} />
                <Metric label="EPS CAGR (5yr)" value={formatPercent(data.eps_cagr_5y)} color={cagColor(data.eps_cagr_5y)} />
                <Metric label="Dividend Yield" value={formatPercent(data.dividend_yield)} color={divColor(data.dividend_yield)} />
                <Metric label="Beta" value={formatNumber(data.beta)} />
                <Metric label="Market Cap" value={formatMarketCap(data.market_cap)} />
                <Metric label="Volatility (1yr)" value={formatPercent((data.price_volatility_1y ?? 0) * 100, 1)} />
                <Metric label="Sector" value={data.sector ?? '—'} />
              </div>

              {data.weekly_prices.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-300 mb-3">52-Week Price History</h3>
                  <ResponsiveContainer width="100%" height={240}>
                    <LineChart
                      data={data.weekly_prices}
                      margin={{ top: 8, right: 8, bottom: 8, left: 8 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis
                        dataKey="date"
                        tickFormatter={(d) => d.slice(5)}
                        tick={{ fill: '#94a3b8', fontSize: 10 }}
                        interval={7}
                      />
                      <YAxis
                        domain={['auto', 'auto']}
                        tick={{ fill: '#94a3b8', fontSize: 10 }}
                        tickFormatter={(v) => `$${v}`}
                        width={50}
                      />
                      <Tooltip
                        contentStyle={{ background: '#1e293b', border: '1px solid #475569', borderRadius: 6, fontSize: 12 }}
                        formatter={(v) => [`$${(v as number).toFixed(2)}`, 'Close']}
                      />
                      {data.price_52w_low && (
                        <ReferenceLine
                          y={data.price_52w_low}
                          stroke="#10b981"
                          strokeDasharray="4 3"
                          label={{ value: '52w Low', fill: '#10b981', fontSize: 10 }}
                        />
                      )}
                      {threshold && (
                        <ReferenceArea
                          y1={data.price_52w_low!}
                          y2={threshold}
                          fill="#10b981"
                          fillOpacity={0.08}
                        />
                      )}
                      <Line
                        type="monotone"
                        dataKey="close"
                        stroke="#818cf8"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4, fill: '#818cf8' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                  <p className="text-xs text-slate-500 mt-1 text-center">
                    Green zone = within 15% of 52-week low (opportunity zone)
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
