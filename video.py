import pygame
import Z80

__show_fps__ = True

SCREEN_WIDTH = 256
SCREEN_HEIGHT = 192
FULL_SCREEN_WIDTH = 384
FULL_SCREEN_HEIGHT = 256
CAPTION = 'PyZX'

COLOR_ON_NORMAL = 205
COLOR_ON_BRIGHT = 255
COLORS = [
    (0, 0, 0),                                            # Black Bright Off
    (0, 0, COLOR_ON_NORMAL),                              # Blue Bright Off
    (COLOR_ON_NORMAL, 0, 0),                              # Red Bright Off
    (COLOR_ON_NORMAL, 0, COLOR_ON_NORMAL),                # Magenta Bright Off
    (0, COLOR_ON_NORMAL, 0),                              # Green Bright Off
    (0, COLOR_ON_NORMAL, COLOR_ON_NORMAL),                # Cyan Bright Off
    (COLOR_ON_NORMAL, COLOR_ON_NORMAL, 0),                # Yellow Bright Off
    (COLOR_ON_NORMAL, COLOR_ON_NORMAL, COLOR_ON_NORMAL),  # White Bright Off

    (0, 0, 0),                                            # Black Bright On
    (0, 0, COLOR_ON_BRIGHT),                              # Blue Bright On
    (COLOR_ON_BRIGHT, 0, 0),                              # Red Bright On
    (COLOR_ON_BRIGHT, 0, COLOR_ON_BRIGHT),                # Magenta Bright On
    (0, COLOR_ON_BRIGHT, 0),                              # Green Bright On
    (0, COLOR_ON_BRIGHT, COLOR_ON_BRIGHT),                # Cyan Bright On
    (COLOR_ON_BRIGHT, COLOR_ON_BRIGHT, 0),                # Yellow Bright On
    (COLOR_ON_BRIGHT, COLOR_ON_BRIGHT, COLOR_ON_BRIGHT)   # White Bright On
]

# Инициализация таблицы адресов пиксельных и аттрибутных линий
addr_attr = [(6144 + ((line // 8) * 32)) for line in range(192)]
zxrowmap = [((coord_y & 0b111) << 3) + ((coord_y & 0b111000) >> 3) + (coord_y & 0b11000000) for coord_y in range(192)]
colormap = [((attr % 8) + (8 if attr & 64 else 0), (attr & 0b1111000) >> 3) for attr in range(256)]


pixelmap = []
def init_pixelmap():
    for i in range(256):
        color_ink, color_paper = colormap[i]
        pixellist = []
        for pix in range(256):
            pixels = bytearray(8)
            for bit in range(8):
                pixels[7-bit] = color_ink if (pix & (1 << bit)) else color_paper
            pixellist.append(bytes(pixels))
        pixelmap.append(pixellist)


zx_screen = None
screen = None
ratio = 2
def init():
    global screen, zx_screen
    init_pixelmap()
    pygame.init()
    icon = pygame.image.load('icon.png')
    zx_screen = pygame.surface.Surface((FULL_SCREEN_WIDTH, FULL_SCREEN_HEIGHT), pygame.HWSURFACE, 8)
    zx_screen.set_palette(COLORS)
    screen = pygame.display.set_mode((FULL_SCREEN_WIDTH*ratio, FULL_SCREEN_HEIGHT*ratio), pygame.HWSURFACE | pygame.DOUBLEBUF, 8)
    pygame.display.set_palette(COLORS)
    pygame.display.set_caption(CAPTION)
    pygame.display.set_icon(icon)
    pygame.display.flip()
    return


clock = pygame.time.Clock()
old_border = -1
def update():
    global __show_fps__, clock, old_border
    if __show_fps__:
        clock.tick()
        pygame.display.set_caption(f'{CAPTION} - {clock.get_fps():.2f} FPS')
    if Z80.ports.current_border != old_border:
        zx_screen.fill(Z80.ports.current_border)
        old_border = Z80.ports.current_border
    fill_screen_map()
    pygame.transform.scale(zx_screen, (FULL_SCREEN_WIDTH*ratio, FULL_SCREEN_HEIGHT*ratio), screen)
    pygame.display.flip()


def fill_screen_map():
    zx_videoram = Z80.memory.mem[16384:16384+6912]
    byte_number = 0
    buffer = zx_screen.get_buffer()
    for coord_y in range(SCREEN_HEIGHT):
        zx_row = zxrowmap[coord_y]
        attr_addr = addr_attr[zx_row]
        pos = (zx_row+32) * FULL_SCREEN_WIDTH
        for i in range(0, 32):
            buffer.write(pixelmap[zx_videoram[attr_addr+i]][zx_videoram[byte_number]], pos+i*8+64)
            byte_number += 1
