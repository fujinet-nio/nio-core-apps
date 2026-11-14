#!/usr/bin/env python3
# Copyright (C) 2026 Andrew Diller
# SPDX-License-Identifier: GPL-3.0-or-later
"""Draw the demo's art: the FUJINET logo and the letter sprites from the Figtree font, and
the icon sprites from plain shapes, as ASCII art in art/*.txt.

The art files are what the build reads (tools/gen_gfx.py), so building the demo never needs
this script, its font or Pillow. Run it to redraw them; they can also be edited by hand.

    python3 tools/render_art.py [--font-dir DIR] [--preview out.png]

Figtree (https://github.com/erikdkennedy/figtree) is under the SIL Open Font License 1.1,
which lets it be used to make artwork like this. The script downloads the two files it uses
at a pinned commit into the repository's build/fonts (or --font-dir), and checks them against
the hashes below. Needs Pillow.
"""
import argparse
import hashlib
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

TOOLS = Path(__file__).resolve().parent
ART = TOOLS.parent / "art"
FONT_CACHE = TOOLS.parents[4] / "build" / "fonts"

FIGTREE = "https://raw.githubusercontent.com/erikdkennedy/figtree/032dfa7fe219ef3a02890d6d3add84eacc9aebfe/fonts/ttf/"
FONTS = {
    "Figtree-BlackItalic.ttf": "817222506620fd2ac8b850a3e5a3eee7f2a2946e18bbe51aa0acf887b050fabd",
    "Figtree-Black.ttf": "d32cf04815985f3cb0fa811236a1e130db44885ea981927a3237427320e851ef",
}
LOGO_FONT = "Figtree-BlackItalic.ttf"
SPRITE_FONT = "Figtree-Black.ttf"
SS = 8  # supersampling


def font_file(name, font_dir):
    """The pinned font, downloaded once; refuses a file that isn't the one pinned."""
    path = font_dir / name
    if not path.exists():
        font_dir.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(FIGTREE + name) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != FONTS[name]:
            raise SystemExit(f"render_art: {FIGTREE + name} is not the pinned font")
        path.write_bytes(data)
    if hashlib.sha256(path.read_bytes()).hexdigest() != FONTS[name]:
        raise SystemExit(f"render_art: {path} is not the pinned font; delete it to download it again")
    return str(path)


