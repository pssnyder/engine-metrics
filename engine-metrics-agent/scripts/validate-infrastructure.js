#!/usr/bin/env node

/**
 * Infrastructure Configuration Validator
 * 
 * Validates all infrastructure configurations for consistency,
 * security, and best practices compliance.
 * 
 * Usage:
 *   node scripts/validate-infrastructure.js [environment]
 *   
 * Examples:
 *   node scripts/validate-infrastructure.js
 *   node scripts/validate-infrastructure.js production
 */

const fs = require('fs').promises;
const path = require('path');
const { loadEnvironmentConfig } = require('./configure-firebase');

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

class ValidationResult {
  constructor() {
    this.checks = [];
    this.warnings = [];
    this.errors = [];
    this.passed = 0;
    this.failed = 0;
  }
  
  addCheck(name, status, message, severity = 'info') {
    const check = { name, status, message, severity };
    this.checks.push(check);
    
    if (status) {
      this.passed++;
    } else {
      this.failed++;
      if (severity === 'error') {
        this.errors.push(check);
      } else {
        this.warnings.push(check);
      }
    }
    
    return this;
  }
  
  isValid() {
    return this.errors.length === 0;
  }
  
  summary() {
    return {
      total: this.checks.length,
      passed: this.passed,
      failed: this.failed,
      warnings: this.warnings.length,
      errors: this.errors.length
    };
  }
}

async function validateEnvironmentConfigs() {
  const result = new ValidationResult();
  const environments = ['development', 'staging', 'production'];
  
  console.log(colorize('🔍 Validating environment configurations...', 'blue'));
  
  for (const env of environments) {
    try {
      const config = await loadEnvironmentConfig(env);
      
      // Validate required fields
      if (!config.projectId) {
        result.addCheck(`${env}-project-id`, false, `Missing projectId in ${env}.json`, 'error');
      } else {
        result.addCheck(`${env}-project-id`, true, `ProjectId defined for ${env}`);
      }
      
      if (!config.environment) {
        result.addCheck(`${env}-environment`, false, `Missing environment field in ${env}.json`, 'error');
      } else if (config.environment !== env) {
        result.addCheck(`${env}-environment`, false, `Environment field mismatch in ${env}.json`, 'error');
      } else {
        result.addCheck(`${env}-environment`, true, `Environment field correct for ${env}`);
      }
      
      // Validate configuration structure
      const requiredSections = ['hosting', 'firestore', 'storage', 'functions'];
      for (const section of requiredSections) {
        if (!config.configuration[section]) {
          result.addCheck(`${env}-${section}`, false, `Missing ${section} configuration in ${env}.json`, 'error');
        } else {
          result.addCheck(`${env}-${section}`, true, `${section} configuration present for ${env}`);
        }
      }
      
      // Validate production-specific requirements
      if (env === 'production') {
        if (!config.security) {
          result.addCheck(`${env}-security`, false, 'Missing security configuration for production', 'error');
        } else {
          result.addCheck(`${env}-security`, true, 'Security configuration present for production');
        }
        
        if (!config.monitoring) {
          result.addCheck(`${env}-monitoring`, false, 'Missing monitoring configuration for production', 'error');
        } else {
          result.addCheck(`${env}-monitoring`, true, 'Monitoring configuration present for production');
        }
        
        // Check for development features disabled in production
        if (config.features.enableEmulators) {
          result.addCheck(`${env}-emulators`, false, 'Emulators should be disabled in production', 'warning');
        } else {
          result.addCheck(`${env}-emulators`, true, 'Emulators properly disabled in production');
        }
        
        if (config.features.enableDetailedLogging) {
          result.addCheck(`${env}-logging`, false, 'Detailed logging should be disabled in production', 'warning');
        } else {
          result.addCheck(`${env}-logging`, true, 'Detailed logging properly disabled in production');
        }
      }
      
    } catch (error) {
      result.addCheck(`${env}-load`, false, `Failed to load ${env} configuration: ${error.message}`, 'error');
    }
  }
  
  return result;
}

