# Alice AI Assistant - Developer Testing Guide

**Comprehensive testing execution guide for Alice development team**

---

## 🎯 Quick Start

### Essential Commands

```bash
# Backend testing (from server/ directory)
make test              # Run all tests
make test-unit         # Unit tests only
make test-integration  # Integration tests only
make test-swedish      # Swedish NLU tests
make test-coverage     # Tests with coverage report

# Frontend testing (from web/ directory)
npm test               # Jest unit tests
npm run test:e2e       # Playwright E2E tests
npm run test:watch     # Interactive test runner
npm run test:coverage  # Coverage report

# Full stack testing (from root directory)
make test-all          # Complete test suite
make test-ci           # Simulate CI environment
make test-performance  # Performance benchmarks
```

### Pre-Development Checklist

Before starting development on Alice:

- [ ] **Environment Setup**: Virtual environment activated
- [ ] **Dependencies Current**: `pip install -r requirements-dev.txt`
- [ ] **Database Ready**: Test database accessible
- [ ] **Services Running**: Backend server and frontend dev server
- [ ] **Tests Passing**: Baseline test suite green

---

## 🏗️ Test Architecture Overview

Alice follows the **Test Pyramid** approach:

```
         🔺 E2E Tests (Few, Slow, High Value)
      🔺🔺 Integration Tests (Some, Medium Speed)  
   🔺🔺🔺 Unit Tests (Many, Fast, Focused)
```

### Test Categories

| Test Type | Purpose | Speed | Reliability | When to Run |
|-----------|---------|--------|-------------|-------------|
| **Unit** | Function/class validation | ⚡ Fast | 🟢 High | Every commit |
| **Integration** | Component interaction | ⚙️ Medium | 🟡 Medium | Before PR |
| **E2E** | User workflow validation | 🐌 Slow | 🔴 Variable | CI/CD pipeline |
| **Performance** | Latency/throughput | 🐌 Slow | 🟡 Medium | Nightly/releases |

---

## 🔧 Backend Testing (Python)

### Development Environment Setup

```bash
# Navigate to server directory
cd server/

# Install development dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Set environment variables
export ALICE_TEST_MODE=true
export DATABASE_URL=sqlite:///test_alice.db

# Verify setup
python -m pytest --version
python -c "import pytest; print('✅ Pytest ready')"
```

### Running Backend Tests

#### Unit Tests

```bash
# All unit tests
python -m pytest tests/ -m unit -v

# Specific test file
python -m pytest tests/test_agent_planner.py -v

# Specific test method
python -m pytest tests/test_agent_planner.py::TestAgentPlanner::test_create_simple_music_plan -v

# With coverage
python -m pytest tests/ -m unit --cov=. --cov-report=html

# Parallel execution (faster)
python -m pytest tests/ -m unit -n auto
```

#### Integration Tests

```bash
# All integration tests
python -m pytest tests/ -m integration -v

# API integration tests
python -m pytest tests/test_*_integration.py -v

# Database integration tests
python -m pytest tests/ -m "integration and database" -v
```

#### Swedish Language Tests

```bash
# All Swedish NLU tests
python -m pytest tests/ -m swedish -v

# Swedish voice command tests
python -m pytest tests/test_swedish_voice_commands.py -v

# Swedish datetime parsing
python -m pytest tests/test_swedish_datetime_parsing.py -v

# With accuracy reporting
python -m pytest tests/ -m swedish --tb=short -v
```

#### RAG System Tests

```bash
# RAG precision tests
python -m pytest tests/ -m rag -v

# Precision@5 specific test
python -m pytest tests/test_rag_precision.py::TestRAGPrecision::test_precision_at_5 -v

# Swedish document retrieval
python -m pytest tests/test_rag_precision.py::TestRAGPrecision::test_swedish_document_retrieval -v
```

### Test Configuration

#### pytest.ini

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --durations=10
markers =
    unit: Unit tests
    integration: Integration tests
    swedish: Swedish language tests
    rag: RAG system tests
    performance: Performance tests
    slow: Slow running tests
asyncio_mode = auto
```

#### Coverage Configuration

```ini
# .coveragerc
[run]
source = .
omit = 
    tests/*
    */venv/*
    */migrations/*
    */node_modules/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:

[html]
directory = htmlcov
```

### Debug and Troubleshooting

```bash
# Drop into debugger on failure
python -m pytest tests/test_failing.py --pdb

