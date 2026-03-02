import client from './client';
import type { RatesHistoryResponse } from '../types/rates';

export interface RatesHistoryParams {
  letras?: string[];
  fecha_desde?: string;
  fecha_hasta?: string;
}

export async function fetchRatesHistory(
  params: RatesHistoryParams = {}
): Promise<RatesHistoryResponse> {
  const res = await client.get<RatesHistoryResponse>('/rates/history', {
    params: {
      // axios serialises repeated param arrays as letras=S17A6&letras=S30A6
      letras: params.letras ?? [],
      ...(params.fecha_desde ? { fecha_desde: params.fecha_desde } : {}),
      ...(params.fecha_hasta ? { fecha_hasta: params.fecha_hasta } : {}),
    },
    // Serialize arrays properly for FastAPI (repeated key style)
    paramsSerializer: (p) => {
      const parts: string[] = [];
      for (const [key, val] of Object.entries(p)) {
        if (Array.isArray(val)) {
          val.forEach((v) => parts.push(`${key}=${encodeURIComponent(v)}`));
        } else if (val !== undefined && val !== null && val !== '') {
          parts.push(`${key}=${encodeURIComponent(String(val))}`);
        }
      }
      return parts.join('&');
    },
  });
  return res.data;
}

export async function parseLetraSymbol(
  simbolo: string
): Promise<{ simbolo: string; vencimiento: string | null; parsed: boolean }> {
  const res = await client.get('/rates/letras/parse', { params: { simbolo } });
  return res.data;
}
