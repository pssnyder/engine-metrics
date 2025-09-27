# 🚀 Getting Started with Engine Metrics Agent

## Quick Start Guide

### 1. Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js 18+** - [Download here](https://nodejs.org/)
- **Python 3.9+** - [Download here](https://python.org/)
- **Git** - [Download here](https://git-scm.com/)
- **Firebase CLI** - Install with: `npm install -g firebase-tools`

### 2. Initial Setup

```bash
# 1. Clone and navigate to the project
cd "S:\Maker Stuff\Programming\Chess Engines\Chess Engine Playground\engine-metrics-agent"

# 2. Install all dependencies
npm run install:all

# 3. Set up Firebase (follow prompts)
firebase login
npm run setup

# 4. Start development environment
npm run dev
```

### 3. Access Your Application

- **Web App**: http://localhost:3000
- **API Functions**: http://localhost:5001
- **AI Service**: http://localhost:5001

## 📁 Project Structure Overview

```
engine-metrics-agent/
├── src/
│   ├── frontend/          # React web application
│   ├── backend/           # Firebase Cloud Functions
│   ├── ai/               # Python AI processing
│   └── data/             # Data processing utilities
├── config/               # Firebase configuration
├── scripts/              # Setup and deployment scripts
└── docs/                 # Documentation
```

## 🎯 Core Features

### 1. Data Upload
- **Supported Files**: PGN (games), JSON (analysis), MD (reports)
- **Storage**: Secure Cloud Storage with automatic processing
- **Processing**: Real-time extraction of performance metrics

### 2. AI Analysis
- **Natural Language Queries**: Ask questions in plain English
- **Performance Comparison**: Compare engines across metrics
- **Trend Analysis**: Track improvement over time
- **Problem Diagnosis**: Identify performance issues

### 3. Interactive Dashboard
- **Real-time Charts**: Performance trends and comparisons
- **Engine Statistics**: Win rates, ELO tracking, game counts
- **Data Visualization**: Radar charts, bar charts, line graphs

## 🤖 Example AI Queries

Once you've uploaded data, try these questions:

```
"How has V7P3R improved since v10.8?"
"Which engine performs best in blitz?"
"Compare SlowMate vs C0BR4 performance"
"What caused the v10.7 performance drop?"
"What factors influence engine performance?"
```

## 📊 Data Sources

Upload files from these directories for analysis:

1. **Game Records**: `S:\...\engine-tester\analysis_results`
2. **Metrics Data**: `S:\...\engine-metrics\datasets`
3. **Battle Results**: `S:\...\automated_battle_framework\battle_results`
4. **Documentation**: `S:\...\v7p3r-chess-engine\docs`

## 🔧 Development Commands

```bash
# Development
npm run dev              # Start all services
npm run frontend         # Frontend only
npm run backend          # Backend only
npm run ai              # AI service only

# Building & Deployment
npm run build           # Build for production
npm run deploy          # Deploy everything
npm run deploy:frontend # Deploy frontend only
npm run deploy:backend  # Deploy backend only

# Utilities
npm run logs           # View function logs
npm run emulator       # Start Firebase emulators
```

## 🚀 Deployment

### Automatic Deployment
```bash
npm run deploy
```

### Manual Steps
1. Build frontend: `npm run build`
2. Deploy to Firebase: `firebase deploy`
3. Monitor at: https://console.firebase.google.com

## 🛠️ Troubleshooting

### Common Issues

**Firebase Auth Error**
```bash
firebase login --reauth
```

**Dependencies Issues**
```bash
npm run install:all
```

**Python Environment**
```bash
cd src/ai
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

**Port Conflicts**
- Frontend: Change port in src/frontend/package.json
- Backend: Use different port with `--port` flag
- AI: Set FLASK_RUN_PORT environment variable

## 📈 Performance Optimization

### For Large Datasets
- Upload files in batches of 10-20
- Use compressed archives when possible
- Monitor Firebase usage quotas

### For Better AI Responses
- Upload diverse game data (different time controls)
- Include recent games for trend analysis
- Add structured metadata in JSON format

## 🔐 Security Notes

- All data is stored in your private Firebase project
- Authentication required for access
- Firestore security rules prevent unauthorized access
- No data shared outside your project

## 💡 Tips for Best Results

1. **Data Quality**: Ensure PGN files have proper headers
2. **Consistency**: Use consistent engine names across files
3. **Metadata**: Include time controls and dates in game records
4. **Regular Updates**: Upload new data regularly for trend analysis

## 🆘 Support

If you encounter issues:

1. Check the browser console for error messages
2. View Firebase function logs: `npm run logs`
3. Verify your data format matches examples
4. Ensure Firebase quotas aren't exceeded

## 🎉 What's Next?

After setup, you can:

1. **Upload Your Data**: Start with recent PGN files
2. **Explore Dashboard**: View performance charts
3. **Ask AI Questions**: Get insights about your engines
4. **Compare Engines**: Analyze strengths and weaknesses
5. **Track Progress**: Monitor improvements over time

---

**Ready to revolutionize your chess engine development with AI-powered analysis!** 🏆