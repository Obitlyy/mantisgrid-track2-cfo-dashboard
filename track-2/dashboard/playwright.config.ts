import { defineConfig } from '@playwright/test';
export default defineConfig({ testDir: 'e2e', outputDir: '../../out/ui/playwright', timeout: 180000, use: { baseURL: process.env.DASHBOARD_URL ?? 'http://localhost:3000', trace: 'on' } });
