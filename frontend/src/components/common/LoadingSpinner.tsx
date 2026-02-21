export default function LoadingSpinner({ size = 32 }: { size?: number }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <div
        className="border-4 border-slate-600 border-t-indigo-400 rounded-full animate-spin"
        style={{ width: size, height: size }}
      />
      <p className="text-slate-400 text-sm">Loading data...</p>
    </div>
  );
}
