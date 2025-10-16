# Troubleshooting Guide - V7P3R Chess Engine Analytics Pipeline

**Purpose**: Common issues, solutions, and debugging procedures for the analytics pipeline.

---

## 🚨 Emergency Recovery Procedures

### Lost Chat Context Recovery
**Problem**: Chat session lost, need to recover project context  
**Solution**:
1. Read `docs/PROJECT-STATUS-DOCUMENTATION.md` for complete current status
2. Run `node scripts/validate-environment.js` to check development environment
3. Review `docs/DECISION-LOG.md` for architectural context
4. Check current phase in todo list (likely Phase 2: Infrastructure as Code)
5. Continue from documented next steps

### Development Environment Issues
**Problem**: Development setup not working after system restart  
**Solution**:
```bash
# 1. Verify Node.js and Python versions
node --version  # Should be 22.16.0
python --version  # Should be 3.13.8

# 2. Reinstall dependencies if needed
npm install
pip install -r requirements-dev.txt

# 3. Run comprehensive validation
node scripts/validate-environment.js

# 4. Check authentication status
firebase login:list
gcloud auth list
```

---

## 🔧 Development Environment Issues

### Node.js Version Issues
**Symptoms**: Package installation failures, compatibility errors  
**Diagnosis**: `node --version` shows wrong version  
**Solution**:
```bash
# Install correct Node.js version
nvm install 22.16.0
nvm use 22.16.0
nvm alias default 22.16.0

# Reinstall packages
rm -rf node_modules package-lock.json
npm install
```

### Python Environment Issues
**Symptoms**: Import errors, package not found  
**Diagnosis**: Wrong Python version or missing packages  
**Solution**:
```bash
# Verify Python version
python --version  # Should be 3.13.8

# Reinstall Python packages
pip install -r requirements.txt
pip install -r requirements-dev.txt

# If using virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate.bat  # Windows
pip install -r requirements.txt
```

### Firebase CLI Issues
**Symptoms**: "Firebase command not found", authentication errors  
**Diagnosis**: CLI not installed or not authenticated  
**Solution**:
```bash
# Install Firebase CLI globally
npm install -g firebase-tools

# Login to Firebase
firebase login

# Verify project access
firebase projects:list

# Set project (if needed)
firebase use chess-engine-metrics-agent
```

### Environment Validation Failures
**Symptoms**: `validate-environment.js` shows errors  
**Diagnosis**: Missing tools or configuration  
**Solution**: Address each failed check individually:
- **Node.js**: Install correct version with nvm
- **Python**: Install correct version with pyenv or direct installation
- **Firebase CLI**: `npm install -g firebase-tools`
- **Google Cloud SDK**: Follow Google Cloud installation guide
- **Git**: Install Git for your operating system

---

## 🔥 Firebase Integration Issues

### Firebase Authentication Errors
**Symptoms**: "Permission denied", "User not authenticated"  
**Diagnosis**: Authentication token expired or wrong project  
**Solution**:
```bash
# Logout and login again
firebase logout
firebase login

# Verify correct project
firebase use --add
firebase use chess-engine-metrics-agent

# Test authentication
firebase projects:list
```

### Firebase Functions Deployment Issues
**Symptoms**: Deployment failures, function not updating  
**Diagnosis**: Configuration errors or insufficient permissions  
**Solution**:
```bash
# Check firebase.json configuration
cat firebase.json

# Verify functions directory structure
ls -la src/backend/functions/

# Deploy with verbose logging
firebase deploy --only functions --debug

# Check Firebase console for errors
echo "Check https://console.firebase.google.com/project/chess-engine-metrics-agent/functions"
```

### Firestore Security Rules Issues
**Symptoms**: "Permission denied" when accessing Firestore  
**Diagnosis**: Security rules blocking access  
**Solution**:
```bash
# Check current security rules
firebase firestore:rules:get

# Test rules locally
firebase emulators:start --only firestore

# Deploy updated rules
firebase deploy --only firestore:rules
```

---

## 📡 API Integration Issues

### Lichess API Connection Issues
**Symptoms**: API calls failing, authentication errors  
**Diagnosis**: API token invalid or rate limiting  
**Solution**:
```bash
# Test API connection
python scripts/test_lichess_api.py

# Check API token in environment
echo $LICHESS_API_TOKEN

# Manual API test
curl -H "Authorization: Bearer lip_1vCANjDGz9euqYAcXwy7" \
     https://lichess.org/api/account
```

**Common API Issues**:
- **Rate Limiting**: Implement backoff and retry logic
- **Token Expiration**: API tokens don't expire, but verify token is correct
- **Network Issues**: Check internet connection and firewall settings
- **API Changes**: Check Lichess API documentation for updates

### Google Cloud Integration Issues
**Symptoms**: GCE instance connection failures, authentication errors  
**Diagnosis**: Authentication or network issues  
**Solution**:
```bash
# Check authentication
gcloud auth list
gcloud auth application-default login

# Verify project
gcloud config get-value project
gcloud config set project v7p3r-lichess-bot

# Test instance connection
gcloud compute instances list
gcloud compute ssh v7p3r-production-bot --zone=us-central1-a
```

---

## 🧪 Testing Issues

### Test Environment Setup Issues
**Symptoms**: Tests failing to run, import errors  
**Diagnosis**: Missing test dependencies or configuration  
**Solution**:
```bash
# Install test dependencies
npm install --dev
pip install -r requirements-dev.txt

# Run tests individually to isolate issues
npm test -- --testPathPattern=unit
python -m pytest tests/unit/ -v

# Check test configuration
cat package.json | grep -A 10 "scripts"
cat pytest.ini
```

