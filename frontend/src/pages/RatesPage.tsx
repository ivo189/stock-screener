/**
 * Tasas ARS — Caución Bursátil Tomadora 1D TNA vs Letras del Tesoro TNA.
 *
 * Features:
 *  - Time-series line chart comparing caución 1D TNA vs one or more letras
 *  - Configurable letras list (add / remove BYMA symbols like S17A6, S30A6)
 *  - Range selector: 1M / 3M / 6M / 1Y / custom
 *  - Maturity date displayed per letra
 */
import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Plus, X, TrendingUp, AlertCircle, Info } from 'lucide-react';
import { fetchRatesHistory } from '../api/rates';
import type { RangeOption, ChartDataPoint } from '../types/rates';

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const RANGE_OPTIONS: { id: RangeOption; label: string; days: number }[] = [
  { id: '1M', label: '1 mes', days: 30 },
  { id: '3M', label: '3 meses', days: 90 },
  { id: '6M', label: '6 meses', days: 180 },
  { id: '1Y', label: '1 año', days: 365 },
  { id: 'custom', label: 'Personalizado', days: 0 },
];

// Distinct colours for up to 8 letras + caución
const SERIES_COLORS = [
  '#34d399', // caucion — emerald
  '#60a5fa', // letra 1 — blue
  '#f59e0b', // letra 2 — amber
  '#a78bfa', // letra 3 — violet
  '#f87171', // letra 4 — red
  '#2dd4bf', // letra 5 — teal
  '#fb923c', // letra 6 — orange
  '#e879f9', // letra 7 — fuchsia
  '#94a3b8', // letra 8 — slate
];

const DEFAULT_LETRAS = ['S17A6', 'S30A6'];

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function isoToday(): string {
  return new Date().toISOString().slice(0, 10);
}

