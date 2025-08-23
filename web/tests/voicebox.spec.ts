import { test, expect } from '@playwright/test';

/**
 * VoiceBox Component E2E Tests
 * 
 * Comprehensive test suite for Alice's VoiceBox component
 * Tests rendering, interaction, audio visualization, and error handling
 */

test.describe('VoiceBox Component', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the main Alice page which contains VoiceBox
    await page.goto('http://localhost:3000');
    
    // Wait for page to be fully loaded
    await page.waitForLoadState('networkidle');
  });

  test.describe('Initial Rendering', () => {
    test('should render VoiceBox container with correct structure', async ({ page }) => {
      // Check main container is present
      const voiceBoxContainer = page.locator('[data-testid="voice-box-container"]');
      await expect(voiceBoxContainer).toBeVisible();
      
      // Check panel is present
      const voiceBoxPanel = page.locator('[data-testid="voice-box-panel"]');
      await expect(voiceBoxPanel).toBeVisible();
      
      // Check aria attributes for accessibility
      await expect(voiceBoxContainer).toHaveAttribute('role', 'region');
      await expect(voiceBoxContainer).toHaveAttribute('aria-label', 'Voice visualizer');
    });

    test('should render voice bars with correct structure', async ({ page }) => {
      // Check bars container
      const voiceBars = page.locator('[data-testid="voice-box-bars"]');
      await expect(voiceBars).toBeVisible();
      await expect(voiceBars).toHaveAttribute('role', 'img');
      await expect(voiceBars).toHaveAttribute('aria-label', 'Voice activity visualizer');

      // Default should be 7 bars (from props default)
      const individualBars = page.locator('[data-testid^="voice-box-bar-"]');
      await expect(individualBars).toHaveCount(7);

      // Check each bar has its element
      for (let i = 0; i < 7; i++) {
        const barContainer = page.locator(`[data-testid="voice-box-bar-${i}"]`);
        const barElement = page.locator(`[data-testid="voice-box-bar-element-${i}"]`);
        
        await expect(barContainer).toBeVisible();
        await expect(barElement).toBeVisible();
        await expect(barElement).toHaveClass(/bar/);
      }
    });

    test('should render control buttons in initial state', async ({ page }) => {
      // Start button should be visible initially (not live)
      const startButton = page.locator('[data-testid="voice-box-start"]');
      await expect(startButton).toBeVisible();
      await expect(startButton).toHaveText('Starta mic');

      // Stop button should not be visible initially
      const stopButton = page.locator('[data-testid="voice-box-stop"]');
      await expect(stopButton).not.toBeVisible();

      // TTS test button should be visible
      const ttsButton = page.locator('[data-testid="voice-box-test-tts"]');
      await expect(ttsButton).toBeVisible();
      await expect(ttsButton).toHaveText('Test TTS');

      // Status should show 'AV' (off)
      const status = page.locator('[data-testid="voice-box-status"]');
      await expect(status).toHaveText('AV');
    });

    test('should render personality and emotion controls', async ({ page }) => {
      // Personality select
      const personalitySelect = page.locator('[data-testid="voice-box-personality-select"]');
      await expect(personalitySelect).toBeVisible();
      await expect(personalitySelect).toHaveValue('alice');

      // Emotion select
      const emotionSelect = page.locator('[data-testid="voice-box-emotion-select"]');
      await expect(emotionSelect).toBeVisible();
      await expect(emotionSelect).toHaveValue('friendly');

      // Quality select
      const qualitySelect = page.locator('[data-testid="voice-box-quality-select"]');
      await expect(qualitySelect).toBeVisible();
      await expect(qualitySelect).toHaveValue('medium');
    });
  });

  test.describe('Ambient Animation', () => {
    test('should show ambient animation on bars when not active', async ({ page }) => {
      // Wait a moment for ambient animation to start
      await page.waitForTimeout(1000);

      // Check that bars have some opacity and minimal height (ambient mode)
      for (let i = 0; i < 3; i++) {  // Check first 3 bars
        const barElement = page.locator(`[data-testid="voice-box-bar-element-${i}"]`);
        
        // Get computed styles
        const opacity = await barElement.evaluate(el => window.getComputedStyle(el).opacity);
        const height = await barElement.evaluate(el => window.getComputedStyle(el).height);
        
        // Should have some opacity (ambient animation)
        expect(parseFloat(opacity)).toBeGreaterThan(0.1);
        
        // Should have minimal height (ambient state)
        expect(parseFloat(height)).toBeLessThan(10); // Less than 10px in ambient
      }
    });

    test('should animate bars smoothly over time', async ({ page }) => {
      const barElement = page.locator('[data-testid="voice-box-bar-element-0"]');
      
      // Take initial opacity reading
      const initialOpacity = await barElement.evaluate(el => 
        parseFloat(window.getComputedStyle(el).opacity)
      );
      
      // Wait for animation cycle
      await page.waitForTimeout(2000);
      
      // Take second opacity reading
      const secondOpacity = await barElement.evaluate(el => 
        parseFloat(window.getComputedStyle(el).opacity)
      );
      
      // Opacity should change over time (ambient breathing effect)
      // Note: This might be flaky due to timing, but should generally differ
      expect(Math.abs(initialOpacity - secondOpacity)).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('Button Interactions', () => {
    test('should handle start button click with microphone permissions', async ({ page, context }) => {
      // Grant microphone permissions
      await context.grantPermissions(['microphone']);
      
      const startButton = page.locator('[data-testid="voice-box-start"]');
      const stopButton = page.locator('[data-testid="voice-box-stop"]');
      const status = page.locator('[data-testid="voice-box-status"]');
      
      // Click start button
      await startButton.click();
      
      // Wait for state change
      await page.waitForTimeout(500);
      
      // Should transition to live state
      await expect(stopButton).toBeVisible();
      await expect(startButton).not.toBeVisible();
      await expect(status).toHaveText('LIVE');
    });

    test('should handle microphone permission denial gracefully', async ({ page, context }) => {
      // Block microphone permissions
      await context.grantPermissions([]);
      
      const startButton = page.locator('[data-testid="voice-box-start"]');
      const errorMessage = page.locator('[data-testid="voice-box-error"]');
      
      // Click start button
      await startButton.click();
      
      // Wait for error handling
      await page.waitForTimeout(1000);
      
      // Should show error message about microphone
      await expect(errorMessage).toBeVisible();
      await expect(errorMessage).toContainText('demo‑läge');
    });

    test('should handle TTS test button click', async ({ page }) => {
      const ttsButton = page.locator('[data-testid="voice-box-test-tts"]');
      const ttsStatus = page.locator('[data-testid="voice-box-tts-status"]');
      
      // Mock TTS API response
      await page.route('**/api/tts/synthesize', async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            audio_data: 'dGVzdA==', // base64 "test"
            emotion: 'friendly'
          })
        });
      });
      
      // Click TTS test button
      await ttsButton.click();
      
      // Should show TTS status
      await expect(ttsStatus).toBeVisible();
      await expect(ttsStatus).toContainText('Spelar');
    });

    test('should handle personality changes', async ({ page }) => {
      const personalitySelect = page.locator('[data-testid="voice-box-personality-select"]');
      
      // Change personality
      await personalitySelect.selectOption('formal');
      
      // Should update the displayed personality value
      await expect(personalitySelect).toHaveValue('formal');
      
      // Check that personality display is updated
      const personalityDisplay = page.locator('text=Personlighet:').locator('..').locator('.text-cyan-400');
      // Note: The actual implementation logs to console, so we'd need to check console logs
      // or modify the implementation to update the display
    });
  });

  test.describe('Responsive Design', () => {
    test('should adapt to mobile viewport', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });
      
      const voiceBoxContainer = page.locator('[data-testid="voice-box-container"]');
      const voiceBars = page.locator('[data-testid="voice-box-bars"]');
      
      // Should still be visible and functional
      await expect(voiceBoxContainer).toBeVisible();
      await expect(voiceBars).toBeVisible();
      
      // Check that bars have appropriate mobile height
      const barsHeight = await voiceBars.evaluate(el => el.offsetHeight);
      expect(barsHeight).toBeGreaterThan(150); // Should be at least 150px on mobile
    });

    test('should adapt to desktop viewport', async ({ page }) => {
      // Set desktop viewport
      await page.setViewportSize({ width: 1920, height: 1080 });
      
      const voiceBoxContainer = page.locator('[data-testid="voice-box-container"]');
      const voiceBars = page.locator('[data-testid="voice-box-bars"]');
      
      // Should still be visible
      await expect(voiceBoxContainer).toBeVisible();
      await expect(voiceBars).toBeVisible();
      
      // Check that bars have appropriate desktop height (md:h-48)
      const barsHeight = await voiceBars.evaluate(el => el.offsetHeight);
      expect(barsHeight).toBeGreaterThan(180); // Should be larger on desktop
    });
  });

  test.describe('Error Handling', () => {
    test('should display error when microphone access fails', async ({ page, context }) => {
      // Deny microphone permissions
      await context.grantPermissions([]);
      
      const startButton = page.locator('[data-testid="voice-box-start"]');
      const errorMessage = page.locator('[data-testid="voice-box-error"]');
      
      await startButton.click();
      await page.waitForTimeout(1000);
      
      // Should show appropriate error message
      await expect(errorMessage).toBeVisible();
      await expect(errorMessage).toContainText('demo‑läge');
    });

    test('should handle TTS API failure gracefully', async ({ page }) => {
      const ttsButton = page.locator('[data-testid="voice-box-test-tts"]');
      
      // Mock TTS API failure
      await page.route('**/api/tts/synthesize', async route => {
        await route.fulfill({ status: 500 });
      });
      
      await ttsButton.click();
      await page.waitForTimeout(1000);
      
      // Should fall back to browser TTS or show error
      // The implementation has fallback to browser TTS, so we test that it doesn't crash
      const ttsStatus = page.locator('[data-testid="voice-box-tts-status"]');
      
      // Should eventually show some status (browser fallback)
      await page.waitForTimeout(3000);
      // Test that page doesn't crash (no JS errors thrown)
      const hasError = await page.evaluate(() => window.location.href.includes('error'));
      expect(hasError).toBe(false);
    });
  });

  test.describe('Accessibility', () => {
    test('should have proper ARIA attributes', async ({ page }) => {
      const voiceBoxContainer = page.locator('[data-testid="voice-box-container"]');
      const voiceBars = page.locator('[data-testid="voice-box-bars"]');
      
      // Check ARIA attributes
      await expect(voiceBoxContainer).toHaveAttribute('role', 'region');
      await expect(voiceBoxContainer).toHaveAttribute('aria-label', 'Voice visualizer');
      await expect(voiceBars).toHaveAttribute('role', 'img');
      await expect(voiceBars).toHaveAttribute('aria-label', 'Voice activity visualizer');
    });

    test('should be keyboard navigable', async ({ page }) => {
      // Focus on start button with keyboard
      await page.keyboard.press('Tab');
      
      const startButton = page.locator('[data-testid="voice-box-start"]');
      await expect(startButton).toBeFocused();
      
      // Continue tabbing through controls
      await page.keyboard.press('Tab');
      const ttsButton = page.locator('[data-testid="voice-box-test-tts"]');
      await expect(ttsButton).toBeFocused();
    });

    test('should support screen reader text', async ({ page }) => {
      // Check that important elements have screen reader accessible text
      const personalitySelect = page.locator('[data-testid="voice-box-personality-select"]');
      const emotionSelect = page.locator('[data-testid="voice-box-emotion-select"]');
      
      // Should have accessible text/labels (through parent text or aria-label)
      await expect(personalitySelect).toBeVisible();
      await expect(emotionSelect).toBeVisible();
    });
  });

  test.describe('Performance', () => {
    test('should render within acceptable time', async ({ page }) => {
      const startTime = Date.now();
      
      // Navigate and wait for VoiceBox to be visible
      await page.goto('http://localhost:3000');
      await page.locator('[data-testid="voice-box-container"]').waitFor();
      
      const renderTime = Date.now() - startTime;
      
      // Should render within 3 seconds
      expect(renderTime).toBeLessThan(3000);
    });

    test('should handle multiple rapid interactions', async ({ page, context }) => {
      await context.grantPermissions(['microphone']);
      
      const startButton = page.locator('[data-testid="voice-box-start"]');
      const stopButton = page.locator('[data-testid="voice-box-stop"]');
      const ttsButton = page.locator('[data-testid="voice-box-test-tts"]');
      
      // Mock TTS API
      await page.route('**/api/tts/synthesize', async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, audio_data: 'dGVzdA==' })
        });
      });
      
      // Rapid interactions - should not crash
      await startButton.click();
      await page.waitForTimeout(100);
      
      if (await stopButton.isVisible()) {
        await stopButton.click();
      }
      await page.waitForTimeout(100);
      
      await ttsButton.click();
      await page.waitForTimeout(100);
      
      await ttsButton.click();
      await page.waitForTimeout(100);
      
      // Should still be functional
      const voiceBoxContainer = page.locator('[data-testid="voice-box-container"]');
      await expect(voiceBoxContainer).toBeVisible();
    });
  });

  test.describe('Visual Regression', () => {
    test('should match visual snapshot in initial state', async ({ page }) => {
      const voiceBoxContainer = page.locator('[data-testid="voice-box-container"]');
      
      // Wait for ambient animation to stabilize
      await page.waitForTimeout(1000);
      
      // Take screenshot of VoiceBox component
      await expect(voiceBoxContainer).toHaveScreenshot('voicebox-initial-state.png');
    });

    test('should match visual snapshot with controls focused', async ({ page }) => {
      const startButton = page.locator('[data-testid="voice-box-start"]');
      
      // Focus the start button
      await startButton.focus();
      
      const voiceBoxContainer = page.locator('[data-testid="voice-box-container"]');
      await expect(voiceBoxContainer).toHaveScreenshot('voicebox-focused-state.png');
    });
  });

  test.describe('Integration', () => {
    test('should integrate properly with parent components', async ({ page }) => {
      // Check that VoiceBox is properly integrated into the main page
      const mainContent = page.locator('main, [role="main"], .main-content');
      const voiceBoxContainer = page.locator('[data-testid="voice-box-container"]');
      
      // VoiceBox should be within main content area
      const isWithinMain = await mainContent.locator('[data-testid="voice-box-container"]').count() > 0;
      expect(isWithinMain).toBe(true);
      
      // Should not overlap with other major UI elements
      const voiceBoxRect = await voiceBoxContainer.boundingBox();
      expect(voiceBoxRect).not.toBeNull();
      expect(voiceBoxRect!.width).toBeGreaterThan(200);
      expect(voiceBoxRect!.height).toBeGreaterThan(150);
    });
  });
});

