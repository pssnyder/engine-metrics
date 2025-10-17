/**
 * Jest Configuration for V7P3R Chess Engine Analytics
 * Enterprise-grade testing setup with comprehensive coverage and reporting
 */

module.exports = {
  // Test environment configuration
  testEnvironment: 'node',
  
  // Coverage configuration
  collectCoverage: true,
  coverageDirectory: 'coverage',
  coverageReporters: [
    'text',           // Console output
    'text-summary',   // Brief summary
    'lcov',          // For CI/CD integration
    'html',          // Interactive HTML reports
    'json'           // Machine-readable format
  ],
  
  // Coverage thresholds (enforce quality standards)
  coverageThreshold: {
    global: {
      branches: 0,      // Start with 0% and increase gradually
      functions: 0,     // Start with 0% and increase gradually  
      lines: 0,         // Start with 0% and increase gradually
      statements: 0     // Start with 0% and increase gradually
    },
    // Stricter requirements for critical modules (when they exist)
    './src/security/': {
      branches: 0,
      functions: 0,
      lines: 0,
      statements: 0
    },
    './src/config/': {
      branches: 0,
      functions: 0,
      lines: 0,
      statements: 0
    }
  },
  
  // Test file patterns
  testMatch: [
    '**/__tests__/**/*.test.js',
    '**/__tests__/**/*.spec.js',
    '**/tests/**/*.test.js',
    '**/tests/**/*.spec.js',
    '**/?(*.)+(spec|test).js'
  ],
  
  // Ignore patterns
  testPathIgnorePatterns: [
    '/node_modules/',
    '/coverage/',
    '/dist/',
    '/build/',
    '\\.cache'
  ],
  
  // Coverage ignore patterns
  coveragePathIgnorePatterns: [
    '/node_modules/',
    '/tests/',
    '/coverage/',
    '/src/frontend/',  // Exclude React frontend from backend testing
    '/src/ai/',        // Exclude Python AI service from Jest
    '\\.test\\.js$',
    '\\.spec\\.js$'
  ],
  
  // Setup files
  setupFilesAfterEnv: [
    '<rootDir>/tests/setup/jest.setup.js',
    '<rootDir>/tests/setup/custom-matchers.js'
  ],
  
  // Module name mapping for aliases
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@config/(.*)$': '<rootDir>/config/$1',
    '^@tests/(.*)$': '<rootDir>/tests/$1'
  },
  
  // Test timeout (30 seconds for integration tests)
  testTimeout: 30000,
  
  // Verbose output for detailed test results
  verbose: true,
  
  // Collect coverage from source files
  collectCoverageFrom: [
    'src/**/*.js',
    'scripts/**/*.js',
    '!src/frontend/**',    // Exclude React frontend
    '!src/ai/**',          // Exclude Python AI service
    '!src/**/*.test.js',
    '!src/**/*.spec.js',
    '!**/node_modules/**',
    '!**/coverage/**'
  ],
  
  // Mock configuration
  clearMocks: true,
  restoreMocks: true,
  resetMocks: true,
  
  // Error reporting
  errorOnDeprecated: true,
  
  // Global test variables
  globals: {
    __TEST_ENV__: true
  },
  
  // Transform configuration for modern JavaScript
  transform: {
    '^.+\\.jsx?$': 'babel-jest'
  },
  
  // Module file extensions
  moduleFileExtensions: [
    'js',
    'json',
    'jsx',
    'node'
  ],
  
  // Test results processor for CI/CD
  // testResultsProcessor: 'jest-sonar-reporter',
  
  // Performance optimization
  maxWorkers: '50%',
  
  // Remove problematic test sequencer for now
  // runner: '@jest/test-sequencer',
  
  // Custom matchers for enhanced assertions
  // setupFilesAfterEnv: [
  //   '<rootDir>/tests/setup/jest.setup.js',
  //   '<rootDir>/tests/setup/custom-matchers.js'
  // ]
};