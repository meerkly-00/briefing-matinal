"""
Génère le cover art podcast 3000x3000 pour "Éco & Tech".
Thème : vert foncé / émeraude, ligne de marché, typographie financière.
"""

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SIZE = 3000
OUT = Path(__file__).parent.parent / "artwork_eco.jpg"

BG_TOP    = (5, 18, 12)
BG_BOT    = (10, 38, 28)
GREEN     = (0, 200, 120)
GREEN_DIM = (0, 150, 90)
WHITE     = (255, 255, 255)
WHITE_DIM = (190, 220, 205)
GOLD      = (200, 175, 60)


def gradient_bg(draw, size):
    for y in range(size):
        t = y / size
        r = int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b))


def draw_chart_line(draw, base_y, width, amplitude=110, periods=3.2, line_w=16):
    """Ligne de marché sinusoïdale avec tendance haussière."""
    points = []
    steps = 400
    trend = 90  # montée globale sur toute la largeur
    x_start = int(SIZE * 0.08)
    x_end   = int(SIZE * 0.92)
    span    = x_end - x_start
    for i in range(steps + 1):
        t = i / steps
        x = x_start + int(t * span)
        wave = math.sin(t * math.pi * 2 * periods - math.pi / 2) * amplitude
        y = base_y - int(trend * t) - int(wave)
        points.append((x, y))

    # Remplissage sous la courbe (gradient vert translucide)
    fill_pts = [(x_start, base_y + 60)] + points + [(x_end, base_y + 60)]
    draw.polygon(fill_pts, fill=(*GREEN, 18))

    # Ligne principale
    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill=(*GREEN, 210), width=line_w)

    # Point final (dernier prix)
    lx, ly = points[-1]
    r = 28
    draw.ellipse([lx - r, ly - r, lx + r, ly + r], fill=GREEN)
    draw.ellipse([lx - r + 6, ly - r + 6, lx + r - 6, ly + r - 6], fill=BG_BOT)


def draw_grid(draw):
    """Grille horizontale discrète style terminal financier."""
    for i in range(5):
        y = int(SIZE * (0.52 + i * 0.06))
        draw.line([(int(SIZE*0.08), y), (int(SIZE*0.92), y)],
                  fill=(*GREEN, 22), width=2)


def main():
    img = Image.new("RGBA", (SIZE, SIZE), BG_TOP)
    draw = ImageDraw.Draw(img, "RGBA")

    gradient_bg(draw, SIZE)
    draw_grid(draw)

    chart_y = int(SIZE * 0.75)
    draw_chart_line(draw, chart_y, SIZE, amplitude=95, periods=3.0)

    # Ligne de base du graphique
    draw.line([(int(SIZE*0.08), chart_y + 60), (int(SIZE*0.92), chart_y + 60)],
              fill=(*GREEN_DIM, 80), width=4)

    try:
        font_title = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 300)
        font_sub1  = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 185)
        font_sub2  = ImageFont.truetype("C:/Windows/Fonts/arial.ttf",   130)
        font_tag   = ImageFont.truetype("C:/Windows/Fonts/arial.ttf",    85)
    except OSError:
        font_title = ImageFont.load_default()
        font_sub1 = font_sub2 = font_tag = font_title

    def centered(draw, text, font, y, color):
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((SIZE - w) / 2, y), text, font=font, fill=color)

    centered(draw, "ECO",      font_title, int(SIZE * 0.07), WHITE)
    centered(draw, "&",        font_sub1,  int(SIZE * 0.21), (*GREEN, 230))
    centered(draw, "TECH",     font_title, int(SIZE * 0.29), WHITE)

    # Ligne décorative
    lw = 660
    bar_y = int(SIZE * 0.435)
    draw.rectangle([(SIZE//2 - lw//2, bar_y), (SIZE//2 + lw//2, bar_y + 10)],
                   fill=GREEN)

    centered(draw, "L'actualite en 12 minutes", font_sub2, int(SIZE * 0.452), WHITE_DIM)
    centered(draw, "Marchés  •  Crypto  •  Tech", font_tag, int(SIZE * 0.895), (*GREEN, 200))

    rgb = img.convert("RGB")
    rgb.save(OUT, "JPEG", quality=95)
    print(f"Artwork eco sauvegarde : {OUT}")


if __name__ == "__main__":
    main()
