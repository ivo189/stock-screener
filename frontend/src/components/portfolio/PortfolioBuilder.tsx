import { useState } from 'react';
import { X, BarChart3, AlertTriangle } from 'lucide-react';
import { useScreenerStore } from '../../store/screenerStore';
import { usePortfolio } from '../../hooks/usePortfolio';
import AllocationChart from './AllocationChart';
import MonteCarloChart from './MonteCarloChart';
import { formatCurrency, formatNumber, formatPercent } from '../../utils/formatters';
import { getSectorColor } from '../../utils/colorScale';
import type { WeightingMethod, PortfolioRequest } from '../../types';

const METHODS: { value: WeightingMethod; label: string; desc: string }[] = [
  { value: 'risk_parity', label: 'Risk Parity', desc: 'Inverse volatility weighting' },
  { value: 'equal', label: 'Equal Weight', desc: '1/N for each stock' },
  { value: 'market_cap', label: 'Market Cap', desc: 'Weighted by market cap' },
];

interface Props {
  onClose: () => void;
}

export default function PortfolioBuilder({ onClose }: Props) {
  const { selectedTickers, clearSelection, capital, setCapital, weightingMethod, setWeightingMethod } =
    useScreenerStore();
  const { mutate, isPending, result } = usePortfolio();
  const [localCapital, setLocalCapital] = useState<string>(capital ? String(capital) : '');
  const [mcRequest, setMcRequest] = useState<PortfolioRequest | null>(null);

  const handleBuild = () => {
    const cap = localCapital ? parseFloat(localCapital) : undefined;
    setCapital(cap);
    const req: PortfolioRequest = {
      tickers: selectedTickers,
      total_capital: cap,
      weighting_method: weightingMethod,
    };
    mutate(req);
    setMcRequest(req);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-slate-900 border-b border-slate-700 px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <BarChart3 className="text-indigo-400" size={20} />
            <h2 className="text-lg font-bold text-white">Portfolio Builder</h2>
            <span className="text-sm text-slate-400">({selectedTickers.length} stocks selected)</span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>

        <div className="p-6">
          {/* Configuration */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <label className="text-xs text-slate-400 font-medium block mb-2">
                Capital to invest (USD, optional)
              </label>
              <input
                type="number"
                placeholder="e.g. 50000"
                value={localCapital}
                onChange={(e) => setLocalCapital(e.target.value)}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium mb-2">Weighting Method</p>
              <div className="flex flex-col gap-2">
                {METHODS.map((m) => (
                  <label key={m.value} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="method"
                      value={m.value}
                      checked={weightingMethod === m.value}
                      onChange={() => setWeightingMethod(m.value)}
                      className="accent-indigo-500"
                    />
                    <span className="text-sm text-slate-200">{m.label}</span>
                    <span className="text-xs text-slate-500">— {m.desc}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* Selected tickers */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-slate-400 font-medium">Selected stocks</p>
              <button onClick={clearSelection} className="text-xs text-red-400 hover:text-red-300">
                Clear all
              </button>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {selectedTickers.map((t) => (
                <span key={t} className="bg-indigo-900/60 border border-indigo-700 text-indigo-200 text-xs px-2 py-0.5 rounded font-mono">
                  {t}
                </span>
              ))}
            </div>
          </div>

          <button
            onClick={handleBuild}
            disabled={selectedTickers.length < 2 || isPending}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors mb-6"
          >
            {isPending ? 'Building...' : 'Build Portfolio'}
          </button>

          {/* Results */}
          {result && (
            <div>
              {result.warnings.length > 0 && (
                <div className="flex gap-2 bg-yellow-900/30 border border-yellow-700/50 rounded-lg p-3 mb-4">
                  <AlertTriangle size={14} className="text-yellow-400 shrink-0 mt-0.5" />
                  <div className="text-xs text-yellow-300 space-y-0.5">
                    {result.warnings.map((w, i) => <p key={i}>{w}</p>)}
                  </div>
                </div>
              )}

              {/* Portfolio metrics */}
              <div className="grid grid-cols-3 gap-3 mb-6">
                <div className="bg-slate-800 rounded-lg p-3 text-center">
                  <p className="text-xs text-slate-400 mb-1">Portfolio Beta</p>
                  <p className="text-lg font-bold text-white">{result.portfolio_beta.toFixed(2)}</p>
                </div>
                <div className="bg-slate-800 rounded-lg p-3 text-center">
                  <p className="text-xs text-slate-400 mb-1">Est. Volatility</p>
                  <p className="text-lg font-bold text-white">{formatPercent((result.portfolio_volatility) * 100, 1)}</p>
                </div>
                <div className="bg-slate-800 rounded-lg p-3 text-center">
                  <p className="text-xs text-slate-400 mb-1">Diversification</p>
                  <p className="text-lg font-bold text-emerald-400">{(result.diversification_score * 100).toFixed(0)}%</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                {/* Sector chart */}
                <div>
                  <h3 className="text-sm font-semibold text-slate-300 mb-3">Sector Allocation</h3>
                  <AllocationChart sectors={result.sector_allocations} />
                </div>

                {/* Sector list */}
                <div>
                  <h3 className="text-sm font-semibold text-slate-300 mb-3">By Sector</h3>
                  <div className="space-y-2">
                    {result.sector_allocations.map((sa) => (
                      <div key={sa.sector} className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full shrink-0"
                          style={{ background: getSectorColor(sa.sector) }}
                        />
                        <span className="text-xs text-slate-300 flex-1 truncate">{sa.sector}</span>
                        <span className="text-xs font-mono text-slate-200">{(sa.weight * 100).toFixed(1)}%</span>
                        <span className="text-xs text-slate-500">{sa.tickers.length} stocks</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Positions table */}
              <h3 className="text-sm font-semibold text-slate-300 mb-3">Positions</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-700">
                      {['Ticker', 'Name', 'Sector', 'Weight', 'Price', ...(result.total_capital ? ['Amount', 'Shares'] : []), 'P/E', 'Div %', 'Beta'].map(
                        (h) => (
                          <th key={h} className="px-3 py-2 text-left text-slate-400 font-medium">
                            {h}
                          </th>
                        )
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {result.positions.map((pos) => (
                      <tr key={pos.ticker} className="border-b border-slate-700/40 hover:bg-slate-800/50">
                        <td className="px-3 py-2 font-mono font-bold text-indigo-300">{pos.ticker}</td>
                        <td className="px-3 py-2 text-slate-300 max-w-[120px] truncate">{pos.name ?? '—'}</td>
                        <td className="px-3 py-2 text-slate-400">{pos.sector ?? '—'}</td>
                        <td className="px-3 py-2 font-mono text-white">{(pos.target_weight * 100).toFixed(1)}%</td>
                        <td className="px-3 py-2 font-mono text-slate-200">{formatCurrency(pos.current_price)}</td>
                        {result.total_capital && (
                          <>
                            <td className="px-3 py-2 font-mono text-slate-200">{formatCurrency(pos.target_amount)}</td>
                            <td className="px-3 py-2 font-mono text-slate-200">{pos.target_shares ?? '—'}</td>
                          </>
                        )}
                        <td className="px-3 py-2 font-mono text-slate-300">{formatNumber(pos.trailing_pe, 1)}x</td>
                        <td className="px-3 py-2 font-mono text-slate-300">{formatPercent(pos.dividend_yield)}</td>
                        <td className="px-3 py-2 font-mono text-slate-300">{formatNumber(pos.beta)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Monte Carlo Simulation */}
              {mcRequest && <MonteCarloChart request={mcRequest} />}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
