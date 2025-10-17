#!/usr/bin/env node

/**
 * Security Scanning Integration
 * 
 * Integrates with various security scanning tools to detect vulnerabilities,
 * exposed secrets, and security misconfigurations.
 * 
 * Usage:
 *   node scripts/security-scan.js [scan-type]
 *   
 * Examples:
 *   node scripts/security-scan.js all
 *   node scripts/security-scan.js dependencies
 *   node scripts/security-scan.js secrets
 */

const { spawn } = require('child_process');
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
  cyan: '\x1b[36m',
  magenta: '\x1b[35m'
};

function colorize(text, color) {
  return `${colors[color]}${text}${colors.reset}`;
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
      resolve({ stdout, stderr, code });
    });
    
    child.on('error', (error) => {
      reject(error);
    });
  });
}

class SecurityScanResult {
  constructor() {
    this.scans = [];
    this.vulnerabilities = [];
    this.warnings = [];
    this.passed = 0;
    this.failed = 0;
  }
  
  addScan(name, status, message, severity = 'info', details = null) {
    const scan = { name, status, message, severity, details };
    this.scans.push(scan);
    
    if (status) {
      this.passed++;
    } else {
      this.failed++;
      if (severity === 'critical' || severity === 'high') {
        this.vulnerabilities.push(scan);
      } else {
        this.warnings.push(scan);
      }
    }
    
    return this;
  }
  
  summary() {
    return {
      total: this.scans.length,
      passed: this.passed,
      failed: this.failed,
      vulnerabilities: this.vulnerabilities.length,
      warnings: this.warnings.length
    };
  }
}

async function scanDependencies() {
  const result = new SecurityScanResult();
  
  console.log(colorize('🔍 Scanning dependencies for vulnerabilities...', 'blue'));
  
  try {
    // Check if npm audit is available
    const auditResult = await runCommand('npm', ['audit', '--json'], { silent: true });
    
    if (auditResult.code === 0) {
      result.addScan('npm-audit', true, 'No vulnerabilities found in dependencies');
    } else {
      try {
        const auditData = JSON.parse(auditResult.stdout);
        
        if (auditData.vulnerabilities) {
          const vulnCount = Object.keys(auditData.vulnerabilities).length;
          const highVulns = Object.values(auditData.vulnerabilities)
            .filter(v => v.severity === 'high' || v.severity === 'critical').length;
          
          if (highVulns > 0) {
            result.addScan(
              'npm-audit-high',
              false,
              `${highVulns} high/critical vulnerabilities found`,
              'high',
              auditData.vulnerabilities
            );
          }
          
          if (vulnCount > highVulns) {
            result.addScan(
              'npm-audit-low',
              false,
              `${vulnCount - highVulns} low/moderate vulnerabilities found`,
              'medium'
            );
          }
        }
      } catch (parseError) {
        result.addScan(
          'npm-audit-parse',
          false,
          'Failed to parse npm audit results',
          'medium'
        );
      }
    }
    
  } catch (error) {
    result.addScan(
      'npm-audit-error',
      false,
      `Dependency scan failed: ${error.message}`,
      'medium'
    );
  }
  
  // Check for outdated packages
  try {
    const outdatedResult = await runCommand('npm', ['outdated', '--json'], { silent: true });
    
    if (outdatedResult.code === 0) {
      result.addScan('npm-outdated', true, 'All packages are up to date');
    } else {
      try {
        const outdatedData = JSON.parse(outdatedResult.stdout);
        const outdatedCount = Object.keys(outdatedData).length;
        
        if (outdatedCount > 0) {
          result.addScan(
            'npm-outdated',
            false,
            `${outdatedCount} packages are outdated`,
            'low',
            outdatedData
          );
        }
      } catch (parseError) {
        result.addScan(
          'npm-outdated',
          true,
          'Package version check completed'
        );
      }
    }
    
  } catch (error) {
    result.addScan(
      'npm-outdated-error',
      false,
      `Package version check failed: ${error.message}`,
      'low'
    );
  }
  
  return result;
}

async function scanSecrets() {
  const result = new SecurityScanResult();
  
  console.log(colorize('🔍 Scanning for exposed secrets...', 'blue'));
  
  // Use our existing secret validation
  const { validateSecrets } = require('./validate-secrets');
  
  try {
    const secretValidation = await validateSecrets();
    
    if (secretValidation.criticalErrors.length === 0) {
      result.addScan('secret-exposure', true, 'No critical secret exposures detected');
    } else {
      result.addScan(
        'secret-exposure',
        false,
        `${secretValidation.criticalErrors.length} critical secret exposures found`,
        'critical',
        secretValidation.criticalErrors
      );
    }
    
    if (secretValidation.warnings.length > 0) {
      result.addScan(
        'secret-warnings',
        false,
        `${secretValidation.warnings.length} secret-related warnings`,
        'medium',
        secretValidation.warnings
      );
    }
    
  } catch (error) {
    result.addScan(
      'secret-scan-error',
      false,
      `Secret scanning failed: ${error.message}`,
      'medium'
    );
  }
  
  return result;
}

