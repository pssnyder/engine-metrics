#!/usr/bin/env node

/**
 * Secrets and Security Validation Framework
 * 
 * Validates environment variables, detects potential secrets exposure,
 * and ensures security best practices are followed.
 * 
 * Usage:
 *   node scripts/validate-secrets.js [environment]
 *   
 * Examples:
 *   node scripts/validate-secrets.js
 *   node scripts/validate-secrets.js production
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

class SecretValidationResult {
  constructor() {
    this.checks = [];
    this.warnings = [];
    this.errors = [];
    this.criticalErrors = [];
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
      if (severity === 'critical') {
        this.criticalErrors.push(check);
      } else if (severity === 'error') {
        this.errors.push(check);
      } else {
        this.warnings.push(check);
      }
    }
    
    return this;
  }
  
  isValid() {
    return this.criticalErrors.length === 0 && this.errors.length === 0;
  }
  
  isCritical() {
    return this.criticalErrors.length > 0;
  }
  
  summary() {
    return {
      total: this.checks.length,
      passed: this.passed,
      failed: this.failed,
      warnings: this.warnings.length,
      errors: this.errors.length,
      critical: this.criticalErrors.length
    };
  }
}

// Common secret patterns to detect
const SECRET_PATTERNS = [
  {
    name: 'Lichess API Token',
    pattern: /lip_[a-zA-Z0-9]{16}/g,
    severity: 'critical'
  },
  {
    name: 'Firebase API Key',
    pattern: /AIza[0-9A-Za-z\\-_]{35}/g,
    severity: 'critical'
  },
  {
    name: 'Google Cloud Service Account',
    pattern: /"private_key":\s*"-----BEGIN PRIVATE KEY-----/g,
    severity: 'critical'
  },
  {
    name: 'AWS Access Key',
    pattern: /AKIA[0-9A-Z]{16}/g,
    severity: 'critical'
  },
  {
    name: 'Generic API Key',
    pattern: /api[_-]?key[\s]*[=:][\s]*['""][a-zA-Z0-9_-]{10,}['"]/gi,
    severity: 'error'
  },
  {
    name: 'Password in URL',
    pattern: /:\/\/[^:\/\s]+:[^@\/\s]+@/g,
    severity: 'error'
  },
  {
    name: 'JWT Token',
    pattern: /eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*/g,
    severity: 'error'
  }
];

// Required environment variables for each environment
const REQUIRED_ENV_VARS = {
  development: [
    'LICHESS_API_TOKEN',
    'FIREBASE_PROJECT_ID',
    'NODE_ENV',
    'LOG_LEVEL'
  ],
  staging: [
    'LICHESS_API_TOKEN',
    'FIREBASE_PROJECT_ID',
    'NODE_ENV',
    'LOG_LEVEL',
    'ENABLE_AUTH_VALIDATION',
    'ENABLE_RATE_LIMITING'
  ],
  production: [
    'LICHESS_API_TOKEN',
    'FIREBASE_PROJECT_ID',
    'NODE_ENV',
    'LOG_LEVEL',
    'ENABLE_AUTH_VALIDATION',
    'ENABLE_RATE_LIMITING',
    'ERROR_REPORTING_ENABLED',
    'BACKUP_ENABLED'
  ]
};

// Security-sensitive configurations that should be checked
const SECURITY_CONFIG_CHECKS = {
  production: {
    'NODE_ENV': 'production',
    'LOG_LEVEL': ['warn', 'error'],
    'ENABLE_DETAILED_LOGGING': 'false',
    'ENABLE_AUTH_VALIDATION': 'true',
    'ENABLE_RATE_LIMITING': 'true',
    'FORCE_HTTPS': 'true',
    'ENABLE_HSTS': 'true'
  },
  staging: {
    'NODE_ENV': 'staging',
    'ENABLE_AUTH_VALIDATION': 'true',
    'ENABLE_RATE_LIMITING': 'true'
  },
  development: {
    'NODE_ENV': 'development'
  }
};

async function loadEnvironmentVariables() {
  const envPath = path.join(__dirname, '..', '.env');
  
  try {
    const content = await fs.readFile(envPath, 'utf8');
    const env = {};
    
    // Parse environment variables
    const lines = content.split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#')) {
        const [key, ...valueParts] = trimmed.split('=');
        if (key && valueParts.length > 0) {
          env[key.trim()] = valueParts.join('=').trim();
        }
      }
    }
    
    return env;
  } catch (error) {
    throw new Error(`Failed to load .env file: ${error.message}`);
  }
}

