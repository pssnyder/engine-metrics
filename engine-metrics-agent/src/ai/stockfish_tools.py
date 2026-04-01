"""
V7P3R Engine Metrics - Stockfish Analysis Tools
Wraps the local Stockfish binary via python-chess to provide analysis
functions callable by the Gemini agent as tool calls.

Stockfish path is resolved from STOCKFISH_PATH env var with a fallback
to the known local installation.
"""

import os
import io
import json
from pathlib import Path
from typing import Optional

try:
    import chess
    import chess.pgn
    import chess.engine
    CHESS_AVAILABLE = True
except ImportError:
    CHESS_AVAILABLE = False

# ─── Stockfish path resolution ────────────────────────────────────────────────

_DEFAULT_STOCKFISH = r"C:\Users\Pat\Documents\Software\stockfish_12_win_x64_bmi2\stockfish_20090216_x64_bmi2.exe"

def _get_stockfish_path() -> str:
    path = os.environ.get("STOCKFISH_PATH", _DEFAULT_STOCKFISH)
    if not Path(path).exists():
        raise FileNotFoundError(
            f"Stockfish not found at: {path}\n"
            "Set STOCKFISH_PATH env var to the correct location."
        )
    return path


def _open_engine() -> "chess.engine.SimpleEngine":
    """Open a Stockfish engine process."""
    if not CHESS_AVAILABLE:
        raise RuntimeError("python-chess is not installed.")
    return chess.engine.SimpleEngine.popen_uci(_get_stockfish_path())


# ─── Tool: analyze_position ──────────────────────────────────────────────────

def analyze_position(fen: str, depth: int = 20, multipv: int = 3) -> dict:
    """
    Analyze a chess position (FEN) with Stockfish.

    Args:
        fen: FEN string of the position to analyze.
        depth: Search depth (default 20, max 30).
        multipv: Number of top lines to return (default 3).

    Returns:
        dict with 'evaluation', 'best_move', 'top_lines', 'is_checkmate'.
    """
    depth = min(int(depth), 30)
    multipv = min(int(multipv), 5)

    engine = _open_engine()
    try:
        board = chess.Board(fen)
        info = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=multipv)

        # info may be a list (multipv) or single dict
        if not isinstance(info, list):
            info = [info]

        lines = []
        for entry in info:
            score = entry.get("score")
            pv = entry.get("pv", [])

            # Convert score to centipawns from White's perspective
            if score is not None:
                score_rel = score.relative
                if score_rel.is_mate():
                    cp = None
                    mate_in = score_rel.mate()
                else:
                    cp = score_rel.score()
                    mate_in = None
                # flip to absolute (from White's perspective)
                score_white = score.white()
                if score_white.is_mate():
                    cp_white = None
                    mate_white = score_white.mate()
                else:
                    cp_white = score_white.score()
                    mate_white = None
            else:
                cp = cp_white = None
                mate_in = mate_white = None

            lines.append({
                "rank": len(lines) + 1,
                "centipawns_white": cp_white,
                "mate_in_white": mate_white,
                "centipawns_relative": cp,
                "mate_in_relative": mate_in,
                "best_move": pv[0].uci() if pv else None,
                "pv_uci": [m.uci() for m in pv[:8]],
                "pv_san": _pv_to_san(board, pv[:8]),
            })

        best = lines[0] if lines else {}
        return {
            "fen": fen,
            "depth": depth,
            "is_checkmate": board.is_checkmate(),
            "is_stalemate": board.is_stalemate(),
            "side_to_move": "white" if board.turn == chess.WHITE else "black",
            "evaluation": {
                "centipawns_white": best.get("centipawns_white"),
                "mate_in_white": best.get("mate_in_white"),
            },
            "best_move": best.get("best_move"),
            "best_move_san": _move_to_san(board, best.get("best_move")),
            "top_lines": lines,
        }
    finally:
        engine.quit()


# ─── Tool: analyze_game_pgn ──────────────────────────────────────────────────

