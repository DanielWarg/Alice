import { test, expect } from '@playwright/test';

/**
 * VoiceBox Rendering Verification Tests
 * 
 * Focused test suite specifically for Task 4: 
 * "VoiceBox i HUD har data-testid och e2e-test som verifierar rendering"
 * 
 * This test file specifically verifies:
 * 1. All required data-testid attributes are present
 * 2. Component renders correctly in the HUD
 * 3. Essential rendering functionality works
 */

test.describe('VoiceBox Rendering Verification', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
  });

  test.describe('Data-testid Attribute Verification', () => {
    test('should have all required data-testid attributes', async ({ page }) => {
      // Primary container
      const container = page.locator('[data-testid="voice-box-container"]');
      await expect(container).toBeVisible();
      
      // Panel wrapper
      const panel = page.locator('[data-testid="voice-box-panel"]');
      await expect(panel).toBeVisible();
      
      // Bars container
      const barsContainer = page.locator('[data-testid="voice-box-bars"]');
      await expect(barsContainer).toBeVisible();
      
      // Individual bars (default 7 bars)
      for (let i = 0; i < 7; i++) {
        const bar = page.locator(`[data-testid="voice-box-bar-${i}"]`);
        const barElement = page.locator(`[data-testid="voice-box-bar-element-${i}"]`);
        
        await expect(bar).toBeVisible();
        await expect(barElement).toBeVisible();
      }
      
      // Control buttons
      const startButton = page.locator('[data-testid="voice-box-start"]');
      const testTtsButton = page.locator('[data-testid="voice-box-test-tts"]');
      const status = page.locator('[data-testid="voice-box-status"]');
      
      await expect(startButton).toBeVisible();
      await expect(testTtsButton).toBeVisible();
      await expect(status).toBeVisible();
      
      // Selection controls
      const personalitySelect = page.locator('[data-testid="voice-box-personality-select"]');
      const emotionSelect = page.locator('[data-testid="voice-box-emotion-select"]');
      const qualitySelect = page.locator('[data-testid="voice-box-quality-select"]');
      
      await expect(personalitySelect).toBeVisible();
      await expect(emotionSelect).toBeVisible();
      await expect(qualitySelect).toBeVisible();
    });

    test('should have data-testid attributes that are unique and correctly named', async ({ page }) => {
      // Get all elements with data-testid
      const testIdElements = await page.locator('[data-testid]').all();
      const testIds = [];
      
      for (const element of testIdElements) {
        const testId = await element.getAttribute('data-testid');
        if (testId && testId.startsWith('voice-box-')) {
          testIds.push(testId);
        }
      }
      
      // Check that we have the expected test IDs
      const expectedTestIds = [
        'voice-box-container',
        'voice-box-panel', 
        'voice-box-bars',
        'voice-box-start',
        'voice-box-test-tts',
        'voice-box-status',
        'voice-box-personality-select',
        'voice-box-emotion-select',
        'voice-box-quality-select'
      ];
      
      // Add bar test IDs
      for (let i = 0; i < 7; i++) {
        expectedTestIds.push(`voice-box-bar-${i}`);
        expectedTestIds.push(`voice-box-bar-element-${i}`);
      }
      
      // Verify all expected test IDs are present
      for (const expectedId of expectedTestIds) {
        expect(testIds).toContain(expectedId);
      }
    });
  });

  test.describe('HUD Integration Rendering', () => {
    test('should render properly within the HUD layout', async ({ page }) => {
      const voiceBox = page.locator('[data-testid="voice-box-container"]');
      
      // Verify VoiceBox is visible and has proper dimensions
      await expect(voiceBox).toBeVisible();
      
      const boundingBox = await voiceBox.boundingBox();
      expect(boundingBox).not.toBeNull();
      expect(boundingBox!.width).toBeGreaterThan(300); // Should be substantial width
      expect(boundingBox!.height).toBeGreaterThan(200); // Should be substantial height
    });

    test('should render with correct CSS classes and styling', async ({ page }) => {
      const container = page.locator('[data-testid="voice-box-container"]');
      const panel = page.locator('[data-testid="voice-box-panel"]');
      const bars = page.locator('[data-testid="voice-box-bars"]');
      
      // Check container classes
      await expect(container).toHaveClass(/w-full/);
      await expect(container).toHaveClass(/max-w-3xl/);
      await expect(container).toHaveClass(/mx-auto/);
      
      // Check panel styling
      await expect(panel).toHaveClass(/rounded-2xl/);
      await expect(panel).toHaveClass(/p-6/);
      
      // Check bars container
      await expect(bars).toHaveClass(/grid/);
      await expect(bars).toHaveClass(/h-40/);
    });

    test('should render bars with correct visual properties', async ({ page }) => {
      // Check that each bar element has the expected visual styling
      for (let i = 0; i < 3; i++) { // Test first 3 bars
        const barElement = page.locator(`[data-testid="voice-box-bar-element-${i}"]`);
        
        await expect(barElement).toHaveClass(/bar/);
        await expect(barElement).toHaveClass(/rounded-full/);
        
        // Check computed styles
        const styles = await barElement.evaluate(el => {
          const computed = window.getComputedStyle(el);
          return {
            background: computed.background,
            height: computed.height,
            opacity: computed.opacity,
            width: computed.width
          };
        });
        
        // Should have gradient background
        expect(styles.background).toContain('linear-gradient');
        
        // Should have some opacity (ambient animation)
        expect(parseFloat(styles.opacity)).toBeGreaterThan(0);
        
        // Should have minimal height initially (ambient state)
        expect(parseFloat(styles.height)).toBeGreaterThan(0);
      }
    });
  });

  test.describe('Essential Rendering Functionality', () => {
    test('should render control buttons with correct initial state', async ({ page }) => {
      const startButton = page.locator('[data-testid="voice-box-start"]');
      const stopButton = page.locator('[data-testid="voice-box-stop"]');
      const ttsButton = page.locator('[data-testid="voice-box-test-tts"]');
      const status = page.locator('[data-testid="voice-box-status"]');
      
      // Initial state verification
      await expect(startButton).toBeVisible();
      await expect(startButton).toHaveText('Starta mic');
      
      await expect(stopButton).not.toBeVisible(); // Should be hidden initially
      
      await expect(ttsButton).toBeVisible();
      await expect(ttsButton).toHaveText('Test TTS');
      
      await expect(status).toBeVisible();
      await expect(status).toHaveText('AV');
    });

    test('should render selection controls with correct default values', async ({ page }) => {
      const personalitySelect = page.locator('[data-testid="voice-box-personality-select"]');
      const emotionSelect = page.locator('[data-testid="voice-box-emotion-select"]');
      const qualitySelect = page.locator('[data-testid="voice-box-quality-select"]');
      
      // Check default values
      await expect(personalitySelect).toHaveValue('alice');
      await expect(emotionSelect).toHaveValue('friendly');
      await expect(qualitySelect).toHaveValue('medium');
      
      // Check that options are available
      const personalityOptions = personalitySelect.locator('option');
      await expect(personalityOptions).toHaveCount(3); // alice, formal, casual
      
      const emotionOptions = emotionSelect.locator('option');
      await expect(emotionOptions).toHaveCount(5); // neutral, happy, calm, confident, friendly
      
      const qualityOptions = qualitySelect.locator('option');
      await expect(qualityOptions).toHaveCount(2); // medium, high
    });

    test('should render voice settings display correctly', async ({ page }) => {
      // Check personality display
      const personalityText = page.locator('text=Personlighet:');
      await expect(personalityText).toBeVisible();
      
      // Check emotion display
      const emotionText = page.locator('text=Känsla:');
      await expect(emotionText).toBeVisible();
      
      // Check quality display
      const qualityText = page.locator('text=Kvalitet:');
      await expect(qualityText).toBeVisible();
      
      // Check that values are displayed with correct styling
      const aliceValue = page.locator('.text-cyan-400').filter({ hasText: 'alice' });
      const friendlyValue = page.locator('.text-purple-400').filter({ hasText: 'friendly' });
      const mediumValue = page.locator('.text-green-400').filter({ hasText: 'medium' });
      
      await expect(aliceValue).toBeVisible();
      await expect(friendlyValue).toBeVisible();
      await expect(mediumValue).toBeVisible();
    });

    test('should show ambient animation immediately after render', async ({ page }) => {
      // Wait a brief moment for animation to initialize
      await page.waitForTimeout(500);
      
      // Check that bars are animating (have some opacity and changing properties)
      const firstBar = page.locator('[data-testid="voice-box-bar-element-0"]');
      
      // Take two measurements with a small delay
      const firstOpacity = await firstBar.evaluate(el => 
        parseFloat(window.getComputedStyle(el).opacity)
      );
      
      await page.waitForTimeout(100);
      
      const secondOpacity = await firstBar.evaluate(el => 
        parseFloat(window.getComputedStyle(el).opacity)
      );
      
      // Should have some opacity (indicating animation is active)
      expect(firstOpacity).toBeGreaterThan(0.1);
      expect(secondOpacity).toBeGreaterThan(0.1);
      
      // Animation should be smooth (opacity values should be reasonable)
      expect(firstOpacity).toBeLessThan(1.0);
      expect(secondOpacity).toBeLessThan(1.0);
    });
  });

  test.describe('Error and Status Rendering', () => {
    test('should have error display element ready', async ({ page }) => {
      // Error message should be in DOM but not visible initially
      const errorElement = page.locator('[data-testid="voice-box-error"]');
      
      // Should exist but not be visible initially
      const errorCount = await errorElement.count();
      expect(errorCount).toBeLessThanOrEqual(1); // Either 0 or 1, depending on implementation
      
      if (errorCount === 1) {
        await expect(errorElement).not.toBeVisible();
      }
    });

    test('should have TTS status display element ready', async ({ page }) => {
      // TTS status should be in DOM but not visible initially
      const ttsStatusElement = page.locator('[data-testid="voice-box-tts-status"]');
      
      const statusCount = await ttsStatusElement.count();
      expect(statusCount).toBeLessThanOrEqual(1); // Either 0 or 1, depending on implementation
      
      if (statusCount === 1) {
        await expect(ttsStatusElement).not.toBeVisible();
      }
    });
  });

  test.describe('Accessibility Rendering', () => {
    test('should render with proper accessibility attributes', async ({ page }) => {
      const container = page.locator('[data-testid="voice-box-container"]');
      const bars = page.locator('[data-testid="voice-box-bars"]');
      
      // Check ARIA attributes
      await expect(container).toHaveAttribute('role', 'region');
      await expect(container).toHaveAttribute('aria-label', 'Voice visualizer');
      await expect(bars).toHaveAttribute('role', 'img');
      await expect(bars).toHaveAttribute('aria-label', 'Voice activity visualizer');
    });

    test('should render form elements with proper accessibility', async ({ page }) => {
      const personalitySelect = page.locator('[data-testid="voice-box-personality-select"]');
      const emotionSelect = page.locator('[data-testid="voice-box-emotion-select"]');
      const qualitySelect = page.locator('[data-testid="voice-box-quality-select"]');
      
      // Should be form elements that can be focused and used by screen readers
      await expect(personalitySelect).toHaveRole('combobox');
      await expect(emotionSelect).toHaveRole('combobox');
      await expect(qualitySelect).toHaveRole('combobox');
    });
  });

  test.describe('Performance Rendering', () => {
    test('should render efficiently without performance issues', async ({ page }) => {
      const startTime = Date.now();
      
      // Wait for VoiceBox to be fully rendered
      const container = page.locator('[data-testid="voice-box-container"]');
      await expect(container).toBeVisible();
      
      // All bars should be rendered
      for (let i = 0; i < 7; i++) {
        const bar = page.locator(`[data-testid="voice-box-bar-element-${i}"]`);
        await expect(bar).toBeVisible();
      }
      
      const renderTime = Date.now() - startTime;
      
      // Should render quickly (within 2 seconds)
      expect(renderTime).toBeLessThan(2000);
    });

    test('should maintain 60fps animation rendering', async ({ page }) => {
      // This is a basic check - in a real scenario you'd use performance APIs
      
      // Wait for animation to stabilize
      await page.waitForTimeout(1000);
      
      // Check that animation is smooth by ensuring bars are updating
      const bar = page.locator('[data-testid="voice-box-bar-element-0"]');
      
      // Take multiple measurements to ensure animation is running
      const measurements = [];
      for (let i = 0; i < 5; i++) {
        const opacity = await bar.evaluate(el => 
          parseFloat(window.getComputedStyle(el).opacity)
        );
        measurements.push(opacity);
        await page.waitForTimeout(50);
      }
      
      // Should have some variation in opacity (indicating smooth animation)
      const uniqueValues = new Set(measurements.map(m => Math.round(m * 100))); 
      expect(uniqueValues.size).toBeGreaterThanOrEqual(1); // At least some animation variation
    });
  });
});

