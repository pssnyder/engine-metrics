#!/usr/bin/env node

/**
 * Firebase Deployment Manager
 * 
 * Handles environment-specific deployments with proper configuration,
 * validation, and rollback capabilities.
 * 
 * Usage:
 *   node scripts/deploy.js [environment] [--services=functions,hosting] [--confirm]
 *   
 * Examples:
 *   node scripts/deploy.js development
 *   node scripts/deploy.js staging --services=functions
 *   node scripts/deploy.js production --confirm
 */

const { spawn } = require('child_process');
const fs = require('fs').promises;
const path = require('path');
const { loadEnvironmentConfig, generateFirebaseJson, validateFirebaseJson } = require('./configure-firebase');

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

function parseArguments() {
  const args = process.argv.slice(2);
  const environment = args[0] || 'development';
  
  const options = {
    services: 'all',
    confirm: false,
    dryRun: false
  };
  
  args.forEach(arg => {
    if (arg.startsWith('--services=')) {
      options.services = arg.split('=')[1];
    } else if (arg === '--confirm') {
      options.confirm = true;
    } else if (arg === '--dry-run') {
      options.dryRun = true;
    }
  });
  
  return { environment, options };
}

async function runCommand(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      stdio: options.silent ? 'pipe' : 'inherit',
      shell: true,
      ...options
    });
    
    let stdout = '';
    let stderr = '';
    
    if (options.silent) {
      child.stdout.on('data', (data) => {
        stdout += data.toString();
      });
      
      child.stderr.on('data', (data) => {
        stderr += data.toString();
      });
    }
    
    child.on('close', (code) => {
      if (code === 0) {
        resolve({ stdout, stderr, code });
      } else {
        reject(new Error(`Command failed with code ${code}: ${stderr || stdout}`));
      }
    });
    
    child.on('error', (error) => {
      reject(error);
    });
  });
}

async function checkPrerequisites() {
  console.log(colorize('🔍 Checking prerequisites...', 'blue'));
  
  // Check Firebase CLI
  try {
    await runCommand('firebase', ['--version'], { silent: true });
    console.log(colorize('✓ Firebase CLI available', 'green'));
  } catch (error) {
    throw new Error('Firebase CLI not found. Install with: npm install -g firebase-tools');
  }
  
  // Check authentication
  try {
    const result = await runCommand('firebase', ['projects:list'], { silent: true });
    if (result.stdout.includes('chess-engine-metrics-agent')) {
      console.log(colorize('✓ Firebase authentication valid', 'green'));
    } else {
      throw new Error('Project access not found');
    }
  } catch (error) {
    throw new Error('Firebase authentication required. Run: firebase login');
  }
  
  // Check Node.js dependencies
  const packageJsonPath = path.join(__dirname, '..', 'src', 'backend', 'functions', 'package.json');
  try {
    await fs.access(packageJsonPath);
    console.log(colorize('✓ Functions dependencies configured', 'green'));
  } catch (error) {
    throw new Error('Functions package.json not found. Run: npm install in functions directory');
  }
}

async function validateDeployment(environment, services) {
  console.log(colorize('🔎 Validating deployment configuration...', 'blue'));
  
  // Validate environment configuration
  const environmentConfig = await loadEnvironmentConfig(environment);
  
  // Generate and validate firebase.json
  const firebaseConfig = await generateFirebaseJson(environmentConfig);
  await validateFirebaseJson();
  
  // Service-specific validations
  const serviceList = services === 'all' ? ['functions', 'hosting', 'firestore', 'storage'] : services.split(',');
  
  for (const service of serviceList) {
    switch (service.trim()) {
      case 'functions':
        await validateFunctions();
        break;
      case 'hosting':
        await validateHosting();
        break;
      case 'firestore':
        await validateFirestore();
        break;
      case 'storage':
        await validateStorage();
        break;
      default:
        console.log(colorize(`⚠️  Unknown service: ${service}`, 'yellow'));
    }
  }
  
  console.log(colorize('✓ Deployment validation passed', 'green'));
  return environmentConfig;
}

async function validateFunctions() {
  const functionsPath = path.join(__dirname, '..', 'src', 'backend', 'functions');
  
  // Check if functions exist
  try {
    await fs.access(path.join(functionsPath, 'index.js'));
    console.log(colorize('✓ Functions source code found', 'green'));
  } catch (error) {
    throw new Error('Functions index.js not found');
  }
  
  // Check for package.json and dependencies
  try {
    const packageJson = JSON.parse(
      await fs.readFile(path.join(functionsPath, 'package.json'), 'utf8')
    );
    
    if (!packageJson.dependencies || Object.keys(packageJson.dependencies).length === 0) {
      throw new Error('No dependencies found in functions package.json');
    }
    
    console.log(colorize('✓ Functions dependencies validated', 'green'));
  } catch (error) {
    throw new Error(`Functions package.json validation failed: ${error.message}`);
  }
}

async function validateHosting() {
  const buildPath = path.join(__dirname, '..', 'src', 'frontend', 'build');
  
  try {
    await fs.access(buildPath);
    console.log(colorize('✓ Hosting build directory found', 'green'));
  } catch (error) {
    console.log(colorize('⚠️  Frontend not built. Run: npm run build', 'yellow'));
  }
}

async function validateFirestore() {
  const rulesPath = path.join(__dirname, '..', 'config', 'firestore.rules');
  
  try {
    await fs.access(rulesPath);
    console.log(colorize('✓ Firestore rules found', 'green'));
  } catch (error) {
    throw new Error('Firestore rules not found');
  }
}

