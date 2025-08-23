import { test, expect } from '@playwright/test'

/**
 * HUD Components Integration Tests
 * Tests VoiceBox and CalendarWidget with data-testid attributes
 */

test.describe('Alice HUD Components', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the main HUD page
    await page.goto('/')
  })

  test.describe('VoiceBox Component', () => {
    test('should render VoiceBox with all required data-testids', async ({ page }) => {
      // Check main container
      const voiceBoxContainer = page.getByTestId('voice-box-container')
      await expect(voiceBoxContainer).toBeVisible()

      // Check main panel
      const voiceBoxPanel = page.getByTestId('voice-box-panel')
      await expect(voiceBoxPanel).toBeVisible()

      // Check bars container
      const voiceBoxBars = page.getByTestId('voice-box-bars')
      await expect(voiceBoxBars).toBeVisible()

      // Check individual bars (should have at least 5 bars by default)
      for (let i = 0; i < 5; i++) {
        const bar = page.getByTestId(`voice-box-bar-${i}`)
        await expect(bar).toBeVisible()
        
        const barElement = page.getByTestId(`voice-box-bar-element-${i}`)
        await expect(barElement).toBeVisible()
      }

      // Check control buttons
      const startButton = page.getByTestId('voice-box-start')
      await expect(startButton).toBeVisible()
      await expect(startButton).toHaveText('Starta mic')

      const testTtsButton = page.getByTestId('voice-box-test-tts')
      await expect(testTtsButton).toBeVisible()
      await expect(testTtsButton).toHaveText('Test TTS')

      // Check status indicator
      const statusIndicator = page.getByTestId('voice-box-status')
      await expect(statusIndicator).toBeVisible()
      await expect(statusIndicator).toHaveText('AV')
    })

    test('should show VoiceBox controls when started', async ({ page }) => {
      const startButton = page.getByTestId('voice-box-start')
      
      // Grant microphone permissions programmatically (if possible)
      await page.context().grantPermissions(['microphone'])
      
      // Click start button
      await startButton.click()
      
      // After starting, should show stop button
      await expect(page.getByTestId('voice-box-stop')).toBeVisible({ timeout: 5000 })
      
      // Status should change to LIVE
      const statusIndicator = page.getByTestId('voice-box-status')
      await expect(statusIndicator).toHaveText('LIVE')
    })

    test('should show VoiceBox settings selectors', async ({ page }) => {
      // Check personality selector
      const personalitySelect = page.getByTestId('voice-box-personality-select')
      await expect(personalitySelect).toBeVisible()
      
      // Check emotion selector
      const emotionSelect = page.getByTestId('voice-box-emotion-select')
      await expect(emotionSelect).toBeVisible()
      
      // Check quality selector
      const qualitySelect = page.getByTestId('voice-box-quality-select')
      await expect(qualitySelect).toBeVisible()
    })

    test('should handle VoiceBox errors gracefully', async ({ page }) => {
      // Block microphone permissions
      await page.context().clearPermissions()
      
      const startButton = page.getByTestId('voice-box-start')
      await startButton.click()
      
      // Should show error message
      const errorMessage = page.getByTestId('voice-box-error')
      await expect(errorMessage).toBeVisible({ timeout: 5000 })
      await expect(errorMessage).toContainText('demo‑läge')
    })

    test('should test TTS functionality', async ({ page }) => {
      const testTtsButton = page.getByTestId('voice-box-test-tts')
      await testTtsButton.click()
      
      // Should show TTS status
      const ttsStatus = page.getByTestId('voice-box-tts-status')
      await expect(ttsStatus).toBeVisible({ timeout: 3000 })
      await expect(ttsStatus).toContainText('Alice')
    })
  })

  test.describe('CalendarWidget Component', () => {
    test('should render CalendarWidget in compact mode', async ({ page }) => {
      // Navigate to a page that shows compact calendar widget
      // (This assumes there's a page or component that renders it in compact mode)
      const compactWidget = page.getByTestId('calendar-widget-compact')
      
      if (await compactWidget.isVisible()) {
        // Check title
        const title = page.getByTestId('calendar-widget-title')
        await expect(title).toBeVisible()
        await expect(title).toHaveText('Kalender')
        
        // Check create button
        const createButton = page.getByTestId('calendar-widget-create-button')
        await expect(createButton).toBeVisible()
        
        // Check events list
        const eventsList = page.getByTestId('calendar-widget-events-list')
        await expect(eventsList).toBeVisible()
        
        // Should show either loading, no events, or actual events
        const loading = page.getByTestId('calendar-widget-loading')
        const noEvents = page.getByTestId('calendar-widget-no-events')
        
        // One of these should be visible
        await expect(
          loading.or(noEvents).or(page.getByTestId('calendar-widget-event-').first())
        ).toBeVisible()
      }
    })

    test('should render CalendarWidget in full mode', async ({ page }) => {
      const fullWidget = page.getByTestId('calendar-widget-full')
      
      if (await fullWidget.isVisible()) {
        // Check title
        const title = page.getByTestId('calendar-widget-full-title')
        await expect(title).toBeVisible()
        await expect(title).toHaveText('Kalender')
        
        // Check create button
        const createButton = page.getByTestId('calendar-widget-full-create-button')
        await expect(createButton).toBeVisible()
        await expect(createButton).toContainText('Ny')
      }
    })

    test('should show quick create form when create button is clicked', async ({ page }) => {
      const fullWidget = page.getByTestId('calendar-widget-full')
      
      if (await fullWidget.isVisible()) {
        const createButton = page.getByTestId('calendar-widget-full-create-button')
        await createButton.click()
        
        // Should show quick create form
        const quickCreateForm = page.getByTestId('calendar-widget-quick-create')
        await expect(quickCreateForm).toBeVisible()
        
        // Should show input field
        const input = page.getByTestId('calendar-widget-quick-create-input')
        await expect(input).toBeVisible()
        await expect(input).toHaveAttribute('placeholder')
      }
    })

    test('should interact with calendar events', async ({ page }) => {
      // This test assumes there are events loaded
      // Wait for any event to appear
      const firstEvent = page.getByTestId('calendar-widget-event-').first()
      
      if (await firstEvent.isVisible({ timeout: 2000 })) {
        // Event should be clickable
        await expect(firstEvent).toBeVisible()
        
        // Click should work (won't verify the action, just that it's clickable)
        await firstEvent.click()
      }
    })
  })

  test.describe('HUD Integration', () => {
    test('should have both VoiceBox and CalendarWidget accessible', async ({ page }) => {
      // Both components should be present on the main HUD page
      const voiceBoxContainer = page.getByTestId('voice-box-container')
      
      // VoiceBox should always be present
      await expect(voiceBoxContainer).toBeVisible()
      
      // CalendarWidget might be in compact or full mode, or both
      const compactCalendar = page.getByTestId('calendar-widget-compact')
      const fullCalendar = page.getByTestId('calendar-widget-full')
      
      // At least one calendar widget should be visible
      await expect(compactCalendar.or(fullCalendar)).toBeVisible()
    })

    test('should maintain Swedish localization', async ({ page }) => {
      // Check that Swedish text is present in components
      await expect(page.getByText('Starta mic')).toBeVisible()
      await expect(page.getByText('Kalender')).toBeVisible()
    })

    test('should have proper accessibility attributes', async ({ page }) => {
      // VoiceBox should have proper ARIA labels
      const voiceBoxContainer = page.getByTestId('voice-box-container')
      await expect(voiceBoxContainer).toHaveAttribute('role', 'region')
      await expect(voiceBoxContainer).toHaveAttribute('aria-label', 'Voice visualizer')
      
      // Bars should have proper role
      const voiceBoxBars = page.getByTestId('voice-box-bars')
      await expect(voiceBoxBars).toHaveAttribute('role', 'img')
      await expect(voiceBoxBars).toHaveAttribute('aria-label', 'Voice activity visualizer')
    })
  })

  test.describe('Responsive Behavior', () => {
    test('should work on different screen sizes', async ({ page }) => {
      // Test desktop view
      await page.setViewportSize({ width: 1280, height: 720 })
      
      const voiceBoxContainer = page.getByTestId('voice-box-container')
      await expect(voiceBoxContainer).toBeVisible()
      
      // Test tablet view
      await page.setViewportSize({ width: 768, height: 1024 })
      await expect(voiceBoxContainer).toBeVisible()
      
      // Test mobile view
      await page.setViewportSize({ width: 375, height: 667 })
      await expect(voiceBoxContainer).toBeVisible()
    })
  })

  test.describe('Error Handling', () => {
    test('should handle network failures gracefully', async ({ page }) => {
      // Intercept calendar API calls and make them fail
      await page.route('**/api/calendar/**', (route) => {
        route.abort()
      })
      
      // Calendar widget should still render
      const compactCalendar = page.getByTestId('calendar-widget-compact')
      const fullCalendar = page.getByTestId('calendar-widget-full')
      
      if (await compactCalendar.or(fullCalendar).isVisible()) {
        // Should not crash the page
        await expect(page.getByTestId('calendar-widget-title')).toBeVisible()
      }
    })

    test('should handle TTS failures gracefully', async ({ page }) => {
      // Intercept TTS API calls and make them fail
      await page.route('**/api/tts/**', (route) => {
        route.abort()
      })
      
      const testTtsButton = page.getByTestId('voice-box-test-tts')
      await testTtsButton.click()
      
      // Should not crash, might show error or fallback
      const voiceBoxContainer = page.getByTestId('voice-box-container')
      await expect(voiceBoxContainer).toBeVisible()
    })
  })
})