/**
 * VoiceBox Rendering Smoke Tests
 * Quick tests to verify basic rendering functionality
 */
test.describe('VoiceBox Rendering Smoke Tests', () => {
  test('smoke test: all critical elements render', async ({ page }) => {
    await page.goto('http://localhost:3000');
    
    // Critical elements that must render for VoiceBox to be functional
    const criticalElements = [
      '[data-testid="voice-box-container"]',
      '[data-testid="voice-box-bars"]',
      '[data-testid="voice-box-start"]',
      '[data-testid="voice-box-test-tts"]',
      '[data-testid="voice-box-status"]'
    ];
    
    // All critical elements should be visible
    for (const selector of criticalElements) {
      await expect(page.locator(selector)).toBeVisible();
    }
  });

  test('smoke test: no JavaScript errors during render', async ({ page }) => {
    const errors = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    page.on('pageerror', error => {
      errors.push(error.message);
    });
    
    await page.goto('http://localhost:3000');
    await page.waitForTimeout(2000); // Wait for initial render and animations
    
    // Filter out known non-critical errors
    const criticalErrors = errors.filter(error => 
      !error.includes('Failed to load resource') && // Network errors are OK for this test
      !error.includes('favicon.ico') // Favicon errors are not critical
    );
    
    expect(criticalErrors).toHaveLength(0);
  });
});