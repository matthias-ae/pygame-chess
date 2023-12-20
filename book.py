import chess
from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage
from tinydb.middlewares import CachingMiddleware
from operator import itemgetter

def _push(board, move):
	p = chess.Board(board.fen())
	p.push(chess.Move.from_uci(move))
	return p

def _partial_fen(fen):
	parts = fen.split()
	return {'fen': " ".join(parts[:4]), 'halfmoves': parts[-2], 'fullmoves': parts[-1]}


class Book:
	def __init__(self, book_path):
		self.db = TinyDB(book_path, storage=CachingMiddleware(JSONStorage), sort_keys=True, indent=1, separators=(',', ': '))

	# method currently multipv only!
	def lookup(self, board):
		def fix_turn(score):
			return chess.engine.PovScore(score.pov(board.turn), board.turn)
		scores = []
		max_depth = 0
		for move, value in self.analysis.items():
			info_lst = value['info']
			depth = max(info['depth'] for info in info_lst)
			score_lst = list(info['score'] for info in info_lst if info['depth'] > depth - 5)
			score = sum(score_lst) // len(score_lst)
			scores.append((score, {'depth': depth, 'move': chess.Move.from_uci(move), 'avg': len(score_lst)}))
			if depth > max_depth:
				max_depth = depth
		return {i+1: info | {'score': fix_turn(chess.engine.PovScore(chess.engine.Cp(score), chess.WHITE))} for i, (score, info) in enumerate(sorted(((s, i) for (s, i) in scores if i['depth'] >= max_depth - 1), reverse=board.turn, key=itemgetter(0))) }

	# method currently multipv only!
	def new_analysis(self, board):
		self.analysis = {}
		results = self.db.search(Query().multipv.exists() & (Query().fen == _partial_fen(board.fen())['fen']))
		if results:
			for move in results[0]['multipv']:
				result = self.db.search(Query().info.exists() & (Query().fen == _partial_fen(_push(board, move).fen())['fen']))
				if result:
					self.analysis[move] = {'info': result[0]['info']}

	def put(self, board, variations):
		prev_analysis = self.analysis
		self.analysis = {}
		changed = False
		for info_in in variations.values():
			move = info_in['move'].uci()
			fen = _push(board, move).fen()
			if move in prev_analysis:
				self.analysis[move] = prev_analysis[move]
				if not 'depth' in self.analysis[move] or info_in['depth'] > self.analysis[move]['depth']:
					self.analysis[move]['depth'] = info_in['depth'] # depth of currently running analysis
					max_depth = max(info['depth'] for info in self.analysis[move]['info']) # max depth including previous analyses 
					if info_in['depth'] > max_depth - 5:
						# add new
						self.analysis[move]['info'].append({'score': info_in['score'].white().score(), 'depth': info_in['depth']})
						if info_in['depth'] > max_depth:
							max_depth = info_in['depth']
						# throw out old
						self.analysis[move]['info'] = [info for info in self.analysis[move]['info'] if info['depth'] > max_depth - 5]
						self.db.update({'info': self.analysis[move]['info']}, Query().info.exists() & (Query().fen == _partial_fen(fen)['fen']))
						changed = True
			else:
				exist = self.db.search(Query().info.exists() & (Query().fen == _partial_fen(fen)['fen']))
				info_out = [{'score': info_in['score'].white().score(), 'depth': info_in['depth']}]
				self.analysis[move] = {'info': info_out, 'depth': info_in['depth']}
				if exist:
					self.db.update({'info': info_out + exist[0]['info']}, doc_ids=[exist[0].doc_id])
				else:
					self.db.insert({'info': info_out, 'move': move} | _partial_fen(fen))
				changed = True
		if not prev_analysis:
			self.db.insert({'multipv': list(self.analysis.keys())} | _partial_fen(board.fen()))
			changed = True
		elif not set(prev_analysis.keys()) == set(self.analysis.keys()) and changed:
			self.db.update({'multipv': list(self.analysis.keys())}, Query().multipv.exists() & (Query().fen == _partial_fen(board.fen())['fen']))
			changed = True
		if changed:
			self.db.storage.flush()