function isoOffset(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function formatDate(iso: string): string {
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y.slice(2)}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Custom Tooltip
// ─────────────────────────────────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 text-xs shadow-xl min-w-[180px]">
      <p className="text-slate-400 mb-2">{label}</p>
      {payload.map((entry: any) => (
        <p key={entry.dataKey} className="font-mono" style={{ color: entry.color }}>
          {entry.name}: <span className="font-semibold">{Number(entry.value).toFixed(1)}%</span>
        </p>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Letra chip (tag with remove button)
// ─────────────────────────────────────────────────────────────────────────────

interface LetraChipProps {
  symbol: string;
  color: string;
  vencimiento?: string | null;
  error?: string | null;
  onRemove: () => void;
}

function LetraChip({ symbol, color, vencimiento, error, onRemove }: LetraChipProps) {
  return (
    <div
      className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border"
      style={{ borderColor: color, color }}
    >
      <span className="font-mono">{symbol}</span>
      {vencimiento && (
        <span className="text-slate-400 font-normal">vto {formatDate(vencimiento)}</span>
      )}
      {error && (
        <span title={error}>
          <AlertCircle size={12} className="text-red-400" />
        </span>
      )}
      <button
        onClick={onRemove}
        className="ml-0.5 hover:text-white transition-colors"
        title={`Quitar ${symbol}`}
      >
        <X size={11} />
      </button>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Page
// ─────────────────────────────────────────────────────────────────────────────

export default function RatesPage() {
  const [range, setRange] = useState<RangeOption>('3M');
  const [customDesde, setCustomDesde] = useState(isoOffset(90));
  const [customHasta, setCustomHasta] = useState(isoToday());
  const [letras, setLetras] = useState<string[]>(DEFAULT_LETRAS);
  const [newLetra, setNewLetra] = useState('');

  // Compute actual date range
  const { fechaDesde, fechaHasta } = useMemo(() => {
    if (range === 'custom') {
      return { fechaDesde: customDesde, fechaHasta: customHasta };
    }
    const opt = RANGE_OPTIONS.find((r) => r.id === range)!;
    return { fechaDesde: isoOffset(opt.days), fechaHasta: isoToday() };
  }, [range, customDesde, customHasta]);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['ratesHistory', letras, fechaDesde, fechaHasta],
    queryFn: () => fetchRatesHistory({ letras, fecha_desde: fechaDesde, fecha_hasta: fechaHasta }),
    staleTime: 10 * 60 * 1000, // 10 min
    retry: 1,
  });

  // ── Build unified chart data ──────────────────────────────────────────────
  const chartData = useMemo((): ChartDataPoint[] => {
    if (!data) return [];

    // Collect all unique dates
    const dateSet = new Set<string>();
    data.caucion_1d.forEach((p) => dateSet.add(p.date));
    letras.forEach((sym) => {
      data.letras[sym]?.data.forEach((p) => dateSet.add(p.date));
    });

    const allDates = Array.from(dateSet).sort();

    return allDates.map((date) => {
      const point: ChartDataPoint = { date: formatDate(date) };

      // Caución
      const cPoint = data.caucion_1d.find((p) => p.date === date);
      if (cPoint) point.caucion_1d = cPoint.tna;

      // Letras
      letras.forEach((sym) => {
        const lPoint = data.letras[sym]?.data.find((p) => p.date === date);
        if (lPoint) point[sym] = lPoint.tna;
      });

      return point;
    });
  }, [data, letras]);

  // ── Y-axis domain ─────────────────────────────────────────────────────────
  const yDomain = useMemo(() => {
    const vals = chartData.flatMap((d) =>
      Object.entries(d)
        .filter(([k]) => k !== 'date')
        .map(([, v]) => Number(v))
        .filter((v) => !isNaN(v))
    );
    if (!vals.length) return [0, 100] as [number, number];
    const min = Math.floor(Math.min(...vals) * 0.97);
    const max = Math.ceil(Math.max(...vals) * 1.03);
    return [min, max] as [number, number];
  }, [chartData]);

  // ── Series colour map ─────────────────────────────────────────────────────
  const colorMap = useMemo(() => {
    const map: Record<string, string> = { caucion_1d: SERIES_COLORS[0] };
    letras.forEach((sym, i) => {
      map[sym] = SERIES_COLORS[(i + 1) % SERIES_COLORS.length];
    });
    return map;
  }, [letras]);

  // ── Handlers ──────────────────────────────────────────────────────────────
  function addLetra() {
    const sym = newLetra.toUpperCase().trim();
    if (!sym || letras.includes(sym) || letras.length >= 8) return;
    setLetras((prev) => [...prev, sym]);
    setNewLetra('');
  }

  function removeLetra(sym: string) {
    setLetras((prev) => prev.filter((s) => s !== sym));
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col gap-4 p-4 max-w-6xl mx-auto w-full">

      {/* ── Header ── */}
      <div className="flex items-center gap-2">
        <TrendingUp className="text-emerald-400" size={20} />
        <h1 className="text-lg font-bold text-white">Tasas ARS — Caución vs Letras del Tesoro</h1>
      </div>

      {/* ── Controls card ── */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 space-y-4">

        {/* Range selector */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-slate-400 mr-1">Período:</span>
          {RANGE_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              onClick={() => setRange(opt.id)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                range === opt.id
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
              }`}
            >
              {opt.label}
            </button>
          ))}
          {/* Custom date pickers */}
          {range === 'custom' && (
            <div className="flex items-center gap-2 ml-1">
              <input
                type="date"
                value={customDesde}
                onChange={(e) => setCustomDesde(e.target.value)}
                className="bg-slate-700 border border-slate-600 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-indigo-400"
              />
              <span className="text-slate-500 text-xs">→</span>
              <input
                type="date"
                value={customHasta}
                max={isoToday()}
                onChange={(e) => setCustomHasta(e.target.value)}
                className="bg-slate-700 border border-slate-600 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-indigo-400"
              />
            </div>
          )}
        </div>

        {/* Letras configurator */}
        <div className="space-y-2">
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-slate-400">Letras del Tesoro:</span>
            <span title="Ingresá símbolos BYMA, ej: S17A6, S30A6, S29Y6">
              <Info size={12} className="text-slate-500 cursor-help" />
            </span>
          </div>

          {/* Active letras chips */}
          <div className="flex flex-wrap gap-2">
            {/* Caución — always shown, not removable */}
            <div
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border"
              style={{ borderColor: SERIES_COLORS[0], color: SERIES_COLORS[0] }}
            >
              <span>Caución 1D</span>
              <span className="text-slate-400 font-normal">siempre activa</span>
            </div>

            {letras.map((sym) => (
              <LetraChip
                key={sym}
                symbol={sym}
                color={colorMap[sym]}
                vencimiento={data?.letras[sym]?.vencimiento}
                error={data?.letras[sym]?.error}
                onRemove={() => removeLetra(sym)}
              />
            ))}

            {/* Add letra input */}
            {letras.length < 8 && (
              <div className="flex items-center gap-1">
                <input
                  type="text"
                  value={newLetra}
                  onChange={(e) => setNewLetra(e.target.value.toUpperCase())}
                  onKeyDown={(e) => e.key === 'Enter' && addLetra()}
                  placeholder="S17A6..."
                  maxLength={8}
                  className="bg-slate-700 border border-slate-600 rounded px-2 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-400 w-24 font-mono uppercase"
                />
                <button
                  onClick={addLetra}
                  disabled={!newLetra.trim()}
                  className="p-1 rounded bg-slate-700 hover:bg-indigo-700 disabled:opacity-40 transition-colors text-slate-300"
                  title="Agregar letra"
                >
                  <Plus size={13} />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Chart area ── */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
        {isLoading && (
          <div className="flex items-center justify-center h-72 text-slate-400 text-sm gap-2">
            <div className="w-4 h-4 border-2 border-slate-500 border-t-indigo-400 rounded-full animate-spin" />
            Cargando datos desde IOL...
          </div>
        )}

        {isError && (
          <div className="flex items-center justify-center h-72 text-red-400 text-sm gap-2">
            <AlertCircle size={16} />
            <span>
              Error al obtener datos:{' '}
              {error instanceof Error ? error.message : 'Error desconocido'}
            </span>
          </div>
        )}

        {!isLoading && !isError && chartData.length === 0 && (
          <div className="flex items-center justify-center h-72 text-slate-500 text-sm">
            Sin datos para el período seleccionado.
          </div>
        )}

        {!isLoading && !isError && chartData.length > 0 && (
          <>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-slate-500">
                TNA % · {chartData.length} días
              </span>
              {data && (
                <span className="text-xs text-slate-500">
                  {formatDate(data.fecha_desde)} → {formatDate(data.fecha_hasta)}
                </span>
              )}
            </div>

            <ResponsiveContainer width="100%" height={360}>
              <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: '#64748b' }}
                  tickLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis
                  domain={yDomain}
                  tick={{ fontSize: 10, fill: '#64748b' }}
                  tickLine={false}
                  tickFormatter={(v) => `${v}%`}
                  width={52}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  wrapperStyle={{ fontSize: 11, color: '#94a3b8', paddingTop: 8 }}
                />

                {/* Caución 1D */}
                <Line
                  type="monotone"
                  dataKey="caucion_1d"
                  name="Caución 1D"
                  stroke={SERIES_COLORS[0]}
                  strokeWidth={2.5}
                  dot={false}
                  activeDot={{ r: 4 }}
                  isAnimationActive={false}
                  connectNulls
                />

                {/* One Line per letra */}
                {letras.map((sym) => (
                  <Line
                    key={sym}
                    type="monotone"
                    dataKey={sym}
                    name={sym}
                    stroke={colorMap[sym]}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                    isAnimationActive={false}
                    connectNulls
                    strokeDasharray={letras.indexOf(sym) % 2 === 0 ? undefined : '5 3'}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </>
        )}
      </div>

      {/* ── Per-letra status table ── */}
      {data && letras.length > 0 && (
        <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-700">
            <span className="text-sm font-medium text-slate-200">Detalle de letras</span>
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-slate-400 border-b border-slate-700">
                <th className="text-left px-4 py-2">Símbolo</th>
                <th className="text-left px-4 py-2">Vencimiento</th>
                <th className="text-right px-4 py-2">Última TNA</th>
                <th className="text-right px-4 py-2">Puntos</th>
                <th className="text-left px-4 py-2">Estado</th>
              </tr>
            </thead>
            <tbody>
              {letras.map((sym) => {
                const lr = data.letras[sym];
                const lastPoint = lr?.data?.at(-1);
                return (
                  <tr key={sym} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                    <td className="px-4 py-2 font-mono font-bold" style={{ color: colorMap[sym] }}>
                      {sym}
                    </td>
                    <td className="px-4 py-2 text-slate-300">
                      {lr?.vencimiento ? formatDate(lr.vencimiento) : '—'}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-slate-200">
                      {lastPoint ? `${lastPoint.tna.toFixed(1)}%` : '—'}
                    </td>
                    <td className="px-4 py-2 text-right text-slate-400">
                      {lr?.data?.length ?? 0}
                    </td>
                    <td className="px-4 py-2">
                      {lr?.error ? (
                        <span className="text-red-400 flex items-center gap-1">
                          <AlertCircle size={11} /> {lr.error}
                        </span>
                      ) : (
                        <span className="text-emerald-400">OK</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Help note ── */}
      <div className="text-xs text-slate-500 flex items-start gap-1.5">
        <Info size={12} className="mt-0.5 flex-shrink-0" />
        <span>
          Símbolos BYMA: <span className="font-mono text-slate-400">S17A6</span> = 17-Abr-2026,{' '}
          <span className="font-mono text-slate-400">S30A6</span> = 30-Abr-2026,{' '}
          <span className="font-mono text-slate-400">S29Y6</span> = 29-May-2026. Formato:{' '}
          <span className="font-mono text-slate-400">[Prefijo][DD][Mes][Año]</span>.
          Meses: F=Feb, H=Mar, A=Abr, Y=May, J=Jun, N=Jul, Q=Ago, U=Sep, V=Oct, X=Nov, Z=Dic, G=Ene.
        </span>
      </div>

    </div>
  );
}
