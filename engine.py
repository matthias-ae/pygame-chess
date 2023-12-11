import chess
import chess.engine

class Engine:
	def __init__(self, uci_path):
		self.engine = chess.engine.SimpleEngine.popen_uci(uci_path)
		self.engine.configure({'Hash': 256, 'Threads': 2})

	def __getattr__(self, attr):
		return getattr(self.engine, attr)

	def start_analysis(self, board, num_moves=1):
		board = chess.Board(board.fen()) # need copy and need chess.Board class
		return Analysis(self.engine.analysis(board, multipv=num_moves))

class Analysis:
	def __init__(self, analysis):
		self.analysis = analysis
		self.results = {}

	def stop(self):
		self.analysis.stop()

	def best_moves(self):
		self._parse_info()
		return self.results

	def _parse_info(self):
		while not self.analysis.would_block():
			info = self.analysis.get()
			# if this UCI line has enough usefull information for us
			if 'score' in info and 'multipv' in info and len(info['pv']) >= 2:
				info['move'] = info['pv'][0]
				if not info['multipv'] in self.results or info['depth'] >= self.results[info['multipv']]['depth']:
					del info['pv']
					self.results[info['multipv']] = info
					del info['multipv']
