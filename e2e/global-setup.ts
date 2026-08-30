import { chromium, type FullConfig } from '@playwright/test';

/**
 * Vite's dev server does a one-time dependency pre-bundling pass triggered
 * by the FIRST real page load, which can abort that same load mid-flight
 * ("ERR_ABORTED; maybe frame was detached?") -- hit this exact race
 * manually earlier in the project's history testing this same dev server.
 * Warming the server up once here, before the real test suite runs
 * against it, avoids every test needing its own retry/timeout workaround
 * for a one-time startup cost that has nothing to do with what's being
 * tested.
 */
export default async function globalSetup(config: FullConfig) {
  const { baseURL } = config.projects[0].use;
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (let attempt = 0; attempt < 5; attempt++) {
    try {
      await page.goto(baseURL!, { waitUntil: 'domcontentloaded', timeout: 15_000 });
      const hasContent = await page.evaluate(() => (document.getElementById('root')?.children.length ?? 0) > 0);
      if (hasContent) break;
    } catch {
      // Expected on the first attempt or two while Vite's optimizer churns.
    }
    await page.waitForTimeout(2000);
  }
  await browser.close();
}