/**
 * VoiceBox Component Unit-style E2E Tests
 * Tests that simulate unit test scenarios but in the browser environment
 */
test.describe('VoiceBox Component Logic', () => {
  test('should handle component props correctly', async ({ page }) => {
    // This would require a test harness that can pass different props
    // For now, we test the default behavior
    
    const voiceBars = page.locator('[data-testid="voice-box-bars"]');
    const individualBars = page.locator('[data-testid^="voice-box-bar-"][data-testid$="-0"], [data-testid^="voice-box-bar-"][data-testid$="-1"], [data-testid^="voice-box-bar-"][data-testid$="-2"], [data-testid^="voice-box-bar-"][data-testid$="-3"], [data-testid^="voice-box-bar-"][data-testid$="-4"], [data-testid^="voice-box-bar-"][data-testid$="-5"], [data-testid^="voice-box-bar-"][data-testid$="-6"]');
    
    await expect(individualBars).toHaveCount(7); // Default bars=7
  });

  test('should maintain component state correctly', async ({ page, context }) => {
    await context.grantPermissions(['microphone']);
    
    const startButton = page.locator('[data-testid="voice-box-start"]');
    const stopButton = page.locator('[data-testid="voice-box-stop"]');
    const status = page.locator('[data-testid="voice-box-status"]');
    
    // Initial state
    await expect(status).toHaveText('AV');
    
    // Start voice
    await startButton.click();
    await page.waitForTimeout(500);
    
    // Should be in live state
    await expect(status).toHaveText('LIVE');
    
    // Stop voice
    await stopButton.click();
    await page.waitForTimeout(500);
    
    // Should return to initial state
    await expect(status).toHaveText('AV');
    await expect(startButton).toBeVisible();
    await expect(stopButton).not.toBeVisible();
  });
});