# Show all print statements
python -m pytest tests/test_debug.py -s

# Verbose failure information
python -m pytest tests/test_failing.py -vvv --tb=long

# Run specific failing test
python -m pytest tests/test_failing.py::test_specific_failure -x -vv
```

---

## 🌐 Frontend Testing (React/Next.js)

### Development Environment Setup

```bash
# Navigate to web directory
cd web/

# Install dependencies
npm ci

# Install Playwright browsers
npx playwright install

# Verify setup
npm run test -- --version
npx playwright --version
```

### Running Frontend Tests

#### Unit Tests (Jest)

```bash
# All unit tests
npm test

# Watch mode for development
npm run test:watch

# Coverage report
npm run test:coverage

# Update snapshots
npm test -- --updateSnapshot

# Specific test file
npm test VoiceBox.test.tsx

# Debug mode
npm test -- --no-cache --verbose
```

#### E2E Tests (Playwright)

```bash
# All E2E tests
npm run test:e2e

# Specific browser
npx playwright test --project=chromium

# Specific test file
npx playwright test voicebox-rendering.spec.ts

# Interactive mode
npx playwright test --ui

# Debug mode with visible browser
npx playwright test --headed --debug

# Generate code
npx playwright codegen localhost:3000
```

#### Visual Regression Tests

```bash
# Run visual tests
npx playwright test --grep="visual"

# Update baselines (when UI changes intentionally)
npx playwright test --grep="visual" --update-snapshots

# Compare specific component
npx playwright test visual-regression.spec.ts --project=chromium
```

### Frontend Test Configuration

#### Jest Configuration

```javascript
// jest.config.js
const nextJest = require('next/jest')

const createJestConfig = nextJest({
  dir: './',
})

const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  collectCoverageFrom: [
    'app/**/*.{js,jsx,ts,tsx}',
    'components/**/*.{js,jsx,ts,tsx}',
    'lib/**/*.{js,jsx,ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
  ],
  coverageThreshold: {
    global: {
      branches: 75,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/$1',
  },
}

module.exports = createJestConfig(customJestConfig)
```

#### Playwright Configuration

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['json', { outputFile: 'test-results.json' }],
    process.env.CI ? ['github'] : ['list']
  ],
  
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],
});
```

---

## 🔗 Integration Testing

### Full-Stack Testing Environment

```bash
# Terminal 1: Start backend
cd server/
export ALICE_TEST_MODE=true
python app.py

# Terminal 2: Start frontend  
cd web/
npm run dev

# Terminal 3: Run integration tests
cd web/
npm run test:integration
```

### Integration Test Categories

#### API Integration Tests

```bash
# Test API endpoints with real backend
python -m pytest tests/test_api_integration.py -v

# Test with external service mocking
python -m pytest tests/test_external_integration.py -v --mock-external
```

#### Full-Stack E2E Tests

```bash
# Complete user workflows
npx playwright test full-stack-*.spec.ts

# Voice workflow end-to-end
npx playwright test full-stack-voice.spec.ts

# Calendar integration workflow  
npx playwright test full-stack-calendar.spec.ts
```

### Database Integration Testing

```bash
# Set up test database
export DATABASE_URL=postgresql://user:pass@localhost/test_alice

# Run database integration tests
python -m pytest tests/ -m "integration and database" -v

# Test database migrations
python -m pytest tests/test_database_migrations.py -v
```

---

## ⚡ Performance Testing

### Backend Performance Tests

```bash
# Voice pipeline latency tests
python -m pytest tests/test_voice_latency.py -v

# RAG search performance
python -m pytest tests/test_rag_performance.py -v

# API response time benchmarks
python -m pytest tests/ -m performance --benchmark-only

# Memory usage profiling
python -m pytest tests/test_memory_usage.py -v --profile
```

### Frontend Performance Tests

```bash
# Lighthouse CI performance testing
npm install -g @lhci/cli
lhci autorun --collect.url=http://localhost:3000

# Web Vitals testing
npx playwright test performance.spec.ts

# Bundle size analysis
npm run analyze
```

### Load Testing

```bash
# Install k6 for load testing
# macOS: brew install k6
# Ubuntu: sudo apt install k6

# Run load tests
k6 run tests/performance/load-test.js

# Voice pipeline load test
k6 run tests/performance/voice-load-test.js

# API endpoint stress test
k6 run tests/performance/api-stress-test.js
```

