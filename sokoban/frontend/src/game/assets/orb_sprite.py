from PIL import Image, ImageDraw, ImageFilter
import math

SIZE = 64

# Palette
BASE = (246, 200, 76)    # warm gold
SHADOW = (200, 143, 42)  # darker gold
HIGHLIGHT = (255, 242, 179)
OUTLINE = (58, 42, 18)   # soft brown
SPARKLE_A = (152, 224, 255)
SPARKLE_B = (255, 216, 240)
FACE_EYE = (45, 45, 45)

def radial_gradient(size, inner, outer, center=(0.35, 0.35)):
    """Create radial gradient circle as separate image."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    cx, cy = int(size * center[0]), int(size * center[1])
    rmax = size // 2 - 2
    for y in range(size):
      for x in range(size):
        dx, dy = x - cx, y - cy
        d = math.sqrt(dx*dx + dy*dy) / rmax
        t = max(0, min(1, d))
        # linear mix inner->outer
        r = int(inner[0]*(1-t) + outer[0]*t)
        g = int(inner[1]*(1-t) + outer[1]*t)
        b = int(inner[2]*(1-t) + outer[2]*t)
        # alpha mask for circle
        if d <= 1.0:
            px[x, y] = (r, g, b, 255)
    return img

def draw_orb(draw, cx, cy, r, fill=BASE, outline=OUTLINE, outline_w=2):
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=fill, outline=outline, width=outline_w)

def draw_star(draw, cx, cy, r, color=OUTLINE, rotate_deg=0):
    # simple 4-point star (diamond + small cross)
    def rot(x, y, a):
        s, c = math.sin(a), math.cos(a)
        return (x*c - y*s, x*s + y*c)
    a = math.radians(rotate_deg)
    pts = []
    for dx, dy in [(0, -r), (r*0.7, 0), (0, r), (-r*0.7, 0)]:
        rx, ry = rot(dx, dy, a)
        pts.append((cx+rx, cy+ry))
    draw.polygon(pts, fill=color)

def draw_face(draw, cx, cy):
    # tiny neutral face
    eye_r = 2
    draw.ellipse((cx-8-eye_r, cy-2-eye_r, cx-8+eye_r, cy-2+eye_r), fill=FACE_EYE)
    draw.ellipse((cx+8-eye_r, cy-2-eye_r, cx+8+eye_r, cy-2+eye_r), fill=FACE_EYE)
    # small mouth
    draw.arc((cx-6, cy+4, cx+6, cy+10), start=0, end=180, fill=FACE_EYE, width=1)

def add_sparkles(img, n=6):
    d = ImageDraw.Draw(img)
    import random
    for _ in range(n):
        x = random.randint(6, SIZE-6)
        y = random.randint(6, SIZE-6)
        c = SPARKLE_A if _ % 2 == 0 else SPARKLE_B
        d.line((x-2, y, x+2, y), fill=c, width=1)
        d.line((x, y-2, x, y+2), fill=c, width=1)

def make_idle():
    img = Image.new("RGBA", (SIZE, SIZE), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    cx, cy, r = SIZE//2, SIZE//2, 26

    # base orb
    draw_orb(draw, cx, cy, r, fill=BASE)
    # inner gradient highlight
    grad = radial_gradient(SIZE, HIGHLIGHT, SHADOW, center=(0.38, 0.35)).filter(ImageFilter.GaussianBlur(1))
    img = Image.alpha_composite(img, grad)
    # star motif
    draw_star(draw, cx, cy, 10, color=OUTLINE, rotate_deg=0)
    # face optional
    draw_face(draw, cx, cy)
    return img

def make_push():
    img = Image.new("RGBA", (SIZE, SIZE), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    cx, cy = SIZE//2, SIZE//2
    # squash/stretch
    rx, ry = 27, 24
    draw.ellipse((cx-rx, cy-ry, cx+rx, cy+ry), fill=BASE, outline=OUTLINE, width=2)
    grad = radial_gradient(SIZE, (255, 228, 135), SHADOW, center=(0.45, 0.40)).filter(ImageFilter.GaussianBlur(1))
    img = Image.alpha_composite(img, grad)
    # star rotated slightly
    draw_star(draw, cx, cy, 10, color=OUTLINE, rotate_deg=6)
    # small leading highlight streak (to the right)
    d2 = ImageDraw.Draw(img)
    d2.pieslice((cx+8, cy-8, cx+24, cy+8), start=300, end=60, fill=(255, 255, 255, 60))
    # face
    draw_face(draw, cx, cy)
    return img

def make_goal():
    img = Image.new("RGBA", (SIZE, SIZE), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    cx, cy, r = SIZE//2, SIZE//2, 26
    draw_orb(draw, cx, cy, r, fill=(250, 210, 100))
    grad = radial_gradient(SIZE, (255, 245, 200), SHADOW, center=(0.35, 0.33)).filter(ImageFilter.GaussianBlur(1))
    img = Image.alpha_composite(img, grad)
    draw_star(draw, cx, cy, 10, color=OUTLINE, rotate_deg=0)
    draw_face(draw, cx, cy)
    add_sparkles(img, n=8)
    return img

if __name__ == "__main__":
    idle = make_idle(); idle.save("star_orb_idle.png")
    push = make_push(); push.save("star_orb_push.png")
    goal = make_goal(); goal.save("star_orb_goal.png")
    print("Saved: star_orb_idle.png, star_orb_push.png, star_orb_goal.png")
