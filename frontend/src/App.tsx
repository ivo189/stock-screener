import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Navbar from './components/layout/Navbar';
import ScreenerPage from './pages/ScreenerPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
        <Navbar />
        <ScreenerPage />
      </div>
    </QueryClientProvider>
  );
}
