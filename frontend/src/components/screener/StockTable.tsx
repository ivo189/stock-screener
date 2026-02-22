import { ChevronUp, ChevronDown, Plus, Check } from 'lucide-react';
import type { StockSummary, SortColumn } from '../../types';
import { useScreenerStore } from '../../store/screenerStore';
import { formatCurrency, formatPercent, formatNumber, formatMarketCap } from '../../utils/formatters';
import { peColor, cagColor, divColor, proximityColor, qualityBg, maColor } from '../../utils/colorScale';
import MiniChart from './MiniChart';
import { useState } from 'react';
import StockDetailDrawer from './StockDetailDrawer';

interface Col {
  key: SortColumn;
  label: string;
  width?: string;
}

const COLUMNS: Col[] = [
  { key: 'ticker', label: 'Ticker', width: 'w-20' },
  { key: 'name', label: 'Name', width: 'w-40' },
  { key: 'sector', label: 'Sector', width: 'w-36' },
  { key: 'current_price', label: 'Price' },
  { key: 'pct_above_52w_low', label: '% vs 52w Low' },
  { key: 'pct_vs_ma200d', label: '% vs MA200d' },
  { key: 'pct_vs_ma30w', label: '% vs MA30w' },
  { key: 'trailing_pe', label: 'P/E' },
  { key: 'eps_cagr_5y', label: 'EPS CAGR' },
  { key: 'dividend_yield', label: 'Div Yield' },
  { key: 'beta', label: 'Beta' },
  { key: 'market_cap', label: 'Mkt Cap' },
  { key: 'quality_score', label: 'Score' },
];

function SortIcon({ col, active, dir }: { col: string; active: string; dir: 'asc' | 'desc' }) {
  if (col !== active) return <ChevronDown size={12} className="text-slate-600" />;
  return dir === 'desc' ? (
    <ChevronDown size={12} className="text-indigo-400" />
  ) : (
    <ChevronUp size={12} className="text-indigo-400" />
  );
}

interface Props {
  stocks: StockSummary[];
  weeklyPrices?: Record<string, { date: string; close: number }[]>;
}

