import { test, expect } from '@playwright/test';

// No backend runs in this CI environment -- these tests deliberately only
// cover what's verifiable without one (the shell, layout, and lazy-loading
// wiring), the same scope manually verified by hand throughout the Tier 0/1
// work this app went through. Real chat/TTS round-trips are covered by the
// backend's own test suite and by the live production endpoint checks run
// after each deploy, not here.

test('the chat shell loads with no console errors beyond the expected offline backend calls', async ({ page }) => {
  const unexpectedErrors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() !== 'error') return;
    const text = msg.text();
    // The dev server has no backend to talk to in CI -- recordVisit's
    // fire-and-forget POST failing is expected, not a real bug.
    if (text.includes('ERR_CONNECTION_REFUSED') || text.includes('Failed to load resource')) return;
    unexpectedErrors.push(text);
  });

  await page.goto('/');
  await expect(page.getByPlaceholder('Rubuta saƙonka anan…')).toBeVisible();
  expect(unexpectedErrors).toEqual([]);
});

test('typing into the message input reflects what was typed', async ({ page }) => {
  await page.goto('/');
  const input = page.getByPlaceholder('Rubuta saƙonka anan…');
  await input.fill('sannu, yaya kake?');
  await expect(input).toHaveValue('sannu, yaya kake?');
});

test('opening the dictionary lazily loads and renders its modal', async ({ page }) => {
  await page.goto('/');

  // Mobile-first layout: the sidebar starts closed behind a menu button.
  const menuButton = page.getByLabel('Buɗe menu (Open menu)');
  if (await menuButton.isVisible()) {
    await menuButton.click();
  }

  await page.getByRole('button', { name: 'Ƙamus' }).click();
  await expect(page.getByText('DICTIONARY — ROBINSON · WIKTIONARY · NEWMAN')).toBeVisible();
});

test('the admin login route lazy-loads independently of the main chat bundle', async ({ page }) => {
  await page.goto('/admin/login');
  // Case-insensitive: the source text is "Reviewer Sign-In", CSS
  // text-transform: uppercase renders it visually differently.
  await expect(page.getByText(/reviewer sign-in/i)).toBeVisible();
});
