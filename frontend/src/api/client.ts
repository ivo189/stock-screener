import axios from 'axios';

const client = axios.create({
  baseURL: '/api',
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