---

## 🛡️ Security Testing

### Automated Security Tests

```bash
# Python security scanning
bandit -r server/ -f json -o security-report.json

# Dependency vulnerability scanning
safety check -r server/requirements.txt --json

# Frontend security audit
npm audit --audit-level=high

# Container security scanning (if using Docker)
docker scan alice-server:latest
```

### Manual Security Testing

```bash
# Test input validation
python -m pytest tests/test_security_validation.py -v

# Test authentication flows
python -m pytest tests/test_auth_security.py -v

# Test SQL injection prevention
python -m pytest tests/test_sql_injection.py -v

# Test XSS prevention
npx playwright test security/xss-prevention.spec.ts
```

---

## 📊 Test Reporting and Metrics

### Coverage Reports

```bash
# Backend coverage
cd server/
python -m pytest --cov=. --cov-report=html
# Open htmlcov/index.html

# Frontend coverage  
cd web/
npm run test:coverage
# Open coverage/lcov-report/index.html

# Combined coverage report
make coverage-report
```

### Test Metrics Dashboard

```bash
# Generate test metrics
python scripts/generate_test_metrics.py

# Performance benchmark report
python -m pytest --benchmark-only --benchmark-json=benchmark.json

# Test execution time analysis
python scripts/analyze_test_performance.py
```

### CI/CD Integration

```bash
# Upload coverage to Codecov
codecov --token=$CODECOV_TOKEN

# Upload test results to GitHub
# Automatically handled by GitHub Actions workflows
```

---

## 🐛 Debugging Test Failures

### Common Issues and Solutions

#### Backend Test Issues

```bash
# Database connection issues
export DATABASE_URL=sqlite:///test_alice.db
python -c "from database import engine; print('✅ DB connected')"

# Import path issues
export PYTHONPATH=$PWD/server:$PYTHONPATH

# Environment variable issues
cp .env.example .env.test
export $(cat .env.test | xargs)

# Async test issues
python -m pytest tests/test_async.py -v --asyncio-mode=auto
```

#### Frontend Test Issues

```bash
# Node modules issues
rm -rf node_modules package-lock.json
npm ci

# Playwright browser issues
npx playwright install --with-deps

# Port conflicts
lsof -i :3000  # Check what's using port 3000
kill -9 <PID>  # Kill process if needed

# Mock service worker issues
npm run msw:init  # Reset service worker
```

#### Integration Test Issues

```bash
# Service startup timing
sleep 15  # Allow more time for services to start

# Port binding conflicts
netstat -tulpn | grep :8000  # Check port usage

# Database state issues
python -c "from database import reset_test_db; reset_test_db()"
```

### Debug Modes

```bash
# Backend debugging
python -m pytest tests/failing_test.py --pdb -s

# Frontend debugging  
npm test -- --no-cache --verbose --detectOpenHandles

# E2E debugging
npx playwright test failing-test.spec.ts --headed --debug --slow-mo=1000
```

---

## 📋 Testing Checklists

### Pre-Commit Testing

Before committing code:

- [ ] **Unit tests pass**: `make test-unit`
- [ ] **Lint checks pass**: `make lint`  
- [ ] **Type checking passes**: `make typecheck`
- [ ] **No security issues**: `make security-scan`
- [ ] **Coverage maintained**: Check coverage report

### Pre-PR Testing

Before creating a pull request:

- [ ] **All backend tests pass**: `make test-backend`
- [ ] **All frontend tests pass**: `make test-frontend` 
- [ ] **Integration tests pass**: `make test-integration`
- [ ] **Swedish NLU tests pass**: `make test-swedish`
- [ ] **Performance tests pass**: `make test-performance`
- [ ] **Documentation updated**: Relevant docs reflect changes

### Pre-Release Testing

Before tagging a release:

- [ ] **Full test suite passes**: `make test-all`
- [ ] **Load testing completed**: `make test-load`
- [ ] **Security audit clean**: `make security-audit`
- [ ] **Cross-browser testing**: E2E tests on all browsers
- [ ] **Mobile responsiveness**: Mobile test suite passes
- [ ] **Accessibility compliance**: WCAG 2.1 AA standards met

---

## 🎯 Test-Driven Development (TDD)

### TDD Cycle for Alice

