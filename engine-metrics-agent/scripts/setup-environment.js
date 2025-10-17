#!/usr/bin/env node

/**
 * Secure Environment Setup Manager
 * 
 * Helps set up environment variables securely for different environments.
 * Provides templates, validation, and security best practices guidance.
 * 
 * Usage:
 *   node scripts/setup-environment.js [environment]
 *   
 * Examples:
 *   node scripts/setup-environment.js development
 *   node scripts/setup-environment.js staging
 *   node scripts/setup-environment.js production
 */

const fs = require('fs').promises;
const path = require('path');
const readline = require('readline');

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

async function createReadlineInterface() {
  return readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
}

async function promptUser(question) {
  const rl = await createReadlineInterface();
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      rl.close();
      resolve(answer.trim());
    });
  });
}

async function checkIfEnvExists() {
  const envPath = path.join(__dirname, '..', '.env');
  
  try {
    await fs.access(envPath);
    return true;
  } catch (error) {
    return false;
  }
}

async function loadTemplate(environment) {
  const templatePath = path.join(__dirname, '..', 'config', 'secrets', 'templates', `.env.${environment}`);
  
  try {
    const content = await fs.readFile(templatePath, 'utf8');
    return content;
  } catch (error) {
    throw new Error(`Template not found for environment '${environment}': ${error.message}`);
  }
}

async function createEnvironmentFile(environment, template) {
  const envPath = path.join(__dirname, '..', '.env');
  
  // Add header comment
  const header = `# Environment Variables for ${environment.toUpperCase()}
# Generated on ${new Date().toISOString()}
# Source template: config/secrets/templates/.env.${environment}
# 
# IMPORTANT SECURITY NOTES:
# - This file contains sensitive information
# - DO NOT commit this file to version control
# - Ensure .env is in your .gitignore file
# - Use secure values for production environments
# 
# ============================================================================
\n`;
  
  const content = header + template;
  
  try {
    await fs.writeFile(envPath, content, 'utf8');
    return envPath;
  } catch (error) {
    throw new Error(`Failed to create .env file: ${error.message}`);
  }
}

async function updateGitignore() {
  const gitignorePath = path.join(__dirname, '..', '.gitignore');
  
  try {
    let gitignoreContent = '';
    try {
      gitignoreContent = await fs.readFile(gitignorePath, 'utf8');
    } catch (error) {
      // File doesn't exist, start with empty content
    }
    
    const envEntries = [
      '# Environment variables and secrets',
      '.env',
      '.env.local',
      '.env.*.local',
      'config/secrets/service-accounts/*.json',
      'config/secrets/*.key',
      'config/secrets/*.pem'
    ];
    
    let needsUpdate = false;
    const updatedEntries = [];
    
    for (const entry of envEntries) {
      if (!gitignoreContent.includes(entry)) {
        updatedEntries.push(entry);
        needsUpdate = true;
      }
    }
    
    if (needsUpdate) {
      const separator = gitignoreContent.length > 0 ? '\n\n' : '';
      const newContent = gitignoreContent + separator + updatedEntries.join('\n') + '\n';
      await fs.writeFile(gitignorePath, newContent, 'utf8');
      console.log(colorize('✓ Updated .gitignore to exclude environment files', 'green'));
    } else {
      console.log(colorize('✓ .gitignore already configured for environment files', 'green'));
    }
    
  } catch (error) {
    console.log(colorize(`⚠️  Could not update .gitignore: ${error.message}`, 'yellow'));
  }
}

async function validateEnvironment(environment) {
  const validEnvironments = ['development', 'staging', 'production'];
  
  if (!validEnvironments.includes(environment)) {
    throw new Error(`Invalid environment '${environment}'. Valid options: ${validEnvironments.join(', ')}`);
  }
  
  return true;
}

async function showSecurityGuidelines(environment) {
  console.log(colorize(`\n🔐 Security Guidelines for ${environment.toUpperCase()}`, 'bright'));
  console.log(colorize(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`, 'cyan'));
  
  if (environment === 'development') {
    console.log(colorize('🛠️  Development Environment:', 'blue'));
    console.log('   • Use test API tokens when possible');
    console.log('   • Never use production secrets in development');
    console.log('   • Keep development tokens with limited permissions');
    console.log('   • Regularly rotate development credentials');
    
  } else if (environment === 'staging') {
    console.log(colorize('🧪 Staging Environment:', 'blue'));
    console.log('   • Use production-like security settings');
    console.log('   • Test all security features before production');
    console.log('   • Use separate Firebase project for isolation');
    console.log('   • Monitor for security vulnerabilities');
    
  } else if (environment === 'production') {
    console.log(colorize('🚨 PRODUCTION Environment:', 'red'));
    console.log(colorize('   • NEVER store secrets in files!', 'red'));
    console.log('   • Use Firebase Functions config: firebase functions:config:set');
    console.log('   • Use Google Secret Manager for sensitive data');
    console.log('   • Enable all security features and monitoring');
    console.log('   • Implement secret rotation procedures');
    console.log('   • Use least-privilege access principles');
  }
  
  console.log(colorize(`\n🔒 General Security Best Practices:`, 'blue'));
  console.log('   • Never commit .env files to version control');
  console.log('   • Use different secrets for each environment');
  console.log('   • Regularly rotate API keys and tokens');
  console.log('   • Monitor for unusual access patterns');
  console.log('   • Keep dependencies updated and scanned');
  console.log('   • Use HTTPS for all external communications');
  
  console.log(colorize(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`, 'cyan'));
}

