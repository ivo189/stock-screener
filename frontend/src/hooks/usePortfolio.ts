import { useMutation } from '@tanstack/react-query';
import { buildPortfolio } from '../api/portfolio';
import type { PortfolioRequest, PortfolioResponse } from '../types';
import { useState } from 'react';

export function usePortfolio() {
  const [result, setResult] = useState<PortfolioResponse | null>(null);

  const mutation = useMutation({
    mutationFn: (req: PortfolioRequest) => buildPortfolio(req),
    onSuccess: (data) => setResult(data),
  });

  return { ...mutation, result, clearResult: () => setResult(null) };
}
