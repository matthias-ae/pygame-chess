# pygame-chess
A chess game using `python-chess` and `pygame`. You can use it for PvP or analysis.

Run
  `python3 game.py`
or if you have a chess engine at hand provide it as an commandline argument like
  `python3 game.py /usr/bin/stockfish`
or, if you're willing to use tinydb,
  `python3 game.py /usr/bin/stockfish book.json`
to write evaluations to database to load later when getting to same board again

You can play a move yourself by using the mouse, or press a space or enter to let the engine play a move (if you provided one).
You can turn analysis (showing top 5 moves) on and off using '?' key
