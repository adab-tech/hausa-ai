/**
 * Captures a real screenshot of the Telemetry tab in the "Matattarar Bayanai"
 * dashboard (NeuralReview) for use as a documentation figure.
 *
 * Usage: node scripts/capture_telemetry_screenshot.mjs [outputPath]
 * Requires: frontend dev server running on http://localhost:3000
 *           backend running on http://127.0.0.1:8000
 */
import { chromium } from 'playwright';
import path from 'node:path';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:3000';
const outPath = process.argv[2] || path.join('docs', 'figures', 'telemetry_real_stats.png');

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });

await page.goto(FRONTEND_URL, { waitUntil: 'networkidle' });

// Open the "Matattarar Bayanai" (Neural Review) dashboard
await page.getByText('Matattarar Bayanai', { exact: true }).click();

// Telemetry tab is the default active tab; wait for real feedback stats to load
await page.getByText('Active Processing Pipeline').waitFor({ state: 'visible' });
await page.waitForTimeout(500); // allow async /api/feedback/stats fetch to resolve

await page.screenshot({ path: outPath });
console.log(`Saved screenshot to ${outPath}`);

await browser.close();
