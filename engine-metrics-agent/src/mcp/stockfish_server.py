"""
V7P3R Stockfish MCP Server
Model Context Protocol server that exposes Stockfish chess analysis tools
over stdio (JSON-RPC 2.0), compatible with Claude Desktop, VS Code Copilot
agent mode, and any other MCP client.

Usage (add to Claude Desktop config or VS Code MCP config):
    {
        "mcpServers": {
            "stockfish": {
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

Or run standalone to test:
    python stockfish_server.py
"""

import sys
import json
import os
import traceback
from pathlib import Path

# Ensure src/ai is on path for stockfish_tools imports
_HERE = Path(__file__).resolve().parent
_AI_DIR = _HERE.parent / "ai"
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from stockfish_tools import (
    stockfish_status,
    analyze_position,
    find_best_moves,
    analyze_game_pgn,
    get_game_key_positions,
)

# ─── MCP Protocol constants ───────────────────────────────────────────────────

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {
    "name": "v7p3r-stockfish-mcp",
    "version": "1.0.0",
}

# ─── Tool definitions ─────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "stockfish_status",
        "description": "Check whether the Stockfish chess engine is installed and available. Returns version info.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "analyze_position",
        "description": (
            "Analyze a chess position using Stockfish. Returns evaluation in centipawns, "
            "best move, and top candidate lines."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "fen": {
                    "type": "string",
                    "description": "FEN string of the chess position.",
                },
                "depth": {
                    "type": "integer",
                    "description": "Search depth (default 20, max 30).",
                    "default": 20,
                },
                "multipv": {
                    "type": "integer",
                    "description": "Number of top candidate lines (default 3, max 5).",
                    "default": 3,
                },
            },
            "required": ["fen"],
        },
    },
    {
        "name": "find_best_moves",
        "description": "Find the top N best moves in a chess position (FEN). Returns ranked moves with evaluations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fen": {"type": "string", "description": "FEN position to analyze."},
                "top_n": {"type": "integer", "description": "Number of moves (default 5, max 10).", "default": 5},
                "depth": {"type": "integer", "description": "Stockfish depth (default 15).", "default": 15},
            },
            "required": ["fen"],
        },
    },
    {
        "name": "analyze_game_pgn",
        "description": (
            "Full move-by-move Stockfish analysis of a single chess game in PGN format. "
            "Identifies blunders (>150cp), mistakes (>80cp), and inaccuracies. "
            "Warning: may take 30-120 seconds depending on game length and depth."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "pgn_text": {"type": "string", "description": "Raw PGN text of a single game."},
                "depth": {"type": "integer", "description": "Stockfish depth per move (default 18).", "default": 18},
                "blunder_threshold_cp": {"type": "integer", "description": "CP loss = blunder (default 150).", "default": 150},
                "mistake_threshold_cp": {"type": "integer", "description": "CP loss = mistake (default 80).", "default": 80},
                "max_moves": {"type": "integer", "description": "Max plies to analyze (default 80).", "default": 80},
            },
            "required": ["pgn_text"],
        },
    },
    {
        "name": "get_game_key_positions",
        "description": (
            "Extract and evaluate 3 key positions from a game: end of opening (~move 10), "
            "middlegame, and final position. Faster than full analysis."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "pgn_text": {"type": "string", "description": "Raw PGN text of a single game."},
                "depth": {"type": "integer", "description": "Stockfish depth (default 15).", "default": 15},
            },
            "required": ["pgn_text"],
        },
    },
]

_TOOL_MAP = {
    "stockfish_status": stockfish_status,
    "analyze_position": analyze_position,
    "find_best_moves": find_best_moves,
    "analyze_game_pgn": analyze_game_pgn,
    "get_game_key_positions": get_game_key_positions,
}


# ─── JSON-RPC helpers ─────────────────────────────────────────────────────────

def _send(obj: dict):
    """Write a JSON-RPC message to stdout."""
    line = json.dumps(obj, ensure_ascii=False)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def _ok(req_id, result):
    _send({"jsonrpc": "2.0", "id": req_id, "result": result})


def _error(req_id, code: int, message: str):
    _send({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})


# ─── Request handlers ─────────────────────────────────────────────────────────

def handle_initialize(req_id, params):
    _ok(req_id, {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": SERVER_INFO,
    })


def handle_tools_list(req_id, params):
    _ok(req_id, {"tools": TOOLS})


def handle_tools_call(req_id, params):
    name = params.get("name")
    args = params.get("arguments", {})

    if name not in _TOOL_MAP:
        _error(req_id, -32601, f"Unknown tool: {name}")
        return

    try:
        result = _TOOL_MAP[name](**args)
        # Truncate large move-by-move lists
        if isinstance(result, dict) and "move_by_move" in result:
            result = dict(result)
            result["move_by_move"] = result["move_by_move"][:40]
            result["_note"] = "move_by_move truncated to 40 plies"

        result_text = json.dumps(result, indent=2, default=str)
        _ok(req_id, {
            "content": [{"type": "text", "text": result_text}],
            "isError": False,
        })
    except Exception as e:
        _ok(req_id, {
            "content": [{"type": "text", "text": f"Error: {e}\n{traceback.format_exc()}"}],
            "isError": True,
        })


def handle_ping(req_id, params):
    _ok(req_id, {})


_HANDLERS = {
    "initialize": handle_initialize,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
    "ping": handle_ping,
}


# ─── Main server loop ─────────────────────────────────────────────────────────

def main():
    """Run the MCP server, reading JSON-RPC from stdin, writing to stdout."""
    # Redirect stderr to avoid polluting the JSON-RPC stream
    # (stockfish and other libraries may print to stderr — that's fine)

    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        try:
            req = json.loads(raw_line)
        except json.JSONDecodeError as e:
            _error(None, -32700, f"Parse error: {e}")
            continue

        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params", {}) or {}

        # Notifications (no id) — handle silently
        if req_id is None:
            if method == "notifications/initialized":
                pass  # nothing to do
            continue

        handler = _HANDLERS.get(method)
        if handler is None:
            _error(req_id, -32601, f"Method not found: {method}")
            continue

        try:
            handler(req_id, params)
        except Exception as e:
            _error(req_id, -32603, f"Internal error: {e}")


if __name__ == "__main__":
    main()