async function validateFirebaseConfig() {
  const result = new ValidationResult();
  
  console.log(colorize('🔍 Validating Firebase configuration files...', 'blue'));
  
  const configFiles = [
    { path: 'firebase.json', required: true },
    { path: 'config/firestore.rules', required: true },
    { path: 'config/firestore.indexes.json', required: true },
    { path: 'config/storage.rules', required: true }
  ];
  
  for (const file of configFiles) {
    const filePath = path.join(__dirname, '..', file.path);
    
    try {
      await fs.access(filePath);
      result.addCheck(`file-${file.path}`, true, `${file.path} exists`);
      
      // Validate JSON files are parseable
      if (file.path.endsWith('.json')) {
        try {
          const content = await fs.readFile(filePath, 'utf8');
          JSON.parse(content);
          result.addCheck(`json-${file.path}`, true, `${file.path} is valid JSON`);
        } catch (error) {
          result.addCheck(`json-${file.path}`, false, `${file.path} is not valid JSON: ${error.message}`, 'error');
        }
      }
      
    } catch (error) {
      const severity = file.required ? 'error' : 'warning';
      result.addCheck(`file-${file.path}`, false, `${file.path} not found`, severity);
    }
  }
  
  // Validate firebase.json structure
  try {
    const firebaseJsonPath = path.join(__dirname, '..', 'firebase.json');
    const firebaseConfig = JSON.parse(await fs.readFile(firebaseJsonPath, 'utf8'));
    
    const requiredSections = ['hosting', 'firestore', 'storage', 'functions'];
    for (const section of requiredSections) {
      if (!firebaseConfig[section]) {
        result.addCheck(`firebase-${section}`, false, `Missing ${section} section in firebase.json`, 'error');
      } else {
        result.addCheck(`firebase-${section}`, true, `${section} section present in firebase.json`);
      }
    }
    
    // Validate functions configuration
    if (firebaseConfig.functions) {
      if (!firebaseConfig.functions.source) {
        result.addCheck('functions-source', false, 'Missing functions source directory', 'error');
      } else {
        const functionsPath = path.join(__dirname, '..', firebaseConfig.functions.source);
        try {
          await fs.access(functionsPath);
          result.addCheck('functions-source', true, 'Functions source directory exists');
        } catch (error) {
          result.addCheck('functions-source', false, 'Functions source directory not found', 'error');
        }
      }
      
      if (!firebaseConfig.functions.runtime) {
        result.addCheck('functions-runtime', false, 'Missing functions runtime specification', 'warning');
      } else {
        result.addCheck('functions-runtime', true, `Functions runtime: ${firebaseConfig.functions.runtime}`);
      }
    }
    
  } catch (error) {
    result.addCheck('firebase-json', false, `Failed to validate firebase.json: ${error.message}`, 'error');
  }
  
  return result;
}

async function validateSecurityRules() {
  const result = new ValidationResult();
  
  console.log(colorize('🔍 Validating security rules...', 'blue'));
  
  // Validate Firestore rules
  try {
    const rulesPath = path.join(__dirname, '..', 'config', 'firestore.rules');
    const rules = await fs.readFile(rulesPath, 'utf8');
    
    // Check for admin email configuration
    if (rules.includes('pat@rapidtechconsultants.com')) {
      result.addCheck('firestore-admin', true, 'Admin email configured in Firestore rules');
    } else {
      result.addCheck('firestore-admin', false, 'Admin email not found in Firestore rules', 'warning');
    }
    
    // Check for email verification requirement
    if (rules.includes('email_verified == true')) {
      result.addCheck('firestore-email-verification', true, 'Email verification required in Firestore rules');
    } else {
      result.addCheck('firestore-email-verification', false, 'Email verification not enforced', 'warning');
    }
    
    // Check for default deny rule
    if (rules.includes('allow read, write: if false')) {
      result.addCheck('firestore-default-deny', true, 'Default deny rule present in Firestore rules');
    } else {
      result.addCheck('firestore-default-deny', false, 'Default deny rule missing - security risk', 'error');
    }
    
  } catch (error) {
    result.addCheck('firestore-rules', false, `Failed to validate Firestore rules: ${error.message}`, 'error');
  }
  
  // Validate Storage rules
  try {
    const rulesPath = path.join(__dirname, '..', 'config', 'storage.rules');
    const rules = await fs.readFile(rulesPath, 'utf8');
    
    // Check for file type validation
    if (rules.includes('isAllowedFileType()')) {
      result.addCheck('storage-file-types', true, 'File type validation present in Storage rules');
    } else {
      result.addCheck('storage-file-types', false, 'File type validation missing', 'warning');
    }
    
    // Check for file size limits
    if (rules.includes('isReasonableSize()')) {
      result.addCheck('storage-file-size', true, 'File size limits present in Storage rules');
    } else {
      result.addCheck('storage-file-size', false, 'File size limits missing', 'warning');
    }
    
    // Check for default deny rule
    if (rules.includes('allow read, write, delete: if false')) {
      result.addCheck('storage-default-deny', true, 'Default deny rule present in Storage rules');
    } else {
      result.addCheck('storage-default-deny', false, 'Default deny rule missing - security risk', 'error');
    }
    
  } catch (error) {
    result.addCheck('storage-rules', false, `Failed to validate Storage rules: ${error.message}`, 'error');
  }
  
  return result;
}

