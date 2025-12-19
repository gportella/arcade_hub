from PIL import Image, ImageDraw

SIZE = 64
BASE = (54, 193, 176)   # teal
MID = (36, 145, 132)
DARK = (26, 110, 100)
OUT = (22, 78, 72)
SPEC = (240, 255, 250)

def make_gem(filename):
    img = Image.new("RGBA", (SIZE, SIZE), (0,0,0,0))
    d = ImageDraw.Draw(img)
    cx, cy = SIZE//2, SIZE//2
    # Faceted diamond
    top = (cx, cy-20); right = (cx+16, cy); bottom = (cx, cy+20); left = (cx-16, cy)
    # Outline
    d.polygon([top, right, bottom, left], outline=OUT, fill=BASE)
    # Facets: split diagonals
    d.polygon([top, (cx+4, cy-6), (cx, cy), (cx-4, cy-6)], fill=MID)    # upper facet
    d.polygon([(cx, cy), (cx+6, cy+8), bottom, (cx-6, cy+8)], fill=DARK) # lower facet
    # Spec highlight
    d.ellipse((cx-10, cy-14, cx-6, cy-10), fill=SPEC)
    img.save(filename)

make_gem("gem_idle.png")
