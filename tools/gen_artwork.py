"""
Génère le cover art podcast 3000x3000 pour "Briefing matinal".
"""

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SIZE = 3000
OUT = Path(__file__).parent.parent / "artwork.jpg"

BG_TOP    = (8, 16, 45)
BG_BOT    = (18, 42, 88)
GOLD      = (220, 170, 55)
WHITE     = (255, 255, 255)
WHITE_DIM = (195, 210, 235)
RAY_COL   = (255, 195, 70)


def gradient_bg(draw, size):
    for y in range(size):
        t = y / size
        r = int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b))


def draw_sunrise(draw, cx, cy):
    # Rayons en éventail au-dessus de l'horizon
    num_rays = 24
    max_len = 820
    for i in range(num_rays):
        angle = math.radians(-170 + i * (160 / (num_rays - 1)))
        x2 = cx + math.cos(angle) * max_len
        y2 = cy + math.sin(angle) * max_len
        alpha = int(35 + 20 * math.sin(i * math.pi / (num_rays - 1)))
        draw.line([(cx, cy), (x2, y2)], fill=(*RAY_COL, alpha), width=55)

    # Demi-cercle soleil
    r_sun = 280
    bbox = [cx - r_sun, cy - r_sun, cx + r_sun, cy + r_sun]
    draw.arc(bbox, start=180, end=360, fill=GOLD, width=22)

    # Remplissage demi-soleil (gradient faux via cercles concentriques)
    for rr in range(r_sun - 22, 0, -20):
        alpha = int(60 * (1 - rr / r_sun))
        b2 = [cx - rr, cy - rr, cx + rr, cy + rr]
        draw.arc(b2, start=180, end=360, fill=(*GOLD, alpha), width=20)

    # Ligne horizon
    draw.line([(cx - 580, cy), (cx + 580, cy)], fill=GOLD, width=10)

    # Ondes radio (petites, centrées sous le titre)
    for i, r in enumerate([110, 195, 280]):
        alpha = 130 - i * 35
        b3 = [cx - r, cy - r_sun - r, cx + r, cy - r_sun + r]
        draw.arc(b3, start=210, end=330, fill=(*WHITE, alpha), width=13 - i * 3)


def main():
    img = Image.new("RGBA", (SIZE, SIZE), BG_TOP)
    draw = ImageDraw.Draw(img, "RGBA")

    gradient_bg(draw, SIZE)

    cx = SIZE // 2
    # Horizon en bas des 2/3 — texte occupe le tiers supérieur
    horizon_y = int(SIZE * 0.73)

    draw_sunrise(draw, cx, horizon_y)

    try:
        font_title = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 340)
        font_sub   = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 155)
        font_tag   = ImageFont.truetype("C:/Windows/Fonts/arial.ttf",    85)
    except OSError:
        font_title = ImageFont.load_default()
        font_sub   = font_title
        font_tag   = font_title

    def centered(draw, text, font, y, color):
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((SIZE - w) / 2, y), text, font=font, fill=color)

    # Titres dans le tiers supérieur, bien au-dessus du soleil
    centered(draw, "BRIEFING", font_title, int(SIZE * 0.07), WHITE)
    centered(draw, "MATINAL",  font_title, int(SIZE * 0.21), GOLD)

    # Ligne décorative
    lw = 700
    bar_y = int(SIZE * 0.375)
    draw.rectangle([(cx - lw//2, bar_y), (cx + lw//2, bar_y + 10)], fill=GOLD)

    # Sous-titre
    centered(draw, "L'actualite en 12 minutes", font_sub, int(SIZE * 0.395), WHITE_DIM)

    # Tag bas de page
    centered(draw, "Francophone  •  Quebec  •  IA", font_tag, int(SIZE * 0.895), (*GOLD, 200))

    rgb = img.convert("RGB")
    rgb.save(OUT, "JPEG", quality=95)
    print(f"Artwork sauvegarde : {OUT}")


if __name__ == "__main__":
    main()
