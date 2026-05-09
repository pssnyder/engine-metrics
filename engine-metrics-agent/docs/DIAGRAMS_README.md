# V7P3R Chess Engine Metrics - Visual Documentation Guide

## 📊 Overview

This directory contains comprehensive Mermaid diagrams documenting the complete V7P3R chess engine metrics data pipeline, from raw data generation through AI-powered analysis and insights delivery.

**Last Updated:** April 24, 2026  
**Project:** chess-engine-metrics-agent  
**Purpose:** Complete data architecture visualization and documentation

---

## 📁 Available Diagrams

### 1. **CEMA_DFD.mmd** - Complete Data Flow Diagram
**Purpose:** End-to-end data flow from generation through consumption  
**Complexity:** High detail  
**Best for:** Understanding complete system integration

**Layers Documented:**
- 🎮 Data Generation Layer (Lichess bot, local engine, Stockfish)
- 📁 Raw Data Sources Layer (PGN files, analysis JSON, docs)
- ⚙️ Processing Layer (analysis scripts, reporting, AI loader)
- 💾 Conformed Data Layer (CSV datasets, reports, cloud storage)
- 🤖 Consumption Layer (Gemini AI agent, Stockfish tools)
- 🔄 Feedback Layer (continuous improvement cycle)

**Key Highlights:**
- Complete file paths and naming conventions
- Actual data volumes (5000 CSV games, 1620 analyzed YTD)
- Processing script names and purposes
- Stockfish analysis metrics (18,539 errors, 6.90 blunders/game)
- AI agent configuration (gemini-2.5-flash, temp 0.15)

**Use this diagram when:**
- Onboarding new team members
- Explaining system architecture to stakeholders
- Planning new feature integration
- Troubleshooting data flow issues

---

### 2. **CEMA_ERD.mmd** - Entity Relationship Diagram
**Purpose:** Data model and entity relationships  
**Complexity:** High detail  
**Best for:** Database design and schema understanding

**Entities Documented:**
- **LICHESS_GAMES** - Central fact table (1620 games YTD)
- **MOVES** - Move-level granular data
- **STOCKFISH_ANALYSIS** - Error analysis per game
- **ERROR_PATTERNS** - Aggregated weakness patterns
- **ENGINE_VERSIONS** - Version tracking and performance
- **VERSION_CHANGELOG** - Change history documentation
- **OPERATIONAL_EVENTS** - Non-engine metric impacts
- **OPENINGS** - Opening repertoire analysis
- **OPPONENTS** - Opponent statistics
- **DOCUMENTATION** - Design docs and build logs
- **GAME_SUMMARIES** - Time-period aggregations
- **AI_AGENT_CONTEXT** - Knowledge base snapshots

**Relationships:**
- Game → Moves (1:N)
- Game → Analysis (1:1)
- Game → Version (N:1)
- Analysis → Error Patterns (1:N)
- Version → Changelog (1:N)
- Version → Games (1:N)

**Use this diagram when:**
- Designing database schemas
- Planning BigQuery table structures
- Understanding data lineage
- Writing complex analytical queries

---

### 3. **DATA_SOURCES_OVERVIEW.mmd** - Data Sources Catalog
**Purpose:** Comprehensive inventory of all data sources  
**Complexity:** Medium detail  
**Best for:** Understanding what data exists and where

**Source Categories:**

#### 🎯 Primary Data Sources
1. **Lichess Platform Data**
   - v7p3r_bot account (Bullet: 1218, Blitz: 1388, Rapid: 1531)
   - PGN exports (cumulative, latest: 2026-04-09)
   - Lichess API (real-time access, webhooks)

2. **Local Engine Development**
   - Engine battle archives (historical testing)
   - Local test games (development validation)

3. **Analysis & Evaluation**
   - Stockfish engine (binary: stockfish_20090216_x64_bmi2.exe)
   - Analysis results JSON (18,539 errors tracked)

#### 📚 Metadata & Documentation Sources
1. **Version & Deployment Tracking**
   - CHANGELOG.md (v18.3 current, deployment history)
   - Development documentation (design docs, build logs)

2. **Operational Metadata**
   - notation_events.json (8 operational events)

3. **Generated Reports & Datasets**
   - CSV datasets (5000 games, game data + summaries + moves)
   - Text reports (gameplay summaries, version comparisons)
   - Markdown insights (enhanced analysis)

#### ☁️ Cloud & External Sources (Optional)
1. **Google Cloud Platform**
   - BigQuery Data Lake (31,659 records, 100% integrity)
   - Firebase Storage (real-time sync)
   - Firestore Database (structured collections)

2. **GCE Compute Engine**
   - E2 Instance v7p3r-production-bot (hourly sync)

