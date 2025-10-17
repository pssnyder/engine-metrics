/**
 * Utilities Module Unit Tests
 * Tests for utility functions and helper methods
 */

describe('Utilities Module', () => {
  describe('Test Utilities', () => {
    test('should generate valid test timestamps', () => {
      const timestamp = global.testUtils.generateTestTimestamp();
      const parsedDate = new Date(timestamp);

      expect(timestamp).toMatch(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z/);
      expect(parsedDate).toBeInstanceOf(Date);
      expect(parsedDate.getTime()).not.toBeNaN();
    });

    test('should generate mock chess game data', () => {
      const mockGame = global.testUtils.generateMockGame();

      expect(mockGame).toBeValidChessGame();
      expect(mockGame.id).toBeDefined();
      expect(mockGame.players.white.user.name).toBe('v7p3r_bot');
      expect(typeof mockGame.players.white.rating).toBe('number');
      expect(typeof mockGame.moves).toBe('string');
    });

    test('should generate mock Firebase document', () => {
      const mockDoc = global.testUtils.generateMockFirebaseDoc();

      expect(mockDoc).toBeValidFirebaseDoc();
      expect(mockDoc.id).toBeDefined();
      expect(typeof mockDoc.data).toBe('function');
      expect(typeof mockDoc.exists).toBe('boolean');
      expect(mockDoc.ref.path).toBeDefined();
    });

    test('should generate random strings with different lengths', () => {
      const lengths = [5, 10, 15, 20];
      
      lengths.forEach(length => {
        const randomString = global.testUtils.generateRandomString(length);
        expect(randomString).toHaveLength(length);
        expect(typeof randomString).toBe('string');
        expect(randomString).toMatch(/^[a-z0-9]+$/);
      });
    });
  });

  describe('Async Utilities', () => {
    test('should provide accurate delay functionality', async () => {
      const delays = [50, 100, 200];
      
      for (const delayMs of delays) {
        const startTime = Date.now();
        await global.testUtils.delay(delayMs);
        const actualDelay = Date.now() - startTime;
        
        expect(actualDelay).toBeGreaterThanOrEqual(delayMs);
        expect(actualDelay).toBeLessThan(delayMs + 50); // Allow 50ms tolerance
      }
    });

    test('should handle concurrent delays', async () => {
      const startTime = Date.now();
      
      const promises = [
        global.testUtils.delay(100),
        global.testUtils.delay(100),
        global.testUtils.delay(100)
      ];
      
      await Promise.all(promises);
      const totalTime = Date.now() - startTime;
      
      // Should run concurrently, not sequentially
      expect(totalTime).toBeLessThan(200); // Much less than 300ms (3 * 100ms)
      expect(totalTime).toBeGreaterThanOrEqual(100);
    });

    test('should work with async/await patterns', async () => {
      const promise = global.testUtils.delay(100);
      
      expect(promise).toBeInstanceOf(Promise);
      await expect(promise).resolves.toBeUndefined();
    });
  });

  describe('Environment Mocking', () => {
    test('should mock environment variables temporarily', () => {
      const originalValue = process.env.TEST_VAR;
      
      const restoreEnv = global.testUtils.mockEnv({
        TEST_VAR: 'test-value',
        ANOTHER_VAR: 'another-value'
      });
      
      expect(process.env.TEST_VAR).toBe('test-value');
      expect(process.env.ANOTHER_VAR).toBe('another-value');
      
      restoreEnv();
      
      expect(process.env.TEST_VAR).toBe(originalValue);
      expect(process.env.ANOTHER_VAR).toBeUndefined();
    });

    test('should handle nested environment mocking', () => {
      const restoreEnv1 = global.testUtils.mockEnv({
        NESTED_VAR: 'level1'
      });
      
      expect(process.env.NESTED_VAR).toBe('level1');
      
      const restoreEnv2 = global.testUtils.mockEnv({
        NESTED_VAR: 'level2'
      });
      
      expect(process.env.NESTED_VAR).toBe('level2');
      
      restoreEnv2();
      // Note: This will restore to the state before restoreEnv2, not restoreEnv1
      // This is expected behavior for this simple implementation
      
      restoreEnv1();
    });
  });

  describe('Data Generation', () => {
    test('should generate unique identifiers', () => {
      const ids = Array.from({ length: 100 }, () => 
        global.testUtils.generateRandomString(10)
      );
      
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(ids.length); // All should be unique
    });

    test('should generate realistic chess game data', () => {
      const games = Array.from({ length: 10 }, () => 
        global.testUtils.generateMockGame()
      );
      
      games.forEach(game => {
        expect(game).toBeValidChessGame();
        expect(game.players.white.user.name).toBe('v7p3r_bot');
        expect(game.rated).toBe(true);
        expect(game.variant).toBe('standard');
        expect(['bullet', 'blitz', 'rapid', 'classical']).toContain(game.speed);
        expect(typeof game.createdAt).toBe('number');
        expect(game.createdAt).toBeGreaterThan(0);
      });
    });

    test('should generate Firebase document structures', () => {
      const docs = Array.from({ length: 5 }, () => 
        global.testUtils.generateMockFirebaseDoc()
      );
      
      docs.forEach(doc => {
        expect(doc).toBeValidFirebaseDoc();
        expect(doc.id).toHaveLength(20);
        expect(typeof doc.data).toBe('function');
        expect(doc.exists).toBe(true);
        expect(doc.ref.path).toMatch(/^[a-zA-Z0-9_/]+$/);
      });
    });
  });
});