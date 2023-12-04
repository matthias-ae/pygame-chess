import chess
from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage
from tinydb.middlewares import CachingMiddleware

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
