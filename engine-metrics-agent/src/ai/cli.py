"""
V7P3R Engine Metrics - Terminal CLI Interface
Interactive REPL for querying the v7p3r_bot analysis agent.
Inspired by Claude Code's terminal UX — run in your terminal and ask questions.

Usage:
    python cli.py
    python cli.py --no-pgn          (skip loading PGN games, faster startup)
    python cli.py --no-docs         (skip loading design docs)
    python cli.py --model gemini-2.0-flash
    python cli.py --query "What is v7p3r_bot's win rate as white?"

Built-in commands:
    /help       — show available commands
    /status     — show knowledge base stats
    /reload     — reload game data (after adding new data)
    /stockfish  — check Stockfish availability
    /clear      — clear conversation history
    /pgn <path> — analyze a specific PGN file
    /quit       — exit
"""

import sys
import os
import argparse
import json
from pathlib import Path

# ─── Ensure src/ai/ is on sys.path when called from anywhere ─────────────────
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.prompt import Prompt
    from rich.text import Text
    from rich.rule import Rule
    from rich.spinner import Spinner
    from rich.live import Live
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI class
# ═══════════════════════════════════════════════════════════════════════════════

class V7P3RCLI:
    BANNER = """
╔══════════════════════════════════════════════════════════════╗
║      V7P3R Engine Metrics Agent  ·  Terminal Interface       ║
║      Powered by Google Gemini · Stockfish analysis           ║
║      Focused exclusively on v7p3r_bot (Lichess bot)          ║
╚══════════════════════════════════════════════════════════════╝
Type your question and press Enter.  /help for commands.  /quit to exit.
"""

    def __init__(self, args):
        self.args = args
        self.console = Console() if RICH_AVAILABLE else None
        self.agent = None

    # ── Startup ──────────────────────────────────────────────────────────────

    def start(self):
        """Initialize agent and enter REPL."""
        self._print_banner()

        # Override model if provided
        if self.args.model:
            os.environ["GEMINI_MODEL"] = self.args.model

        # Handle single-shot query mode
        if self.args.query:
            self._init_agent()
            self._run_query(self.args.query)
            return

        self._init_agent()
        self._repl()

    def _init_agent(self):
        """Load the agent (shows spinner if rich available)."""
        self._print_status("Loading v7p3r_bot knowledge base and initializing Gemini agent...")

        from agent import V7P3RAgent
        self.agent = V7P3RAgent(verbose=self.args.verbose)

        self._print_status(f"Ready.  {self.agent.get_stats_summary()}")

    # ── REPL ─────────────────────────────────────────────────────────────────

    def _repl(self):
        """Main read-evaluate-print loop."""
        while True:
            try:
                user_input = self._read_input()
            except (KeyboardInterrupt, EOFError):
                self._print_info("\nGoodbye.")
                break

            if not user_input.strip():
                continue

            if user_input.strip().startswith("/"):
                handled = self._handle_command(user_input.strip())
                if handled == "quit":
                    break
                continue

            self._run_query(user_input)

    def _read_input(self) -> str:
        """Read input from the user with a styled prompt."""
        if RICH_AVAILABLE:
            return Prompt.ask("\n[bold cyan]v7p3r>[/bold cyan]", console=self.console)
        else:
            return input("\nv7p3r> ")

    # ── Query execution ───────────────────────────────────────────────────────

    def _run_query(self, query: str):
        """Send a query to the agent and print the response."""
        if not self.agent:
            self._print_error("Agent not initialized.")
            return

        self._print_thinking()
        try:
            response = self.agent.chat(query)
            self._print_response(response)
        except Exception as e:
            self._print_error(f"Agent error: {e}")
            if self.args.verbose:
                import traceback
                traceback.print_exc()

    # ── Built-in commands ─────────────────────────────────────────────────────

    def _handle_command(self, cmd: str) -> str:
        """Handle /commands. Returns 'quit' to exit REPL."""
        parts = cmd.split(None, 1)
        command = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if command in ("/quit", "/exit", "/q"):
            self._print_info("Goodbye.")
            return "quit"

        elif command == "/help":
            self._print_help()

        elif command == "/status":
            if self.agent:
                self._print_info(self.agent.get_stats_summary())
            else:
                self._print_info("Agent not initialized.")

        elif command == "/reload":
            if self.agent:
                self.agent.reload_context()
                self._print_info(f"Reloaded.  {self.agent.get_stats_summary()}")

        elif command == "/clear":
            if self.agent:
                self.agent.clear_history()
                self._print_info("Conversation history cleared.")

        elif command == "/stockfish":
            from stockfish_tools import stockfish_status
            result = stockfish_status()
            self._print_info(json.dumps(result, indent=2))

        elif command == "/pgn":
            if not arg:
                self._print_error("Usage: /pgn <path-to-pgn-file>")
            else:
                self._load_and_analyze_pgn(arg.strip())

        elif command == "/context":
            if self.agent:
                self._print_info(self.agent._context_text[:3000] + "\n[...truncated]")

        else:
            self._print_error(f"Unknown command: {command}. Type /help for help.")

        return ""

    def _load_and_analyze_pgn(self, pgn_path: str):
        """Load a PGN file and ask the agent to analyze it."""
        path = Path(pgn_path)
        if not path.exists():
            self._print_error(f"File not found: {pgn_path}")
            return

        pgn_text = path.read_text(encoding="utf-8", errors="ignore")
        # Limit to first game if huge file
        first_game_end = pgn_text.find("\n\n[", 200)
        if first_game_end > 0:
            pgn_text = pgn_text[:first_game_end]

        query = f"Please analyze this game from v7p3r_bot:\n\n{pgn_text}"
        self._print_info(f"Analyzing PGN: {path.name}")
        self._run_query(query)

    # ── Display helpers ───────────────────────────────────────────────────────

    def _print_banner(self):
        if RICH_AVAILABLE:
            self.console.print(Panel(
                Text(self.BANNER.strip(), style="bold white"),
                border_style="cyan",
                expand=False,
            ))
        else:
            print(self.BANNER)

    def _print_response(self, text: str):
        if RICH_AVAILABLE:
            self.console.print(Rule(style="dim"))
            try:
                self.console.print(Markdown(text))
            except Exception:
                self.console.print(text)
        else:
            print("\n" + text + "\n")

    def _print_thinking(self):
        if RICH_AVAILABLE:
            self.console.print("[dim italic]Thinking...[/dim italic]")
        else:
            print("Thinking...", end="", flush=True)

    def _print_status(self, msg: str):
        if RICH_AVAILABLE:
            self.console.print(f"[green]✓[/green] {msg}")
        else:
            print(f"[OK] {msg}")

    def _print_info(self, msg: str):
        if RICH_AVAILABLE:
            self.console.print(f"[cyan]{msg}[/cyan]")
        else:
            print(msg)

    def _print_error(self, msg: str):
        if RICH_AVAILABLE:
            self.console.print(f"[bold red]Error:[/bold red] {msg}")
        else:
            print(f"Error: {msg}", file=sys.stderr)

    def _print_help(self):
        help_text = """
**Built-in commands:**

| Command | Description |
|---------|-------------|
| `/help`         | Show this help |
| `/status`       | Show loaded game data stats |
| `/reload`       | Reload knowledge base after adding new data |
| `/stockfish`    | Check Stockfish engine availability |
| `/clear`        | Clear conversation history (fresh start) |
| `/pgn <path>`   | Load and analyze a specific PGN file |
| `/context`      | Show current context loaded into agent |
| `/quit`         | Exit the CLI |

**Example questions:**
- "What is v7p3r_bot's win rate as white vs black?"
- "Show me performance changes between v12 and v14"
- "What openings does v7p3r_bot struggle with?"
- "Analyze this position: [FEN]"
- "How did the v12.0 rollback affect the engine's ELO?"
- "Find blunders in my most recent bullet games"
"""
        if RICH_AVAILABLE:
            self.console.print(Markdown(help_text))
        else:
            print(help_text)


# ─── CLI entry point ─────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="V7P3R Engine Metrics CLI — chat with your chess analysis agent"
    )
    parser.add_argument(
        "--query", "-q",
        metavar="QUESTION",
        help="Run a single query and exit (non-interactive mode)"
    )
    parser.add_argument(
        "--model", "-m",
        metavar="MODEL",
        default=None,
        help="Gemini model to use (default: gemini-2.0-flash)"
    )
    parser.add_argument(
        "--no-pgn",
        action="store_true",
        help="Skip loading PGN games (faster startup)"
    )
    parser.add_argument(
        "--no-docs",
        action="store_true",
        help="Skip loading design docs"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show debug output (tool calls, data loading)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    cli = V7P3RCLI(args)
    cli.start()


if __name__ == "__main__":
    main()
