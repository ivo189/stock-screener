import { useEffect, useState } from 'react';
import { ServerCrash } from 'lucide-react';

export default function LoadingSpinner({ size = 32 }: { size?: number }) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  const isSlowStart = seconds >= 5;

  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <div
        className="border-4 border-slate-600 border-t-indigo-400 rounded-full animate-spin"
        style={{ width: size, height: size }}
      />
      {!isSlowStart ? (
        <p className="text-slate-400 text-sm">Cargando datos...</p>
      ) : (
        <div className="flex flex-col items-center gap-1 text-center">
          <div className="flex items-center gap-2 text-yellow-400 text-sm">
            <ServerCrash size={16} />
            <span>Despertando el servidor...</span>
          </div>
          <p className="text-slate-500 text-xs">
            El servidor gratuito tarda hasta 2 min en arrancar tras inactividad.
          </p>
          <p className="text-slate-600 text-xs mt-1">{seconds}s</p>
        </div>
      )}
    </div>
  );
}