def render(text, cap_height, font_path, spacing=0.0):
    """Render text so its capital letters are exactly cap_height pixels tall."""
    size = cap_height * SS * 1.45
    for _ in range(30):  # find the size whose cap height matches
        font = ImageFont.truetype(font_path, int(size))
        box = font.getbbox("H")
        h = box[3] - box[1]
        size *= cap_height * SS / h
    font = ImageFont.truetype(font_path, int(size))
    top = font.getbbox("H")[1]
    width = int(sum(font.getlength(c) for c in text) + spacing * SS * len(text)) + 40 * SS
    img = Image.new("L", (width, cap_height * SS), 0)
    draw = ImageDraw.Draw(img)
    x = 4 * SS
    for c in text:
        draw.text((x, -top), c, font=font, fill=255)
        x += font.getlength(c) + spacing * SS
    small = img.resize((width // SS, cap_height), Image.BOX)
    bits = [[1 if small.getpixel((x, y)) >= 128 else 0 for x in range(small.width)]
            for y in range(cap_height)]
    # trim empty columns
    cols = [x for x in range(small.width) if any(row[x] for row in bits)]
    lo, hi = min(cols), max(cols)
    return [row[lo:hi + 1] for row in bits]


def draw_icons():
    """Simple 24x21 icons drawn with PIL primitives at 8x, then thresholded."""
    S = SS
    def canvas():
        img = Image.new("L", (24 * S, 21 * S), 0)
        return img, ImageDraw.Draw(img)
    def px(v):
        return [c * S for c in v]
    def done(img):
        small = img.resize((24, 21), Image.BOX)
        return [[1 if small.getpixel((x, y)) >= 128 else 0 for x in range(24)] for y in range(21)]
    icons = []

    img, d = canvas()  # floppy disk
    d.rectangle(px((1, 0, 22.99, 20.99)), fill=255)
    d.polygon(px((19, 0, 23, 4, 23, 0)), fill=0)  # clipped corner
    d.rectangle(px((5, 0, 17.99, 6.99)), fill=0)  # shutter recess
    d.rectangle(px((6, 0, 16.99, 5.99)), fill=255)
    d.rectangle(px((12, 1, 14.99, 4.99)), fill=0)  # shutter window
    d.rectangle(px((4, 10, 19.99, 20.99)), fill=0)  # label
    for y in (12, 15, 18):
        d.rectangle(px((6, y, 17.99, y + 0.99)), fill=255)
    icons.append(("floppy", done(img)))

    img, d = canvas()  # wifi
    cx, cy = 12 * S, 20 * S
    for r in (20, 13.5, 7):
        d.pieslice((cx - r * S, cy - r * S, cx + r * S, cy + r * S), 222, 318, fill=255)
        q = r - 3.5
        d.pieslice((cx - q * S, cy - q * S, cx + q * S, cy + q * S), 200, 340, fill=0)
    d.rectangle(px((0, 20.5, 24, 21)), fill=0)
    d.ellipse(px((9.5, 15.5, 14.5, 20.5)), fill=255)
    icons.append(("wifi", done(img)))

    img, d = canvas()  # globe
    d.ellipse(px((1.5, 0, 22.5, 21)), fill=255)
    d.ellipse(px((3.5, 2, 20.5, 19)), fill=0)
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).ellipse(px((3.5, 2, 20.5, 19)), fill=255)
    lines = Image.new("L", img.size, 0)
    l = ImageDraw.Draw(lines)
    l.ellipse(px((7.5, 0, 16.5, 21)), outline=255, width=int(1.6 * S))
    l.rectangle(px((11, 0, 13, 21)), fill=255)
    for y in (5.2, 9.7, 14.6):
        l.rectangle(px((0, y, 24, y + 1.6)), fill=255)
    img.paste(lines, (0, 0), mask)
    icons.append(("globe", done(img)))

    img, d = canvas()  # cloud
    d.ellipse(px((1, 8, 11, 18)), fill=255)
    d.ellipse(px((5, 2, 17, 14)), fill=255)
    d.ellipse(px((12, 6, 22, 16)), fill=255)
    d.ellipse(px((15, 10, 23.5, 18)), fill=255)
    d.rectangle(px((6, 12, 19, 18)), fill=255)
    icons.append(("cloud", done(img)))

    img, d = canvas()  # heart
    d.ellipse(px((1, 1, 13, 13)), fill=255)
    d.ellipse(px((11, 1, 23, 13)), fill=255)
    d.polygon(px((1.6, 9, 22.4, 9, 12, 20.5)), fill=255)
    d.ellipse(px((4, 4, 7, 7)), fill=0)  # shine
    icons.append(("heart", done(img)))

    img, d = canvas()  # beamed eighth notes
    d.ellipse(px((1, 14, 9, 20.5)), fill=255)
    d.ellipse(px((13, 12, 21, 18.5)), fill=255)
    d.rectangle(px((7, 3, 8.99, 17)), fill=255)
    d.rectangle(px((19, 1, 20.99, 15)), fill=255)
    d.polygon(px((7, 3, 21, 0, 21, 4, 7, 7)), fill=255)
    icons.append(("note", done(img)))

    img, d = canvas()  # joystick
    d.rounded_rectangle(px((1, 14, 23, 20.9)), radius=2 * S, fill=255)
    d.rectangle(px((10.5, 6, 13.5, 15)), fill=255)
    d.ellipse(px((7, 0, 17, 9)), fill=255)
    d.ellipse(px((9, 2, 12, 5)), fill=0)
    d.ellipse(px((3, 11.5, 7, 14.5)), fill=255)  # fire button
    icons.append(("joystick", done(img)))

    img, d = canvas()  # pocket phone
    d.rounded_rectangle(px((6, 0, 18, 20.9)), radius=3 * S, fill=255)
    d.rectangle(px((8, 3, 15.99, 16.99)), fill=0)
    d.rectangle(px((10, 1, 13.99, 1.99)), fill=0)  # speaker
    d.ellipse(px((10.5, 17.6, 13.5, 20.4)), fill=0)  # button
    d.rectangle(px((9, 6, 14.99, 7.99)), fill=255)   # tiny on-screen stripes
    d.rectangle(px((9, 9, 12.99, 10.99)), fill=255)
    d.rectangle(px((9, 12, 14.99, 13.99)), fill=255)
    icons.append(("phone", done(img)))
    return icons


def to_text(bits):
    return "\n".join("".join("#" if b else "." for b in row) for row in bits)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--font-dir", type=Path, default=FONT_CACHE,
                    help="where the pinned Figtree files are, or are downloaded to (default: build/fonts)")
    ap.add_argument("--preview", help="also write a PNG of everything drawn")
    args = ap.parse_args()

    logo = render("FUJINET", 40, font_file(LOGO_FONT, args.font_dir), spacing=1.5)
    assert len(logo[0]) <= 320, len(logo[0])
    (ART / "logo.txt").write_text(to_text(logo) + "\n")
    print("logo", len(logo[0]), "x", len(logo))

    letters = []
    sprite_font = font_file(SPRITE_FONT, args.font_dir)
    for c in "FUJINET":
        bits = render(c, 21, sprite_font)
        w = len(bits[0])
        assert w <= 24, (c, w)
        pad = (24 - w) // 2
        letters.append((c, [[0] * pad + row + [0] * (24 - w - pad) for row in bits]))
    with open(ART / "letters.txt", "w") as f:
        for c, bits in letters:
            f.write(f"= {c}\n{to_text(bits)}\n")

    icons = draw_icons()
    with open(ART / "icons.txt", "w") as f:
        for name, bits in icons:
            f.write(f"= {name}\n{to_text(bits)}\n")

    if args.preview:
        scale = 4
        img = Image.new("RGB", (len(logo[0]) * scale, (len(logo) + 52) * scale), (0, 0, 40))
        for y, row in enumerate(logo):
            for x, b in enumerate(row):
                if b and (y % 8) != 7:
                    img.paste((255, 180, 0), (x * scale, y * scale, (x + 1) * scale, (y + 1) * scale))
        for i, (c, bits) in enumerate(letters):
            for y, row in enumerate(bits):
                for x, b in enumerate(row):
                    if b:
                        X, Y = i * 28 + x, 44 + y
                        img.paste((120, 220, 255), (X * scale, Y * scale, (X + 1) * scale, (Y + 1) * scale))
        for i, (name, bits) in enumerate(icons):
            for y, row in enumerate(bits):
                for x, b in enumerate(row):
                    if b:
                        X, Y = i * 28 + x, 68 + y
                        img.paste((255, 255, 255), (X * scale, Y * scale, (X + 1) * scale, (Y + 1) * scale))
        img.save(args.preview)


if __name__ == "__main__":
    main()
