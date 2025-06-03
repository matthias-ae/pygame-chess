# pygame-chess
A chess game using `python-chess` and `pygame`. You can use it for PvP or analysis.

Run
  `python3 game.py`
or if you have a chess engine at hand provide it as an commandline argument like
  `python3 game.py --engine /usr/bin/stockfish`
or, if you're willing to use tinydb,
  `python3 game.py --engine /usr/bin/stockfish --book book.json`
to write evaluations to database to load later when getting to same position again

You can play a move yourself by using the mouse, or press a space or enter to let the engine play a move (if you provided one).
You can turn analysis (showing top 5 moves) on and off using '?' key


**File Descriptions:**

*   **`book.py`**: This file defines the `Book` class, which manages interaction with a local TinyDB database to store and retrieve chess analysis results (scores, depths, variations) associated with specific board positions, identified by their partial FEN. It allows looking up analysis data for the current board, loading previously saved analysis into an internal structure (`self.analysis`), and writing new or updated analysis information obtained from the engine back to the database.
*   **`engine.py`**: This file provides an interface to a UCI-compatible chess engine using the `python-chess` library. It defines an `Engine` class to launch and configure the engine process and an `Analysis` class to asynchronously handle and parse the engine's multi-PV analysis output, extracting information like scores, depths, and best moves.
*   **`game.py`**: This is the main application file that orchestrates the chess game and analysis. It initializes the Pygame display and UI (`pgboard`), handles user input (mouse clicks for moves, keyboard shortcuts for controls), integrates with the `Engine` for analysis and automated moves, interacts with the `Book` for saving and loading analysis, uses the `Tree` for automated game lines, displays the board, and shows engine analysis results on the screen.
*   **`pgboard.py`**: This file defines the `Board` class, a Pygame-specific wrapper around `python-chess.Board` that handles the visual representation of the chessboard. It uses `python-chess.svg` to render the board and pieces as Pygame surfaces, manages piece sizing, draws the board and pieces, handles board flipping, highlights selected or moved squares, and translates Pygame mouse coordinates back into chess square indices.
*   **`tree.py`**: This file defines the `Tree` class, which maintains a simple game tree as a dictionary of board positions (FEN strings). Primarily used with the `--auto` argument, it tracks visited positions and, using analysis data from the `Book` module, helps identify and suggest the "next best" move according to score differences, enabling the automatic playing of specific lines based on engine analysis.
