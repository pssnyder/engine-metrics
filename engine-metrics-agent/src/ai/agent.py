"""
V7P3R Engine Metrics - Gemini Analysis Agent
Core agent powered by Google Gemini with:
  - Low temperature (0.15) for precise, analytical responses
  - Function calling for Stockfish tools
  - Rich context from game data, changelogs, and design docs
  - Exclusive focus on v7p3r_bot (lichess bot, not human player)

Authentication:
  Uses GEMINI_API_KEY env var (from .env file or environment).
  Alternatively, uses Vertex AI via GOOGLE_APPLICATION_CREDENTIALS
  and GOOGLE_CLOUD_PROJECT=chess-engine-metrics-agent.
"""

import os
import json
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env from the ai/ directory
_HERE = Path(__file__).resolve().parent
load_dotenv(_HERE / ".env", override=False)

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from data_loader import build_agent_context, context_to_prompt_text
from stockfish_tools import TOOL_REGISTRY


# ─── Agent configuration ────────────────────────────────────────────────────

MODEL_NAME  = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
TEMPERATURE = float(os.environ.get("AGENT_TEMPERATURE", "0.15"))
MAX_TOKENS  = int(os.environ.get("AGENT_MAX_TOKENS", "8192"))

SYSTEM_INSTRUCTION = """\
You are the V7P3R Engine Metrics Analyst — a specialized, precise chess analysis \
agent exclusively focused on the v7p3r_bot account on Lichess (username: v7p3r_bot). \
This is an automated chess engine, NOT the human player who also uses the v7p3r handle. \
Do not confuse v7p3r_bot with the C0BR4 bot, SlowMate bot, or any human accounts.

Your responsibilities:
1. Analyze v7p3r_bot game performance across all engine versions (v7 through v14+)
2. Cross-reference development changes in the CHANGELOG with observed performance shifts
3. Identify openings, time controls, and tactical patterns where the engine excels or struggles
4. Use Stockfish tools to evaluate specific positions and detect blunders/mistakes when asked
5. Connect ELO trajectory to specific code changes or tuning decisions
6. Provide precise, data-driven answers — avoid speculation without supporting data

Analysis style:
- Be concise and analytical. Lead with the key finding, then support with data.
- Cite specific version numbers, date ranges, and game counts when discussing trends.
- When using Stockfish, explain the evaluation in chess terms (not just centipawns).
- Temperature is low (0.15) intentionally — prioritize accuracy over creativity.
- If you lack data to answer confidently, say so and suggest what data would help.

Tools available:
- stockfish_status: verify Stockfish engine is available
- analyze_position(fen, depth, multipv): evaluate a FEN position
- find_best_moves(fen, top_n, depth): get ranked move options
- analyze_game_pgn(pgn_text, depth): full move-by-move blunder/mistake analysis
- get_game_key_positions(pgn_text, depth): opening/midgame/endgame position snapshots
"""

# ─── Gemini function declarations ────────────────────────────────────────────

_TOOL_DECLARATIONS = [
    types.FunctionDeclaration(
        name="stockfish_status",
        description="Check whether the Stockfish engine is available and get its version. Call this before any analysis if unsure.",
        parameters=types.Schema(type=types.Type.OBJECT, properties={}),
    ),
    types.FunctionDeclaration(
        name="analyze_position",
        description=(
            "Analyze a chess position given as a FEN string using Stockfish. "
            "Returns evaluation in centipawns, best move, and top lines."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "fen": types.Schema(
                    type=types.Type.STRING,
                    description="FEN string of the chess position to analyze.",
                ),
                "depth": types.Schema(
                    type=types.Type.INTEGER,
                    description="Search depth (default 20, max 30). Higher = more accurate but slower.",
                ),
                "multipv": types.Schema(
                    type=types.Type.INTEGER,
                    description="Number of top candidate lines to return (default 3, max 5).",
                ),
            },
            required=["fen"],
        ),
    ),
    types.FunctionDeclaration(
        name="find_best_moves",
        description=(
            "Return the top N best moves for a chess position in FEN format. "
            "Useful for comparing what v7p3r_bot played vs what Stockfish recommends."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "fen": types.Schema(type=types.Type.STRING, description="FEN position."),
                "top_n": types.Schema(type=types.Type.INTEGER, description="Number of top moves (default 5, max 10)."),
                "depth": types.Schema(type=types.Type.INTEGER, description="Search depth (default 15)."),
            },
            required=["fen"],
        ),
    ),
    types.FunctionDeclaration(
        name="analyze_game_pgn",
        description=(
            "Perform full move-by-move Stockfish analysis of a single chess game in PGN format. "
            "Identifies blunders (>150cp loss), mistakes (>80cp), and inaccuracies. "
            "Best used for deep diagnosis of a specific game. May take 30-120 seconds."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "pgn_text": types.Schema(type=types.Type.STRING, description="Raw PGN text of a single game."),
                "depth": types.Schema(type=types.Type.INTEGER, description="Stockfish depth (default 18, lower=faster)."),
                "blunder_threshold_cp": types.Schema(type=types.Type.INTEGER, description="CP loss to call a blunder (default 150)."),
                "mistake_threshold_cp": types.Schema(type=types.Type.INTEGER, description="CP loss to call a mistake (default 80)."),
                "max_moves": types.Schema(type=types.Type.INTEGER, description="Max plies to analyze (default 80)."),
            },
            required=["pgn_text"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_game_key_positions",
        description=(
            "Extract and evaluate 3 key positions from a game: opening end (~move 10), "
            "middlegame, and final position. Faster than full analysis. Good for quick game snapshots."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "pgn_text": types.Schema(type=types.Type.STRING, description="Raw PGN text of a single game."),
                "depth": types.Schema(type=types.Type.INTEGER, description="Stockfish depth (default 15)."),
            },
            required=["pgn_text"],
        ),
    ),
]


