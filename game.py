import pygame
import chess
import pgboard
import chess.engine
import sys
import random
import argparse

def _push(board, move):
	p = chess.Board(board.fen())
	p.push(chess.Move.from_uci(move))
	return p

class Book:
	to_db = {
		'fen': lambda f: f,
		'score': lambda s: s.white().score(),
		'move': lambda m: m.uci(),
		'depth': lambda d: d,
		'multipv': lambda mpv: mpv
	}

	def __init__(self, book_path):
		self.db = TinyDB(book_path, storage=CachingMiddleware(JSONStorage))

	def lookup(self, board, multipv=False):
		def average(lst):
			return sum(lst) // len(lst)
		def fix_turn(info):
			info['score'] = chess.engine.PovScore(info['score'].pov(board.turn), board.turn)
			return info
		if multipv:
			parent = self.db.search(Query().multipv.exists() & (Query().fen == board.fen()))
			if parent:
				return {i+1: fix_turn(self.lookup(_push(board, move))) | {'move': chess.Move.from_uci(move)} for i, move in enumerate(parent[0]['multipv'])}
		else:
			info_lst = self.db.search(Query().score.exists() & (Query().fen == board.fen()))
			if info_lst:
				depth = max(info['depth'] for info in info_lst)
				score = average([info['score'] for info in info_lst if info['depth'] == depth])
				return {'score': chess.engine.PovScore(chess.engine.Cp(score), chess.WHITE), 'depth': depth}

	def put(self, board, info, multipv=False):
		if multipv:
			variations = info

			changed = sum(self.put(_push(board, info['move'].uci()), info) is not None for v, info in variations.items()) \
			        + (self.put(board, {'depth': min(info['depth'] for info in variations.values()), 'multipv': [variations[v]['move'].uci() for v in sorted(variations.keys())]}) is not None)
			if changed:
				self.db.storage.flush()
		else:
			info = {key: Book.to_db[key](val) for key, val in info.items() if key in Book.to_db}
			query = Query().fen == board.fen()
			for key in ['multipv', 'score']:
				if key in info:
					query = getattr(Query(), key).exists() & query
			existing = self.db.search(query)
			info = info | {'fen': board.fen()}
			if existing:
				if info['depth'] > existing[0]['depth']:
					print("update", info)
					self.db.update(info, doc_ids=[existing[0].doc_id])
					return existing[0].doc_id
			else:
				print("insert", info)
				return self.db.insert(info)

class Engine:
	def __init__(self, uci_path, book=None):
		self.engine = chess.engine.SimpleEngine.popen_uci(uci_path)
		self.engine.configure({'Hash': 256, 'Threads': 2})
		self.book = book

	def __getattr__(self, attr):
		return getattr(self.engine, attr)

	def start_analysis(self, board, num_moves=1):
		if self.book:
			initial_values = self.book.lookup(board, multipv=num_moves > 1)
			return Analysis(
				self.engine.analysis(board.board, multipv=num_moves),
				initial_values if num_moves > 1 or not initial_values else {1: initial_values},
				lambda info: self.book.put(board, info if num_moves > 1 else info[1], multipv=num_moves > 1)
			)
		else:
			return Analysis(self.engine.analysis(board.board, multipv=num_moves))


class Analysis:
	def __init__(self, analysis, initial_values=None, callback=None):
		self.analysis = analysis
		self.running = True
		if initial_values:
			self.results = initial_values
		else:
			self.results = {}
		self.callback = callback

	def stop(self):
		self.analysis.stop()

	def best_moves(self):
		self._parse_info()
		if self.results and self.callback:
			self.callback(self.results)
		return self.results

	def _parse_info(self):
		while not self.analysis.would_block():
			info = self.analysis.get()
			# if this UCI line has enough usefull information for us
			if 'score' in info and 'multipv' in info and len(info['pv']) >= 2:
				info['move'] = info['pv'][0]
				print(info['score'], info['move'], info['depth'], end='\r')
				if not info['multipv'] in self.results or info['depth'] >= self.results[info['multipv']]['depth']:
					del info['pv']
					self.results[info['multipv']] = info
					del info['multipv']

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
pygame.display.flip()

CHECK_ANALYSIS = pygame.USEREVENT + 1

book = None
if args.book:
	from tinydb import TinyDB, Query
	from tinydb.storages import JSONStorage
	from tinydb.middlewares import CachingMiddleware
	book = Book(args.book)

engine = None
if args.engine:
	engine = Engine(args.engine, book)
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
			except IndexError:
				print('Already at beginning of game')
			analysis = restart_analysis(analysis)
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
			print(move)
			if make_move(move):
				analysis = restart_analysis(analysis)
			from_square = None
	elif event.type == CHECK_ANALYSIS:
		top = analysis.best_moves()
		y = 22
		screen.blit(analysis_surf, (board.size()[0], 0))

		# help=False: just evaluation of current position
		if not help:
			text_screen = sfont.render('depth=' + str(top[1]['depth']), True, (0, 0, 0), (200, 228, 255))
			screen.blit(text_screen, (board.size()[0] + 3 + 12, 2))
			score = top[1]['score'].white().score()
			text_screen = font.render('+' + str(score) if score >= 0 else str(score), True, (20, 20, 20), (235, 235, 235))
			screen.blit(text_screen, (board.size()[0] + 3 + 16, 32))
			pygame.display.flip()
			continue

		# help==True: analysis with top 5 moves
		for v in sorted(top):
			text_screen = sfont.render('depth=' + str(top[v]['depth']), True, (0, 0, 0), (200, 228, 255))
			screen.blit(text_screen, (board.size()[0] + 3 + 12, 2))
			score = top[v]['score'].white().score()
			text_screen = font.render('+' + str(score) if score >= 0 else str(score), True, (20, 20, 20), (235, 235, 235))
			screen.blit(text_screen, (board.size()[0] + 3, y))
			text_screen = font.render(top[v]['move'].uci(), True, (0, 0, 0), (200, 228, 255))
			screen.blit(text_screen, (board.size()[0] + 3 + 38, y))
			y += text_screen.get_size()[1] + 2
		pygame.display.flip()

if engine:
	engine.quit()
pygame.quit()
