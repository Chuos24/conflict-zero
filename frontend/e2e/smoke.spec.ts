import { test, expect } from '@playwright/test';

test.describe('Landing Page', () => {
  test('homepage loads and shows title', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Conflict Zero/);
  });

  test('navigation links are visible', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('link', { name: /Iniciar Sesión/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Registrarse/i })).toBeVisible();
  });
});

test.describe('Auth Flow', () => {
  test('login page loads', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: /Iniciar Sesión/i })).toBeVisible();
    await expect(page.getByLabel(/Email/i)).toBeVisible();
    await expect(page.getByLabel(/Contraseña/i)).toBeVisible();
  });

  test('register page loads', async ({ page }) => {
    await page.goto('/register');
    await expect(page.getByRole('heading', { name: /Crear Cuenta/i })).toBeVisible();
  });
});

test.describe('Dashboard (protected)', () => {
  test('redirects to login when not authenticated', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForURL('/login');
    await expect(page).toHaveURL(/login/);
  });

  test('dashboard/compare redirects to login', async ({ page }) => {
    await page.goto('/dashboard/compare');
    await page.waitForURL('/login');
    await expect(page).toHaveURL(/login/);
  });

  test('dashboard/history redirects to login', async ({ page }) => {
    await page.goto('/dashboard/history');
    await page.waitForURL('/login');
    await expect(page).toHaveURL(/login/);
  });

  test('dashboard/stats redirects to login', async ({ page }) => {
    await page.goto('/dashboard/stats');
    await page.waitForURL('/login');
    await expect(page).toHaveURL(/login/);
  });

  test('dashboard/api-keys redirects to login', async ({ page }) => {
    await page.goto('/dashboard/api-keys');
    await page.waitForURL('/login');
    await expect(page).toHaveURL(/login/);
  });

  test('dashboard/settings redirects to login', async ({ page }) => {
    await page.goto('/dashboard/settings');
    await page.waitForURL('/login');
    await expect(page).toHaveURL(/login/);
  });
});

test.describe('Pricing Page', () => {
  test('pricing page shows plans', async ({ page }) => {
    await page.goto('/pricing');
    await expect(page.getByRole('heading', { name: /Planes/i })).toBeVisible();
    await expect(page.getByText(/Essential/i)).toBeVisible();
    await expect(page.getByText(/Professional/i)).toBeVisible();
    await expect(page.getByText(/Enterprise/i)).toBeVisible();
  });
});

test.describe('Legal Pages', () => {
  test('terminos page loads', async ({ page }) => {
    await page.goto('/terminos');
    await expect(page.getByRole('heading', { name: /Términos/i })).toBeVisible();
  });

  test('privacidad page loads', async ({ page }) => {
    await page.goto('/privacidad');
    await expect(page.getByRole('heading', { name: /Privacidad/i })).toBeVisible();
  });
});

test.describe('Contact Page', () => {
  test('contacto page loads', async ({ page }) => {
    await page.goto('/contacto');
    await expect(page.getByRole('heading', { name: /Contacto/i })).toBeVisible();
  });
});
