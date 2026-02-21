import { useScreenerStore } from '../../store/screenerStore';

interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit?: string;
  onChange: (v: number) => void;
}

function Slider({ label, value, min, max, step, unit = '', onChange }: SliderProps) {
  return (
    <div className="mb-4">
      <div className="flex justify-between items-center mb-1">
        <label className="text-xs text-slate-300 font-medium">{label}</label>
        <span className="text-xs text-indigo-300 font-mono">
          {value > 0 ? value : value}{unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1.5 bg-slate-600 rounded-full appearance-none cursor-pointer accent-indigo-500"
      />
      <div className="flex justify-between text-xs text-slate-500 mt-0.5">
        <span>{min}{unit}</span>
        <span>{max}{unit}</span>
      </div>
    </div>
  );
}

export default function FilterPanel({ passCount, totalCount }: { passCount: number; totalCount: number }) {
  const { filters, updateFilter, resetFilters, showOnlyPassing, setShowOnlyPassing } = useScreenerStore();

  const toggleUniverse = (index: string) => {
    const cur = filters.universe;
    if (cur.includes(index) && cur.length === 1) return; // keep at least one
    const next = cur.includes(index) ? cur.filter((u) => u !== index) : [...cur, index];
    updateFilter('universe', next);
  };

  return (
    <aside className="w-72 shrink-0 bg-slate-800 border-r border-slate-700 p-4 flex flex-col gap-2 overflow-y-auto">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-semibold text-white">Filters</h2>
        <button
          onClick={resetFilters}
          className="text-xs text-slate-400 hover:text-indigo-300 transition-colors"
        >
          Reset
        </button>
      </div>

      {/* Universe toggles */}
      <div className="mb-4">
        <p className="text-xs text-slate-300 font-medium mb-2">Universe</p>
        <div className="flex gap-2">
          {['SP500', 'DJIA'].map((idx) => (
            <button
              key={idx}
              onClick={() => toggleUniverse(idx)}
              className={`flex-1 py-1.5 text-xs rounded-md border transition-colors font-medium ${
                filters.universe.includes(idx)
                  ? 'bg-indigo-600 border-indigo-500 text-white'
                  : 'bg-slate-700 border-slate-600 text-slate-400 hover:border-indigo-500'
              }`}
            >
              {idx}
            </button>
          ))}
        </div>
      </div>

      <Slider
        label="Max % above 52w Low"
        value={filters.max_pct_above_52w_low}
        min={0}
        max={50}
        step={1}
        unit="%"
        onChange={(v) => updateFilter('max_pct_above_52w_low', v)}
      />

      <Slider
        label="Max P/E Ratio"
        value={filters.max_trailing_pe}
        min={5}
        max={60}
        step={1}
        unit="x"
        onChange={(v) => updateFilter('max_trailing_pe', v)}
      />

      <div className="border-t border-slate-700 my-2" />
      <p className="text-xs text-slate-400 font-medium">Income filter (EPS CAGR OR Dividend Yield)</p>

      <Slider
        label="Min EPS CAGR (5yr)"
        value={filters.min_eps_cagr_5y}
        min={-10}
        max={40}
        step={1}
        unit="%"
        onChange={(v) => updateFilter('min_eps_cagr_5y', v)}
      />

      <Slider
        label="Min Dividend Yield"
        value={filters.min_dividend_yield}
        min={0}
        max={10}
        step={0.5}
        unit="%"
        onChange={(v) => updateFilter('min_dividend_yield', v)}
      />

      <div className="flex items-center gap-2 mt-1">
        <input
          type="checkbox"
          id="require-both"
          checked={filters.require_both}
          onChange={(e) => updateFilter('require_both', e.target.checked)}
          className="accent-indigo-500"
        />
        <label htmlFor="require-both" className="text-xs text-slate-300">
          Require BOTH (AND instead of OR)
        </label>
      </div>

      <div className="border-t border-slate-700 my-2" />

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="only-passing"
          checked={showOnlyPassing}
          onChange={(e) => setShowOnlyPassing(e.target.checked)}
          className="accent-indigo-500"
        />
        <label htmlFor="only-passing" className="text-xs text-slate-300">
          Show only opportunities
        </label>
      </div>

      {/* Results count */}
      <div className="mt-auto pt-4 border-t border-slate-700">
        <div className="rounded-lg bg-slate-700 p-3 text-center">
          <p className="text-2xl font-bold text-white">{passCount}</p>
          <p className="text-xs text-slate-400">
            opportunities of {totalCount} stocks
          </p>
        </div>
      </div>
    </aside>
  );
}
