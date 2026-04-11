import chess
import json
import datetime
import time
from datasets import load_dataset
import os
from openai import OpenAI

# --- CONFIGURATION ---
LLM_API_URL = "http://localhost:8080/v1"
LLM_API_KEY = "no-key-required"
MODEL_NAME = ""
NUM_PUZZLES_TO_TEST = 999999  # Adjust based on your time constraints
LOCAL_DATASET_PATH = "./train-00000-of-00003.parquet" # https://huggingface.co/datasets/Lichess/chess-puzzles/blob/main/data/train-00000-of-00003.parquet

REASONING_DISABLED = False
if REASONING_DISABLED:
    print("⚠️  Reasoning is disabled for this benchmark. The model will not be able to explain its moves or thought process. This may lead to lower performance, but will test the model's raw move generation capabilities.")

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
                    "uci_move": {"type": "string", "description": "The move in UCI format (e.g., e2e4)."}
                },
                "required": ["uci_move"]
            }
        }
    }
]

def get_llm_move(board):
    fen = board.fen()
    legal_moves = ", ".join([move.uci() for move in board.legal_moves])
    
    prompt = (
        f"You are a chess expert solving a puzzle as {'White' if board.turn == chess.WHITE else 'Black'}.\n"
        f"Current FEN: {fen}\n"
        f"Board:\n{str(board)}\n\n"
        f"Legal Moves: {legal_moves}\n"
        "Find the best move to win material or mate. Use the 'make_move' tool."
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            tools=CHESS_TOOLS,
            tool_choice={"type": "function", "function": {"name": "make_move"}},
            temperature=0.1,

            # Disable reasoning
            extra_body={
                "chat_template_kwargs": {"enable_thinking": not REASONING_DISABLED}
            },
            max_tokens=256 if REASONING_DISABLED else None,
        )
        message = response.choices[0].message
        if message.tool_calls:
            args = json.loads(message.tool_calls[0].function.arguments)
            return args.get("uci_move"), response.usage.total_tokens, message.content
    except Exception as e:
        print(f"API Error: {e}")
    return None, 0, None

def solve_puzzle(puzzle_row):
    board = chess.Board(puzzle_row['FEN'])
    solution_moves = puzzle_row['Moves'].split()
    
    puzzle_id = puzzle_row['PuzzleId']
    moves_history = []
    success = True
    total_tokens = 0

    for i in range(0, len(solution_moves), 2):
        correct_move_uci = solution_moves[i]
        
        # 1. Ask LLM for the move
        llm_move_uci, tokens, reasoning = get_llm_move(board)
        total_tokens += tokens
        
        move_info = {
            "expected": correct_move_uci,
            "received": llm_move_uci,
            "reasoning": reasoning
        }
        moves_history.append(move_info)

        # 2. Validate
        if llm_move_uci != correct_move_uci:
            success = False
            break
        
        # 3. Apply LLM move to board
        board.push_uci(llm_move_uci)
        
        # 4. Play the opponent's predefined response (if it exists)
        if i + 1 < len(solution_moves):
            opponent_move = solution_moves[i+1]
            board.push_uci(opponent_move)

    return success, total_tokens, moves_history

def run_benchmark():
    if not os.path.exists(LOCAL_DATASET_PATH):
        print(f"Error: Local file not found at {LOCAL_DATASET_PATH}")
        return

    print(f"Loading local dataset from {LOCAL_DATASET_PATH}...")
    # Infers format from extension (csv, parquet, json)
    file_ext = os.path.splitext(LOCAL_DATASET_PATH)[1][1:]
    dataset = load_dataset(file_ext, data_files=LOCAL_DATASET_PATH, split="train")
    
    results = []
    solved_count = 0
    total_solved_rating = 0
    num_puzzles_completed = 0
    
    print(f"Benchmarking {MODEL_NAME} on {NUM_PUZZLES_TO_TEST} puzzles...\n")
    
    for i, row in enumerate(dataset):
        try:
            if i >= NUM_PUZZLES_TO_TEST: break
            
            print(f"[{i+1}/{NUM_PUZZLES_TO_TEST}] Solving Puzzle {row['PuzzleId']} (Rating: {row['Rating']})...", end="\r")
            
            success, tokens, history = solve_puzzle(row)
            if success: 
                solved_count += 1
                total_solved_rating += row['Rating']
            num_puzzles_completed += 1
            results.append({
                "id": row['PuzzleId'],
                "rating": row['Rating'],
                "success": success,
                "tokens": tokens,
                "history": history
            })
            #time.sleep(0.5)
            print(f"{row['PuzzleId']} - {'✅' if success else '❌'} - Tokens: {tokens} - Rating: {row['Rating']}                          ")
        except KeyboardInterrupt:
            print("\nBenchmark interrupted by user.")
            break
    
    avg_solved_rating = total_solved_rating / solved_count if solved_count > 0 else 0

    # --- EXPORT RESULTS ---
    summary_file = f"{MODEL_NAME}{'-no-reasoning' if REASONING_DISABLED else ''}_puzzle_bench.md"
    with open(summary_file, "w") as f:
        f.write(f"# Chess Puzzle Benchmark: {MODEL_NAME}\n\n")
        f.write(f"- **Total Puzzles**: {num_puzzles_completed}\n")
        f.write(f"- **Solved**: {solved_count}\n")
        f.write(f"- **Accuracy**: {(solved_count/num_puzzles_completed)*100:.1f}%\n\n")
        f.write(f"- **Avg Rating of Solved**: {avg_solved_rating:.0f}\n\n")
        
        f.write("| Puzzle ID | Rating | Status | Tokens | Moves Played |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        for r in results:
            status = "✅" if r['success'] else "❌"
            moves = " -> ".join([m['received'] or "NONE" for m in r['history']])
            f.write(f"| {r['id']} | {r['rating']} | {status} | {r['tokens']} | {moves} |\n")
    print(f"\nBenchmark Complete. Accuracy: {(solved_count/num_puzzles_completed)*100:.1f}%")
    print(f"Results saved to {summary_file}")

if __name__ == "__main__":
    run_benchmark()