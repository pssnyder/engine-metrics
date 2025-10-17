# Service Account Management

This directory contains templates and configurations for Google Cloud service accounts used in the V7P3R Chess Engine Analytics project.

## ⚠️ SECURITY WARNING

**NEVER COMMIT ACTUAL SERVICE ACCOUNT KEYS TO VERSION CONTROL**

This directory should contain:
- ✅ Templates and configuration documentation
- ✅ Service account setup scripts
- ✅ Permission and role definitions
- ❌ Actual .json key files
- ❌ Private keys or credentials

## Service Account Structure

### Development Environment
```
development-service-account.json.template   # Template for development SA
```

### Staging Environment  
```
staging-service-account.json.template      # Template for staging SA
```

### Production Environment
```
production-service-account.json.template   # Template for production SA
```

## Required Permissions

### Firebase Functions Service Account
- **Cloud Datastore User**: Read/write access to Firestore
- **Storage Object Admin**: Read/write access to Cloud Storage
- **Cloud Functions Invoker**: Invoke other functions
- **Firebase Admin**: Administrative access to Firebase services

### Analytics Service Account
- **BigQuery Data Editor**: Write access to analytics datasets
- **Cloud Storage Object Viewer**: Read access to raw data
- **Monitoring Metric Writer**: Write custom metrics

### Backup Service Account
- **Storage Admin**: Full access to backup storage buckets
- **Cloud SQL Backup**: Database backup operations
- **Compute Instance Admin**: Snapshot creation

## Setup Procedures

### 1. Create Service Accounts
```bash
# Development
gcloud iam service-accounts create v7p3r-dev-functions \
  --display-name="V7P3R Development Functions" \
  --description="Service account for development environment functions"

# Staging  
gcloud iam service-accounts create v7p3r-staging-functions \
  --display-name="V7P3R Staging Functions" \
  --description="Service account for staging environment functions"

# Production
gcloud iam service-accounts create v7p3r-prod-functions \
  --display-name="V7P3R Production Functions" \
  --description="Service account for production environment functions"
```

### 2. Assign Roles (Least Privilege)
```bash
# Firebase roles
gcloud projects add-iam-policy-binding chess-engine-metrics-agent \
  --member="serviceAccount:v7p3r-prod-functions@chess-engine-metrics-agent.iam.gserviceaccount.com" \
  --role="roles/datastore.user"

# Storage roles  
gcloud projects add-iam-policy-binding chess-engine-metrics-agent \
  --member="serviceAccount:v7p3r-prod-functions@chess-engine-metrics-agent.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

### 3. Generate and Secure Keys
```bash
# Generate key (do this securely!)
gcloud iam service-accounts keys create production-service-account.json \
  --iam-account=v7p3r-prod-functions@chess-engine-metrics-agent.iam.gserviceaccount.com

# Secure the file
chmod 600 production-service-account.json

# Move to secure location
mv production-service-account.json /path/to/secure/storage/
```

## Key Rotation Schedule

- **Development**: Every 90 days
- **Staging**: Every 60 days  
- **Production**: Every 30 days

## Monitoring and Auditing

- Monitor service account usage in Cloud Console
- Set up alerts for unusual access patterns
- Regular audit of permissions and roles
- Log all service account activities

## Emergency Procedures

### Compromised Service Account
1. Immediately disable the service account
2. Revoke all existing keys
3. Generate new service account with different name
4. Update all applications with new credentials
5. Investigate scope of compromise
6. Update incident response documentation