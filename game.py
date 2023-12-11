import pygame
import chess
import pgboard
import sys
import random
import argparse
from engine import Engine, Analysis

def show_analysis(best_moves):
	y = 22
	screen.blit(analysis_surf, (board.size()[0], 0))

	depth = min(info['depth'] for info in best_moves.values())
	text_screen = sfont.render('depth=' + str(depth), True, (0, 0, 0), (200, 228, 255))
	screen.blit(text_screen, (board.size()[0] + 3 + 12, 2))

	# help=False: just evaluation of current position
	if not help:
		score = best_moves[1]['score'].white().score()
		text_screen = font.render('+' + str(score) if score >= 0 else str(score), True, (20, 20, 20), (235, 235, 235))
		screen.blit(text_screen, (board.size()[0] + 3 + 16, 32))

	else: #help==True: analysis with top 5 moves
		for v in sorted(best_moves):
			score = best_moves[v]['score'].white().score()
			text_screen = font.render('+' + str(score) if score >= 0 else str(score), True, (20, 20, 20), (235, 235, 235))
			screen.blit(text_screen, (board.size()[0] + 3, y))
			text_screen = font.render(best_moves[v]['move'].uci(), True, (0, 0, 0), (200, 228, 255))
			screen.blit(text_screen, (board.size()[0] + 3 + 38, y))
			y += text_screen.get_size()[1] + 2
	pygame.display.flip()

parser = argparse.ArgumentParser()
parser.add_argument('-e', '--engine', help='path to UCI chess engine, e.g. /usr/games/stockfish')
parser.add_argument('-b', '--book', help='Json file for recording and retrieving analysis results')
args = parser.parse_args()

pygame.init()
print()
board = pgboard.Board(piece_size=64)

font = pygame.font.Font(None, 26)
sfont = pygame.font.Font(None, 22)
analysis_surf = pygame.Surface((128, 128))
analysis_surf.fill((235, 235, 235))

screen = pygame.display.set_mode((board.size()[0] + 200, board.size()[1]))
board.draw(screen)

CHECK_ANALYSIS = pygame.USEREVENT + 1

book = None
if args.book:
	from book import Book
	book = Book(args.book)
	book.new_analysis(board)
	best_moves = book.lookup(board)
	if (best_moves):
		show_analysis(best_moves)

pygame.display.flip()

engine = None
analysis = None
if args.engine:
	engine = Engine(args.engine)
	analysis = engine.start_analysis(board, num_moves=5)
	pygame.time.set_timer(CHECK_ANALYSIS, 500)

def make_move(move):
	board.highlight([move.from_square, move.to_square])
	if move in board.legal_moves:
		board.push(move)
		board.draw(screen)
		pygame.display.flip()
		return True
	else:
		print('Invalid move:', move)

def restart_analysis(analysis):
	if book:
		book.new_analysis(board)
		best_moves = book.lookup(board)
		if (best_moves):
			show_analysis(best_moves)
	if engine:
		analysis.stop()
		return engine.start_analysis(board, num_moves=5 if help else 1)


from_square = None
help = True

while True:
	event = pygame.event.wait()
	if event.type == pygame.QUIT:
		break
	elif event.type == pygame.KEYDOWN:
		if event.key == pygame.K_BACKSPACE:
			try:
				board.highlight([])
				board.pop()
				board.draw(screen)
				pygame.display.flip()
				analysis = restart_analysis(analysis)
			except IndexError:
				print('Already at beginning of game')
		elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
			thresh = 100
			variations = analysis.best_moves()
			variations = [info for v, info in variations.items() if
					variations[1]['score'].relative.score() - info['score'].relative.score() < thresh]
			make_move(random.choice(variations)['move'])
			analysis = restart_analysis(analysis)
		elif event.key in [pygame.K_SLASH, pygame.K_QUESTION] or event.unicode == '?':
			help = not help
			analysis = restart_analysis(analysis)
		elif event.key in [pygame.K_TAB, pygame.K_DOWN, pygame.K_UP]:
			board.flip()
			board.draw(screen)
			pygame.display.flip()
		else:
			if event.unicode:
				print('pressed ', event.unicode)
	elif event.type == pygame.MOUSEBUTTONDOWN and from_square is None:
		from_square = board.select(event.pos)
		board.highlight([from_square])
		board.draw(screen)
		pygame.display.flip()
	elif event.type == pygame.MOUSEBUTTONUP and from_square is not None: # to-square => make move
		to_square = board.select(event.pos)
		if to_square is not None and to_square != from_square:
			move = chess.Move(from_square, to_square)
			if make_move(move):
				analysis = restart_analysis(analysis)
				pygame.display.flip()
			from_square = None
	elif event.type == CHECK_ANALYSIS:
		best_moves = analysis.best_moves()
		print(", ".join(list("d=" + str(info['depth']) + " " + str(info['score'].white().score()) + "cp " + info['move'].uci() for info in best_moves.values())), end='\r')
		if book:
			book.put(board, best_moves)
			best_moves = book.lookup(board)
		show_analysis(best_moves)

if engine:
	engine.quit()
pygame.quit()
