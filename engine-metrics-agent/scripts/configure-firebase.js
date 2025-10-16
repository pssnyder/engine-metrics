#!/usr/bin/env node

/**
 * Firebase Configuration Manager
 * 
 * Generates environment-specific firebase.json configurations
 * from environment configuration files.
 * 
 * Usage:
 *   node scripts/configure-firebase.js [environment]
 *   
 * Environments: development, staging, production
 * Default: development
 */

const fs = require('fs').promises;
const path = require('path');

// Colors for console output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

function colorize(text, color) {
  return `${colors[color]}${text}${colors.reset}`;
}

async function loadEnvironmentConfig(environment) {
  const configPath = path.join(__dirname, '..', 'config', 'environments', `${environment}.json`);
  
  try {
    const configData = await fs.readFile(configPath, 'utf8');
    return JSON.parse(configData);
  } catch (error) {
    throw new Error(`Failed to load environment config for '${environment}': ${error.message}`);
  }
}

async function generateFirebaseJson(environmentConfig) {
  const { configuration } = environmentConfig;
  
  // Base firebase.json structure
  const firebaseConfig = {
    hosting: configuration.hosting,
    firestore: configuration.firestore,
    storage: configuration.storage,
    functions: configuration.functions
  };
  
  // Add emulators configuration for development
  if (configuration.emulators) {
    firebaseConfig.emulators = configuration.emulators;
  }
  
  return firebaseConfig;
}

async function writeFirebaseJson(firebaseConfig) {
  const firebaseJsonPath = path.join(__dirname, '..', 'firebase.json');
  
  try {
    await fs.writeFile(
      firebaseJsonPath, 
      JSON.stringify(firebaseConfig, null, 2) + '\n', 
      'utf8'
    );
    return firebaseJsonPath;
  } catch (error) {
    throw new Error(`Failed to write firebase.json: ${error.message}`);
  }
}

async function backupExistingFirebaseJson() {
  const firebaseJsonPath = path.join(__dirname, '..', 'firebase.json');
  const backupPath = path.join(__dirname, '..', `firebase.json.backup.${Date.now()}`);
  
  try {
    await fs.access(firebaseJsonPath);
    await fs.copyFile(firebaseJsonPath, backupPath);
    console.log(colorize(`✓ Backed up existing firebase.json to ${path.basename(backupPath)}`, 'green'));
    return backupPath;
  } catch (error) {
    // File doesn't exist, no backup needed
    return null;
  }
}

async function validateEnvironment(environment) {
  const validEnvironments = ['development', 'staging', 'production'];
  
  if (!validEnvironments.includes(environment)) {
    throw new Error(`Invalid environment '${environment}'. Valid options: ${validEnvironments.join(', ')}`);
  }
  
  return true;
}

async function showEnvironmentSummary(environmentConfig) {
  const { projectId, environment, features, services } = environmentConfig;
  
  console.log(colorize(`\n📊 Environment Configuration Summary`, 'bright'));
  console.log(colorize(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`, 'cyan'));
  console.log(`Environment: ${colorize(environment, 'yellow')}`);
  console.log(`Project ID:  ${colorize(projectId, 'yellow')}`);
  
  console.log(colorize(`\n🎛️  Features:`, 'blue'));
  Object.entries(features).forEach(([key, value]) => {
    const status = value ? colorize('✓ enabled', 'green') : colorize('✗ disabled', 'red');
    console.log(`  ${key}: ${status}`);
  });
  
  console.log(colorize(`\n🔧 Services:`, 'blue'));
  Object.entries(services).forEach(([key, config]) => {
    if (typeof config === 'object' && config.enabled !== undefined) {
      const status = config.enabled ? colorize('✓ enabled', 'green') : colorize('✗ disabled', 'red');
      console.log(`  ${key}: ${status}`);
    } else {
      console.log(`  ${key}: ${colorize('configured', 'green')}`);
    }
  });
  
  console.log(colorize(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`, 'cyan'));
}

async function validateFirebaseJson() {
  const firebaseJsonPath = path.join(__dirname, '..', 'firebase.json');
  
  try {
    const content = await fs.readFile(firebaseJsonPath, 'utf8');
    const config = JSON.parse(content);
    
    // Basic validation
    const requiredSections = ['hosting', 'firestore', 'storage', 'functions'];
    const missingSections = requiredSections.filter(section => !config[section]);
    
    if (missingSections.length > 0) {
      throw new Error(`Missing required sections: ${missingSections.join(', ')}`);
    }
    
    console.log(colorize('✓ firebase.json validation passed', 'green'));
    return true;
  } catch (error) {
    throw new Error(`firebase.json validation failed: ${error.message}`);
  }
}

async function main() {
  try {
    // Get environment from command line argument or default to development
    const environment = process.argv[2] || 'development';
    
    console.log(colorize(`🔧 Firebase Configuration Manager`, 'bright'));
    console.log(colorize(`Configuring for environment: ${environment}`, 'cyan'));
    
    // Validate environment
    await validateEnvironment(environment);
    
    // Load environment configuration
    console.log(colorize(`📖 Loading environment configuration...`, 'blue'));
    const environmentConfig = await loadEnvironmentConfig(environment);
    
    // Show configuration summary
    await showEnvironmentSummary(environmentConfig);
    
    // Backup existing firebase.json
    await backupExistingFirebaseJson();
    
    // Generate new firebase.json
    console.log(colorize(`⚙️  Generating firebase.json for ${environment}...`, 'blue'));
    const firebaseConfig = await generateFirebaseJson(environmentConfig);
    
    // Write firebase.json
    const firebaseJsonPath = await writeFirebaseJson(firebaseConfig);
    console.log(colorize(`✓ Generated firebase.json`, 'green'));
    
    // Validate the generated configuration
    await validateFirebaseJson();
    
    console.log(colorize(`\n🎉 Configuration complete!`, 'bright'));
    console.log(colorize(`Firebase configured for ${environment} environment`, 'green'));
    
    if (environment === 'development') {
      console.log(colorize(`\n💡 Next steps:`, 'yellow'));
      console.log(`  1. Start emulators: ${colorize('firebase emulators:start', 'cyan')}`);
      console.log(`  2. Run development server: ${colorize('npm run dev', 'cyan')}`);
    } else {
      console.log(colorize(`\n💡 Next steps:`, 'yellow'));
      console.log(`  1. Deploy to ${environment}: ${colorize(`firebase deploy --project ${environmentConfig.projectId}`, 'cyan')}`);
    }
    
  } catch (error) {
    console.error(colorize(`❌ Configuration failed: ${error.message}`, 'red'));
    process.exit(1);
  }
}

// Run the configuration if this script is executed directly
if (require.main === module) {
  main();
}

module.exports = {
  loadEnvironmentConfig,
  generateFirebaseJson,
  validateFirebaseJson
};