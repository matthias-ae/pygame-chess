import pygame
import chess
import chess.svg
import io

def _svg2image(svg):
	return pygame.image.load(io.BytesIO(str(svg).encode('utf-8')))

def _make_symbol(letter, size):
	return _svg2image(chess.svg.piece(chess.Piece.from_symbol(letter), size))

class Pt:
	def __init__(self, x, y):
		self.x = x
		self.y = y

	def __add__(self, other):
		return Pt(self.x + other.x, self.y + other.y)

	def __sub__(self, other):
		return Pt(self.x - other.x, self.y - other.y)

	def __mul__(self, other):
		return Pt(self.x * other.x, self.y * other.y)

	def __rmul__(self, fac):
		return Pt(fac * self.x, fac * self.y)

	def __floordiv__(self, denom):
		try:
			return Pt(self.x // denom.x, self.y // denom.y)
		except AttributeError:
			return Pt(self.x // denom, self.y // denom)

	def __iter__(self):
		yield self.x
		yield self.y

	def __str__(self):
		return "Pt(x=" + str(self.x) + ", y=" + str(self.y) + ")"

class Board:
	def __init__(self, piece_size=45):
		self.board = chess.Board()

		default_piece_size = Pt(*_svg2image(chess.svg.piece(chess.Piece.from_symbol('Q'))).get_size())
		default_border = (Pt(*_svg2image(chess.svg.board()).get_size()) - 8 * default_piece_size) // 2
		self._border = piece_size * default_border // default_piece_size
		self._symbol = {}
		for letter in 'kqrbnp':
			self._symbol[letter] = _make_symbol(letter, piece_size)
			self._symbol[letter.upper()] = _make_symbol(letter.upper(), piece_size)
			self._symbol_size = Pt(*self._symbol[letter].get_size())
		self._empty_board = _svg2image(chess.svg.board(size=8*piece_size+2*self._border.x))

		self._highlight = pygame.Surface(tuple(self._symbol_size))
		self._highlight.fill(pygame.Color(255, 255, 0))
		self._highlight.set_alpha(65)
		self._highlighted = []

	def __getattr__(self, attr):
		return getattr(self.board, attr)

	def draw(self, screen):
		screen.blit(self._empty_board, (0, 0))
		pos = Pt(0, 0)
		for square in self._highlighted:
			screen.blit(self._highlight, tuple(self._symbol_size * Pt(chess.square_file(square), 7-chess.square_rank(square)) + self._border))
		for c in str(self.board):
			if c == '\n':
				pos.y += 1
				pos.x = 0
			if c in self._symbol:
				screen.blit(self._symbol[c], tuple(self._symbol_size * pos + self._border))
			if c in self._symbol or c == '.':
				pos.x += 1

	def size(self):
		return self._empty_board.get_size()

	def select(self, cursor):
		pos = (Pt(*cursor) - self._border) // self._symbol_size
		if 0 <= pos.x < 8 and 0 <= pos.y < 8:
			return chess.square(pos.x, 7-pos.y)

	def highlight(self, squares):
		self._highlighted = squares
