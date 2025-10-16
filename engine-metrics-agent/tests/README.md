# Test Directory Structure

This directory contains comprehensive tests for the V7P3R Chess Analytics pipeline.

## Structure

- **unit/**: Unit tests for individual functions and modules
- **integration/**: Integration tests for service interactions
- **e2e/**: End-to-end tests for complete workflows

## Running Tests

```bash
# All tests
npm test

# Unit tests only
npm run test:unit

# Integration tests only
npm run test:integration

# End-to-end tests only
npm run test:e2e

# Python tests
npm run test:python
```

## Test Configuration

- **Jest**: JavaScript/TypeScript testing framework
- **pytest**: Python testing framework
- **Firebase Emulator Suite**: Local testing environment
- **Playwright**: Browser automation for E2E tests

## Coverage Requirements

- Minimum 80% code coverage
- Critical paths must have 100% coverage
- Integration tests for all external API calls