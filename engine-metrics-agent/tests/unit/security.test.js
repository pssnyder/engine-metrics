/**
 * Security Module Unit Tests
 * Tests for the security validation and secret management functionality
 */

describe('Security Module', () => {
  // Test data setup
  const mockEnvironmentVars = {
    NODE_ENV: 'test',
    FIREBASE_PROJECT_ID: 'test-project',
    LICHESS_API_TOKEN: 'test-token'
  };

  beforeEach(() => {
    // Reset environment for each test
    jest.clearAllMocks();
  });

  describe('Environment Variable Validation', () => {
    test('should validate required environment variables', () => {
      // Test our custom matcher
      expect(mockEnvironmentVars).toBeValidEnvironmentConfig();
    });

    test('should fail validation when required variables are missing', () => {
      const incompleteEnv = {
        NODE_ENV: 'test'
        // Missing FIREBASE_PROJECT_ID and LICHESS_API_TOKEN
      };

      expect(() => {
        expect(incompleteEnv).toBeValidEnvironmentConfig();
      }).toThrow();
    });

    test('should handle environment variable mocking', () => {
      const restoreEnv = global.testUtils.mockEnv({
        TEST_VAR: 'test-value'
      });

      expect(process.env.TEST_VAR).toBe('test-value');

      // Restore original environment
      restoreEnv();
      expect(process.env.TEST_VAR).toBeUndefined();
    });
  });

  describe('Secret Detection', () => {
    test('should detect exposed secrets in strings', () => {
      const secureString = 'This is a safe configuration';
      const insecureString = 'token: lip_1234567890abcdef';

      expect(secureString).toBeSecure();
      expect(() => {
        expect(insecureString).toBeSecure();
      }).toThrow();
    });

    test('should identify various secret patterns', () => {
      const secretPatterns = [
        'AIzaSyB234567890abcdef', // Google API key
        'sk_test_1234567890abcdef', // Stripe key
        'lip_1234567890abcdef' // Lichess token
      ];

      secretPatterns.forEach(secret => {
        expect(() => {
          expect(secret).toBeSecure();
        }).toThrow();
      });
    });
  });

  describe('Configuration Validation', () => {
    test('should validate secure configuration objects', () => {
      const secureConfig = {
        environment: 'test',
        features: {
          analytics: true,
          monitoring: false
        }
      };

      expect(secureConfig).toBeSecure();
    });

    test('should reject configuration with embedded secrets', () => {
      const insecureConfig = {
        environment: 'test',
        apiKey: 'lip_dangerous_secret_key'  // This contains a Lichess token pattern
      };

      expect(() => {
        expect(JSON.stringify(insecureConfig)).toBeSecure();
      }).toThrow();
    });
  });

  describe('Test Utilities', () => {
    test('should generate random test strings', () => {
      const randomString1 = global.testUtils.generateRandomString();
      const randomString2 = global.testUtils.generateRandomString();

      expect(randomString1).not.toBe(randomString2);
      expect(randomString1).toHaveLength(10);
      expect(typeof randomString1).toBe('string');
    });

    test('should generate random strings of specified length', () => {
      const shortString = global.testUtils.generateRandomString(5);
      const longString = global.testUtils.generateRandomString(20);

      expect(shortString).toHaveLength(5);
      expect(longString).toHaveLength(20);
    });

    test('should provide async delay utility', async () => {
      const startTime = Date.now();
      await global.testUtils.delay(100);
      const endTime = Date.now();

      expect(endTime - startTime).toBeGreaterThanOrEqual(100);
      expect(endTime - startTime).toBeLessThan(150); // Allow some tolerance
    });
  });
});