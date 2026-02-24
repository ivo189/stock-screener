import client from './client';
import type {
  BondsStatusResponse,
  BondHistoryResponse,
  BondOrderRequest,
  BondOrderResponse,
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
