/**
 * Custom Jest Matchers
 * Extended assertions for V7P3R Chess Engine Analytics testing
 */

// Custom matcher to check if a value is a valid chess game
expect.extend({
  toBeValidChessGame(received) {
    const pass = received &&
      typeof received.id === 'string' &&
      typeof received.rated === 'boolean' &&
      received.players &&
      received.players.white &&
      received.players.black &&
      typeof received.moves === 'string';

    if (pass) {
      return {
        message: () => `expected ${received} not to be a valid chess game`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected ${received} to be a valid chess game with id, rated, players, and moves`,
        pass: false,
      };
    }
  },

  // Custom matcher for Lichess API response format
  toBeValidLichessResponse(received) {
    const pass = received &&
      (received.data || received.error) &&
      typeof received.status !== 'undefined';

    if (pass) {
      return {
        message: () => `expected ${received} not to be a valid Lichess API response`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected ${received} to be a valid Lichess API response with data/error and status`,
        pass: false,
      };
    }
  },

  // Custom matcher for Firebase document structure
  toBeValidFirebaseDoc(received) {
    const pass = received &&
      typeof received.id === 'string' &&
      typeof received.data === 'function' &&
      typeof received.exists === 'boolean';

    if (pass) {
      return {
        message: () => `expected ${received} not to be a valid Firebase document`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected ${received} to be a valid Firebase document with id, data(), and exists`,
        pass: false,
      };
    }
  },

  // Custom matcher for environment variable validation
  toBeValidEnvironmentConfig(received) {
    const requiredVars = [
      'NODE_ENV',
      'FIREBASE_PROJECT_ID',
      'LICHESS_API_TOKEN'
    ];

    const missingVars = requiredVars.filter(varName => !received[varName]);
    const pass = missingVars.length === 0;

    if (pass) {
      return {
        message: () => `expected environment config to be missing required variables`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected environment config to have all required variables, missing: ${missingVars.join(', ')}`,
        pass: false,
      };
    }
  },

  // Custom matcher for performance benchmarks
  toMeetPerformanceBenchmark(received, benchmark) {
    const { executionTime, memoryUsage, throughput } = received;
    let pass = true;
    const failures = [];

    if (benchmark.maxExecutionTime && executionTime > benchmark.maxExecutionTime) {
      pass = false;
      failures.push(`execution time ${executionTime}ms exceeds max ${benchmark.maxExecutionTime}ms`);
    }

    if (benchmark.maxMemoryUsage && memoryUsage > benchmark.maxMemoryUsage) {
      pass = false;
      failures.push(`memory usage ${memoryUsage}MB exceeds max ${benchmark.maxMemoryUsage}MB`);
    }

    if (benchmark.minThroughput && throughput < benchmark.minThroughput) {
      pass = false;
      failures.push(`throughput ${throughput} below min ${benchmark.minThroughput}`);
    }

    if (pass) {
      return {
        message: () => `expected performance metrics not to meet benchmark`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected performance metrics to meet benchmark, failures: ${failures.join(', ')}`,
        pass: false,
      };
    }
  },

  // Custom matcher for security validation
  toBeSecure(received) {
    const securityChecks = [
      // No exposed secrets
      !received.toString().includes('lip_'),
      !received.toString().includes('AIza'),
      !received.toString().includes('sk_'),
      // No hardcoded passwords
      !received.toString().toLowerCase().includes('password'),
      !received.toString().toLowerCase().includes('secret'),
    ];

    const pass = securityChecks.every(check => check);

    if (pass) {
      return {
        message: () => `expected ${received} not to be secure`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected ${received} to be secure (no exposed secrets or hardcoded credentials)`,
        pass: false,
      };
    }
  },

  // Custom matcher for async operations
  toResolveWithin(received, timeoutMs) {
    const startTime = Date.now();
    return received.then(
      (result) => {
        const executionTime = Date.now() - startTime;
        const pass = executionTime <= timeoutMs;
        
        if (pass) {
          return {
            message: () => `expected promise not to resolve within ${timeoutMs}ms`,
            pass: true,
          };
        } else {
          return {
            message: () => `expected promise to resolve within ${timeoutMs}ms, took ${executionTime}ms`,
            pass: false,
          };
        }
      },
      (error) => {
        return {
          message: () => `expected promise to resolve, but it rejected with: ${error}`,
          pass: false,
        };
      }
    );
  }
});

console.log('🎯 Custom Jest matchers loaded successfully!');