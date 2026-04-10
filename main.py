from fileinput import filename
import chess
import chess.pgn
import json
import datetime
import sys
import time
from openai import OpenAI

# --- CONFIGURATION ---
LLM_API_URL = "http://localhost:8080/v1"
LLM_API_KEY = "no-key-required"
MODEL_NAME = "MODEL_NAME_HERE" # find using http://localhost:8080/v1/models
MAX_MOVES_PER_GAME = 9999

client = OpenAI(base_url=LLM_API_URL, api_key=LLM_API_KEY)

CHESS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "make_move",
            "description": "Submits your chosen chess move in UCI format.",
            "parameters": {
                "type": "object",
                "properties": {
                    "uci_move": {
                        "type": "string",
                        "description": "The move in UCI format."
                    }
                },
                "required": ["uci_move"]
            }
        }
    }
]

def get_llm_move(board):
    fen = board.fen()
    board_ascii = str(board)
    legal_moves = ", ".join([move.uci() for move in board.legal_moves])

    prompt = (
        f"You are a chess grandmaster playing as {'White' if board.turn == chess.WHITE else 'Black'}.\n"
        f"Current FEN string: {fen}\n"
        f"Board Representation:\n{board_ascii}\n\n"
        f"Legal Moves in UCI format: {legal_moves}\n\n"
        "Analyze the position and use the 'make_move' tool to submit your move."
    )

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        tools=CHESS_TOOLS,
        tool_choice={"type": "function", "function": {"name": "make_move"}},
        temperature=0.1,
        #extra_body={
        #    "reasoning_budget": 0,
        #    "enable_thinking": False
        #}
    )

    message = response.choices[0].message
    reasoning = message.content or "No textual reasoning provided."
    full_trace = json.dumps(message.to_dict(), indent=2)
    
    if message.tool_calls and len(message.tool_calls) > 0:
        tool_call = message.tool_calls[0]
        arguments = json.loads(tool_call.function.arguments)
        tokens = response.usage.total_tokens if response.usage else 0
    else:
        arguments = {"uci_move": None}
        tokens = 0

    return arguments.get("uci_move"), tokens, reasoning, full_trace

def play_game(game_id):
    board = chess.Board()
    game = chess.pgn.Game()
    game.headers["Event"] = f"ChessBench - Game {game_id}"
    game.headers["White"] = MODEL_NAME
    game.headers["Black"] = MODEL_NAME
    
    node = game
    move_count = 0
    total_game_tokens = 0
    move_history = []

    total_moves = 0
    total_moves_illegal = 0

    while not board.is_game_over() and move_count < MAX_MOVES_PER_GAME:
        color = 'White' if board.turn == chess.WHITE else 'Black'
        print(f"Game {game_id} - Move {move_count + 1} ({color})", end="\r")
        
        time.sleep(1)

        move_uci, tokens, reasoning, trace = get_llm_move(board)
        total_game_tokens += tokens
        total_moves += 1
        
        move_info = {
            "move_num": move_count + 1,
            "color": color,
            "uci": move_uci,
            "reasoning": reasoning,
            "trace": trace,
            "fen_before": board.fen()
        }
        
        if not move_uci:
            game.headers["Termination"] = "LLM_ERROR"
            move_history.append(move_info)
            break
            
        try:
            move = chess.Move.from_uci(move_uci)
            if move in board.legal_moves:
                board.push(move)
                node = node.add_variation(move)
                move_count += 1
                move_history.append(move_info)
            else:
                game.headers["Termination"] = "ILLEGAL_MOVE"
                move_history.append(move_info)
                total_moves_illegal += 1
                break
        except ValueError:
            game.headers["Termination"] = "INVALID_FORMAT"
            move_history.append(move_info)
            break

    game.headers["Result"] = board.result()
    game.headers["Total_Tokens"] = str(total_game_tokens)
    game.headers["Total_Moves"] = str(total_moves)
    game.headers["Total_Moves_Illegal"] = str(total_moves_illegal)
    print(f"\nGame {game_id} Finished: {board.result()}")
    return game, move_history

