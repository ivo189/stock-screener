import axios from 'axios';

// In production (Vercel), VITE_API_URL points to the Render backend.
// In local dev, falls back to relative /api (same-origin via localhost:8000).
const BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

const client = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

client.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail || err.message || 'Unknown error';
    return Promise.reject(new Error(message));
  }
);

export default client;