async function scanCodeQuality() {
  const result = new SecurityScanResult();
  
  console.log(colorize('🔍 Scanning code quality and security patterns...', 'blue'));
  
  // ESLint security scanning
  try {
    const eslintResult = await runCommand('npx', ['eslint', 'src/', '--format', 'json'], { silent: true });
    
    if (eslintResult.code === 0) {
      result.addScan('eslint-security', true, 'No ESLint security issues found');
    } else {
      try {
        const eslintData = JSON.parse(eslintResult.stdout);
        const securityIssues = eslintData
          .flatMap(file => file.messages)
          .filter(msg => msg.ruleId && msg.ruleId.includes('security'));
        
        if (securityIssues.length > 0) {
          result.addScan(
            'eslint-security',
            false,
            `${securityIssues.length} ESLint security issues found`,
            'medium',
            securityIssues
          );
        } else {
          const totalIssues = eslintData.reduce((sum, file) => sum + file.messages.length, 0);
          if (totalIssues > 0) {
            result.addScan(
              'eslint-general',
              false,
              `${totalIssues} code quality issues found`,
              'low'
            );
          } else {
            result.addScan('eslint-general', true, 'No code quality issues found');
          }
        }
        
      } catch (parseError) {
        result.addScan(
          'eslint-parse',
          false,
          'Failed to parse ESLint results',
          'low'
        );
      }
    }
    
  } catch (error) {
    result.addScan(
      'eslint-error',
      false,
      `Code quality scan failed: ${error.message}`,
      'low'
    );
  }
  
  return result;
}

async function scanConfiguration() {
  const result = new SecurityScanResult();
  
  console.log(colorize('🔍 Scanning configuration security...', 'blue'));
  
  // Check Firebase configuration
  try {
    const firebaseJsonPath = path.join(__dirname, '..', 'firebase.json');
    const firebaseConfig = JSON.parse(await fs.readFile(firebaseJsonPath, 'utf8'));
    
    // Check for development features in production-looking config
    if (firebaseConfig.emulators && process.env.NODE_ENV === 'production') {
      result.addScan(
        'firebase-emulators-prod',
        false,
        'Emulators configuration found in production environment',
        'high'
      );
    } else {
      result.addScan('firebase-config', true, 'Firebase configuration appears secure');
    }
    
    // Check security rules exist
    if (firebaseConfig.firestore && firebaseConfig.firestore.rules) {
      result.addScan('firestore-rules', true, 'Firestore security rules configured');
    } else {
      result.addScan(
        'firestore-rules',
        false,
        'Firestore security rules not configured',
        'high'
      );
    }
    
  } catch (error) {
    result.addScan(
      'firebase-config-error',
      false,
      `Firebase configuration scan failed: ${error.message}`,
      'medium'
    );
  }
  
  // Check environment configuration
  try {
    const envPath = path.join(__dirname, '..', '.env');
    
    try {
      await fs.access(envPath);
      
      const envContent = await fs.readFile(envPath, 'utf8');
      
      // Check for placeholder values
      if (envContent.includes('your_') || envContent.includes('REPLACE_WITH_')) {
        result.addScan(
          'env-placeholders',
          false,
          'Environment file contains placeholder values',
          'medium'
        );
      } else {
        result.addScan('env-placeholders', true, 'No placeholder values in environment file');
      }
      
      // Check for hardcoded URLs
      if (envContent.includes('localhost') && process.env.NODE_ENV === 'production') {
        result.addScan(
          'env-localhost-prod',
          false,
          'Environment file contains localhost URLs in production',
          'high'
        );
      }
      
    } catch (envError) {
      result.addScan(
        'env-missing',
        false,
        'Environment file not found',
        'medium'
      );
    }
    
  } catch (error) {
    result.addScan(
      'env-scan-error',
      false,
      `Environment scan failed: ${error.message}`,
      'low'
    );
  }
  
  return result;
}

async function generateSecurityReport(results) {
  const reportPath = path.join(__dirname, '..', 'security-report.json');
  
  const report = {
    timestamp: new Date().toISOString(),
    summary: {
      totalScans: results.reduce((sum, r) => sum + r.summary().total, 0),
      totalPassed: results.reduce((sum, r) => sum + r.summary().passed, 0),
      totalFailed: results.reduce((sum, r) => sum + r.summary().failed, 0),
      totalVulnerabilities: results.reduce((sum, r) => sum + r.summary().vulnerabilities, 0),
      totalWarnings: results.reduce((sum, r) => sum + r.summary().warnings, 0)
    },
    scans: {
      dependencies: results[0]?.scans || [],
      secrets: results[1]?.scans || [],
      codeQuality: results[2]?.scans || [],
      configuration: results[3]?.scans || []
    }
  };
  
  try {
    await fs.writeFile(reportPath, JSON.stringify(report, null, 2));
    console.log(colorize(`📄 Security report saved to: ${reportPath}`, 'green'));
  } catch (error) {
    console.log(colorize(`⚠️  Could not save security report: ${error.message}`, 'yellow'));
  }
  
  return report;
}

