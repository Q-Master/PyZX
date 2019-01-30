import time
import pygame
from pygame.locals import *

# SDL_WINDOWID="ggi"
pygame.init()

sx = int((320 - 256) / 2)
sy = int((200 - 192) / 2)

screen = pygame.display.set_mode((320, 200), HWSURFACE)  # |FULLSCREEN)
# screen_map = pygame.Surface((256, 192))


set_at = screen.set_at
# fill = screen_map.fill
color = (255, 0, 0)
time.sleep(3)

start = time.time()
for i in range(10):
    pygame.display.flip()
    # screen.blit(screen_map, (0, 0))
    for x in range(sx, sx + 256):
        for y in range(sy, sy + 192):
            set_at((x, y), color)
        # fill(color, (x,y,1,1))
end = time.time()
dt = end - start
print(dt)