async function showNextSteps(environment, envPath) {
  console.log(colorize(`\n🚀 Next Steps for ${environment.toUpperCase()}`, 'bright'));
  console.log(colorize(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`, 'cyan'));
  
  console.log(colorize('1. Review and update the .env file:', 'blue'));
  console.log(`   ${colorize(`code ${envPath}`, 'cyan')}`);
  
  console.log(colorize('\n2. Replace placeholder values with actual secrets:', 'blue'));
  console.log('   • LICHESS_API_TOKEN: Your actual Lichess API token');
  console.log('   • GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON');
  console.log('   • FIREBASE_PROJECT_ID: Your Firebase project ID');
  
  if (environment === 'development') {
    console.log(colorize('\n3. Start development environment:', 'blue'));
    console.log(`   ${colorize('npm run configure:dev', 'cyan')}`);
    console.log(`   ${colorize('npm run dev', 'cyan')}`);
    
  } else if (environment === 'staging') {
    console.log(colorize('\n3. Deploy to staging:', 'blue'));
    console.log(`   ${colorize('npm run configure:staging', 'cyan')}`);
    console.log(`   ${colorize('npm run deploy:staging', 'cyan')}`);
    
  } else if (environment === 'production') {
    console.log(colorize('\n3. Set up secure secret management:', 'red'));
    console.log(`   ${colorize('firebase functions:config:set lichess.token="your_token"', 'cyan')}`);
    console.log(`   ${colorize('firebase functions:config:set gcp.credentials="path_to_service_account"', 'cyan')}`);
    console.log(colorize('\n4. Deploy to production:', 'red'));
    console.log(`   ${colorize('npm run configure:prod', 'cyan')}`);
    console.log(`   ${colorize('npm run deploy:prod', 'cyan')}`);
  }
  
  console.log(colorize('\n4. Validate your setup:', 'blue'));
  console.log(`   ${colorize('npm run validate:infrastructure', 'cyan')}`);
  console.log(`   ${colorize('node scripts/validate-secrets.js', 'cyan')}`);
  
  console.log(colorize(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`, 'cyan'));
}

async function showExistingEnvWarning() {
  console.log(colorize(`\n⚠️  WARNING: .env file already exists!`, 'yellow'));
  console.log(colorize(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`, 'yellow'));
  console.log('An .env file already exists in your project root.');
  console.log('This setup will create a backup and replace it with a new template.');
  console.log(colorize(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`, 'yellow'));
}

async function backupExistingEnv() {
  const envPath = path.join(__dirname, '..', '.env');
  const backupPath = path.join(__dirname, '..', `.env.backup.${Date.now()}`);
  
  try {
    await fs.copyFile(envPath, backupPath);
    console.log(colorize(`✓ Backed up existing .env to ${path.basename(backupPath)}`, 'green'));
    return backupPath;
  } catch (error) {
    throw new Error(`Failed to backup existing .env: ${error.message}`);
  }
}

async function main() {
  try {
    const environment = process.argv[2] || 'development';
    
    console.log(colorize(`🔐 Secure Environment Setup Manager`, 'bright'));
    console.log(colorize(`Setting up environment: ${environment}`, 'cyan'));
    
    // Validate environment
    await validateEnvironment(environment);
    
    // Check if .env already exists
    const envExists = await checkIfEnvExists();
    if (envExists) {
      await showExistingEnvWarning();
      
      const proceed = await promptUser('Do you want to continue and replace the existing .env file? (y/N): ');
      if (proceed.toLowerCase() !== 'y' && proceed.toLowerCase() !== 'yes') {
        console.log(colorize('❌ Setup cancelled', 'red'));
        process.exit(0);
      }
      
      // Backup existing .env
      await backupExistingEnv();
    }
    
    // Load template
    console.log(colorize(`📖 Loading template for ${environment}...`, 'blue'));
    const template = await loadTemplate(environment);
    
    // Create .env file
    console.log(colorize(`📝 Creating .env file...`, 'blue'));
    const envPath = await createEnvironmentFile(environment, template);
    console.log(colorize(`✓ Created .env file: ${envPath}`, 'green'));
    
    // Update .gitignore
    await updateGitignore();
    
    // Show security guidelines
    await showSecurityGuidelines(environment);
    
    // Show next steps
    await showNextSteps(environment, envPath);
    
    console.log(colorize(`\n🎉 Environment setup complete!`, 'bright'));
    console.log(colorize(`Remember to update the .env file with your actual secrets before using.`, 'green'));
    
  } catch (error) {
    console.error(colorize(`❌ Setup failed: ${error.message}`, 'red'));
    process.exit(1);
  }
}

// Run setup if this script is executed directly
if (require.main === module) {
  main();
}

module.exports = {
  loadTemplate,
  createEnvironmentFile,
  validateEnvironment
};