# ─── V7P3RAgent class ────────────────────────────────────────────────────────

class V7P3RAgent:
    """
    Gemini-powered chess analysis agent for v7p3r_bot.
    Maintains conversation history and can call Stockfish tools.
    """

    def __init__(self, verbose: bool = False):
        if not GENAI_AVAILABLE:
            raise RuntimeError(
                "google-genai package not installed. Run: python -m pip install google-genai"
            )

        self.verbose = verbose
        self._init_client()
        self._load_context()
        self.history: list = []
        self._context_injected = False

    def _init_client(self):
        """Initialize the Gemini client."""
        api_key = os.environ.get("GEMINI_API_KEY")
        project = os.environ.get("GOOGLE_CLOUD_PROJECT", "chess-engine-metrics-agent")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

        if api_key:
            # Direct Gemini API (AI Studio key)
            self.client = genai.Client(api_key=api_key)
            self._auth_mode = "gemini_api_key"
            print(f"[Agent] Using Gemini API key authentication (model: {MODEL_NAME})")
        else:
            # Vertex AI (uses GOOGLE_APPLICATION_CREDENTIALS / ADC)
            self.client = genai.Client(
                vertexai=True,
                project=project,
                location=location,
            )
            self._auth_mode = "vertex_ai"
            print(f"[Agent] Using Vertex AI authentication (project: {project}, model: {MODEL_NAME})")

    def _load_context(self):
        """Load game data and build context for the agent."""
        if self.verbose:
            print("[Agent] Loading v7p3r_bot knowledge base...")
        self._ctx = build_agent_context(include_pgn_games=True, include_docs=True, verbose=self.verbose)
        self._context_text = context_to_prompt_text(self._ctx)
        if self.verbose:
            stats = self._ctx.get("stats", {})
            print(f"[Agent] Context ready — {stats.get('total_games', 0)} games loaded")

    def reload_context(self):
        """Reload the knowledge base (call after ingesting new data)."""
        self._load_context()
        self._context_injected = False
        print("[Agent] Knowledge base reloaded.")

    def _build_config(self) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION + "\n\n" + self._context_text,
            temperature=TEMPERATURE,
            max_output_tokens=MAX_TOKENS,
            tools=[types.Tool(function_declarations=_TOOL_DECLARATIONS)],
        )

    def chat(self, user_message: str) -> str:
        """
        Send a message and get a response. Handles multi-turn tool calls internally.

        Args:
            user_message: The user's question or instruction.

        Returns:
            The agent's final text response.
        """
        self.history.append(
            types.Content(role="user", parts=[types.Part(text=user_message)])
        )

        config = self._build_config()
        final_text = self._run_turn(config)
        return final_text

    def _run_turn(self, config: types.GenerateContentConfig) -> str:
        """
        Execute one turn, potentially invoking tools in a loop until
        the model returns a final text response.
        """
        max_tool_rounds = 5  # prevent runaway tool loops

        for _round in range(max_tool_rounds):
            response = self.client.models.generate_content(
                model=MODEL_NAME,
                contents=self.history,
                config=config,
            )

            candidate = response.candidates[0]
            content = candidate.content

            # Collect any function calls from this response
            function_calls = [
                part.function_call
                for part in content.parts
                if part.function_call is not None
            ]

            if not function_calls:
                # No tool calls — extract final text and record in history
                final_text = "".join(
                    part.text for part in content.parts if hasattr(part, "text") and part.text
                )
                self.history.append(content)
                return final_text.strip()

            # Append model's function-call message to history
            self.history.append(content)

            # Execute each tool call and collect results
            tool_results = []
            for fc in function_calls:
                result = self._execute_tool(fc.name, dict(fc.args) if fc.args else {})
                if self.verbose:
                    print(f"[Tool] {fc.name}({list(fc.args.keys()) if fc.args else ''})")
                tool_results.append(
                    types.Part.from_function_response(
                        name=fc.name,
                        response={"result": result},
                    )
                )

            # Append tool results to history
            self.history.append(
                types.Content(role="user", parts=tool_results)
            )

        return "[Agent error: exceeded max tool call rounds]"

    def _execute_tool(self, name: str, args: dict) -> dict:
        """Dispatch a function call to the appropriate Stockfish tool."""
        if name not in TOOL_REGISTRY:
            return {"error": f"Unknown tool: {name}"}
        try:
            result = TOOL_REGISTRY[name](**args)
            # Truncate large move-by-move lists to avoid huge context
            if isinstance(result, dict) and "move_by_move" in result:
                result = dict(result)
                result["move_by_move"] = result["move_by_move"][:40]
                result["note"] = "move_by_move truncated to first 40 plies for context"
            return result
        except Exception as e:
            return {"error": str(e), "tool": name, "args": args}

    def clear_history(self):
        """Clear conversation history (start fresh conversation)."""
        self.history = []

    def get_stats_summary(self) -> str:
        """Return a quick text summary of the loaded game stats."""
        stats = self._ctx.get("stats", {})
        deployed = self._ctx.get("latest_version", "unknown")
        csv_ver  = self._ctx.get("csv_version", "unknown")
        ver_str  = deployed
        if csv_ver != deployed:
            ver_str = f"{deployed} (deployed) / {csv_ver} (CSV data)"
        return (
            f"v7p3r_bot: {stats.get('total_games', 0)} games | "
            f"Win%: {stats.get('win_rate_pct', 0)} | "
            f"Avg ELO: {stats.get('avg_elo', 0)} | "
            f"Latest ELO: {stats.get('latest_elo', 0)} | "
            f"Version: {ver_str}"
        )