1. **Red**: Write failing test for new feature
2. **Green**: Write minimal code to make test pass
3. **Refactor**: Improve code while keeping tests green

#### Example: Adding New Voice Command

```python
# 1. RED: Write failing test
def test_weather_voice_command():
    parser = SwedishNLUParser()
    result = parser.parse("vad är väder idag")
    
    assert result.intent == "GET_WEATHER"
    assert result.slots["date"] == "today"
    assert result.confidence > 0.8

# 2. GREEN: Implement minimal feature
class SwedishNLUParser:
    def parse(self, text):
        if "väder" in text:
            return NLUResult(
                intent="GET_WEATHER",
                slots={"date": "today"} if "idag" in text else {},
                confidence=0.9
            )

# 3. REFACTOR: Improve implementation
# Add proper regex patterns, improve accuracy, etc.
```

### TDD Benefits for Alice

- **Swedish Language Coverage**: Ensures all Swedish commands tested
- **Voice Pipeline Reliability**: Critical path always validated  
- **API Contract Testing**: Ensures backward compatibility
- **Performance Regression Prevention**: Benchmarks in tests

---

## 🔍 Advanced Testing Techniques

### Property-Based Testing

```python
# Using Hypothesis for property-based testing
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=100))
def test_voice_input_never_crashes(voice_input):
    """Voice parser should never crash on any input"""
    parser = SwedishNLUParser()
    result = parser.parse(voice_input)
    assert result is not None
    assert hasattr(result, 'intent')
    assert hasattr(result, 'confidence')
```

### Mutation Testing

```bash
# Install mutation testing tool
pip install mutmut

# Run mutation testing
mutmut run --paths-to-mutate server/core/

# View mutation results
mutmut results
mutmut html  # Generate HTML report
```

### Contract Testing

```python
# API contract testing with Pact
from pact import Consumer, Provider

# Define contract between frontend and backend
pact = Consumer('alice-frontend').has_pact_with(Provider('alice-backend'))

pact.given('user has Swedish voice enabled') \
    .upon_receiving('a Swedish voice command') \
    .with_request('POST', '/api/voice/process', body={'text': 'spela musik'}) \
    .will_respond_with(200, body={'intent': 'PLAY_MUSIC'})
```

### Chaos Engineering Testing

```python
# Simulate network failures, database issues
import random

class ChaosTest:
    def test_voice_pipeline_resilience(self):
        with chaos_network_delay(200):  # Add 200ms delay
            result = process_voice_command("spela musik")
            assert result.success  # Should still work
            
        with chaos_database_failure():  # Simulate DB failure  
            result = process_voice_command("visa kalender")
            assert result.fallback_response is not None
```

---

## 📚 Additional Resources

### Documentation

- **Testing Framework Documentation**: [TESTING.md](../TESTING.md)
- **API Documentation**: [API.md](../API.md)
- **Contributing Guidelines**: [CONTRIBUTING.md](../CONTRIBUTING.md)
- **Git Workflow**: [docs/GIT_WORKFLOW.md](./GIT_WORKFLOW.md)

### Tools and Libraries

#### Backend Testing
- **pytest**: Primary testing framework
- **pytest-cov**: Coverage reporting
- **pytest-asyncio**: Async test support
- **httpx**: HTTP client testing
- **respx**: HTTP mocking
- **factory-boy**: Test data generation

#### Frontend Testing
- **Jest**: Unit testing framework
- **Playwright**: E2E testing
- **Testing Library**: React component testing
- **MSW**: API mocking
- **Lighthouse CI**: Performance testing

#### Security Testing
- **bandit**: Python security scanner
- **safety**: Dependency vulnerability scanner
- **OWASP ZAP**: Web app security testing
- **semgrep**: Static analysis

### Best Practices References

- **Test Pyramid**: [Martin Fowler's Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)
- **TDD Guidelines**: [Test-Driven Development](https://www.agilealliance.org/glossary/tdd/)
- **Property-Based Testing**: [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- **Playwright Best Practices**: [Playwright Testing Guide](https://playwright.dev/docs/best-practices)

---

**This developer testing guide ensures all Alice contributors can effectively test their code and maintain the high quality standards expected for a production AI assistant.**

---

**Last Updated**: January 22, 2025  
**Version**: 1.0  
**Maintained By**: Alice QA Team  
**Review Schedule**: Quarterly