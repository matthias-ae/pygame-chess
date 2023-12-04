import chess
import chess.engine

class Engine:
	def __init__(self, uci_path, book=None):
		self.engine = chess.engine.SimpleEngine.popen_uci(uci_path)
		self.engine.configure({'Hash': 256, 'Threads': 2})
		self.book = book

	def __getattr__(self, attr):
		return getattr(self.engine, attr)

	def start_analysis(self, board, num_moves=1):
		board = chess.Board(board.fen()) # need copy and need chess.Board class
		if self.book:
			initial_values = self.book.lookup(board, multipv=num_moves > 1)
			return Analysis(
				self.engine.analysis(board, multipv=num_moves),
				initial_values if num_moves > 1 or not initial_values else {1: initial_values},
				lambda info: self.book.put(board, info if num_moves > 1 else info[1], multipv=num_moves > 1)
			)
		else:
			return Analysis(self.engine.analysis(board, multipv=num_moves))


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
