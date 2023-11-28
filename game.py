import pygame
import chess
import pgboard
import chess.engine
import sys

def _push(fen, move):
	p = chess.Board(fen)
	p.push(chess.Move.from_uci(move))
	return p.fen()

class Book:
	to_db = {
		'fen': lambda f: f,
		'score': lambda s: s.white().score(),
		'move': lambda m: m.uci(),
		'depth': lambda d: d,
		'multipv': lambda mpv: mpv
	}

	def __init__(self, book_path):
		self.db = TinyDB(book_path)

	def lookup(self, fen, multipv=False):
		def average(lst):
			return sum(lst) // len(lst)
		if multipv:
			parent = self.db.search(Query().multipv.exists() & (Query().fen == fen))
			if parent:
				return {i+1: self.lookup(_push(fen, move)) | {'move': chess.Move.from_uci(move)} for i, move in enumerate(parent[0]['multipv'])}
		else:
			info_lst = self.db.search(Query().score.exists() & (Query().fen == fen))
			if info_lst:
				depth = max(info['depth'] for info in info_lst)
				score = average([info['score'] for info in info_lst if info['depth'] == depth])
				return {'score': chess.engine.PovScore(chess.engine.Cp(score), chess.WHITE), 'depth': depth}

	def put(self, fen, info, multipv=False):
		if multipv:
			variations = info
			for v, info in variations.items():
				self.put(_push(fen, info['move'].uci()), info)
			self.put(fen, {'depth': min(info['depth'] for info in variations.values()), 'multipv': [variations[v]['move'].uci() for v in sorted(variations.keys())]})
		else:
			info = {key: Book.to_db[key](val) for key, val in info.items() if key in Book.to_db}
			query = Query().fen == fen
			for key in ['multipv', 'score']:
				if key in info:
					query = getattr(Query(), key).exists() & query
			existing = self.db.search(query)
			info = info | {'fen': fen}
			if existing:
				if info['depth'] > existing[0]['depth']:
					print("update", info)
					self.db.update(info, doc_ids=[existing[0].doc_id])
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
			initial_values = self.book.lookup(board.fen(), multipv=num_moves > 1)
			return Analysis(
				self.engine.analysis(board.board, multipv=num_moves),
				initial_values if num_moves > 1 or not initial_values else {1: initial_values},
				lambda info: self.book.put(board.fen(), info if num_moves > 1 else info[1], multipv=num_moves > 1)
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
		return True
	else:
		print('Invalid move:', move)

def restart_analysis(analysis):
	if engine:
		if analysis:
			analysis.stop()
		return engine.start_analysis(board, num_moves=5 if help else 1)


from_square = None
analysis = None
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
			print(event, type(event.key), event.key)
			if analysis:
				analysis.stop()
			result = engine.play(board.board, chess.engine.Limit(time=0.1))
			make_move(result.move)
			analysis = engine.start_analysis(board, num_moves=5 if help else 1)
		elif event.key in [pygame.K_SLASH, pygame.K_QUESTION] or event.unicode == '?':
			help = not help
			analysis = restart_analysis(analysis)
		elif event.key in [pygame.K_TAB, pygame.K_DOWN, pygame.K_UP]:
			board.flip()
			board.draw(screen)
			pygame.display.flip()
		else:
			print('unknown key', event.key, event.unicode if hasattr(event, 'unicode') else '')
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
		if analysis:
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
