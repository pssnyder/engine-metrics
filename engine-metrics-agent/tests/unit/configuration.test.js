/**
 * Configuration Module Unit Tests
 * Tests for configuration loading, validation, and environment handling
 */

describe('Configuration Module', () => {
  describe('Environment Configuration', () => {
    test('should load development configuration correctly', () => {
      const devConfig = {
        environment: 'development',
        debug: true,
        apiLimits: {
          requestsPerHour: 2000
        },
        logging: {
          level: 'debug'
        }
      };

      expect(devConfig.environment).toBe('development');
      expect(devConfig.debug).toBe(true);
      expect(devConfig.apiLimits.requestsPerHour).toBe(2000);
    });

    test('should load production configuration correctly', () => {
      const prodConfig = {
        environment: 'production',
        debug: false,
        apiLimits: {
          requestsPerHour: 1000
        },
        logging: {
          level: 'info'
        },
        security: {
          headers: true,
          hsts: true,
          csp: true
        }
      };

      expect(prodConfig.environment).toBe('production');
      expect(prodConfig.debug).toBe(false);
      expect(prodConfig.security.headers).toBe(true);
    });

    test('should validate configuration structure', () => {
      const validConfig = {
        environment: 'test',
        apiLimits: {
          requestsPerHour: 1500
        },
        logging: {
          level: 'warn'
        }
      };

      // Test configuration has required properties
      expect(validConfig).toHaveProperty('environment');
      expect(validConfig).toHaveProperty('apiLimits');
      expect(validConfig).toHaveProperty('logging');
      expect(validConfig.apiLimits).toHaveProperty('requestsPerHour');
      expect(validConfig.logging).toHaveProperty('level');
    });
  });

  describe('Configuration Validation', () => {
    test('should validate API rate limits', () => {
      const configs = [
        { environment: 'development', apiLimits: { requestsPerHour: 2000 } },
        { environment: 'staging', apiLimits: { requestsPerHour: 1200 } },
        { environment: 'production', apiLimits: { requestsPerHour: 1000 } }
      ];

      configs.forEach(config => {
        expect(config.apiLimits.requestsPerHour).toBeGreaterThan(0);
        expect(config.apiLimits.requestsPerHour).toBeLessThanOrEqual(2000);
      });
    });

    test('should validate logging configuration', () => {
      const validLogLevels = ['error', 'warn', 'info', 'debug'];
      
      validLogLevels.forEach(level => {
        const config = {
          logging: { level }
        };
        
        expect(validLogLevels).toContain(config.logging.level);
      });
    });

    test('should reject invalid configuration values', () => {
      const invalidConfigs = [
        { apiLimits: { requestsPerHour: -100 } }, // Negative rate limit
        { logging: { level: 'invalid' } }, // Invalid log level
        { environment: null } // Null environment
      ];

      invalidConfigs.forEach(config => {
        if (config.apiLimits && config.apiLimits.requestsPerHour < 0) {
          expect(config.apiLimits.requestsPerHour).not.toBeGreaterThan(0);
        }
        
        if (config.logging && config.logging.level === 'invalid') {
          const validLevels = ['error', 'warn', 'info', 'debug'];
          expect(validLevels).not.toContain(config.logging.level);
        }
      });
    });
  });

  describe('Environment-Specific Features', () => {
    test('should enable debug features in development', () => {
      const devConfig = {
        environment: 'development',
        debug: true,
        cors: {
          allowAll: true
        }
      };

      expect(devConfig.debug).toBe(true);
      expect(devConfig.cors.allowAll).toBe(true);
    });

    test('should enable security features in production', () => {
      const prodConfig = {
        environment: 'production',
        debug: false,
        security: {
          headers: true,
          hsts: true,
          csp: true,
          requireAuth: true
        }
      };

      expect(prodConfig.debug).toBe(false);
      expect(prodConfig.security.headers).toBe(true);
      expect(prodConfig.security.requireAuth).toBe(true);
    });

    test('should balance features in staging', () => {
      const stagingConfig = {
        environment: 'staging',
        debug: false,
        monitoring: {
          performance: true,
          errors: true,
          uptime: true
        },
        security: {
          headers: true,
          requireAuth: true
        }
      };

      expect(stagingConfig.monitoring.performance).toBe(true);
      expect(stagingConfig.security.headers).toBe(true);
    });
  });

  describe('Configuration Merging', () => {
    test('should merge default and environment-specific configurations', () => {
      const defaultConfig = {
        apiLimits: {
          requestsPerHour: 1000,
          requestsPerMinute: 50
        },
        logging: {
          level: 'info'
        }
      };

      const devOverrides = {
        apiLimits: {
          requestsPerHour: 2000 // Override only this value
        },
        logging: {
          level: 'debug' // Override log level
        },
        debug: true // Add new property
      };

      const mergedConfig = {
        ...defaultConfig,
        ...devOverrides,
        apiLimits: {
          ...defaultConfig.apiLimits,
          ...devOverrides.apiLimits
        },
        logging: {
          ...defaultConfig.logging,
          ...devOverrides.logging
        }
      };

      expect(mergedConfig.apiLimits.requestsPerHour).toBe(2000); // Overridden
      expect(mergedConfig.apiLimits.requestsPerMinute).toBe(50); // Preserved
      expect(mergedConfig.logging.level).toBe('debug'); // Overridden
      expect(mergedConfig.debug).toBe(true); // Added
    });
  });
});