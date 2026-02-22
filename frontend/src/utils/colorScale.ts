// Returns Tailwind color classes for metric values

export function peColor(pe: number | null): string {
  if (pe == null) return 'text-slate-400';
  if (pe <= 12) return 'text-emerald-400';
  if (pe <= 18) return 'text-yellow-400';
  if (pe <= 25) return 'text-orange-400';
  return 'text-red-400';
}

export function cagColor(cagr: number | null): string {
  if (cagr == null) return 'text-slate-400';
  if (cagr >= 15) return 'text-emerald-400';
  if (cagr >= 8) return 'text-green-400';
  if (cagr >= 3) return 'text-yellow-400';
  if (cagr >= 0) return 'text-orange-400';
  return 'text-red-400';
}

export function divColor(div: number | null): string {
  if (div == null || div === 0) return 'text-slate-400';
  if (div >= 4) return 'text-emerald-400';
  if (div >= 2) return 'text-green-400';
  if (div >= 1) return 'text-yellow-400';
  return 'text-slate-400';
}

export function proximityColor(pct: number | null): string {
  if (pct == null) return 'text-slate-400';
  if (pct <= 5) return 'text-emerald-400 font-semibold';
  if (pct <= 10) return 'text-green-400';
  if (pct <= 20) return 'text-yellow-400';
  if (pct <= 35) return 'text-orange-400';
  return 'text-slate-400';
}

// MA distance color: negative (below MA) = bullish opportunity = green
export function maColor(pct: number | null): string {
  if (pct == null) return 'text-slate-400';
  if (pct <= -20) return 'text-emerald-400 font-semibold'; // very far below MA
  if (pct <= -10) return 'text-green-400';
  if (pct <= -5)  return 'text-yellow-400';
  if (pct <= 0)   return 'text-orange-300';
  if (pct <= 10)  return 'text-slate-300';
  return 'text-slate-500'; // far above MA
}

export function qualityBg(score: number | null): string {
  if (score == null) return 'bg-slate-700';
  if (score >= 70) return 'bg-emerald-600';
  if (score >= 50) return 'bg-green-700';
  if (score >= 30) return 'bg-yellow-700';
  return 'bg-slate-700';
}

// Sector colors for pie chart
export const SECTOR_COLORS: Record<string, string> = {
  'Technology': '#6366f1',
  'Health Care': '#22c55e',
  'Financials': '#3b82f6',
  'Consumer Discretionary': '#f59e0b',
  'Communication Services': '#8b5cf6',
  'Industrials': '#06b6d4',
  'Consumer Staples': '#f97316',
  'Energy': '#ef4444',
  'Utilities': '#a3e635',
  'Real Estate': '#ec4899',
  'Materials': '#14b8a6',
  'Unknown': '#64748b',
};

export function getSectorColor(sector: string): string {
  return SECTOR_COLORS[sector] || '#64748b';
}
