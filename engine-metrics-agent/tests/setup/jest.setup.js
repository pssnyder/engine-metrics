/**
 * Jest Setup Configuration
 * Global test setup and environment configuration for V7P3R Chess Engine Analytics
 */

// Set test environment variables
process.env.NODE_ENV = 'test';
process.env.LOG_LEVEL = 'error'; // Reduce noise during testing

// Global test timeout for async operations
jest.setTimeout(30000);

// Mock console methods in tests to reduce noise
const originalConsole = { ...console };

beforeAll(() => {
  // Reduce console noise during testing
  console.log = jest.fn();
  console.info = jest.fn();
  console.warn = jest.fn();
  console.debug = jest.fn();
  // Keep console.error for debugging test failures
});

afterAll(() => {
  // Restore console methods after tests
  Object.assign(console, originalConsole);
});

// Global test utilities
global.testUtils = {
  // Async delay utility for testing timing
  delay: (ms) => new Promise(resolve => setTimeout(resolve, ms)),
  
  // Generate test timestamps
  generateTestTimestamp: () => new Date().toISOString(),
  
  // Mock environment variables
  mockEnv: (envVars) => {
    const originalEnv = { ...process.env };
    Object.assign(process.env, envVars);
    return () => {
      process.env = originalEnv;
    };
  },
  
  // Generate random test data
  generateRandomString: (length = 10) => {
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  },
  
  // Mock Lichess game data
  generateMockGame: () => ({
    id: global.testUtils.generateRandomString(8),
    rated: true,
    variant: 'standard',
    speed: 'blitz',
    perf: 'blitz',
    createdAt: Date.now(),
    lastMoveAt: Date.now(),
    status: 'mate',
    players: {
      white: {
        user: { name: 'v7p3r_bot' },
        rating: 1388,
        ratingDiff: 10
      },
      black: {
        user: { name: 'opponent' },
        rating: 1400,
        ratingDiff: -10
      }
    },
    winner: 'white',
    moves: 'e4 e5 Nf3 Nc6 Bc4 Bc5'
  }),
  
  // Mock Firebase document
  generateMockFirebaseDoc: () => ({
    id: global.testUtils.generateRandomString(20),
    data: () => ({}),
    exists: true,
    ref: {
      path: 'games/test'
    }
  })
};

// Global error handler for unhandled promises
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

// Suppress Firebase warnings in tests
process.env.SUPPRESS_NO_CONFIG_WARNING = 'true';
process.env.FIREBASE_CONFIG = JSON.stringify({
  projectId: 'test-project',
  apiKey: 'test-key'
});

// Mock fetch for API testing
global.fetch = jest.fn();

// Clean up after each test
afterEach(() => {
  // Clear all mocks
  jest.clearAllMocks();
  
  // Reset fetch mock
  if (global.fetch.mockClear) {
    global.fetch.mockClear();
  }
});

console.log('🧪 Jest test environment initialized successfully!');