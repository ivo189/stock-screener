import client from './client';
import type {
  BondsStatusResponse,
  BondHistoryResponse,
  BondOrderRequest,
  BondOrderResponse,
  PaperTradeResponse,
} from '../types/bonds';

export async function fetchBondsStatus(): Promise<BondsStatusResponse> {
  const res = await client.get<BondsStatusResponse>('/bonds/status');
  return res.data;
}

export async function triggerBondRefresh(): Promise<{ status: string; message: string }> {
  const res = await client.post('/bonds/refresh');
  return res.data;
}

export async function fetchPairHistory(
  pairId: string,
  limit = 200
): Promise<BondHistoryResponse> {
  const res = await client.get<BondHistoryResponse>(`/bonds/${pairId}/history`, {
    params: { limit },
  });
  return res.data;
}

export async function placeBondOrder(req: BondOrderRequest): Promise<BondOrderResponse> {
  const res = await client.post<BondOrderResponse>('/bonds/order', req);
  return res.data;
}

export async function fetchPaperTrades(limit = 100): Promise<PaperTradeResponse> {
  const res = await client.get<PaperTradeResponse>('/bonds/paper-trades', { params: { limit } });
  return res.data;
}

export interface FlushResult {
  status: string;
  message: string;
  total: number;
  open: number;
  closed: number;
}

export async function flushPaperTradesToGithub(): Promise<FlushResult> {
  const res = await client.post<FlushResult>('/bonds/paper-trades/flush');
  return res.data;
}
