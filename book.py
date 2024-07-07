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
		min_depth = 99

		for move in self.analysis['moves']:
			info_lst = self.analysis[move]['info']
			depth = max(info['depth'] for info in info_lst)
			score_lst = list(info['score'] for info in info_lst if info['depth'] > depth - 5)
			try:
				score = sum(score_lst) // len(score_lst)
			except TypeError:
				print(score_lst)
				continue
			scores.append((score, {'depth': depth, 'move': chess.Move.from_uci(move), 'avg': len(score_lst)}))
			if depth < min_depth:
				min_depth = depth
		return {i+1: info | {'score': fix_turn(chess.engine.PovScore(chess.engine.Cp(score), chess.WHITE))} for i, (score, info) in enumerate(sorted(scores, reverse=board.turn, key=itemgetter(0))) }

	# method currently multipv only!
	def new_analysis(self, board):
		self.analysis = {'moves': []}
		results = self.db.search(Query().multipv.exists() & (Query().fen == _partial_fen(board.fen())['fen']))
		if results:
			self.analysis = {'moves': results[0]['multipv'], 'depth': results[0]['depth']}
			for move in results[0]['multipv']:
				result = self.db.search(Query().info.exists() & (Query().fen == _partial_fen(_push(board, move).fen())['fen']))
				if result:
					self.analysis[move] = {'info': result[0]['info']}

	def put(self, board, variations):
		moves = {info['move'].uci(): info for info in variations.values()}
		for move in set(moves).difference(self.analysis['moves']):
			print("difference:", move, move in self.analysis)
			if not move in self.analysis:
				part_fen = _partial_fen(_push(board, move).fen())
				exist = self.db.search(Query().info.exists() & (Query().fen == part_fen['fen']))
				info_out = [{'score': moves[move]['score'].white().score(), 'depth': moves[move]['depth']}]
				if exist:
					self.analysis[move] = {'info': exist[0]['info']}
				else:
					self.db.insert({'info': info_out, 'move': move} | part_fen)
					self.analysis[move] = {'info': info_out, 'depth': moves[move]['depth']}

		changed = False
		for move, info_in in moves.items():
			fen = _push(board, move).fen()
			move_info = self.analysis[move]
			if not 'depth' in move_info or info_in['depth'] > move_info['depth']:
				move_info['depth'] = info_in['depth'] # depth of currently running analysis
				max_depth = max(info['depth'] for info in move_info['info']) # max depth including previous analyses
				if info_in['depth'] > max_depth - 5:
					# add new
					move_info['info'].append({'score': info_in['score'].white().score(), 'depth': info_in['depth']})
					if info_in['depth'] > max_depth:
						max_depth = info_in['depth']
					# throw out old
					move_info['info'] = [info for info in move_info['info'] if info['depth'] > max_depth - 5]
					self.db.update({'info': move_info['info']}, Query().info.exists() & (Query().fen == _partial_fen(fen)['fen']))
					changed = True

		min_depth = min(self.analysis[move]['depth'] for move in moves.keys())
		if not 'depth' in self.analysis:
			print("insert", {'multipv': list(moves.keys()), 'depth': min_depth} | _partial_fen(board.fen()))
			self.analysis['depth'] = min_depth
			self.db.insert({'multipv': list(moves.keys()), 'depth': min_depth} | _partial_fen(board.fen()))
			changed = True
		elif not set(self.analysis['moves']) == set(moves.keys()) and min_depth > self.analysis['depth']:
			print("update", {'multipv':  list(moves.keys()), 'depth': min_depth} | _partial_fen(board.fen()))
			self.db.update({'multipv': list(moves.keys()), 'depth': min_depth}, Query().multipv.exists() & (Query().fen == _partial_fen(board.fen())['fen']))
			changed = True
		self.analysis['moves'] = list(moves.keys())
		if changed:
			self.db.storage.flush()