async function validateFunctionsConfig() {
  const result = new ValidationResult();
  
  console.log(colorize('🔍 Validating Functions configuration...', 'blue'));
  
  const functionsPath = path.join(__dirname, '..', 'src', 'backend', 'functions');
  
  // Check package.json
  try {
    const packageJsonPath = path.join(functionsPath, 'package.json');
    const packageJson = JSON.parse(await fs.readFile(packageJsonPath, 'utf8'));
    
    if (!packageJson.engines || !packageJson.engines.node) {
      result.addCheck('functions-node-version', false, 'Node.js version not specified in functions package.json', 'warning');
    } else {
      result.addCheck('functions-node-version', true, `Node.js version specified: ${packageJson.engines.node}`);
    }
    
    if (!packageJson.dependencies || Object.keys(packageJson.dependencies).length === 0) {
      result.addCheck('functions-dependencies', false, 'No dependencies found in functions package.json', 'error');
    } else {
      result.addCheck('functions-dependencies', true, `${Object.keys(packageJson.dependencies).length} dependencies defined`);
    }
    
    // Check for required dependencies
    const requiredDeps = ['firebase-admin', 'firebase-functions'];
    for (const dep of requiredDeps) {
      if (!packageJson.dependencies[dep]) {
        result.addCheck(`functions-dep-${dep}`, false, `Missing required dependency: ${dep}`, 'error');
      } else {
        result.addCheck(`functions-dep-${dep}`, true, `Required dependency present: ${dep}`);
      }
    }
    
  } catch (error) {
    result.addCheck('functions-package-json', false, `Failed to validate functions package.json: ${error.message}`, 'error');
  }
  
  // Check index.js
  try {
    const indexPath = path.join(functionsPath, 'index.js');
    await fs.access(indexPath);
    result.addCheck('functions-index', true, 'Functions index.js exists');
    
    const indexContent = await fs.readFile(indexPath, 'utf8');
    
    // Check for proper exports
    if (indexContent.includes('exports.') || indexContent.includes('module.exports')) {
      result.addCheck('functions-exports', true, 'Functions properly export modules');
    } else {
      result.addCheck('functions-exports', false, 'No function exports found in index.js', 'error');
    }
    
  } catch (error) {
    result.addCheck('functions-index', false, 'Functions index.js not found', 'error');
  }
  
  return result;
}

async function validateProjectStructure() {
  const result = new ValidationResult();
  
  console.log(colorize('🔍 Validating project structure...', 'blue'));
  
  const requiredDirectories = [
    'src',
    'src/backend',
    'src/backend/functions',
    'config',
    'config/environments',
    'scripts',
    'tests',
    'tests/unit',
    'tests/integration',
    'tests/e2e'
  ];
  
  for (const dir of requiredDirectories) {
    const dirPath = path.join(__dirname, '..', dir);
    
    try {
      const stat = await fs.stat(dirPath);
      if (stat.isDirectory()) {
        result.addCheck(`dir-${dir}`, true, `Directory exists: ${dir}`);
      } else {
        result.addCheck(`dir-${dir}`, false, `Path exists but is not a directory: ${dir}`, 'error');
      }
    } catch (error) {
      result.addCheck(`dir-${dir}`, false, `Directory missing: ${dir}`, 'warning');
    }
  }
  
  // Check for important files
  const requiredFiles = [
    'package.json',
    'README.md',
    '.env.example',
    'scripts/configure-firebase.js',
    'scripts/deploy.js'
  ];
  
  for (const file of requiredFiles) {
    const filePath = path.join(__dirname, '..', file);
    
    try {
      await fs.access(filePath);
      result.addCheck(`file-${file}`, true, `File exists: ${file}`);
    } catch (error) {
      result.addCheck(`file-${file}`, false, `File missing: ${file}`, 'warning');
    }
  }
  
  return result;
}