def analyze_game_pgn(
    pgn_text: str,
    depth: int = 18,
    blunder_threshold_cp: int = 150,
    mistake_threshold_cp: int = 80,
    max_moves: int = 80,
) -> dict:
    """
    Analyze all moves in a PGN game and classify blunders/mistakes/inaccuracies.

    Args:
        pgn_text: Raw PGN text of a single game.
        depth: Stockfish depth per move (default 18, lower=faster).
        blunder_threshold_cp: Centipawn loss to classify as blunder (default 150).
        mistake_threshold_cp: Centipawn loss to classify as mistake (default 80).
        max_moves: Maximum ply to analyze (default 80 = 40 full moves).

    Returns:
        dict with move-by-move analysis, blunders, mistakes, accuracy estimates.
    """
    depth = min(int(depth), 25)

    game = _read_single_pgn(pgn_text)
    if game is None:
        return {"error": "Could not parse PGN game."}

    headers = dict(game.headers)
    engine = _open_engine()
    try:
        board = game.board()
        moves_analysis = []
        prev_eval_cp = None
        blunders = []
        mistakes = []
        inaccuracies = []

        ply = 0
        node = game
        while node.variations and ply < max_moves:
            node = node.variation(0)
            move = node.move

            # Eval before move
            before_info = engine.analyse(board, chess.engine.Limit(depth=depth))
            before_score = before_info["score"].white()
            before_cp = before_score.score(mate_score=10000) if not before_score.is_mate() else (10000 if before_score.mate() > 0 else -10000)

            # Make the move
            san = board.san(move)
            board.push(move)
            ply += 1

            # Eval after move (from White's perspective)
            after_info = engine.analyse(board, chess.engine.Limit(depth=depth))
            after_score = after_info["score"].white()
            after_cp = after_score.score(mate_score=10000) if not after_score.is_mate() else (10000 if after_score.mate() > 0 else -10000)

            # Loss is from the mover's perspective
            if board.turn == chess.WHITE:
                # Black just moved — Black's loss = after_cp - before_cp (White gains)
                cp_loss = after_cp - before_cp   # positive = good for white (bad for black)
                mover = "black"
            else:
                # White just moved — White's loss = before_cp - after_cp (White loses)
                cp_loss = before_cp - after_cp   # positive = good for black (bad for white)
                mover = "white"

            # Classify
            classification = "good"
            if cp_loss >= blunder_threshold_cp:
                classification = "blunder"
                blunders.append({"ply": ply, "san": san, "cp_loss": cp_loss, "mover": mover})
            elif cp_loss >= mistake_threshold_cp:
                classification = "mistake"
                mistakes.append({"ply": ply, "san": san, "cp_loss": cp_loss, "mover": mover})
            elif cp_loss >= 30:
                classification = "inaccuracy"
                inaccuracies.append({"ply": ply, "san": san, "cp_loss": cp_loss, "mover": mover})

            moves_analysis.append({
                "ply": ply,
                "move_number": (ply + 1) // 2,
                "mover": mover,
                "san": san,
                "uci": move.uci(),
                "eval_before_cp_white": before_cp,
                "eval_after_cp_white": after_cp,
                "cp_loss": cp_loss,
                "classification": classification,
            })

        # Accuracy metric (simplified: % of moves not blunders/mistakes)
        total = len(moves_analysis)
        white_moves = [m for m in moves_analysis if m["mover"] == "white"]
        black_moves = [m for m in moves_analysis if m["mover"] == "black"]
        white_acc = _accuracy(white_moves)
        black_acc = _accuracy(black_moves)

        return {
            "game_headers": headers,
            "total_plies_analyzed": total,
            "white_accuracy_pct": white_acc,
            "black_accuracy_pct": black_acc,
            "blunders": blunders,
            "mistakes": mistakes,
            "inaccuracies": inaccuracies,
            "blunder_count": {"white": sum(1 for b in blunders if b["mover"]=="white"),
                              "black": sum(1 for b in blunders if b["mover"]=="black")},
            "mistake_count": {"white": sum(1 for m in mistakes if m["mover"]=="white"),
                              "black": sum(1 for m in mistakes if m["mover"]=="black")},
            "move_by_move": moves_analysis,
        }
    finally:
        engine.quit()


# ─── Tool: find_best_moves ───────────────────────────────────────────────────

def find_best_moves(fen: str, top_n: int = 5, depth: int = 15) -> dict:
    """
    Return the top N best moves for a given FEN position.

    Args:
        fen: Position to analyze.
        top_n: Number of top moves to return (max 10).
        depth: Search depth (default 15).

    Returns:
        dict with ranked list of best moves and their evaluations.
    """
    top_n = min(int(top_n), 10)
    result = analyze_position(fen, depth=depth, multipv=top_n)
    return {
        "fen": fen,
        "side_to_move": result.get("side_to_move"),
        "top_moves": [
            {
                "rank": line["rank"],
                "move_uci": line["best_move"],
                "move_san": line.get("best_move_san") or _move_to_san(chess.Board(fen), line["best_move"]),
                "evaluation_cp_white": line["centipawns_white"],
                "mate_in": line["mate_in_white"],
                "continuation_uci": line["pv_uci"],
                "continuation_san": line["pv_san"],
            }
            for line in result.get("top_lines", [])
        ],
    }


