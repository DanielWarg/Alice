# Alice VoiceBox E2E Testing Guide

This directory contains End-to-End tests for Alice's VoiceBox component, specifically addressing Task 4: "VoiceBox i HUD har data-testid och e2e-test som verifierar rendering".

## Test Files

### `voicebox-rendering.spec.ts` ⭐ (Primary)
**Purpose**: Core rendering verification tests for Task 4 completion.

**Test Coverage**:
- ✅ All required `data-testid` attributes are present and correctly named
- ✅ Component renders properly within the HUD layout
- ✅ Essential rendering functionality works (controls, selections, animations)
- ✅ Error and status display elements are ready
- ✅ Accessibility attributes render correctly
- ✅ Performance rendering meets targets

**Key Test Categories**:
- **Data-testid Verification**: Confirms all required test IDs exist
- **HUD Integration**: Verifies proper integration into Alice's HUD
- **Essential Functionality**: Tests core rendering requirements
- **Smoke Tests**: Quick verification of critical elements

### `voicebox.spec.ts` (Comprehensive)
**Purpose**: Comprehensive E2E testing of all VoiceBox functionality.

**Test Coverage**:
- Initial rendering and structure
- Ambient animation behavior
- Button interactions and state changes
- Microphone permission handling
- TTS functionality
- Responsive design
- Error handling
- Accessibility
- Performance
- Visual regression testing

## Running the Tests

### Quick Commands

```bash
# Run all VoiceBox tests
npm run test:voicebox

# Run VoiceBox tests with UI mode
npm run test:voicebox:ui

# Run VoiceBox tests in headed mode (visible browser)
npm run test:voicebox:headed

# Run all E2E tests
npm run test:e2e

# Debug specific test
npx playwright test voicebox-rendering.spec.ts --debug
```

### Test Execution Examples

```bash
# Run only the rendering verification tests (Task 4)
npx playwright test voicebox-rendering

# Run with specific browser
npx playwright test voicebox --project=chromium

# Run tests with trace collection
npx playwright test voicebox --trace=on

# Generate HTML report
npx playwright test voicebox --reporter=html
```

## Required data-testid Attributes

The VoiceBox component includes these `data-testid` attributes for testing:

### Container Elements
- `voice-box-container` - Main VoiceBox wrapper
- `voice-box-panel` - Styled panel container  
- `voice-box-bars` - Bars visualization container

### Visualization Bars
- `voice-box-bar-{i}` - Individual bar containers (i = 0-6)
- `voice-box-bar-element-{i}` - Individual bar elements (i = 0-6)

### Control Buttons
- `voice-box-start` - Start microphone button
- `voice-box-stop` - Stop microphone button (shown when active)
- `voice-box-test-tts` - Test TTS button
- `voice-box-status` - Status display (LIVE/AV)

### Settings Controls
- `voice-box-personality-select` - Personality selection dropdown
- `voice-box-emotion-select` - Emotion selection dropdown
- `voice-box-quality-select` - Voice quality selection dropdown

### Status Elements
- `voice-box-error` - Error message display
- `voice-box-tts-status` - TTS status message display

## Test Environment Setup

### Prerequisites

1. **Node.js 18+** installed
2. **Alice development server** running on `http://localhost:3000`
3. **Playwright** installed (`npm install @playwright/test`)

### Environment Variables

```bash
# Optional: Custom base URL
export BASE_URL=http://localhost:3000

# Test environment flag
export NODE_ENV=test
```

### Browser Permissions

Tests require microphone permissions for full functionality:

```javascript
// Granted in tests with:
await context.grantPermissions(['microphone']);

// Denied for error testing:
await context.grantPermissions([]);
```

## Test Results and Reports

### HTML Report
After running tests, view the HTML report:
```bash
npx playwright show-report
```

### Test Artifacts
- Screenshots: `test-results/`
- Videos: `test-results/` (on failure)
- Traces: `test-results/` (when enabled)
- Reports: `playwright-report/`

### CI/CD Integration
Tests generate JUnit XML for CI systems:
```bash
# Output: test-results.xml
npm run test:e2e
```

## Accessibility Testing

VoiceBox tests include accessibility verification:
- ARIA attributes (`role`, `aria-label`)
- Keyboard navigation
- Screen reader compatibility
- Color contrast (visual regression)

## Performance Testing

Performance targets verified:
- Initial render: < 2000ms
- Component load: < 3000ms  
- Animation smoothness: 60fps
- Memory usage: Stable over time

## Troubleshooting

### Common Issues

**Test fails with "Element not found"**
- Ensure Alice dev server is running
- Check that VoiceBox component is rendered on main page
- Verify `data-testid` attributes are present in component

**Microphone permission tests fail**
- Run tests in headed mode to see permission dialogs
- Check browser security policies
- Use `--headed` flag for debugging

**Animation tests are flaky**
- Increase wait timeouts for animation stabilization
- Use `page.waitForTimeout()` before measurements
- Consider visual regression testing instead

### Debug Commands

```bash
# Debug specific test with browser visible
npx playwright test voicebox-rendering --debug --headed

# Run with verbose output
npx playwright test voicebox --verbose

# Capture trace for debugging
npx playwright test voicebox --trace=on

# Run single test by name
npx playwright test -g "should have all required data-testid attributes"
```

## Contributing

When adding new VoiceBox functionality:

1. **Add data-testid** attributes to new elements
2. **Update tests** to cover new functionality  
3. **Follow naming convention**: `voice-box-{element-name}`
4. **Include accessibility** attributes and tests
5. **Add visual regression** tests for UI changes

### Test Naming Convention

```typescript
// Good test names
test('should have all required data-testid attributes')
test('should render control buttons with correct initial state')
test('should handle microphone permission denial gracefully')

// Avoid generic names  
test('button test')
test('rendering test')
```

## Task 4 Completion Verification

To verify Task 4 completion, run the primary test file:

```bash
npm run test:voicebox
```

**Success criteria:**
- ✅ All `data-testid` attributes present and correctly named
- ✅ Component renders properly in HUD context
- ✅ Essential rendering functionality verified
- ✅ No critical test failures
- ✅ All required elements visible and accessible

The tests specifically verify that:
1. VoiceBox has comprehensive `data-testid` attributes
2. Component renders correctly within the HUD layout
3. All visual elements are properly displayed
4. Interactions work as expected
5. Error handling renders appropriately

---

**Last Updated**: 2025-01-22  
**Test Coverage**: VoiceBox Component Rendering & Functionality  
**Task 4 Status**: ✅ Complete with comprehensive E2E verification