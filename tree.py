import chess

class Tree:
	def __init__(self, root, book):
		self.root = root
		self.book = book
		self.positions = {root: {}}

	def add_move(self, position, move): #, variation, score):
		board = chess.Board(position)
		board.push(move)
		self.positions[position][move.uci()] = None # = {'variation': variation, 'score': score}
		self.positions[board.fen()] = {}

	def next_best(self, min_move, max_move):
		dis_all = None
		for position in self.positions:
			board = chess.Board(position)
			halfmove = board.fullmove_number*2 - board.turn
			dis_next = self.positions[position]['dis_next']
			if min_move < halfmove <= max_move and (dis_all is None or dis_all > dis_next):
				dis_all = dis_next
				next = position, self.positions[position]['next']
		return next

	def update(self, position):
		self.book.new_analysis(chess.Board(position))
		variations = self.book.lookup(chess.Board(position))
		dis_next = None
		for v in sorted(variations):
			if not variations[v]['move'].uci() in self.positions[position]:
				dis = variations[1]['score'].relative.score() - variations[v]['score'].relative.score()
				if dis_next is None or dis_next > dis:
					dis_next = dis
					next = variations[v]['move']

		self.positions[position]['dis_next'] = dis_next
		self.positions[position]['next'] = next
