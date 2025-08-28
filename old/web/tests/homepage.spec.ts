import { test, expect } from '@playwright/test';

test.describe('Alice Web Interface Homepage', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should load homepage successfully', async ({ page }) => {
    // Wait for the page to load
    await page.waitForLoadState('networkidle');
    
    // Check if the page title contains expected content
    await expect(page).toHaveTitle(/Alice/i);
  });

  test('should have working navigation', async ({ page }) => {
    // Check for basic navigation elements
    const navigation = page.locator('nav, header, [role="navigation"]');
    
    // Should have some form of navigation present
    const hasNavigation = await navigation.count() > 0;
    expect(hasNavigation).toBeTruthy();
  });

  test('should be responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Page should still be accessible
    await page.waitForLoadState('networkidle');
    
    // Check if page renders without major layout issues
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });

  test('should load without JavaScript errors', async ({ page }) => {
    const errors: string[] = [];
    
    page.on('pageerror', (error) => {
      errors.push(error.message);
    });
    
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Should have no critical JavaScript errors
    expect(errors.filter(error => 
      !error.includes('ResizeObserver') && 
      !error.includes('Non-passive event listener')
    )).toHaveLength(0);
  });
});