def export_to_markdown(games_data):
    if not games_data: return
    filename = f"{MODEL_NAME}_summary.md"
    games = [g[0] for g in games_data]
    total_games = len(games)
    total_tokens = sum(int(g.headers.get("Total_Tokens", 0)) for g in games)
    wins, losses, draws, illegal_moves = 0, 0, 0, 0

    total_moves = sum(int(g.headers.get("Total_Moves", 0)) for g in games)
    total_moves_illegal = sum(int(g.headers.get("Total_Moves_Illegal", 0)) for g in games)

    for g in games:
        res, term = g.headers.get("Result"), g.headers.get("Termination", "Normal")
        if term in ["ILLEGAL_MOVE", "INVALID_FORMAT", "LLM_ERROR"]: illegal_moves += 1
        if res == "1-0": wins += 1
        elif res == "0-1": losses += 1
        else: draws += 1

    game_success_rate = ((total_games - illegal_moves) / total_games) * 100
    illegal_move_pct = (total_moves_illegal / total_moves * 100) if total_moves > 0 else 0
    
    avg_tokens_per_move = (total_tokens / total_moves) if total_moves > 0 else 0

    with open(filename, "w") as f:
        f.write(f"# ChessBench Summary: {MODEL_NAME}\n\n")

        f.write(f"| Metric | Value | Description |\n")
        f.write(f"| :--- | :--- | :--- |\n")
        f.write(f"| **Total Games** | {total_games} | Total number of matches played. |\n")
        f.write(f"| **White W / D / L** | {wins} / {draws} / {losses} | Record of wins, draws, and losses. |\n")
        f.write(f"| **Game Completion Rate** | {game_success_rate:.1f}% | % of games that ended naturally (mate/draw). |\n")
        f.write(f"| **Total Moves** | {total_moves} | Total number of moves the LLM tried to make. |\n")
        f.write(f"| **Illegal Move Rate** | {illegal_move_pct:.2f}% | % of total move attempts that were illegal or malformed. |\n")
        f.write(f"| **Total Tokens** | {total_tokens} | Cumulative count of output tokens used. |\n")
        f.write(f"| **Avg Tokens / Move** | {avg_tokens_per_move:.1f} | Average token cost per individual move attempt. |\n\n")
        
        for i, game in enumerate(games):
            f.write(f"## Game {i+1}\n- **Result**: {game.headers.get('Result')}\n- **PGN**:\n```pgn\n{str(game)}\n```\n\n---\n")
    print(f"Summary exported to {filename}")

def export_to_detailed_log(games_data):
    if not games_data: return
    filename = f"{MODEL_NAME}_detailed_trace.md"
    with open(filename, "w") as f:
        f.write(f"# Detailed Move Trace: {MODEL_NAME}\n")
        f.write(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        for i, (game_pgn, history) in enumerate(games_data):
            f.write(f"## Game {i+1} Trace\n")
            f.write(f"**Final Result**: {game_pgn.headers.get('Result')} ({game_pgn.headers.get('Termination', 'Natural')})\n\n")
            for move in history:
                f.write(f"### Move {move['move_num']} ({move['color']})\n")
                f.write(f"- **FEN**: `{move['fen_before']}`\n")
                f.write(f"- **Move Selected**: `{move['uci']}`\n\n")
                f.write("#### Reasoning\n")
                f.write(f"> {move['reasoning']}\n\n")
                f.write("#### API Output Trace\n")
                f.write(f"```json\n{move['trace']}\n```\n\n")
            f.write("\n---\n\n")
    print(f"Detailed traces exported to {filename}")

if __name__ == "__main__":
    all_games_data = []
    game_counter = 1
    
    print(f"Starting ChessBench for {MODEL_NAME}...")
    print("Press Ctrl+C at any time to stop and export results.\n")
    
    try:
        while True:
            game_result = play_game(game_counter)
            all_games_data.append(game_result)
            game_counter += 1
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n[!] Interrupt received. Stopping games and saving data...")
    finally:
        if all_games_data:
            export_to_markdown(all_games_data)
            export_to_detailed_log(all_games_data)
        else:
            print("No games were completed. Nothing to export.")
        print("Done.")