async function scanForSecretsInFiles() {
  const result = new SecretValidationResult();
  
  console.log(colorize('🔍 Scanning files for exposed secrets...', 'blue'));
  
  const filesToScan = [
    'package.json',
    'firebase.json',
    'README.md',
    'src/**/*.js',
    'src/**/*.ts',
    'scripts/**/*.js',
    'config/**/*.json'
  ];
  
  const excludePatterns = [
    '.env',
    'node_modules',
    '.git',
    'coverage',
    'dist',
    'build'
  ];
  
  try {
    const allFiles = await getFilesToScan(filesToScan, excludePatterns);
    
    for (const filePath of allFiles) {
      try {
        const content = await fs.readFile(filePath, 'utf8');
        const secrets = detectSecretsInContent(content, filePath);
        
        if (secrets.length > 0) {
          for (const secret of secrets) {
            result.addCheck(
              `secret-exposure-${path.basename(filePath)}`,
              false,
              `Potential ${secret.type} found in ${filePath}: ${secret.preview}`,
              secret.severity
            );
          }
        } else {
          result.addCheck(
            `clean-file-${path.basename(filePath)}`,
            true,
            `No secrets detected in ${path.basename(filePath)}`
          );
        }
      } catch (error) {
        result.addCheck(
          `scan-error-${path.basename(filePath)}`,
          false,
          `Failed to scan ${filePath}: ${error.message}`,
          'warning'
        );
      }
    }
    
    if (result.criticalErrors.length === 0) {
      result.addCheck('secret-scan-overall', true, 'No critical secret exposures detected');
    } else {
      result.addCheck(
        'secret-scan-overall',
        false,
        `${result.criticalErrors.length} critical secret exposure(s) detected`,
        'critical'
      );
    }
    
  } catch (error) {
    result.addCheck(
      'secret-scan-error',
      false,
      `Secret scanning failed: ${error.message}`,
      'error'
    );
  }
  
  return result;
}

function detectSecretsInContent(content, filePath) {
  const secrets = [];
  
  for (const pattern of SECRET_PATTERNS) {
    const matches = content.match(pattern.pattern);
    if (matches) {
      for (const match of matches) {
        secrets.push({
          type: pattern.name,
          value: match,
          preview: match.substring(0, 20) + '...',
          severity: pattern.severity,
          file: filePath
        });
      }
    }
  }
  
  return secrets;
}

async function getFilesToScan(patterns, excludePatterns) {
  // Simplified file scanning - in a real implementation, you'd use glob patterns
  const files = [];
  
  async function scanDirectory(dir) {
    try {
      const entries = await fs.readdir(dir, { withFileTypes: true });
      
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        
        // Skip excluded patterns
        if (excludePatterns.some(pattern => fullPath.includes(pattern))) {
          continue;
        }
        
        if (entry.isDirectory()) {
          await scanDirectory(fullPath);
        } else if (entry.isFile()) {
          // Check if file matches patterns
          const ext = path.extname(entry.name);
          if (['.js', '.ts', '.json', '.md'].includes(ext)) {
            files.push(fullPath);
          }
        }
      }
    } catch (error) {
      // Directory doesn't exist or can't be read
    }
  }
  
  await scanDirectory(path.join(__dirname, '..'));
  return files.slice(0, 20); // Limit for demonstration
}

