import { useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Navbar from './components/layout/Navbar';
import ScreenerPage from './pages/ScreenerPage';
import ErrorBoundary from './components/common/ErrorBoundary';
import client from './api/client';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Ping backend every 10 minutes to prevent Render free tier from sleeping
function KeepAlive() {
  useEffect(() => {
    const ping = () => client.get('/screener/universe').catch(() => {});
    const id = setInterval(ping, 10 * 60 * 1000);
    return () => clearInterval(id);
  }, []);
  return null;
}

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <KeepAlive />
        <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
          <Navbar />
          <ScreenerPage />
        </div>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
