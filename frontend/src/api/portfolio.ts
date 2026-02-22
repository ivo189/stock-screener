import client from './client';
import type { PortfolioRequest, PortfolioResponse, MonteCarloResult } from '../types';

export async function buildPortfolio(request: PortfolioRequest): Promise<PortfolioResponse> {
  const res = await client.post<PortfolioResponse>('/portfolio', request);
  return res.data;
}

export async function previewPortfolio(
  tickers: string[],
  capital?: number,
  method: string = 'risk_parity'
): Promise<PortfolioResponse> {
  const params = new URLSearchParams();
  tickers.forEach((t) => params.append('tickers', t));
  if (capital) params.set('capital', String(capital));
  params.set('method', method);
  const res = await client.get<PortfolioResponse>(`/portfolio/preview?${params.toString()}`);
  return res.data;
}

export async function runMonteCarlo(
  request: PortfolioRequest,
  nWeeks: number = 52
): Promise<MonteCarloResult> {
  const res = await client.post<MonteCarloResult>(
    `/portfolio/monte-carlo?n_weeks=${nWeeks}`,
    request
  );
  return res.data;
}
