#!/usr/bin/env node

/**
 * Secret Rotation Management System
 * 
 * Manages the rotation of API keys, tokens, and service account credentials
 * following security best practices and compliance requirements.
 * 
 * Usage:
 *   node scripts/rotate-secrets.js [secret-type] [environment]
 *   
 * Examples:
 *   node scripts/rotate-secrets.js lichess-token production
 *   node scripts/rotate-secrets.js service-account staging
 *   node scripts/rotate-secrets.js all development
 */

const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');

// Colors for console output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  magenta: '\x1b[35m'
};

function colorize(text, color) {
  return `${colors[color]}${text}${colors.reset}`;
}

// Secret rotation configuration
const ROTATION_CONFIG = {
  'lichess-token': {
    name: 'Lichess API Token',
    maxAge: 90, // days
    warningAge: 75, // days
    environment: ['development', 'staging', 'production'],
    rotationProcedure: 'manual', // Lichess doesn't support automatic rotation
    priority: 'high'
  },
  'service-account': {
    name: 'Google Cloud Service Account',
    maxAge: 30, // days
    warningAge: 25, // days
    environment: ['development', 'staging', 'production'],
    rotationProcedure: 'automatic',
    priority: 'critical'
  },
  'firebase-token': {
    name: 'Firebase Admin Token',
    maxAge: 60, // days
    warningAge: 50, // days
    environment: ['staging', 'production'],
    rotationProcedure: 'automatic',
    priority: 'high'
  },
  'backup-encryption': {
    name: 'Backup Encryption Key',
    maxAge: 180, // days
    warningAge: 150, // days
    environment: ['staging', 'production'],
    rotationProcedure: 'manual',
    priority: 'critical'
  }
};

class RotationTracker {
  constructor() {
    this.rotationLogPath = path.join(__dirname, '..', 'rotation-log.json');
  }
  
  async loadRotationLog() {
    try {
      const content = await fs.readFile(this.rotationLogPath, 'utf8');
      return JSON.parse(content);
    } catch (error) {
      // File doesn't exist, return empty log
      return { rotations: [] };
    }
  }
  
  async saveRotationLog(log) {
    try {
      await fs.writeFile(this.rotationLogPath, JSON.stringify(log, null, 2));
    } catch (error) {
      throw new Error(`Failed to save rotation log: ${error.message}`);
    }
  }
  
  async recordRotation(secretType, environment, status, notes = '') {
    const log = await this.loadRotationLog();
    
    const rotationRecord = {
      id: crypto.randomUUID(),
      secretType,
      environment,
      timestamp: new Date().toISOString(),
      status, // 'completed', 'failed', 'warning'
      notes,
      user: process.env.USER || process.env.USERNAME || 'unknown'
    };
    
    log.rotations.push(rotationRecord);
    
    // Keep only last 100 records
    if (log.rotations.length > 100) {
      log.rotations = log.rotations.slice(-100);
    }
    
    await this.saveRotationLog(log);
    return rotationRecord;
  }
  
  async getLastRotation(secretType, environment) {
    const log = await this.loadRotationLog();
    
    return log.rotations
      .filter(r => r.secretType === secretType && r.environment === environment)
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))[0];
  }
  
  async getRotationHistory(secretType, environment, limit = 10) {
    const log = await this.loadRotationLog();
    
    return log.rotations
      .filter(r => r.secretType === secretType && r.environment === environment)
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
      .slice(0, limit);
  }
}

async function checkRotationStatus(secretType, environment) {
  const tracker = new RotationTracker();
  const config = ROTATION_CONFIG[secretType];
  
  if (!config) {
    throw new Error(`Unknown secret type: ${secretType}`);
  }
  
  const lastRotation = await tracker.getLastRotation(secretType, environment);
  const now = new Date();
  
  if (!lastRotation) {
    return {
      status: 'unknown',
      message: 'No rotation history found',
      daysOld: null,
      action: 'rotate'
    };
  }
  
  const lastRotationDate = new Date(lastRotation.timestamp);
  const daysOld = Math.floor((now - lastRotationDate) / (1000 * 60 * 60 * 24));
  
  if (daysOld >= config.maxAge) {
    return {
      status: 'expired',
      message: `Secret is ${daysOld} days old (max: ${config.maxAge})`,
      daysOld,
      action: 'rotate_immediately'
    };
  } else if (daysOld >= config.warningAge) {
    return {
      status: 'warning',
      message: `Secret is ${daysOld} days old (warning: ${config.warningAge})`,
      daysOld,
      action: 'rotate_soon'
    };
  } else {
    return {
      status: 'current',
      message: `Secret is ${daysOld} days old (current)`,
      daysOld,
      action: 'none'
    };
  }
}