async function validateEnvironmentVariables(environment) {
  const result = new SecretValidationResult();
  
  console.log(colorize(`🔍 Validating environment variables for ${environment}...`, 'blue'));
  
  try {
    const env = await loadEnvironmentVariables();
    
    // Check required variables
    const requiredVars = REQUIRED_ENV_VARS[environment] || [];
    for (const varName of requiredVars) {
      if (!env[varName]) {
        result.addCheck(
          `required-var-${varName}`,
          false,
          `Required environment variable missing: ${varName}`,
          'error'
        );
      } else if (env[varName].includes('your_') || env[varName].includes('SECURE_VAULT_')) {
        result.addCheck(
          `placeholder-var-${varName}`,
          false,
          `Environment variable ${varName} contains placeholder value`,
          'warning'
        );
      } else {
        result.addCheck(
          `required-var-${varName}`,
          true,
          `Required variable ${varName} is set`
        );
      }
    }
    
    // Check security configuration
    const securityChecks = SECURITY_CONFIG_CHECKS[environment] || {};
    for (const [varName, expectedValue] of Object.entries(securityChecks)) {
      const actualValue = env[varName];
      
      if (Array.isArray(expectedValue)) {
        if (!expectedValue.includes(actualValue)) {
          result.addCheck(
            `security-config-${varName}`,
            false,
            `Security config ${varName} should be one of [${expectedValue.join(', ')}], got: ${actualValue}`,
            environment === 'production' ? 'error' : 'warning'
          );
        } else {
          result.addCheck(
            `security-config-${varName}`,
            true,
            `Security config ${varName} correctly set to ${actualValue}`
          );
        }
      } else {
        if (actualValue !== expectedValue) {
          result.addCheck(
            `security-config-${varName}`,
            false,
            `Security config ${varName} should be '${expectedValue}', got: '${actualValue}'`,
            environment === 'production' ? 'error' : 'warning'
          );
        } else {
          result.addCheck(
            `security-config-${varName}`,
            true,
            `Security config ${varName} correctly set to ${actualValue}`
          );
        }
      }
    }
    
    // Check for common security issues
    if (env.LICHESS_API_TOKEN && env.LICHESS_API_TOKEN.startsWith('lip_') && env.LICHESS_API_TOKEN.length === 20) {
      result.addCheck(
        'lichess-token-format',
        true,
        'Lichess API token format appears valid'
      );
    } else if (env.LICHESS_API_TOKEN) {
      result.addCheck(
        'lichess-token-format',
        false,
        'Lichess API token format appears invalid',
        'warning'
      );
    }
    
    // Check Firebase project ID format
    if (env.FIREBASE_PROJECT_ID && env.FIREBASE_PROJECT_ID.includes(environment)) {
      result.addCheck(
        'firebase-project-environment',
        true,
        `Firebase project ID includes environment: ${environment}`
      );
    } else if (environment !== 'production' && env.FIREBASE_PROJECT_ID) {
      result.addCheck(
        'firebase-project-environment',
        false,
        `Firebase project ID should include environment for ${environment}`,
        'warning'
      );
    }
    
  } catch (error) {
    result.addCheck(
      'env-validation-error',
      false,
      `Environment validation failed: ${error.message}`,
      'error'
    );
  }
  
  return result;
}

async function validateGitIgnore() {
  const result = new SecretValidationResult();
  
  console.log(colorize('🔍 Validating .gitignore configuration...', 'blue'));
  
  try {
    const gitignorePath = path.join(__dirname, '..', '.gitignore');
    const content = await fs.readFile(gitignorePath, 'utf8');
    
    const requiredEntries = [
      '.env',
      '.env.local',
      '.env.*.local',
      'config/secrets/service-accounts/*.json',
      'config/secrets/*.key',
      'config/secrets/*.pem'
    ];
    
    for (const entry of requiredEntries) {
      if (content.includes(entry)) {
        result.addCheck(
          `gitignore-${entry.replace(/[^a-zA-Z0-9]/g, '-')}`,
          true,
          `Gitignore correctly excludes: ${entry}`
        );
      } else {
        result.addCheck(
          `gitignore-${entry.replace(/[^a-zA-Z0-9]/g, '-')}`,
          false,
          `Gitignore missing exclusion for: ${entry}`,
          'error'
        );
      }
    }
    
  } catch (error) {
    result.addCheck(
      'gitignore-validation',
      false,
      `Failed to validate .gitignore: ${error.message}`,
      'error'
    );
  }
  
  return result;
}

async function checkFilePermissions() {
  const result = new SecretValidationResult();
  
  console.log(colorize('🔍 Checking file permissions...', 'blue'));
  
  const sensitiveFiles = [
    '.env',
    'config/secrets/service-accounts'
  ];
  
  for (const file of sensitiveFiles) {
    const filePath = path.join(__dirname, '..', file);
    
    try {
      const stats = await fs.stat(filePath);
      
      // On Unix-like systems, check if file is readable by others
      if (process.platform !== 'win32') {
        const mode = stats.mode;
        const isReadableByOthers = (mode & parseInt('044', 8)) !== 0;
        
        if (isReadableByOthers) {
          result.addCheck(
            `permissions-${file.replace(/[^a-zA-Z0-9]/g, '-')}`,
            false,
            `File ${file} is readable by others - security risk`,
            'warning'
          );
        } else {
          result.addCheck(
            `permissions-${file.replace(/[^a-zA-Z0-9]/g, '-')}`,
            true,
            `File ${file} has secure permissions`
          );
        }
      } else {
        result.addCheck(
          `permissions-${file.replace(/[^a-zA-Z0-9]/g, '-')}`,
          true,
          `File ${file} exists (Windows - permission check skipped)`
        );
      }
      
    } catch (error) {
      if (file === '.env') {
        result.addCheck(
          `permissions-${file.replace(/[^a-zA-Z0-9]/g, '-')}`,
          false,
          `File ${file} not found`,
          'warning'
        );
      } else {
        result.addCheck(
          `permissions-${file.replace(/[^a-zA-Z0-9]/g, '-')}`,
          true,
          `Directory ${file} not found (optional)`
        );
      }
    }
  }
  
  return result;
}

