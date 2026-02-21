export function formatCurrency(value: number | null | undefined, decimals = 2): string {
  if (value == null) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatPercent(value: number | null | undefined, decimals = 1): string {
  if (value == null) return '—';
  return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
}

export function formatNumber(value: number | null | undefined, decimals = 2): string {
  if (value == null) return '—';
  return value.toFixed(decimals);
}

export function formatMarketCap(value: number | null | undefined): string {
  if (value == null) return '—';
  if (value >= 1e12) return `$${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  return `$${value.toFixed(0)}`;
}

export function formatAge(seconds: number | null | undefined): string {
  if (seconds == null) return 'Unknown';
  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}
