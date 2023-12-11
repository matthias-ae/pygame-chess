import chess
from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage
from tinydb.middlewares import CachingMiddleware
from operator import itemgetter

def _push(board, move):
	p = chess.Board(board.fen())
	p.push(chess.Move.from_uci(move))
	return p

class Book:
	def __init__(self, book_path):
		self.db = TinyDB(book_path, storage=CachingMiddleware(JSONStorage))

	# method currently multipv only!
	def lookup(self, board):
		def average(lst):
			return sum(lst) // len(lst)
		def fix_turn(score):
			return chess.engine.PovScore(score.pov(board.turn), board.turn)
		scores = []
		max_depth = 0
		for move, value in self.analysis.items():
			info_lst = value['info']
			depth = max(info['depth'] for info in info_lst)
			score = average([info['score'] for info in info_lst if info['depth'] > depth - 5])
			scores.append((score, {'depth': depth, 'move': chess.Move.from_uci(move)}))
			if depth > max_depth:
				max_depth = depth
		return {i+1: info | {'score': fix_turn(chess.engine.PovScore(chess.engine.Cp(score), chess.WHITE))} for i, (score, info) in enumerate(sorted(((s, i) for (s, i) in scores if i['depth'] >= max_depth - 1), reverse=board.turn, key=itemgetter(0))) }

	# method currently multipv only!
	def new_analysis(self, board):
		self.analysis = {}
		results = self.db.search(Query().multipv.exists() & (Query().fen == board.fen()))
		if results:
			for move in results[0]['multipv']:
				result = self.db.search(Query().info.exists() & (Query().fen == _push(board, move).fen()))
				if result:
					self.analysis[move] = {'info': result[0]['info']}

	def put(self, board, variations):
		multipv = set(self.analysis.keys())
		changed = False
		for info_in in variations.values():
			move = info_in['move'].uci()
			fen = _push(board, move).fen()
			if move in self.analysis:
				if not 'depth' in self.analysis[move] or info_in['depth'] > self.analysis[move]['depth']:
					self.analysis[move]['depth'] = info_in['depth']
					max_depth = max(info['depth'] for info in self.analysis[move]['info'])
					if info_in['depth'] > max_depth - 5:
						# add new
						self.analysis[move]['info'].append({'score': info_in['score'].white().score(), 'depth': info_in['depth']})
						if info_in['depth'] > max_depth:
							max_depth = info_in['depth']
						# throw out old
						self.analysis[move]['info'] = [info for info in self.analysis[move]['info'] if info['depth'] > max_depth - 5]
						self.db.update({'info': self.analysis[move]['info']}, Query().info.exists() & (Query().fen == fen))
						changed = True
			else:
				info_out = [{'score': info_in['score'].white().score(), 'depth': info_in['depth']}]
				self.analysis[move] = {'info': info_out, 'depth': info_in['depth']}
				self.db.insert({'info': info_out, 'fen': fen, 'move': move})
				changed = True
		if not multipv:
			self.db.insert({'multipv': list(self.analysis.keys()), 'fen': board.fen()})
			changed = True
		elif not multipv == set(self.analysis.keys()):
			self.db.update({'multipv': list(self.analysis.keys())}, Query().multipv.exists() & (Query().fen == board.fen()))
			changed = True
		if changed:
			self.db.storage.flush()