# ─── Tool: get_game_key_positions ────────────────────────────────────────────

def get_game_key_positions(pgn_text: str, depth: int = 15) -> dict:
    """
    Extract critical positions from a game: opening end, middlegame peak
    imbalance, and final position. Returns FEN + eval for each.

    Args:
        pgn_text: Raw PGN of a single game.
        depth: Stockfish depth.

    Returns:
        dict with key position snapshots.
    """
    game = _read_single_pgn(pgn_text)
    if game is None:
        return {"error": "Could not parse PGN."}

    board = game.board()
    positions = []
    node = game
    while node.variations:
        node = node.variation(0)
        board.push(node.move)
        positions.append((board.ply(), board.fen()))

    if not positions:
        return {"error": "No moves in game."}

    snapshots = {}
    engine = _open_engine()
    try:
        # Opening end (~move 10)
        opening_ply = min(20, len(positions) - 1)
        snapshots["opening_end"] = _eval_position(engine, positions[opening_ply], depth)

        # Midgame (middle ply)
        mid_ply = len(positions) // 2
        snapshots["middlegame"] = _eval_position(engine, positions[mid_ply], depth)

        # Final position
        snapshots["final"] = _eval_position(engine, positions[-1], depth)

        return {
            "game_headers": dict(game.headers),
            "total_plies": len(positions),
            "key_positions": snapshots,
        }
    finally:
        engine.quit()


# ─── Tool: stockfish_status ──────────────────────────────────────────────────

def stockfish_status() -> dict:
    """
    Check if Stockfish is available and return version info.
    No analysis performed — just a connectivity check.
    """
    if not CHESS_AVAILABLE:
        return {"available": False, "error": "python-chess not installed"}

    try:
        path = _get_stockfish_path()
        engine = chess.engine.SimpleEngine.popen_uci(path)
        name = engine.id.get("name", "Unknown")
        engine.quit()
        return {
            "available": True,
            "path": path,
            "engine_name": name,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


# ─── Private helpers ─────────────────────────────────────────────────────────

def _read_single_pgn(pgn_text: str) -> Optional["chess.pgn.Game"]:
    try:
        return chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return None


def _pv_to_san(board: "chess.Board", moves: list) -> list[str]:
    """Convert a list of chess.Move objects to SAN notation."""
    san_list = []
    b = board.copy()
    for m in moves:
        try:
            san_list.append(b.san(m))
            b.push(m)
        except Exception:
            break
    return san_list


def _move_to_san(board_or_fen, uci_str: Optional[str]) -> Optional[str]:
    """Convert a UCI move string to SAN for a given position."""
    if not uci_str:
        return None
    try:
        if isinstance(board_or_fen, str):
            board = chess.Board(board_or_fen)
        else:
            board = board_or_fen.copy()
        move = chess.Move.from_uci(uci_str)
        return board.san(move)
    except Exception:
        return uci_str


def _accuracy(moves: list[dict]) -> float:
    """Simple accuracy: % of moves classified as good or inaccuracy (not blunder/mistake)."""
    if not moves:
        return 100.0
    good = sum(1 for m in moves if m["classification"] in ("good", "inaccuracy"))
    return round(good / len(moves) * 100, 1)


def _eval_position(engine, position_tuple: tuple, depth: int) -> dict:
    ply, fen = position_tuple
    board = chess.Board(fen)
    info = engine.analyse(board, chess.engine.Limit(depth=depth))
    score = info["score"].white()
    cp = score.score(mate_score=10000) if not score.is_mate() else None
    mate = score.mate() if score.is_mate() else None
    return {
        "ply": ply,
        "move_number": (ply + 1) // 2,
        "fen": fen,
        "eval_cp_white": cp,
        "mate_in": mate,
    }


# ─── Tool registry (for agent function calling) ───────────────────────────────

TOOL_REGISTRY = {
    "stockfish_status": stockfish_status,
    "analyze_position": analyze_position,
    "find_best_moves": find_best_moves,
    "analyze_game_pgn": analyze_game_pgn,
    "get_game_key_positions": get_game_key_positions,
}


if __name__ == "__main__":
    status = stockfish_status()
    print(json.dumps(status, indent=2))
    if status["available"]:
        # Quick position test: Italian game after 1.e4 e5 2.Nf3 Nc6 3.Bc4
        result = analyze_position("r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3")
        print(json.dumps(result, indent=2, default=str))
