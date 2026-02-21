import client from './client';
import type { StockMetrics } from '../types';

export async function fetchStockDetail(ticker: string): Promise<StockMetrics> {
  const res = await client.get<StockMetrics>(`/stock/${ticker}`);
  return res.data;
}