export default function StockTable({ stocks, weeklyPrices = {} }: Props) {
  const { selectedTickers, toggleTicker, sortColumn, sortDirection, setSort, filters, selectAll, clearSelection } =
    useScreenerStore();
  const [detailTicker, setDetailTicker] = useState<string | null>(null);

  const sorted = [...stocks].sort((a, b) => {
    const aVal = a[sortColumn] as number | string | null;
    const bVal = b[sortColumn] as number | string | null;
    if (aVal == null && bVal == null) return 0;
    if (aVal == null) return 1;
    if (bVal == null) return -1;
    const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
    return sortDirection === 'asc' ? cmp : -cmp;
  });

  const allSelected = sorted.length > 0 && sorted.every((s) => selectedTickers.includes(s.ticker));

  return (
    <>
      <div className="overflow-auto flex-1">
        <table className="w-full text-sm border-collapse min-w-[900px]">
          <thead className="sticky top-0 bg-slate-800 border-b border-slate-700 z-10">
            <tr>
              <th className="px-3 py-2 text-left w-8">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={() =>
                    allSelected ? clearSelection() : selectAll(sorted.map((s) => s.ticker))
                  }
                  className="accent-indigo-500"
                />
              </th>
              <th className="px-3 py-2 text-left w-24 text-xs text-slate-400">Chart</th>
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  onClick={() => setSort(col.key)}
                  className={`px-3 py-2 text-left text-xs text-slate-400 cursor-pointer hover:text-slate-200 transition-colors select-none ${col.width ?? ''}`}
                >
                  <span className="flex items-center gap-1">
                    {col.label}
                    <SortIcon col={col.key} active={sortColumn} dir={sortDirection} />
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((stock) => {
              const selected = selectedTickers.includes(stock.ticker);
              const prices = weeklyPrices[stock.ticker] || [];
              return (
                <tr
                  key={stock.ticker}
                  className={`border-b border-slate-700/50 hover:bg-slate-700/40 transition-colors ${
                    stock.passes_filter ? '' : 'opacity-50'
                  } ${selected ? 'bg-indigo-950/30' : ''}`}
                >
                  <td className="px-3 py-2">
                    <button
                      onClick={() => toggleTicker(stock.ticker)}
                      className={`w-5 h-5 rounded flex items-center justify-center border transition-colors ${
                        selected
                          ? 'bg-indigo-600 border-indigo-500 text-white'
                          : 'border-slate-600 hover:border-indigo-400'
                      }`}
                    >
                      {selected ? <Check size={11} /> : <Plus size={11} className="text-slate-500" />}
                    </button>
                  </td>
                  <td className="px-2 py-1">
                    <MiniChart
                      prices={prices}
                      low52w={stock.price_52w_low}
                      maxPct={filters.max_pct_above_52w_low}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <button
                      onClick={() => setDetailTicker(stock.ticker)}
                      className="font-mono font-bold text-indigo-300 hover:text-indigo-100 transition-colors"
                    >
                      {stock.ticker}
                    </button>
                    <div className="flex gap-1 mt-0.5">
                      {stock.index_membership.map((idx) => (
                        <span key={idx} className="text-[9px] bg-slate-700 text-slate-400 px-1 rounded">
                          {idx}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-slate-300 max-w-[140px] truncate" title={stock.name ?? ''}>
                    {stock.name ?? '—'}
                  </td>
                  <td className="px-3 py-2 text-slate-400 text-xs">{stock.sector ?? '—'}</td>
                  <td className="px-3 py-2 text-slate-200 font-mono">
                    {formatCurrency(stock.current_price)}
                  </td>
                  <td className={`px-3 py-2 font-mono ${proximityColor(stock.pct_above_52w_low)}`}>
                    {stock.pct_above_52w_low != null ? `+${stock.pct_above_52w_low.toFixed(1)}%` : '—'}
                  </td>
                  <td className={`px-3 py-2 font-mono ${maColor(stock.pct_vs_ma200d)}`}>
                    {stock.pct_vs_ma200d != null ? `${stock.pct_vs_ma200d > 0 ? '+' : ''}${stock.pct_vs_ma200d.toFixed(1)}%` : '—'}
                  </td>
                  <td className={`px-3 py-2 font-mono ${maColor(stock.pct_vs_ma30w)}`}>
                    {stock.pct_vs_ma30w != null ? `${stock.pct_vs_ma30w > 0 ? '+' : ''}${stock.pct_vs_ma30w.toFixed(1)}%` : '—'}
                  </td>
                  <td className={`px-3 py-2 font-mono ${peColor(stock.trailing_pe)}`}>
                    {formatNumber(stock.trailing_pe, 1)}x
                  </td>
                  <td className={`px-3 py-2 font-mono ${cagColor(stock.eps_cagr_5y)}`}>
                    {formatPercent(stock.eps_cagr_5y)}
                  </td>
                  <td className={`px-3 py-2 font-mono ${divColor(stock.dividend_yield)}`}>
                    {formatPercent(stock.dividend_yield)}
                  </td>
                  <td className="px-3 py-2 text-slate-300 font-mono">
                    {formatNumber(stock.beta)}
                  </td>
                  <td className="px-3 py-2 text-slate-300 font-mono text-xs">
                    {formatMarketCap(stock.market_cap)}
                  </td>
                  <td className="px-3 py-2">
                    {stock.quality_score != null ? (
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs font-bold text-white ${qualityBg(
                          stock.quality_score
                        )}`}
                      >
                        {stock.quality_score.toFixed(0)}
                      </span>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              );
            })}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={COLUMNS.length + 3} className="text-center py-12 text-slate-500">
                  No stocks match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <StockDetailDrawer ticker={detailTicker} onClose={() => setDetailTicker(null)} />
    </>
  );
}
