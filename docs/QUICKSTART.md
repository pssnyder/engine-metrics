# V7P3R Engine Metrics Agent — Quick Start Guide

Conversational chess analytics for **v7p3r_bot** (Lichess bot), powered by Google Gemini 2.5 Flash + Stockfish. Ask questions in plain English about game performance, engine version history, ELO trends, and opening patterns — all grounded in real game data and changelogs.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | `python --version` to check |
| Google Cloud SDK (`gcloud`) | [install guide](https://cloud.google.com/sdk/docs/install) |
| Stockfish binary | Installed at the path in your `.env` |
| GCP project access | `chess-engine-metrics-agent` — requires auth (see Step 2) |

---

## Step 1 — Install Python dependencies

From the workspace root:

```powershell
pip install google-genai google-cloud-aiplatform python-chess python-dotenv rich
```

Or install from the full requirements file:

```powershell
pip install -r engine-metrics-agent\requirements.txt
```

---

## Step 2 — Authenticate with Google Cloud

The agent uses **Vertex AI Application Default Credentials** — no API key file needed.

```powershell
gcloud auth application-default login --project chess-engine-metrics-agent
```

A browser window will open. Sign in with the Google account that has access to the `chess-engine-metrics-agent` GCP project. Once complete you will see:

```
Credentials saved to file: [...\application_default_credentials.json]
Quota project "chess-engine-metrics-agent" was added to ADC
```

This only needs to be done once (credentials persist until they expire or you revoke them).

---

## Step 3 — Configure the `.env` file

The `.env` file lives at `engine-metrics-agent\src\ai\.env`. If it doesn't exist yet, copy the example:

```powershell
copy engine-metrics-agent\src\ai\.env.example engine-metrics-agent\src\ai\.env
```

The default configuration uses Vertex AI (ADC) — no changes required after Step 2. The key settings:

```ini
# Leave empty to use Vertex AI / ADC (recommended)
GEMINI_API_KEY=

GOOGLE_CLOUD_PROJECT=chess-engine-metrics-agent
GEMINI_MODEL=gemini-2.5-flash
AGENT_TEMPERATURE=0.15

# Update this path to match your Stockfish installation
STOCKFISH_PATH=C:\Users\Pat\Documents\Software\stockfish_12_win_x64_bmi2\stockfish_20090216_x64_bmi2.exe
```

> **Alternative auth**: If you prefer a direct API key instead of ADC, get one from [Google AI Studio](https://aistudio.google.com/app/apikey) and set `GEMINI_API_KEY=your_key_here`.

---

## Step 4 — Launch the agent

From the **workspace root** (`engine-metrics\`):

```powershell
python run_agent.py
```

On startup you will see the knowledge base load and a status line:

```
[Agent] Using Vertex AI authentication (project: chess-engine-metrics-agent, model: gemini-2.5-flash)
Ready.  v7p3r_bot: 5000 games | Win%: 35.0 | Avg ELO: 1358 | Latest ELO: 1467 | Version: v18.3 (deployed) / v17.5 (CSV data)
```

Then ask away:

```
v7p3r> What is v7p3r_bot's win rate as white vs black?
v7p3r> How did the engine perform during the v17.4 deployment?
v7p3r> Why did ELO drop in December 2025?
v7p3r> Which openings does the bot struggle with most?
```

---

## Usage modes

### Interactive REPL (default)
```powershell
python run_agent.py
```

### Single query — no REPL
```powershell
python run_agent.py --query "What is the current deployed engine version?"
```

### Skip PGN loading (faster startup, no move-level data)
```powershell
python run_agent.py --no-pgn
```

### Skip design docs (minimal context, fastest startup)
```powershell
python run_agent.py --no-pgn --no-docs
```

### Use a different Gemini model
```powershell
python run_agent.py --model gemini-2.5-pro
```

---

## Built-in commands

Type these at the `v7p3r>` prompt:

| Command | What it does |
|---|---|
| `/help` | Show all commands |
| `/status` | Current knowledge base stats (games, ELO, version) |
| `/stockfish` | Check Stockfish engine availability and version |
| `/reload` | Reload all data — use after adding new PGNs or docs |
| `/pgn <path>` | Load and analyze a specific PGN file |
| `/clear` | Clear conversation history (start fresh) |
| `/context` | Show the first 3000 chars of injected context |
| `/quit` | Exit |

---

## Feeding new data to the agent

The agent reads from three locations under `raw_data\`. Drop files in and type `/reload`:

| What to add | Where to put it | Format |
|---|---|---|
| New game PGN exports from Lichess | `raw_data\game_records\Lichess V7P3R Bot\` | `.pgn` |
| Engine design docs, build reports | `raw_data\v7p3r_docs\` | `.md` |
| Deployment changelog (version history) | `raw_data\v7p3r_docs\CHANGELOG.md` | Markdown (existing format) |
| Operational events (config changes, bugs, tuning) | `raw_data\notation_events.json` | JSON (existing format) |
| Any other context docs or notes | `raw_data\` (top level) | `.md`, `.txt`, or `.json` |

After adding files:
```
v7p3r> /reload
```

---

## Updating the operational events log

When something significant happens that is **not a chess engine code change** (lichess-bot config update, matchmaking on/off, infrastructure change, performance investigation finding), add an entry to `raw_data\notation_events.json`:

```json
{
  "date": "2026-04-15",
  "date_approximate": false,
  "type": "config_change",
  "title": "Brief description of what changed",
  "change_scope": "lichess_bot_config",
  "engine_version_affected": "v18.3",
  "description": "Full details of what changed and why.",
  "expected_metric_impact": "How this might affect win rate, ELO, or game counts."
}
```

Valid `type` values: `config_change` | `tuning` | `infrastructure` | `operational` | `environment`

---

## Stockfish MCP server (for Claude Desktop / VS Code)

The Stockfish MCP server lets other AI tools (Claude Desktop, VS Code Copilot agent mode) use Stockfish analysis directly.

**Claude Desktop** — add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "v7p3r-stockfish": {
      "command": "python",
      "args": [
        "e:/Programming Stuff/Chess Engines/Chess Engine Playground/engine-metrics/engine-metrics-agent/src/mcp/stockfish_server.py"
      ],
      "env": {
        "STOCKFISH_PATH": "C:/Users/Pat/Documents/Software/stockfish_12_win_x64_bmi2/stockfish_20090216_x64_bmi2.exe"
      }
    }
  }
}
```

**Test the MCP server standalone:**
```powershell
python engine-metrics-agent\src\mcp\stockfish_server.py
```

---

## Project layout (relevant files)

```
engine-metrics\
├── run_agent.py                          ← ENTRY POINT — run this
├── raw_data\
│   ├── notation_events.json              ← Operational events log
│   ├── game_records\Lichess V7P3R Bot\   ← PGN game exports
│   ├── v7p3r_docs\
│   │   └── CHANGELOG.md                 ← Engine deployment history
│   └── analysis_results\                ← JSON analysis reports
├── reporting_datasets\
│   └── v7p3r_game_data_latest.csv       ← Main game data CSV
└── engine-metrics-agent\src\ai\
    ├── .env                             ← Your config (not in git)
    ├── .env.example                     ← Config template
    ├── agent.py                         ← Gemini agent core
    ├── cli.py                           ← Terminal REPL
    ├── data_loader.py                   ← Data ingestion layer
    └── stockfish_tools.py               ← Stockfish analysis tools
```

---

## Troubleshooting

**`404 NOT_FOUND` for Gemini model**
The model name is invalid for your project region. Try `gemini-2.5-flash` or re-run `gcloud auth application-default login`.

**`Reauthentication is needed`**
ADC credentials have expired. Re-run:
```powershell
gcloud auth application-default login --project chess-engine-metrics-agent
```

**`Stockfish not found`**
Update `STOCKFISH_PATH` in `.env` to the path of your Stockfish executable.

**Agent reports wrong current version**
Update `raw_data\v7p3r_docs\CHANGELOG.md` with the new deployment entry (Status: DEPLOYED) and type `/reload`.

**Context is stale after adding new data**
Type `/reload` in the REPL or restart with `python run_agent.py`.