function displayResults(results) {
  console.log(colorize(`\n📊 Infrastructure Validation Results`, 'bright'));
  console.log(colorize(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`, 'cyan'));
  
  let totalPassed = 0;
  let totalFailed = 0;
  let totalWarnings = 0;
  let totalErrors = 0;
  
  for (const [category, result] of Object.entries(results)) {
    const summary = result.summary();
    totalPassed += summary.passed;
    totalFailed += summary.failed;
    totalWarnings += summary.warnings;
    totalErrors += summary.errors;
    
    console.log(colorize(`\n🔧 ${category}:`, 'blue'));
    console.log(`   Passed: ${colorize(summary.passed, 'green')} | Failed: ${colorize(summary.failed, summary.failed > 0 ? 'red' : 'green')} | Warnings: ${colorize(summary.warnings, summary.warnings > 0 ? 'yellow' : 'green')}`);
    
    // Show failed checks
    if (result.errors.length > 0) {
      console.log(colorize(`   ❌ Errors:`, 'red'));
      result.errors.forEach(check => {
        console.log(`      • ${check.message}`);
      });
    }
    
    if (result.warnings.length > 0) {
      console.log(colorize(`   ⚠️  Warnings:`, 'yellow'));
      result.warnings.forEach(check => {
        console.log(`      • ${check.message}`);
      });
    }
  }
  
  console.log(colorize(`\n📈 Overall Summary:`, 'bright'));
  console.log(`Total Checks: ${totalPassed + totalFailed}`);
  console.log(`Passed: ${colorize(totalPassed, 'green')}`);
  console.log(`Failed: ${colorize(totalFailed, totalFailed > 0 ? 'red' : 'green')}`);
  console.log(`Warnings: ${colorize(totalWarnings, totalWarnings > 0 ? 'yellow' : 'green')}`);
  console.log(`Errors: ${colorize(totalErrors, totalErrors > 0 ? 'red' : 'green')}`);
  
  console.log(colorize(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`, 'cyan'));
  
  if (totalErrors === 0) {
    console.log(colorize(`\n✅ Infrastructure validation passed!`, 'green'));
    console.log(colorize(`All critical checks passed. Infrastructure is ready for deployment.`, 'green'));
  } else {
    console.log(colorize(`\n❌ Infrastructure validation failed!`, 'red'));
    console.log(colorize(`${totalErrors} critical error(s) must be resolved before deployment.`, 'red'));
  }
  
  if (totalWarnings > 0) {
    console.log(colorize(`\n⚠️  ${totalWarnings} warning(s) detected. Consider addressing these for optimal configuration.`, 'yellow'));
  }
  
  return totalErrors === 0;
}

async function main() {
  try {
    const environment = process.argv[2];
    
    console.log(colorize(`🔍 Infrastructure Configuration Validator`, 'bright'));
    
    if (environment) {
      console.log(colorize(`Validating for environment: ${environment}`, 'cyan'));
    } else {
      console.log(colorize(`Validating all environments and configurations`, 'cyan'));
    }
    
    // Run all validations
    const results = {
      'Environment Configurations': await validateEnvironmentConfigs(),
      'Firebase Configuration': await validateFirebaseConfig(),
      'Security Rules': await validateSecurityRules(),
      'Functions Configuration': await validateFunctionsConfig(),
      'Project Structure': await validateProjectStructure()
    };
    
    // Display results
    const isValid = displayResults(results);
    
    if (!isValid) {
      process.exit(1);
    }
    
  } catch (error) {
    console.error(colorize(`❌ Validation failed: ${error.message}`, 'red'));
    process.exit(1);
  }
}

// Run validation if this script is executed directly
if (require.main === module) {
  main();
}

module.exports = {
  validateEnvironmentConfigs,
  validateFirebaseConfig,
  validateSecurityRules,
  validateFunctionsConfig,
  validateProjectStructure
};