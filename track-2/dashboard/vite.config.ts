import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig(({ command, mode }) => {
  if (command === 'build' && (process.env.VITE_USE_FIXTURES ?? loadEnv(mode, process.cwd()).VITE_USE_FIXTURES) === 'true') throw new Error('Fixture mode is disabled in production builds.');
  return { plugins: [react()], server: { proxy: { '/v1': 'http://localhost:8000' } } };
});
