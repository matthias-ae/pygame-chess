import pygame
import chess
import pgboard

pygame.init()
board = pgboard.Board()

screen = pygame.display.set_mode(board.size())
board.draw(screen)
pygame.display.flip()

running = True
while running:
	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			running = False

pygame.quit()