function displayResults(results) {
  console.log(colorize(`\n🛡️  Security Scanning Results`, 'bright'));
  console.log(colorize(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`, 'cyan'));
  
  const scanTypes = ['Dependencies', 'Secrets', 'Code Quality', 'Configuration'];
  let totalVulnerabilities = 0;
  let totalWarnings = 0;
  let totalPassed = 0;
  let totalFailed = 0;
  
  results.forEach((result, index) => {
    const summary = result.summary();
    totalPassed += summary.passed;
    totalFailed += summary.failed;
    totalVulnerabilities += summary.vulnerabilities;
    totalWarnings += summary.warnings;
    
    console.log(colorize(`\n🔧 ${scanTypes[index]}:`, 'blue'));
    console.log(`   Passed: ${colorize(summary.passed, 'green')} | Failed: ${colorize(summary.failed, summary.failed > 0 ? 'red' : 'green')} | Vulnerabilities: ${colorize(summary.vulnerabilities, summary.vulnerabilities > 0 ? 'red' : 'green')} | Warnings: ${colorize(summary.warnings, summary.warnings > 0 ? 'yellow' : 'green')}`);
    
    // Show vulnerabilities
    if (result.vulnerabilities.length > 0) {
      console.log(colorize(`   🚨 VULNERABILITIES:`, 'red'));
      result.vulnerabilities.forEach(vuln => {
        console.log(`      • ${vuln.message}`);
      });
    }
    
    // Show warnings
    if (result.warnings.length > 0) {
      console.log(colorize(`   ⚠️  Warnings:`, 'yellow'));
      result.warnings.forEach(warning => {
        console.log(`      • ${warning.message}`);
      });
    }
  });
  
  console.log(colorize(`\n📈 Overall Security Summary:`, 'bright'));
  console.log(`Total Scans: ${totalPassed + totalFailed}`);
  console.log(`Passed: ${colorize(totalPassed, 'green')}`);
  console.log(`Failed: ${colorize(totalFailed, totalFailed > 0 ? 'red' : 'green')}`);
  console.log(`Vulnerabilities: ${colorize(totalVulnerabilities, totalVulnerabilities > 0 ? 'red' : 'green')}`);
  console.log(`Warnings: ${colorize(totalWarnings, totalWarnings > 0 ? 'yellow' : 'green')}`);
  
  console.log(colorize(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`, 'cyan'));
  
  if (totalVulnerabilities > 0) {
    console.log(colorize(`\n🚨 SECURITY VULNERABILITIES DETECTED!`, 'red'));
    console.log(colorize(`${totalVulnerabilities} security vulnerability(ies) found that require immediate attention.`, 'red'));
  } else if (totalFailed > 0) {
    console.log(colorize(`\n❌ Security scan found issues!`, 'red'));
    console.log(colorize(`${totalFailed} security check(s) failed and should be addressed.`, 'red'));
  } else {
    console.log(colorize(`\n✅ Security scans passed!`, 'green'));
    console.log(colorize(`All security checks passed. Configuration appears secure.`, 'green'));
  }
  
  if (totalWarnings > 0) {
    console.log(colorize(`\n⚠️  ${totalWarnings} warning(s) detected. Consider addressing these for enhanced security.`, 'yellow'));
  }
  
  return totalVulnerabilities === 0 && totalFailed === 0;
}

async function main() {
  try {
    const scanType = process.argv[2] || 'all';
    
    console.log(colorize(`🛡️  Security Scanning Integration`, 'bright'));
    console.log(colorize(`Running security scans: ${scanType}`, 'cyan'));
    
    const results = [];
    
    if (scanType === 'all' || scanType === 'dependencies') {
      results.push(await scanDependencies());
    }
    
    if (scanType === 'all' || scanType === 'secrets') {
      results.push(await scanSecrets());
    }
    
    if (scanType === 'all' || scanType === 'code') {
      results.push(await scanCodeQuality());
    }
    
    if (scanType === 'all' || scanType === 'config') {
      results.push(await scanConfiguration());
    }
    
    if (results.length === 0) {
      throw new Error(`Unknown scan type: ${scanType}. Available: all, dependencies, secrets, code, config`);
    }
    
    // Generate security report
    if (scanType === 'all') {
      await generateSecurityReport(results);
    }
    
    // Display results
    const isSecure = displayResults(results);
    
    if (!isSecure) {
      process.exit(1);
    }
    
  } catch (error) {
    console.error(colorize(`❌ Security scanning failed: ${error.message}`, 'red'));
    process.exit(1);
  }
}

// Run security scanning if this script is executed directly
if (require.main === module) {
  main();
}

module.exports = {
  scanDependencies,
  scanSecrets,
  scanCodeQuality,
  scanConfiguration
};