**Data Source Metrics:**
- **Update Frequency:** Manual export (PGN), on-demand (analysis), hourly (cloud)
- **Data Volume:** 1620+ games YTD, ~50-200MB analysis JSON, 31,659 BigQuery records
- **Quality:** 100% PGN completeness, validated depth 18, 100% BigQuery integrity

**Use this diagram when:**
- Planning data ingestion pipelines
- Auditing data coverage
- Identifying missing data sources
- Documenting data governance

---

### 4. **SYSTEM_ARCHITECTURE.mmd** - Complete System Architecture
**Purpose:** 7-layer architecture overview  
**Complexity:** Very high detail  
**Best for:** System design and architecture planning

**Architecture Layers:**

**Layer 1: Data Generation** 🎮
- v7p3r_bot (Lichess bot, ~30 games/day)
- Development team (code, docs)

**Layer 2: Raw Data Storage** 💾
- Local filesystem (raw_data/)
- Cloud storage (Firebase, BigQuery)

**Layer 3: Processing & Transformation** ⚙️
- Analysis pipeline (Stockfish analyzer)
- Data extraction (PGN → CSV)
- Report generation (TXT, MD)
- AI context builder (multi-source aggregation)

**Layer 4: Conformed Data** 📊
- CSV datasets (5000 games)
- Generated reports (summaries, insights)
- AI agent context (knowledge base)

**Layer 5: Intelligence & Analytics** 🤖
- Gemini AI system (gemini-2.5-flash, temp 0.15)
- Stockfish function tools
- Authentication (Vertex AI, ADC)

**Layer 6: User Interface** 🖥️
- Terminal CLI (run_agent.py)
- Built-in commands (/help, /status, /reload, etc.)

**Layer 7: Feedback & Monitoring** 🔄
- User interaction tracking
- System monitoring
- Continuous improvement

**External Services:** 🌐
- Lichess.org (game platform, API)
- Stockfish binary (analysis engine)
- Google Cloud SDK (auth, resources)

**Use this diagram when:**
- Designing new system features
- Understanding component interactions
- Planning scalability improvements
- Explaining technical architecture

---

### 5. **PIPELINE_FLOW_SIMPLIFIED.mmd** - Simplified Pipeline Flow
**Purpose:** High-level pipeline overview  
**Complexity:** Low detail (simplified)  
**Best for:** Executive summaries and quick understanding

**Pipeline Stages:**
1. **Input** 📥 - Games, documentation, operations
2. **Raw Data Layer** 💾 - PGN files, docs, logs
3. **Processing Layer** ⚙️ - Analysis, extraction, reporting
4. **Conformed Data Layer** 📊 - Results, datasets, reports
5. **Intelligence Layer** 🤖 - AI agent, tools
6. **Interface Layer** 🖥️ - CLI
7. **Output** 📤 - Insights, metrics, actions

**Key Metrics Overlay:**
- Data Volume: 5000 CSV games, 1620 analyzed YTD, 31,659 BigQuery records
- Quality: 70.1% avg accuracy, 6.90 blunders/game, 4.55 mistakes/game
- Performance: 35.0% win rate, ELO 1467, version v18.3

**Update Frequency:**
- Real-time: Lichess games
- On-demand: Stockfish analysis, reports
- As-needed: Documentation, events

**Use this diagram when:**
- Presenting to non-technical stakeholders
- Creating executive summaries
- Quick orientation for new users
- High-level project planning

---

## 🎨 Viewing the Diagrams

### Method 1: VS Code (Recommended)

1. Install the **Mermaid Preview** extension
2. Open any `.mmd` file
3. Right-click → "Open Preview to the Side"
4. View rendered diagram

### Method 2: Online Mermaid Live Editor

1. Visit https://mermaid.live/
2. Copy the content of any `.mmd` file
3. Paste into the editor
4. View and export as PNG/SVG

### Method 3: GitHub/GitLab

- GitHub and GitLab automatically render `.mmd` files
- Simply view the file in the web interface

### Method 4: Export to Image

Using Mermaid CLI:
```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i CEMA_DFD.mmd -o CEMA_DFD.png
```

---

## 📐 Diagram Conventions

### Colors & Styling

- **Blue** 🔵 - Input/Source data
- **Purple** 🟣 - Raw storage
- **Orange** 🟠 - Processing/transformation
- **Green** 🟢 - Conformed/clean data
- **Pink** 🎀 - AI/Intelligence layer
- **Gray** ⚫ - External services
- **Yellow** 🟡 - Metrics/monitoring

### Arrow Types

- **Solid arrow** → - Primary data flow
- **Dotted arrow** -.-> - Optional/conditional flow
- **Bidirectional** ↔ - Two-way communication

