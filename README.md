# chessbench
Testing Local LLMs by their Chess-playing proficiency through tool use.

> [!IMPORTANT]
> ### ChessBench Flags
> 
> * **`ILLEGAL_MOVE`**: The model returned a move, but it was not legal according to the current board state.
> * **`INVALID_FORMAT`**: The model returned a response that could not be parsed as a move (e.g., conversational text or incorrect notation).
> * **`LLM_ERROR`**: The model failed to provide a result due to technical limits, such as getting stuck in an infinite loop or running out of context.

## Puzzles
| Model Name | Total Puzzles | Accuracy | Average rating |
| ---------- | ------------- | -------- | -------------- |
| [Llama-3.2-3B-Instruct-Q4_K_M](https://github.com/ChefZander/chessbench/blob/main/puzzles/Llama-3.2-3B-Instruct-Q4_K_M_puzzle_bench.md) | 11521 | 5.7% | 1057 Elo |
| [Llama-3.2-1B-Instruct-Q4_K_M](https://github.com/ChefZander/chessbench/blob/main/puzzles/Llama-3.2-1B-Instruct-Q4_K_M_puzzle_bench.md) | 6162 | 3.1% | 1046 Elo |
| [nanbeige4.1-3b-q4_k_m](https://github.com/ChefZander/chessbench/blob/main/puzzles/nanbeige4.1-3b-q4_k_m_puzzle_bench.md) | 93 | 12.9% | 1044 Elo |
| [gemma-4-E4B-it-Q4_K_M](https://github.com/ChefZander/chessbench/blob/main/puzzles/gemma-4-E4B-it-Q4_K_M_puzzle_bench.md) | 1286 | 9.9% | 1044 Elo |
| [gemma-4-E4B-it-Q4_K_M-no-reasoning](https://github.com/ChefZander/chessbench/blob/main/puzzles/gemma-4-E4B-it-Q4_K_M-no-reasoning_puzzle_bench.md) | 256 | 11.7% | 945 Elo |

## Self-Play
| Model Name        |   Total Games | Game Completion Rate   | Illegal Move Rate   |   Avg. Tokens/Move | W / D / L    | Note |
|:------------------|--------------:|:----------------------|:--------------------|-------------------:|:-------------|-|
| [gemma-4-E4B-it-Q4_K_M](https://github.com/ChefZander/chessbench/blob/main/gemma-4-E4B-it-Q4_K_M_summary.md) | 69 | 2.9% | 0.9% | 1422.5 | 0 / 68 / 1 | I'm very impressed, even though play is honestly very bad. |
| [gemma-4-E2B-it-Q4_K_M](https://github.com/ChefZander/chessbench/blob/main/gemma-4-E2B-it-Q4_K_M.md) | 11 | 0.0% | N/A | N/A | 0 / 11 / 0 | The N/A values are missing because this benchmark is from an older version of ChessBench. |
| [Qwen3.5-4B-Q4_K_M](https://github.com/ChefZander/chessbench/blob/main/Qwen3.5-4B-Q4_K_M_summary.md) | 10 | 0.0% | 0.0% | 1227.8 | 0 / 10 / 0 | This model loves to get stuck in infinitely repeating sequences, making itself run out of context. |