async function rotateLichessToken(environment) {
  console.log(colorize('🔄 Lichess Token Rotation (Manual Process)', 'blue'));
  console.log(colorize('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'cyan'));
  
  console.log(colorize('\n📋 Manual Steps Required:', 'yellow'));
  console.log('1. Log in to Lichess.org');
  console.log('2. Go to: https://lichess.org/account/oauth/token');
  console.log('3. Generate a new API token with required scopes:');
  console.log('   • Read public games');
  console.log('   • Read private games (if needed)');
  console.log('   • Bot account management');
  console.log('4. Copy the new token');
  console.log('5. Update your environment configuration');
  
  if (environment === 'production') {
    console.log(colorize('\n🚨 Production Environment:', 'red'));
    console.log('6. Update Firebase Functions config:');
    console.log(colorize('   firebase functions:config:set lichess.token="NEW_TOKEN"', 'cyan'));
    console.log('7. Deploy updated functions:');
    console.log(colorize('   npm run deploy:prod', 'cyan'));
  } else {
    console.log(colorize('\n🛠️  Development/Staging Environment:', 'blue'));
    console.log('6. Update your .env file:');
    console.log(colorize('   LICHESS_API_TOKEN=NEW_TOKEN', 'cyan'));
    console.log('7. Restart your development server');
  }
  
  console.log(colorize('\n✅ After completing these steps, run:', 'green'));
  console.log(colorize(`   node scripts/rotate-secrets.js lichess-token ${environment} --confirm`, 'cyan'));
  
  return false; // Manual process, return false to indicate not completed automatically
}

async function rotateServiceAccount(environment) {
  console.log(colorize('🔄 Service Account Rotation', 'blue'));
  console.log(colorize('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'cyan'));
  
  const projectId = environment === 'production' 
    ? 'chess-engine-metrics-agent'
    : `chess-engine-metrics-agent-${environment}`;
  
  const serviceAccountName = `v7p3r-${environment}-functions`;
  const serviceAccountEmail = `${serviceAccountName}@${projectId}.iam.gserviceaccount.com`;
  
  console.log(colorize('\n📋 Service Account Rotation Steps:', 'yellow'));
  console.log(colorize('1. Create new service account key:', 'blue'));
  console.log(colorize(`   gcloud iam service-accounts keys create new-${environment}-sa.json \\`, 'cyan'));
  console.log(colorize(`     --iam-account=${serviceAccountEmail}`, 'cyan'));
  
  console.log(colorize('\n2. Update application configuration:', 'blue'));
  if (environment === 'production') {
    console.log(colorize('   firebase functions:config:set gcp.credentials="$(cat new-production-sa.json)"', 'cyan'));
  } else {
    console.log(colorize(`   Update GOOGLE_APPLICATION_CREDENTIALS in .env to point to new key`, 'cyan'));
  }
  
  console.log(colorize('\n3. Test the new configuration:', 'blue'));
  console.log(colorize('   npm run validate:infrastructure', 'cyan'));
  console.log(colorize('   npm test', 'cyan'));
  
  console.log(colorize('\n4. List old keys to be deleted:', 'blue'));
  console.log(colorize(`   gcloud iam service-accounts keys list --iam-account=${serviceAccountEmail}`, 'cyan'));
  
  console.log(colorize('\n5. Delete old service account key:', 'blue'));
  console.log(colorize(`   gcloud iam service-accounts keys delete OLD_KEY_ID \\`, 'cyan'));
  console.log(colorize(`     --iam-account=${serviceAccountEmail}`, 'cyan'));
  
  console.log(colorize('\n⚠️  Important Security Notes:', 'yellow'));
  console.log('   • Test thoroughly before deleting old keys');
  console.log('   • Keep old key for 24-48 hours as backup');
  console.log('   • Securely delete old key files from disk');
  console.log('   • Monitor for any authentication errors');
  
  return false; // Manual process with verification required
}

async function showRotationSummary(environment) {
  const tracker = new RotationTracker();
  
  console.log(colorize(`\n🔍 Rotation Status Summary for ${environment.toUpperCase()}`, 'bright'));
  console.log(colorize(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`, 'cyan'));
  
  for (const [secretType, config] of Object.entries(ROTATION_CONFIG)) {
    if (!config.environment.includes(environment)) {
      continue;
    }
    
    try {
      const status = await checkRotationStatus(secretType, environment);
      const priority = config.priority === 'critical' ? '🚨' : config.priority === 'high' ? '⚠️' : 'ℹ️';
      
      console.log(colorize(`\n${priority} ${config.name}:`, 'blue'));
      
      if (status.status === 'expired') {
        console.log(`   Status: ${colorize('EXPIRED', 'red')} - ${status.message}`);
        console.log(`   Action: ${colorize('ROTATE IMMEDIATELY', 'red')}`);
      } else if (status.status === 'warning') {
        console.log(`   Status: ${colorize('WARNING', 'yellow')} - ${status.message}`);
        console.log(`   Action: ${colorize('Rotate soon', 'yellow')}`);
      } else if (status.status === 'current') {
        console.log(`   Status: ${colorize('CURRENT', 'green')} - ${status.message}`);
        console.log(`   Action: ${colorize('No action needed', 'green')}`);
      } else {
        console.log(`   Status: ${colorize('UNKNOWN', 'yellow')} - ${status.message}`);
        console.log(`   Action: ${colorize('Initialize rotation tracking', 'yellow')}`);
      }
      
      console.log(`   Max Age: ${config.maxAge} days | Warning: ${config.warningAge} days`);
      console.log(`   Rotation: ${config.rotationProcedure}`);
      
    } catch (error) {
      console.log(`   Status: ${colorize('ERROR', 'red')} - ${error.message}`);
    }
  }
  
  console.log(colorize(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`, 'cyan'));
}

async function main() {
  try {
    const secretType = process.argv[2];
    const environment = process.argv[3] || 'development';
    const isConfirm = process.argv.includes('--confirm');
    
    console.log(colorize(`🔐 Secret Rotation Management System`, 'bright'));
    
    if (!secretType || secretType === 'status') {
      await showRotationSummary(environment);
      return;
    }
    
    if (secretType === 'all') {
      console.log(colorize(`Checking all secrets for ${environment}...`, 'cyan'));
      await showRotationSummary(environment);
      
      // Check for any expired secrets
      let hasExpired = false;
      for (const [type, config] of Object.entries(ROTATION_CONFIG)) {
        if (config.environment.includes(environment)) {
          const status = await checkRotationStatus(type, environment);
          if (status.status === 'expired') {
            hasExpired = true;
            break;
          }
        }
      }
      
      if (hasExpired) {
        console.log(colorize('\n🚨 Action required: Some secrets have expired!', 'red'));
        console.log(colorize('Run rotation for specific secret types to resolve.', 'red'));
      }
      return;
    }
    
    if (!ROTATION_CONFIG[secretType]) {
      throw new Error(`Unknown secret type: ${secretType}. Available: ${Object.keys(ROTATION_CONFIG).join(', ')}`);
    }
    
    const config = ROTATION_CONFIG[secretType];
    if (!config.environment.includes(environment)) {
      throw new Error(`Secret type '${secretType}' not applicable to environment '${environment}'`);
    }
    
    console.log(colorize(`Rotating ${config.name} for ${environment}...`, 'cyan'));
    
    // Check current status
    const status = await checkRotationStatus(secretType, environment);
    console.log(colorize(`Current status: ${status.message}`, 'blue'));
    
    // Perform rotation based on secret type
    let rotationResult = false;
    const tracker = new RotationTracker();
    
    try {
      if (secretType === 'lichess-token') {
        rotationResult = await rotateLichessToken(environment);
      } else if (secretType === 'service-account') {
        rotationResult = await rotateServiceAccount(environment);
      } else {
        console.log(colorize(`⚠️  Rotation procedure for ${secretType} not yet implemented`, 'yellow'));
        rotationResult = false;
      }
      
      if (isConfirm && !rotationResult) {
        // User confirms manual rotation was completed
        await tracker.recordRotation(secretType, environment, 'completed', 'Manual rotation confirmed by user');
        console.log(colorize(`✅ Rotation recorded as completed for ${config.name}`, 'green'));
      } else if (rotationResult) {
        await tracker.recordRotation(secretType, environment, 'completed', 'Automatic rotation completed');
        console.log(colorize(`✅ Automatic rotation completed for ${config.name}`, 'green'));
      } else {
        await tracker.recordRotation(secretType, environment, 'initiated', 'Manual rotation process initiated');
        console.log(colorize(`📋 Manual rotation process initiated for ${config.name}`, 'yellow'));
      }
      
    } catch (error) {
      await tracker.recordRotation(secretType, environment, 'failed', error.message);
      throw error;
    }
    
  } catch (error) {
    console.error(colorize(`❌ Rotation failed: ${error.message}`, 'red'));
    process.exit(1);
  }
}

// Run rotation management if this script is executed directly
if (require.main === module) {
  main();
}

module.exports = {
  RotationTracker,
  checkRotationStatus,
  ROTATION_CONFIG
};