#!/usr/bin/env node
/**
 * Environment Validation Script
 * Checks that all required tools and configurations are properly set up
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// ANSI color codes for terminal output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
};

class EnvironmentValidator {
  constructor() {
    this.checks = [];
    this.warnings = [];
    this.errors = [];
  }

  log(message, color = 'reset') {
    console.log(`${colors[color]}${message}${colors.reset}`);
  }

  success(message) {
    this.log(`✅ ${message}`, 'green');
  }

  warning(message) {
    this.log(`⚠️  ${message}`, 'yellow');
    this.warnings.push(message);
  }

  error(message) {
    this.log(`❌ ${message}`, 'red');
    this.errors.push(message);
  }

  info(message) {
    this.log(`ℹ️  ${message}`, 'blue');
  }

  header(message) {
    this.log(`\n${colors.bright}${colors.cyan}${message}${colors.reset}`);
  }

  async checkCommand(command, description, required = true) {
    try {
      const output = execSync(command, { encoding: 'utf8', stdio: 'pipe' });
      this.success(`${description}: ${output.trim()}`);
      return true;
    } catch (error) {
      if (required) {
        this.error(`${description}: Not found or not working`);
      } else {
        this.warning(`${description}: Not found (optional)`);
      }
      return false;
    }
  }

  checkFile(filePath, description, required = true) {
    if (fs.existsSync(filePath)) {
      this.success(`${description}: Found`);
      return true;
    } else {
      if (required) {
        this.error(`${description}: Missing (${filePath})`);
      } else {
        this.warning(`${description}: Missing (${filePath})`);
      }
      return false;
    }
  }

  async checkNodeVersion() {
    this.header('🟢 Node.js Environment');
    
    await this.checkCommand('node --version', 'Node.js version');
    await this.checkCommand('npm --version', 'npm version');
    
    // Check if using correct Node version
    try {
      const nodeVersion = execSync('node --version', { encoding: 'utf8' }).trim();
      const majorVersion = parseInt(nodeVersion.replace('v', '').split('.')[0]);
      
      if (majorVersion >= 18) {
        this.success(`Node.js version ${nodeVersion} is compatible`);
      } else {
        this.error(`Node.js version ${nodeVersion} is too old. Requires Node 18+`);
      }
    } catch (error) {
      this.error('Could not determine Node.js version');
    }
  }

  async checkPythonEnvironment() {
    this.header('🐍 Python Environment');
    
    await this.checkCommand('python --version', 'Python version');
    await this.checkCommand('pip --version', 'pip version');
    
    // Check Python version
    try {
      const pythonVersion = execSync('python --version', { encoding: 'utf8' }).trim();
      const versionMatch = pythonVersion.match(/Python (\d+)\.(\d+)/);
      
      if (versionMatch) {
        const [, major, minor] = versionMatch;
        if (parseInt(major) === 3 && parseInt(minor) >= 9) {
          this.success(`${pythonVersion} is compatible`);
        } else {
          this.error(`${pythonVersion} is too old. Requires Python 3.9+`);
        }
      }
    } catch (error) {
      this.error('Could not determine Python version');
    }
  }

  async checkFirebaseTools() {
    this.header('🔥 Firebase Tools');
    
    const firebaseInstalled = await this.checkCommand('firebase --version', 'Firebase CLI');
    
    if (firebaseInstalled) {
      try {
        // Check if logged in
        execSync('firebase projects:list', { encoding: 'utf8', stdio: 'pipe' });
        this.success('Firebase: Authenticated');
      } catch (error) {
        this.warning('Firebase: Not authenticated. Run: firebase login');
      }
    }
  }

  async checkGoogleCloudSDK() {
    this.header('☁️ Google Cloud SDK');
    
    const gcloudInstalled = await this.checkCommand('gcloud --version', 'Google Cloud SDK', false);
    const gsutilInstalled = await this.checkCommand('gsutil --version', 'gsutil', false);
    
    if (gcloudInstalled) {
      try {
        const accounts = execSync('gcloud auth list --format="value(account)"', { 
          encoding: 'utf8', 
          stdio: 'pipe' 
        }).trim();
        
        if (accounts) {
          this.success(`Google Cloud: Authenticated (${accounts.split('\n')[0]})`);
        } else {
          this.warning('Google Cloud: Not authenticated. Run: gcloud auth login');
        }
      } catch (error) {
        this.warning('Google Cloud: Authentication status unknown');
      }
    }
  }

  checkProjectStructure() {
    this.header('📁 Project Structure');
    
    const requiredDirs = [
      'src',
      'src/backend',
      'src/backend/functions',
      'tests',
      'docs',
      'scripts',
      'config'
    ];
    
    const requiredFiles = [
      'package.json',
      'firebase.json',
      'requirements.txt',
      '.eslintrc.json',
      '.prettierrc.json',
      'tsconfig.json'
    ];
    
    requiredDirs.forEach(dir => {
      this.checkFile(dir, `Directory: ${dir}`);
    });
    
    requiredFiles.forEach(file => {
      this.checkFile(file, `File: ${file}`);
    });
  }

  checkGitConfiguration() {
    this.header('📋 Git Configuration');
    
    this.checkCommand('git --version', 'Git version');
    
    try {
      const gitUser = execSync('git config user.name', { encoding: 'utf8' }).trim();
      const gitEmail = execSync('git config user.email', { encoding: 'utf8' }).trim();
      
      this.success(`Git user: ${gitUser} <${gitEmail}>`);
    } catch (error) {
      this.warning('Git user configuration not set');
    }
    
    // Check if we're in a git repository
    try {
      execSync('git rev-parse --git-dir', { stdio: 'pipe' });
      this.success('Git repository: Initialized');
    } catch (error) {
      this.error('Git repository: Not initialized');
    }
  }

  checkEnvironmentVariables() {
    this.header('🔐 Environment Variables');
    
    const envVars = [
      'NODE_ENV',
      'GOOGLE_APPLICATION_CREDENTIALS',
      'FIREBASE_PROJECT_ID'
    ];
    
    envVars.forEach(envVar => {
      if (process.env[envVar]) {
        this.success(`${envVar}: Set`);
      } else {
        this.warning(`${envVar}: Not set`);
      }
    });
  }

  async checkDependencies() {
    this.header('📦 Dependencies');
    
    // Check if node_modules exists
    if (fs.existsSync('node_modules')) {
      this.success('Node modules: Installed');
    } else {
      this.error('Node modules: Not installed. Run: npm install');
    }
    
    // Check if Python packages are installed
    try {
      execSync('pip list | grep requests', { stdio: 'pipe' });
      this.success('Python packages: Some packages detected');
    } catch (error) {
      this.warning('Python packages: May need installation. Run: pip install -r requirements-dev.txt');
    }
  }

  generateReport() {
    this.header('📊 Validation Summary');
    
    const total = this.checks.length;
    const errorCount = this.errors.length;
    const warningCount = this.warnings.length;
    const successCount = total - errorCount - warningCount;
    
    this.log(`\nResults:`);
    this.log(`  ✅ Passed: ${successCount}`, 'green');
    this.log(`  ⚠️  Warnings: ${warningCount}`, 'yellow');
    this.log(`  ❌ Errors: ${errorCount}`, 'red');
    
    if (errorCount > 0) {
      this.log(`\n🚨 Critical issues found:`, 'red');
      this.errors.forEach(error => this.log(`   • ${error}`, 'red'));
    }
    
    if (warningCount > 0) {
      this.log(`\n⚠️  Recommendations:`, 'yellow');
      this.warnings.forEach(warning => this.log(`   • ${warning}`, 'yellow'));
    }
    
    if (errorCount === 0) {
      this.log(`\n🎉 Environment validation passed! Ready for development.`, 'green');
      return true;
    } else {
      this.log(`\n🛠️  Please fix the critical issues before proceeding.`, 'red');
      return false;
    }
  }

  async run() {
    this.log(`${colors.bright}${colors.magenta}🔍 V7P3R Chess Analytics - Environment Validation${colors.reset}`);
    this.log(`${colors.cyan}Checking development environment setup...${colors.reset}\n`);
    
    await this.checkNodeVersion();
    await this.checkPythonEnvironment();
    await this.checkFirebaseTools();
    await this.checkGoogleCloudSDK();
    this.checkProjectStructure();
    this.checkGitConfiguration();
    this.checkEnvironmentVariables();
    await this.checkDependencies();
    
    return this.generateReport();
  }
}

// Run validation if called directly
if (require.main === module) {
  const validator = new EnvironmentValidator();
  validator.run().then(success => {
    process.exit(success ? 0 : 1);
  }).catch(error => {
    console.error('Validation failed:', error);
    process.exit(1);
  });
}

module.exports = EnvironmentValidator;