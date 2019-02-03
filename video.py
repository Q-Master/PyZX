import pygame
import Z80

SCREEN_WIDTH = 256
SCREEN_HEIGHT = 192

color_on_normal = 205
color_on_bright = 255

colors = [(0, 0, 0),                                            # Black Bright Off
          (0, 0, color_on_normal),                              # Blue Bright Off
          (color_on_normal, 0, 0),                              # Red Bright Off
          (color_on_normal, 0, color_on_normal),                # Magenta Bright Off
          (0, color_on_normal, 0),                              # Green Bright Off
          (0, color_on_normal, color_on_normal),                # Cyan Bright Off
          (color_on_normal, color_on_normal, 0),                # Yellow Bright Off
          (color_on_normal, color_on_normal, color_on_normal),  # White Bright Off

          (0, 0, 0),                                            # Black Bright On
          (0, 0, color_on_bright),                              # Blue Bright On
          (color_on_bright, 0, 0),                              # Red Bright On
          (color_on_bright, 0, color_on_bright),                # Magenta Bright On
          (0, color_on_bright, 0),                              # Green Bright On
          (0, color_on_bright, color_on_bright),                # Cyan Bright On
          (color_on_bright, color_on_bright, 0),                # Yellow Bright On
          (color_on_bright, color_on_bright, color_on_bright)]  # White Bright On

colormap = [
    ((attr % 8) + (8 if attr > 127 else 0), (attr & 0b1111000) >> 3) for attr in range(256)
]

zxrowmap = [
    ((coord_y & 0b111) << 3) + ((coord_y & 0b111000) >> 3) + (coord_y & 0b11000000) for coord_y in range(192)
]

pixelmap = []
for i in range(256):
    color_ink, color_paper = colormap[i]
    pixellist = []
    for pix in range(256):
        pixels = bytearray(8)
        for bit in range(8):
            pixels[7-bit] = color_ink if (pix & (1 << bit)) else color_paper
        pixellist.append(bytes(pixels))
    pixelmap.append(pixellist)

def init():
    global screen
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), 0, 8)
    pygame.display.set_palette(colors)
    pygame.display.set_caption("ZX Spectrum")
    pygame.mouse.set_cursor((8, 8), (0, 0), (0,) * int(64 / 8), (0,) * int(64 / 8))  # Pygame trick, no visible cursor
    pygame.display.flip()
    return


def update():
    fill_screen_map()
    pygame.display.flip()


def fill_screen_map():
    zx_screen = Z80.memory.mem[16384:16384+6912]
    byte_number = 0
    buffer = screen.get_buffer()
    for coord_y in range(192):
        zx_row = zxrowmap[coord_y]
        pos = zx_row * 256
        for counter_x in range(0, 32):
            attr = zx_screen[0x1800 + zx_row // 8 * 32 + counter_x]
            offset = attr*256+zx_screen[byte_number]*8
            buffer.write(pixelmap[attr][zx_screen[byte_number]], pos+counter_x*8)
            byte_number += 1
