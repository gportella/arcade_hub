from PIL import Image, ImageDraw

SIZE = 64
BASE = (111, 169, 216)     # steel blue
OUT = (47, 75, 102)
PANEL = (86, 133, 175)
EYE = (255, 224, 122)
EYE_OUT = (120, 90, 30)

def make_robot(filename):
    img = Image.new("RGBA", (SIZE, SIZE), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Rounded square body
    d.rounded_rectangle((8, 8, 56, 56), radius=10, fill=BASE, outline=OUT, width=2)
    # Panel band
    d.rounded_rectangle((12, 30, 52, 40), radius=6, fill=PANEL, outline=OUT, width=1)
    # Eyes
    d.ellipse((18, 20, 28, 30), fill=EYE, outline=EYE_OUT, width=1)
    d.ellipse((36, 20, 46, 30), fill=EYE, outline=EYE_OUT, width=1)
    # Tiny antenna
    d.line((32, 8, 32, 2), fill=OUT, width=2)
    img.save(filename)

make_robot("robot_idle.png")
