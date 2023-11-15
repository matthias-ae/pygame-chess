import pygame
import chess
import pgboard
import chess.engine
import sys

class Book:
	def __init__(self, book_path):
		self.db = TinyDB(book_path)

	def __getattr__(self, attr):
		return getattr(self.db, attr)

	def lookup(self, board):
		def average(lst):
			return sum(lst) // len(lst)
		infos = self.db.search(Query().fen == board.fen())
		depth = max(info['depth'] for info in infos)
		score = average([info['score'] for info in infos if info['depth'] == depth])
		return {'score': chess.engine.PovScore(chess.engine.Cp(score), chess.WHITE), 'depth': int(depth)}

	def put(self, id, info):
		score = info['score'].white().score()
		depth = info['depth']
		if id:
			self.db.update({'depth': depth, 'score': score}, doc_ids=[id])
			return id
		else:
			return self.db.insert({'fen': info['fen'], 'depth': depth, 'score': score})

class Engine:
	def __init__(self, uci_path, book=None):
		self.wrapper = chess.engine.SimpleEngine.popen_uci(uci_path)
		self.wrapper.configure({'Hash': 256, 'Threads': 2})
		self.running = False
		self.best = None
		self.book = book

	def __getattr__(self, attr):
		return getattr(self.wrapper, attr)

	def start_analysis(self, board, num_moves=1):
		if self.running:
			self.stop_analysis()
		self.best = {'fen': board.fen()}
		try:
			self.best.update(self.book.lookup(board))
		except Exception as e:
			pass
		if not 'depth' in self.best or self.best['depth'] < 50:
			self.analysis = self.wrapper.analysis(board)
			self.running = True
			self.db_id = None

	def _parse_info(self):
		improved = False
		while not self.analysis.would_block():
			info = self.analysis.get()
			if 'seldepth' in info:
				if not 'depth' in self.best or info['depth'] > self.best['depth']:
					self.best.update({'score': info['score'], 'move': [pv.uci() for pv in info['pv'][:2]], 'depth': info['depth']})
					improved = True
		return improved

	def stop_analysis(self):
		if not self.running:
			return
		self.analysis.stop()
		try:
			self._parse_info()
		except chess.engine.AnalysisComplete:
			pass
		self.running = False
		return self.analysis.wait()

	def current_best_moves(self):
		if self.running:
			improved = self._parse_info()
			if self.book and improved:
				self.db_id = self.book.put(self.db_id, self.best)
		if self.best and 'score' in self.best:
			return self.best.copy()

pygame.init()
print()
board = pgboard.Board()

screen = pygame.display.set_mode(board.size())
board.draw(screen)
pygame.display.flip()

CHECK_ANALYSIS = pygame.USEREVENT + 1

book = None
try:
	from tinydb import TinyDB, Query
	book = Book(sys.argv[2])
except IndexError:
    print('Not recording analysis: if a file name is provided as additional commanline argument (e.g. `python3 game.py /usr/bin/stockfish book.json`), any analysis results will be saved so next time in the same position they will be available immediately')
except Exception as e:
    print('Not recording analysis:', str(e))

engine = None
try:
	engine = Engine(sys.argv[1], book)
	pygame.time.set_timer(CHECK_ANALYSIS, 500)
except:
	print('Proceeding without engine: you could provide path to engine as commandline argument (e.g. `python3 game.py /usr/bin/stockfish`), then keypress will make engine move')

def make_move(move):
	board.highlight([move.from_square, move.to_square])
	if move in board.legal_moves:
		board.push(move)
		board.draw(screen)
		pygame.display.flip()
	else:
		print('Invalid move:', move)

from_square = None
best = None
analysis = None
while True:
	event = pygame.event.wait()
	if event.type == pygame.QUIT:
		break
	elif event.type == pygame.KEYDOWN:
		if event.key == pygame.K_BACKSPACE:
			board.highlight([])
			board.pop()
			board.draw(screen)
			pygame.display.flip()
		else:
			engine.stop_analysis()
			result = engine.play(board, chess.engine.Limit(time=0.1))
			make_move(result.move)
		engine.start_analysis(board)
		best = None
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
			if engine:
				engine.start_analysis(board)
				best = None
			from_square = None
	elif event.type == CHECK_ANALYSIS:
		prev_best = best
		best = engine.current_best_moves()
		if best:
			if prev_best is None or best['depth'] > prev_best['depth']:
				print(best['score'], 'depth=' + str(best['depth']))

if engine:
	engine.quit()
pygame.quit()
