import pygame
import chess
import chess.svg
import io

def _svg2image(svg):
	return pygame.image.load(io.BytesIO(str(svg).encode('utf-8')))

def _make_symbol(letter):
	return _svg2image(chess.svg.piece(chess.Piece.from_symbol(letter)))

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

class Board(chess.Board):
	def __init__(self, *args, **kwargs):
		super(Board, self).__init__(*args, **kwargs)
		self._symbol = {}
		for letter in 'kqrbnp':
			self._symbol[letter] = _make_symbol(letter)
			self._symbol[letter.upper()] = _make_symbol(letter.upper())
			self._symbol_size = Pt(*self._symbol[letter].get_size())
		self._empty_board = _svg2image(chess.svg.board())
		self._border = (Pt(*self._empty_board.get_size()) - 8 * self._symbol_size) // 2

	def draw(self, screen):
		screen.blit(self._empty_board, (0, 0))
		pos = Pt(0, 0)
		for c in str(self):
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
			return chess.parse_square('abcdefgh'[pos.x] + str(8-pos.y))
