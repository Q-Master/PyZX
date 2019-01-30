from PIL import Image
from PIL import ImagePalette

name = '.\\games\\Storm Lord.Sna'

f = open(name, 'rb')
f.seek(27)
buf = f.read(6912)

# background = Image.new("RGB", (w, h), (r, g, b))

# img = Image.new("RGB", (256, 192), (0, 0, 0))



# colorz = [(0, 0, 0),        # Black Bright Off
#           (0, 0, 192),      # Blue Bright Off
#           (192, 0, 0),      # Red Bright Off
#           (192, 0, 192),    # Magenta Bright Off
#           (0, 192, 0),      # Green Bright Off
#           (0, 192, 192),    # Cyan Bright Off
#           (192, 192, 0),    # Yellow Bright Off
#           (192, 192, 192),  # White Bright Off
#
#           (0, 0, 0),        # Black Bright On
#           (0, 0, 255),      # Blue Bright On
#           (255, 0, 0),      # Red Bright On
#           (255, 0, 255),    # Magenta Bright On
#           (0, 255, 0),      # Green Bright On
#           (0, 255, 255),    # Cyan Bright On
#           (255, 255, 0),    # Yellow Bright On
#           (255, 255, 255)]  # White Bright On

colors = [0, 0, 0,        # Black Bright Off
          0, 0, 192,      # Blue Bright Off
          192, 0, 0,      # Red Bright Off
          192, 0, 192,    # Magenta Bright Off
          0, 192, 0,      # Green Bright Off
          0, 192, 192,    # Cyan Bright Off
          192, 192, 0,    # Yellow Bright Off
          192, 192, 192,  # White Bright Off

          0, 0, 0,        # Black Bright On
          0, 0, 255,      # Blue Bright On
          255, 0, 0,      # Red Bright On
          255, 0, 255,    # Magenta Bright On
          0, 255, 0,      # Green Bright On
          0, 255, 255,    # Cyan Bright On
          255, 255, 0,    # Yellow Bright On
          255, 255, 255]  # White Bright On

img = Image.new("P", (256, 192), 0)

img.putpalette(colors, 'RGB')

pixels = img.load()



# colors = [0,        # Black Bright Off
#           1,      # Blue Bright Off
#           2,      # Red Bright Off
#           3,    # Magenta Bright Off
#           4,      # Green Bright Off
#           5,    # Cyan Bright Off
#           6,    # Yellow Bright Off
#           7,  # White Bright Off
#           8,        # Black Bright On
#           9,      # Blue Bright On
#           10,      # Red Bright On
#           11,    # Magenta Bright On
#           12,      # Green Bright On
#           13,    # Cyan Bright On
#           14,    # Yellow Bright On
#           15]  # White Bright On

# ImagePalette.ImagePalette("RGB", palette=colorz, size=16*3)

pix_num = 0
coord_y = 0

for counter_y in range(0, 192):

    zx_row = ((coord_y & 0b111) << 3) + ((coord_y & 0b111000) >> 3) + (coord_y & 0b11000000)

    for counter_x in range(0, 256, 8):

        attr_adr = 0x1800 + zx_row // 8 * 32 + counter_x // 8

        attr = buf[attr_adr]

        # color_ink = colors[(attr & 0b1111000) >> 3]
        # color_paper = colors[((attr & 0b1000000) >> 3) + (attr & 0b111)]

        color_ink = (attr & 0b1111000) >> 3
        color_paper = ((attr & 0b1000000) >> 3) + (attr & 0b111)


        pix_group = [0, 0, 0, 0, 0, 0, 0, 0]
        pix = buf[pix_num]

        if pix & 0b00000001:
            pix_group[7] = 1
        if pix & 0b00000010:
            pix_group[6] = 1
        if pix & 0b00000100:
            pix_group[5] = 1
        if pix & 0b00001000:
            pix_group[4] = 1
        if pix & 0b00010000:
            pix_group[3] = 1
        if pix & 0b00100000:
            pix_group[2] = 1
        if pix & 0b01000000:
            pix_group[1] = 1
        if pix & 0b10000000:
            pix_group[0] = 1

        coord_x = 0

        for pixt in pix_group:

            if pixt:
                pixels[counter_x + coord_x, zx_row] = color_paper
            else:
                pixels[counter_x + coord_x, zx_row] = color_ink
            coord_x += 1

        pix_num += 1

    coord_y += 1


# img.putpalette(colorz, 'RGB')
# a = img.getpalette()
# print(a)

# for j in range(192):
#     for i in range(256):
#         pixels[i, j] = i
#
#
#

img.save('zx-image.png')

img.show()
