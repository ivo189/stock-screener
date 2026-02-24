/**
 * Modal panel for placing sandbox/live bond orders.
 * Defaults to sandbox=true for safety.
 */
import { useState } from 'react';
import { X, AlertTriangle, CheckCircle, Loader2 } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import { placeBondOrder } from '../../api/bonds';
import type { BondPairState, OrderSide, OrderPlazo, BondOrderRequest } from '../../types/bonds';

interface Props {
  pairState: BondPairState;
  onClose: () => void;
}

export default function OrderPanel({ pairState, onClose }: Props) {
  const { config, latest } = pairState;

  const [symbol, setSymbol] = useState(config.local_symbol);
  const [side, setSide] = useState<OrderSide>('buy');
  const [quantity, setQuantity] = useState(1000);
  const [price, setPrice] = useState<number>(latest?.local_price ?? 0);
  const [plazo, setPlazo] = useState<OrderPlazo>('t2');
  const [sandbox, setSandbox] = useState(true);

  const mutation = useMutation({
    mutationFn: (req: BondOrderRequest) => placeBondOrder(req),
  });

  function handleSymbolChange(s: string) {
    setSymbol(s);
    if (s === config.local_symbol) setPrice(latest?.local_price ?? 0);
    else setPrice(latest?.ny_price ?? 0);
  }

  function handleSubmit() {
    mutation.mutate({ pair_id: config.id, symbol, side, quantity, price, plazo, sandbox });
  }

  const isLive = !sandbox;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-slate-800 rounded-xl border border-slate-600 w-full max-w-md shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
          <div>
            <p className="font-semibold text-white">{config.label} — Enviar orden</p>
            <p className="text-slate-400 text-xs">{config.description}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Form */}
        <div className="px-5 py-4 space-y-4">
          {/* Sandbox toggle */}
          <div className={`flex items-center justify-between rounded-lg px-3 py-2 ${isLive ? 'bg-red-900/30 border border-red-500/40' : 'bg-emerald-900/20 border border-emerald-600/30'}`}>
            <div>
              <p className={`text-sm font-medium ${isLive ? 'text-red-300' : 'text-emerald-300'}`}>
                {isLive ? 'MODO REAL — Operación en cuenta live' : 'Modo Sandbox (simulación)'}
              </p>
              {isLive && (
                <p className="text-red-400 text-xs mt-0.5 flex items-center gap-1">
                  <AlertTriangle size={11} /> Esta orden afectará tu cuenta real de IOL.
                </p>
              )}
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                className="sr-only peer"
                checked={!sandbox}
                onChange={(e) => setSandbox(!e.target.checked)}
              />
              <div className="w-9 h-5 bg-slate-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-red-600" />
            </label>
          </div>

          {/* Symbol selector */}
          <div className="grid grid-cols-2 gap-2">
            {[config.local_symbol, config.ny_symbol].map((sym) => (
              <button
                key={sym}
                onClick={() => handleSymbolChange(sym)}
                className={`py-2 rounded-lg text-sm font-mono transition-colors border ${
                  symbol === sym
                    ? 'bg-indigo-600 border-indigo-500 text-white'
                    : 'bg-slate-700 border-slate-600 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {sym}
                <span className="block text-xs font-sans font-normal text-slate-400">
                  {sym === config.local_symbol ? 'Ley local' : 'Ley NY'}
                </span>
              </button>
            ))}
          </div>

          {/* Side */}
          <div className="grid grid-cols-2 gap-2">
            {(['buy', 'sell'] as OrderSide[]).map((s) => (
              <button
                key={s}
                onClick={() => setSide(s)}
                className={`py-2 rounded-lg text-sm font-medium transition-colors border ${
                  side === s
                    ? s === 'buy'
                      ? 'bg-emerald-600 border-emerald-500 text-white'
                      : 'bg-red-600 border-red-500 text-white'
                    : 'bg-slate-700 border-slate-600 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {s === 'buy' ? 'Comprar' : 'Vender'}
              </button>
            ))}
          </div>

          {/* Quantity + Price */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-slate-400 text-xs">Cantidad (VN)</label>
              <input
                type="number"
                min={1}
                value={quantity}
                onChange={(e) => setQuantity(Number(e.target.value))}
                className="mt-1 w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="text-slate-400 text-xs">Precio límite</label>
              <input
                type="number"
                step={0.01}
                value={price}
                onChange={(e) => setPrice(Number(e.target.value))}
                className="mt-1 w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          {/* Plazo */}
          <div>
            <label className="text-slate-400 text-xs">Plazo de liquidación</label>
            <div className="grid grid-cols-3 gap-2 mt-1">
              {(['t0', 't1', 't2'] as OrderPlazo[]).map((p) => (
                <button
                  key={p}
                  onClick={() => setPlazo(p)}
                  className={`py-1.5 rounded-lg text-xs font-mono transition-colors border ${
                    plazo === p
                      ? 'bg-slate-600 border-slate-400 text-white'
                      : 'bg-slate-700 border-slate-600 text-slate-400 hover:bg-slate-600'
                  }`}
                >
                  {p.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {/* Order total estimate */}
          <div className="bg-slate-700/50 rounded-lg px-3 py-2 text-xs text-slate-400">
            Total estimado:{' '}
            <span className="text-white font-mono">
              ${(quantity * price).toLocaleString('es-AR', { maximumFractionDigits: 0 })}
            </span>
          </div>

          {/* Result feedback */}
          {mutation.isSuccess && (
            <div
              className={`flex items-start gap-2 rounded-lg p-3 text-xs ${
                mutation.data.success
                  ? 'bg-emerald-900/30 border border-emerald-600/40 text-emerald-300'
                  : 'bg-red-900/30 border border-red-500/40 text-red-300'
              }`}
            >
              {mutation.data.success ? (
                <CheckCircle size={14} className="flex-shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
              )}
              <div>
                <p>{mutation.data.message}</p>
                {mutation.data.order_id && (
                  <p className="mt-1 font-mono">Orden #{mutation.data.order_id}</p>
                )}
              </div>
            </div>
          )}

          {mutation.isError && (
            <div className="bg-red-900/30 border border-red-500/40 text-red-300 rounded-lg p-3 text-xs">
              {(mutation.error as Error).message}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-5 py-4 border-t border-slate-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-300 hover:text-white transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleSubmit}
            disabled={mutation.isPending || quantity <= 0 || price <= 0}
            className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
              isLive
                ? 'bg-red-600 hover:bg-red-500 text-white'
                : 'bg-indigo-600 hover:bg-indigo-500 text-white'
            }`}
          >
            {mutation.isPending && <Loader2 size={14} className="animate-spin" />}
            {isLive ? 'Enviar orden REAL' : 'Enviar simulación'}
          </button>
        </div>
      </div>
    </div>
  );
}