### Firebase Emulator Issues
**Symptoms**: Emulators not starting, connection refused  
**Diagnosis**: Port conflicts or configuration issues  
**Solution**:
```bash
# Check if ports are in use
netstat -tulpn | grep -E ':(4000|8080|9099|5001)'

# Start emulators with specific ports
firebase emulators:start --port 4000

# Clear emulator data
firebase emulators:exec --ui "echo 'Clearing data'" && firebase emulators:start
```

---

## 📊 Data Pipeline Issues

### Data Collection Failures
**Symptoms**: No new game data appearing, stale data  
**Diagnosis**: API issues, function failures, or scheduling problems  
**Solution**:
1. **Check Function Logs**:
   ```bash
   firebase functions:log --only lichess-collector
   ```

2. **Test Manual Collection**:
   ```bash
   python scripts/test_lichess_api.py
   ```

3. **Verify Scheduling**:
   - Check Firebase Console for scheduled function status
   - Verify cron expressions in firebase.json

4. **Check Data Storage**:
   - Verify Firestore has recent data
   - Check for error documents in error collections

### Data Quality Issues
**Symptoms**: Missing fields, incorrect calculations, data inconsistencies  
**Diagnosis**: Data processing or validation errors  
**Solution**:
1. **Enable Debug Logging**: Add detailed logging to data processing functions
2. **Validate Input Data**: Check raw API responses for expected structure
3. **Test Processing Logic**: Unit test data transformation functions
4. **Check Data Types**: Verify Firestore schema matches expectations

---

## 🖥️ Development Workflow Issues

### Git Issues
**Symptoms**: Push failures, merge conflicts, authentication errors  
**Diagnosis**: Git configuration or repository issues  
**Solution**:
```bash
# Check Git configuration
git config --list

# Fix authentication (if using HTTPS)
git config --global credential.helper store

# Fix remote URL (if needed)
git remote -v
git remote set-url origin https://github.com/pssnyder/engine-metrics.git

# Reset to clean state (if needed)
git stash
git pull origin main
```

### Code Quality Tool Issues
**Symptoms**: Linting errors, formatting inconsistencies  
**Diagnosis**: Tool configuration or version issues  
**Solution**:
```bash
# Fix linting issues automatically
npm run lint:fix
npm run format

# Python code quality
black src/
isort src/
flake8 src/

# Update tool configurations if needed
cat .eslintrc.json
cat .prettierrc.json
cat pyproject.toml
```

---

## 🔍 Debugging Procedures

### Systematic Debugging Approach
1. **Identify Scope**: Is it environment, code, data, or configuration?
2. **Check Logs**: Function logs, browser console, terminal output
3. **Isolate Variables**: Test components individually
4. **Verify Assumptions**: Check that expected conditions are true
5. **Reproduce Minimally**: Create minimal test case
6. **Document Solution**: Update this guide with findings

### Useful Debugging Commands
```bash
# Environment validation
node scripts/validate-environment.js

# Firebase status
firebase use
firebase projects:list
firebase functions:log

# API testing
python scripts/test_lichess_api.py
curl -H "Authorization: Bearer lip_1vCANjDGz9euqYAcXwy7" https://lichess.org/api/account

# Local development
npm run dev
firebase emulators:start

# Check service status
ps aux | grep -E "(node|python|firebase)"
netstat -tulpn | grep -E ":(3000|5000|4000|8080)"
```

### Log Analysis
- **Firebase Functions**: Check Firebase Console → Functions → Logs
- **Local Development**: Check terminal output from `npm run dev`
- **API Calls**: Enable verbose logging in HTTP clients
- **Database**: Check Firestore Console for data consistency

---

## 📞 Getting Help

### Internal Resources
1. **Documentation**: Check `docs/` directory for relevant guides
2. **Decision Log**: `docs/DECISION-LOG.md` explains why choices were made
3. **Project Status**: `docs/PROJECT-STATUS-DOCUMENTATION.md` for current state

### External Resources
1. **Firebase Documentation**: https://firebase.google.com/docs
2. **Lichess API Documentation**: https://lichess.org/api
3. **Google Cloud Documentation**: https://cloud.google.com/docs
4. **Node.js Best Practices**: https://github.com/goldbergyoni/nodebestpractices

### Community Support
- **Firebase Discord**: Firebase community Discord server
- **Stack Overflow**: Tag questions with specific technologies
- **GitHub Issues**: Check repository issues for similar problems

---

## 📝 Issue Reporting Template

When documenting new issues, use this template:

```markdown
## Issue Title: [Brief Description]

**Date**: [YYYY-MM-DD]
**Environment**: [Development/Staging/Production]
**Phase**: [Current project phase]

### Problem Description
[Detailed description of the issue]

### Steps to Reproduce
1. [First step]
2. [Second step]
3. [etc.]

### Expected Behavior
[What should happen]

### Actual Behavior
[What actually happens]

### Error Messages
```
[Include full error messages and stack traces]
```

### Environment Details
- Node.js version: [version]
- Python version: [version]
- Firebase CLI version: [version]
- Operating System: [OS and version]

### Investigation Steps Taken
[What debugging steps were already attempted]

### Solution (if found)
[How the issue was resolved]

### Prevention
[How to prevent this issue in the future]
```

---

**Note**: Keep this troubleshooting guide updated as new issues are discovered and resolved. Each solution should be tested and verified before documenting.