/**
 * Opciones — screener de call ratio spreads (compro X calls en A, vendo Y > X calls en B > A, a crédito).
 *
 * 1) Subyacentes cerca de un máximo (ATH / 52w / 26w / 13w) con vol realizada alta.
 * 2) Al elegir uno, arma combinaciones de strikes con la cadena real y muestra el payoff.
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, Search } from 'lucide-react';
import {
  CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import {
  fetchRatioSpreads, scanUnderlyings,
  type HighRef, type ScanParams, type SpreadParams, type SpreadRow,
} from '../api/options';

const DEFAULT_SCAN: ScanParams = {
  high_ref: 'ath', max_dist_pct: 8, min_vol_pct: 30, min_traded_musd: 300, top: 30,
};
const DEFAULT_SPREAD: SpreadParams = {
  x: 1, y: 3, min_dte: 14, max_dte: 45, min_credit: 0,
  max_otm_long_pct: 5, max_otm_short_pct: 25, min_open_interest: 50,
};

function NumField({ label, value, onChange, step = 1 }: {
  label: string; value: number; onChange: (v: number) => void; step?: number;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs text-slate-400">
      {label}
      <input
        type="number" step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="bg-slate-800 border border-slate-600 rounded px-2 py-1 w-24 text-slate-100"
      />
    </label>
  );
}

function PayoffChart({ spread }: { spread: SpreadRow }) {
  return (
    <div style={{ height: 220 }}>
      <ResponsiveContainer>
        <LineChart data={spread.payoff}>
          <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
          <XAxis dataKey="spot" stroke="#94a3b8" tick={{ fontSize: 11 }} />
          <YAxis stroke="#94a3b8" tick={{ fontSize: 11 }} />
          <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #475569' }} />
          <ReferenceLine y={0} stroke="#64748b" />
          <ReferenceLine x={spread.k_long} stroke="#60a5fa" strokeDasharray="4 4" />
          <ReferenceLine x={spread.k_short} stroke="#f59e0b" strokeDasharray="4 4" />
          <Line type="monotone" dataKey="pnl" stroke="#34d399" dot={false} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function OptionsPage() {
  const [scan, setScan] = useState<ScanParams>(DEFAULT_SCAN);
  const [spreadP, setSpreadP] = useState<SpreadParams>(DEFAULT_SPREAD);
  const [selected, setSelected] = useState<string | null>(null);
  const [picked, setPicked] = useState<SpreadRow | null>(null);
  const [runScan, setRunScan] = useState<ScanParams | null>(null);

  const scanQ = useQuery({
    queryKey: ['options-scan', runScan],
    queryFn: () => scanUnderlyings(runScan!),
    enabled: runScan !== null,
    staleTime: 10 * 60 * 1000,
  });

  const spreadsQ = useQuery({
    queryKey: ['options-spreads', selected, spreadP],
    queryFn: () => fetchRatioSpreads(selected!, spreadP),
    enabled: selected !== null,
  });

  const invalidRatio = spreadP.y <= spreadP.x;

  return (
    <main className="p-4 flex flex-col gap-6 max-w-7xl w-full mx-auto">
      <section className="bg-slate-800/60 border border-slate-700 rounded-lg p-4">
        <h2 className="font-semibold mb-3">1 · Subyacentes: cerca de un máximo y con volatilidad alta</h2>
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1 text-xs text-slate-400">
            Máximo de referencia
            <select
              value={scan.high_ref}
              onChange={(e) => setScan({ ...scan, high_ref: e.target.value as HighRef })}
              className="bg-slate-800 border border-slate-600 rounded px-2 py-1 text-slate-100"
            >
              <option value="ath">Histórico (ATH)</option>
              <option value="52w">52 semanas</option>
              <option value="26w">26 semanas</option>
              <option value="13w">13 semanas</option>
            </select>
          </label>
          <NumField label="Dist. máx. al máximo (%)" value={scan.max_dist_pct} onChange={(v) => setScan({ ...scan, max_dist_pct: v })} />
          <NumField label="Vol realizada mín. (%)" value={scan.min_vol_pct} onChange={(v) => setScan({ ...scan, min_vol_pct: v })} />
          <NumField label="Operado 30d mín. (USD M)" value={scan.min_traded_musd} onChange={(v) => setScan({ ...scan, min_traded_musd: v })} step={50} />
          <button
            onClick={() => setRunScan({ ...scan })}
            disabled={scanQ.isFetching}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-sm"
          >
            <Search size={14} /> {scanQ.isFetching ? 'Escaneando… (puede tardar minutos)' : 'Escanear'}
          </button>
        </div>
        {scanQ.error && <p className="text-red-400 text-sm mt-3">{(scanQ.error as Error).message}</p>}

        {scanQ.data && (
          <div className="overflow-x-auto mt-4">
            <table className="w-full text-sm">
              <thead className="text-slate-400 text-xs text-right">
                <tr>
                  <th className="text-left py-1">Ticker</th><th>Cierre</th><th>Máx.</th><th>Dist.</th>
                  <th>RV21</th><th>Mayor movida</th><th>1σ 15d</th><th>Earnings</th><th>Score</th>
                </tr>
              </thead>
              <tbody>
                {scanQ.data.results.map((r) => (
                  <tr
                    key={r.ticker}
                    onClick={() => { setSelected(r.ticker); setPicked(null); }}
                    className={`text-right cursor-pointer border-t border-slate-700 hover:bg-slate-700/40 ${
                      selected === r.ticker ? 'bg-slate-700/60' : ''
                    }`}
                  >
                    <td className="text-left py-1 font-medium">{r.ticker}</td>
                    <td>{r.close.toFixed(2)}</td>
                    <td>{r.high_ref.toFixed(2)}</td>
                    <td>{r.dist_pct.toFixed(1)}%</td>
                    <td>{r.rv21.toFixed(0)}%</td>
                    <td>{r.max_move_pct.toFixed(1)}%</td>
                    <td>±{r.sigma15_pct.toFixed(1)}%</td>
                    <td>
                      {r.earnings_date ?? '—'}
                      {r.days_to_earnings != null && r.days_to_earnings >= 0 && r.days_to_earnings <= 21 && (
                        <AlertTriangle size={12} className="inline ml-1 text-amber-400" />
                      )}
                    </td>
                    <td className="font-semibold">{r.score.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {scanQ.data.results.length === 0 && (
              <p className="text-slate-400 text-sm py-3">Ningún subyacente cumple los filtros. Aflojá la distancia o la vol mínima.</p>
            )}
          </div>
        )}
      </section>

      <section className="bg-slate-800/60 border border-slate-700 rounded-lg p-4">
        <h2 className="font-semibold mb-3">
          2 · Ratio spread {spreadP.x}:{spreadP.y} {selected ? `en ${selected}` : '(elegí un subyacente arriba)'}
        </h2>
        <div className="flex flex-wrap items-end gap-4">
          <NumField label="Compro X" value={spreadP.x} onChange={(v) => setSpreadP({ ...spreadP, x: v })} />
          <NumField label="Vendo Y (> X)" value={spreadP.y} onChange={(v) => setSpreadP({ ...spreadP, y: v })} />
          <NumField label="DTE mín." value={spreadP.min_dte} onChange={(v) => setSpreadP({ ...spreadP, min_dte: v })} />
          <NumField label="DTE máx." value={spreadP.max_dte} onChange={(v) => setSpreadP({ ...spreadP, max_dte: v })} />
          <NumField label="Crédito mín. (USD/acción)" value={spreadP.min_credit} step={0.05} onChange={(v) => setSpreadP({ ...spreadP, min_credit: v })} />
          <NumField label="Larga ±% del spot" value={spreadP.max_otm_long_pct} onChange={(v) => setSpreadP({ ...spreadP, max_otm_long_pct: v })} />
          <NumField label="Corta hasta +% spot" value={spreadP.max_otm_short_pct} onChange={(v) => setSpreadP({ ...spreadP, max_otm_short_pct: v })} />
          <NumField label="OI mín." value={spreadP.min_open_interest} step={10} onChange={(v) => setSpreadP({ ...spreadP, min_open_interest: v })} />
        </div>
        {invalidRatio && <p className="text-amber-400 text-sm mt-3">Y debe ser mayor que X para que queden calls descubiertas.</p>}
        {spreadsQ.isFetching && <p className="text-slate-400 text-sm mt-3">Leyendo cadenas de opciones…</p>}
        {spreadsQ.error && <p className="text-red-400 text-sm mt-3">{(spreadsQ.error as Error).message}</p>}

        {spreadsQ.data && !invalidRatio && (
          <div className="mt-4 grid lg:grid-cols-[1fr_380px] gap-4">
            <div className="overflow-x-auto">
              <p className="text-xs text-slate-400 mb-2">Spot {spreadsQ.data.spot}. Valores por combo (×100). Ordenado por colchón hasta el breakeven superior.</p>
              <table className="w-full text-sm">
                <thead className="text-slate-400 text-xs text-right">
                  <tr>
                    <th className="text-left">Venc.</th><th>DTE</th><th>Larga</th><th>Corta</th>
                    <th>Crédito</th><th>Gan. máx.</th><th>BE sup.</th><th>Desc.</th>
                  </tr>
                </thead>
                <tbody>
                  {spreadsQ.data.spreads.map((s, i) => (
                    <tr
                      key={i}
                      onClick={() => setPicked(s)}
                      className={`text-right cursor-pointer border-t border-slate-700 hover:bg-slate-700/40 ${picked === s ? 'bg-slate-700/60' : ''}`}
                    >
                      <td className="text-left">{s.expiration}</td>
                      <td>{s.dte}</td>
                      <td>{s.k_long}</td>
                      <td>{s.k_short}</td>
                      <td className="text-emerald-400">${s.net_credit.toFixed(0)}</td>
                      <td>${s.max_profit.toFixed(0)}</td>
                      <td>{s.upper_breakeven} ({s.upper_breakeven_pct?.toFixed(1)}%)</td>
                      <td className="text-amber-400">{s.naked}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {spreadsQ.data.spreads.length === 0 && (
                <p className="text-slate-400 text-sm py-3">Sin combinaciones a crédito con esos filtros.</p>
              )}
            </div>
            <div>{picked ? <PayoffChart spread={picked} /> : <p className="text-slate-500 text-sm">Elegí una fila para ver el payoff al vencimiento.</p>}</div>
          </div>
        )}

        <p className="text-xs text-slate-500 mt-4 flex items-start gap-1.5">
          <AlertTriangle size={12} className="mt-0.5 flex-shrink-0" />
          Las calls descubiertas tienen pérdida ilimitada por encima del breakeven superior. Un gap por earnings
          dentro del vencimiento es el principal riesgo. Los precios son punto medio de yfinance (pueden venir con
          delay): validá bid/ask, IV y margen en TWS antes de operar.
        </p>
      </section>
    </main>
  );
}