### Node Shapes

- `[Rectangle]` - Data storage
- `([Rounded])` - Process/action
- `{Diamond}` - Decision/gateway
- `[(Cylinder)]` - Database
- `[[Subroutine]]` - Script/function

---

## 🔄 Updating the Diagrams

When making changes to the system:

1. **Identify affected diagrams** - Which diagrams need updates?
2. **Update Mermaid code** - Edit the `.mmd` files
3. **Validate syntax** - Check in Mermaid Live Editor
4. **Update metrics** - Keep data volumes and counts current
5. **Document changes** - Note what changed and why
6. **Commit with message** - Clear commit describing changes

### Common Update Scenarios

**New data source added:**
- Update: DATA_SOURCES_OVERVIEW.mmd
- Update: CEMA_DFD.mmd (if affects flow)
- Update: CEMA_ERD.mmd (if new entity)

**New processing script:**
- Update: CEMA_DFD.mmd (processing layer)
- Update: SYSTEM_ARCHITECTURE.mmd (Layer 3)

**Data volume changes:**
- Update metrics in all diagrams with specific counts
- Check: CEMA_DFD.mmd, DATA_SOURCES_OVERVIEW.mmd, PIPELINE_FLOW_SIMPLIFIED.mmd

**New AI feature:**
- Update: CEMA_DFD.mmd (consumption layer)
- Update: SYSTEM_ARCHITECTURE.mmd (Layer 5)

---

## 📊 Diagram Usage Matrix

| Use Case | Primary Diagram | Secondary Diagram |
|----------|----------------|-------------------|
| **Onboarding new developer** | SYSTEM_ARCHITECTURE.mmd | CEMA_DFD.mmd |
| **Database design** | CEMA_ERD.mmd | DATA_ARCHITECTURE.md |
| **Executive presentation** | PIPELINE_FLOW_SIMPLIFIED.mmd | DATA_SOURCES_OVERVIEW.mmd |
| **Troubleshooting data issues** | CEMA_DFD.mmd | DATA_SOURCES_OVERVIEW.mmd |
| **Planning new features** | SYSTEM_ARCHITECTURE.mmd | CEMA_DFD.mmd |
| **Data audit** | DATA_SOURCES_OVERVIEW.mmd | CEMA_ERD.mmd |
| **Performance optimization** | CEMA_DFD.mmd | SYSTEM_ARCHITECTURE.mmd |
| **Documentation review** | All diagrams | DATA_ARCHITECTURE.md |

---

## 🎯 Quick Reference

### Current System Stats (as of April 24, 2026)

- **Total Games (CSV):** 5,000
- **Games Analyzed (YTD 2026):** 1,620
- **Total Errors Tracked:** 18,539
- **Blunders per Game:** 6.90
- **Mistakes per Game:** 4.55
- **Average Accuracy:** 70.1%
- **Current ELO:** 1,467
- **Win Rate:** 35.0%
- **Current Version:** v18.3 (DEPLOYED)
- **BigQuery Records:** 31,659 (100% integrity)

### Key File Locations

```
engine-metrics/
├── raw_data/
│   ├── game_records/Lichess V7P3R Bot/
│   │   └── lichess_v7p3r_bot_2026-04-09.pgn (latest cumulative)
│   ├── analysis_results/
│   │   └── v18_3_ytd_analysis_20260422_111912.json (latest analysis)
│   ├── v7p3r_docs/
│   │   └── CHANGELOG.md (version history)
│   └── notation_events.json (8 operational events)
├── reporting_datasets/
│   ├── v7p3r_game_data_latest.csv (5000 games)
│   ├── v7p3r_game_summary_enhanced_latest.csv
│   └── v7p3r_moves_latest.csv
├── scripts/
│   └── analyze_ytd_games.py (Stockfish analysis)
└── engine-metrics-agent/src/ai/
    ├── data_loader.py (context builder)
    ├── agent.py (Gemini AI)
    └── run_agent.py (CLI interface)
```

---

## 🚀 Next Steps

After reviewing these diagrams:

1. ✅ **Verify understanding** - Can you trace data from source to insight?
2. ✅ **Identify gaps** - Any missing data sources or flows?
3. ✅ **Plan improvements** - What enhancements would add value?
4. ✅ **Update documentation** - Keep diagrams current as system evolves

---

## 📞 Support & Feedback

These diagrams are living documentation. If you:
- Find inaccuracies
- Identify missing components
- Suggest improvements
- Need clarification

Update the diagrams directly and commit changes, or create issues for discussion.

---

**Maintained by:** V7P3R Development Team  
**Last Review:** April 24, 2026  
**Next Review:** When system architecture changes