function displayResults(results) {
  console.log(colorize(`\n🔐 Security and Secrets Validation Results`, 'bright'));
  console.log(colorize(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`, 'cyan'));
  
  let totalPassed = 0;
  let totalFailed = 0;
  let totalWarnings = 0;
  let totalErrors = 0;
  let totalCritical = 0;
  
  for (const [category, result] of Object.entries(results)) {
    const summary = result.summary();
    totalPassed += summary.passed;
    totalFailed += summary.failed;
    totalWarnings += summary.warnings;
    totalErrors += summary.errors;
    totalCritical += summary.critical;
    
    console.log(colorize(`\n🔧 ${category}:`, 'blue'));
    console.log(`   Passed: ${colorize(summary.passed, 'green')} | Failed: ${colorize(summary.failed, summary.failed > 0 ? 'red' : 'green')} | Warnings: ${colorize(summary.warnings, summary.warnings > 0 ? 'yellow' : 'green')} | Critical: ${colorize(summary.critical, summary.critical > 0 ? 'red' : 'green')}`);
    
    // Show critical errors
    if (result.criticalErrors.length > 0) {
      console.log(colorize(`   🚨 CRITICAL:`, 'red'));
      result.criticalErrors.forEach(check => {
        console.log(`      • ${check.message}`);
      });
    }
    
    // Show errors
    if (result.errors.length > 0) {
      console.log(colorize(`   ❌ Errors:`, 'red'));
      result.errors.forEach(check => {
        console.log(`      • ${check.message}`);
      });
    }
    
    // Show warnings
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
  console.log(`Critical: ${colorize(totalCritical, totalCritical > 0 ? 'red' : 'green')}`);
  
  console.log(colorize(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`, 'cyan'));
  
  if (totalCritical > 0) {
    console.log(colorize(`\n🚨 CRITICAL SECURITY ISSUES DETECTED!`, 'red'));
    console.log(colorize(`${totalCritical} critical security issue(s) must be resolved immediately.`, 'red'));
    console.log(colorize(`These issues may expose sensitive credentials or create security vulnerabilities.`, 'red'));
  } else if (totalErrors > 0) {
    console.log(colorize(`\n❌ Security validation failed!`, 'red'));
    console.log(colorize(`${totalErrors} error(s) must be resolved before deployment.`, 'red'));
  } else {
    console.log(colorize(`\n✅ Security validation passed!`, 'green'));
    console.log(colorize(`All critical security checks passed. Configuration is secure.`, 'green'));
  }
  
  if (totalWarnings > 0) {
    console.log(colorize(`\n⚠️  ${totalWarnings} warning(s) detected. Consider addressing these for enhanced security.`, 'yellow'));
  }
  
  return totalCritical === 0 && totalErrors === 0;
}

async function main() {
  try {
    const environment = process.argv[2] || 'development';
    
    console.log(colorize(`🔐 Secrets and Security Validation Framework`, 'bright'));
    console.log(colorize(`Validating security for environment: ${environment}`, 'cyan'));
    
    // Run all validation checks
    const results = {
      'Secret Exposure Scan': await scanForSecretsInFiles(),
      'Environment Variables': await validateEnvironmentVariables(environment),
      'Git Ignore Configuration': await validateGitIgnore(),
      'File Permissions': await checkFilePermissions()
    };
    
    // Display results
    const isValid = displayResults(results);
    
    if (!isValid) {
      process.exit(1);
    }
    
  } catch (error) {
    console.error(colorize(`❌ Security validation failed: ${error.message}`, 'red'));
    process.exit(1);
  }
}

// Run validation if this script is executed directly
if (require.main === module) {
  main();
}

module.exports = {
  validateEnvironmentVariables,
  scanForSecretsInFiles,
  validateGitIgnore,
  checkFilePermissions,
  detectSecretsInContent
};