async function validateStorage() {
  const rulesPath = path.join(__dirname, '..', 'config', 'storage.rules');
  
  try {
    await fs.access(rulesPath);
    console.log(colorize('✓ Storage rules found', 'green'));
  } catch (error) {
    throw new Error('Storage rules not found');
  }
}

async function showDeploymentSummary(environment, environmentConfig, services, options) {
  console.log(colorize(`\n🚀 Deployment Summary`, 'bright'));
  console.log(colorize(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`, 'cyan'));
  console.log(`Environment: ${colorize(environment, 'yellow')}`);
  console.log(`Project ID:  ${colorize(environmentConfig.projectId, 'yellow')}`);
  console.log(`Services:    ${colorize(services, 'yellow')}`);
  console.log(`Dry Run:     ${colorize(options.dryRun ? 'Yes' : 'No', options.dryRun ? 'yellow' : 'green')}`);
  
  if (environment === 'production') {
    console.log(colorize(`\n⚠️  PRODUCTION DEPLOYMENT WARNING`, 'red'));
    console.log(colorize(`This will deploy to the live production environment!`, 'red'));
  }
  
  console.log(colorize(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`, 'cyan'));
}

async function confirmDeployment(environment, options) {
  if (options.confirm) {
    return true;
  }
  
  if (environment === 'production' && !options.dryRun) {
    console.log(colorize('⚠️  Production deployment requires --confirm flag', 'red'));
    console.log(colorize('Add --confirm to proceed with production deployment', 'yellow'));
    return false;
  }
  
  return true;
}

async function performDeployment(environment, environmentConfig, services, options) {
  const { projectId } = environmentConfig;
  
  if (options.dryRun) {
    console.log(colorize('🏃 Performing dry run (no actual deployment)...', 'yellow'));
    console.log(`Would deploy: ${services} to ${projectId}`);
    return;
  }
  
  console.log(colorize(`🚀 Starting deployment to ${environment}...`, 'blue'));
  
  // Configure Firebase for the specific environment
  console.log(colorize('📝 Configuring Firebase for deployment...', 'blue'));
  await runCommand('node', ['scripts/configure-firebase.js', environment]);
  
  // Build deployment command
  const deployArgs = ['deploy'];
  
  if (services !== 'all') {
    deployArgs.push('--only', services);
  }
  
  deployArgs.push('--project', projectId);
  
  // Add force flag for non-production deployments
  if (environment !== 'production') {
    deployArgs.push('--force');
  }
  
  try {
    console.log(colorize(`🔧 Running: firebase ${deployArgs.join(' ')}`, 'cyan'));
    await runCommand('firebase', deployArgs);
    
    console.log(colorize(`\n🎉 Deployment successful!`, 'bright'));
    console.log(colorize(`Environment: ${environment}`, 'green'));
    console.log(colorize(`Project: ${projectId}`, 'green'));
    
    // Show post-deployment URLs
    if (services === 'all' || services.includes('hosting')) {
      console.log(colorize(`\n🌐 Hosting URL: https://${projectId}.web.app`, 'cyan'));
    }
    
  } catch (error) {
    throw new Error(`Deployment failed: ${error.message}`);
  }
}

async function createDeploymentRecord(environment, environmentConfig, services, options) {
  const deploymentRecord = {
    timestamp: new Date().toISOString(),
    environment,
    projectId: environmentConfig.projectId,
    services,
    options,
    user: process.env.USER || process.env.USERNAME || 'unknown',
    success: true
  };
  
  const recordsPath = path.join(__dirname, '..', 'deployment-records.json');
  
  try {
    let records = [];
    try {
      const existingRecords = await fs.readFile(recordsPath, 'utf8');
      records = JSON.parse(existingRecords);
    } catch (error) {
      // File doesn't exist, start with empty array
    }
    
    records.push(deploymentRecord);
    
    // Keep only last 50 records
    if (records.length > 50) {
      records = records.slice(-50);
    }
    
    await fs.writeFile(recordsPath, JSON.stringify(records, null, 2));
    console.log(colorize('📝 Deployment record saved', 'green'));
    
  } catch (error) {
    console.log(colorize(`⚠️  Could not save deployment record: ${error.message}`, 'yellow'));
  }
}

async function main() {
  try {
    const { environment, options } = parseArguments();
    
    console.log(colorize(`🚀 Firebase Deployment Manager`, 'bright'));
    console.log(colorize(`Deploying to: ${environment}`, 'cyan'));
    
    // Check prerequisites
    await checkPrerequisites();
    
    // Validate deployment
    const environmentConfig = await validateDeployment(environment, options.services);
    
    // Show deployment summary
    await showDeploymentSummary(environment, environmentConfig, options.services, options);
    
    // Confirm deployment
    const confirmed = await confirmDeployment(environment, options);
    if (!confirmed) {
      console.log(colorize('❌ Deployment cancelled', 'red'));
      process.exit(1);
    }
    
    // Perform deployment
    await performDeployment(environment, environmentConfig, options.services, options);
    
    // Record deployment
    if (!options.dryRun) {
      await createDeploymentRecord(environment, environmentConfig, options.services, options);
    }
    
    console.log(colorize(`\n✨ Deployment complete!`, 'bright'));
    
  } catch (error) {
    console.error(colorize(`❌ Deployment failed: ${error.message}`, 'red'));
    process.exit(1);
  }
}

// Run deployment if this script is executed directly
if (require.main === module) {
  main();
}

module.exports = {
  validateDeployment,
  performDeployment
};