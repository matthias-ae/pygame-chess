import pygame
import chess
import pgboard
import chess.engine
import sys

pygame.init()
print()
board = pgboard.Board()

screen = pygame.display.set_mode(board.size())
board.draw(screen)
pygame.display.flip()

try:
	engine = chess.engine.SimpleEngine.popen_uci(sys.argv[1])
except:
	print('Proceeding without engine: You could provide path to engine as commandline argument (e.g. `python3 chessgame.py /usr/bin/stockfish`), then keypress will make engine move')

def make_move(move):
	board.highlight([move.from_square, move.to_square])
	if move in board.legal_moves:
		board.push(move)
		board.draw(screen)
		pygame.display.flip()
	else:
		print('Invalid move:', move)

from_square = None
while True:
	event = pygame.event.wait()
	if event.type == pygame.QUIT:
		break
	elif event.type == pygame.KEYDOWN:
		result = engine.play(board, chess.engine.Limit(time=0.1))
		make_move(result.move)
	elif event.type == pygame.MOUSEBUTTONDOWN and not from_square:
		from_square = board.select(event.pos)
		board.highlight([from_square])
		board.draw(screen)
		pygame.display.flip()
	elif event.type == pygame.MOUSEBUTTONUP and from_square: # to-square => make move
		to_square = board.select(event.pos)
		if to_square and to_square != from_square:
			move = chess.Move(from_square, to_square)
			print(move)
			make_move(move)
			from_square = None

engine.quit()
pygame.quit()
