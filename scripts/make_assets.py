#!/usr/bin/env python3
"""Draws every image of the profile README in the look of Teul's interface.

Run from the repository root:  python3 scripts/make_assets.py
Needs Pillow, numpy and fontTools. Inputs: fonts/ (OFL fonts) and assets/src/ (Teul title-screen captures made
with scripts/capture_teul.mjs, and screenshots/figures from each project's own repository). Output: assets/*.png.

Pixel art is only ever scaled by whole numbers with nearest-neighbour. The pixel fonts (Pixelify Sans, Tiny5) are
not rasterised by FreeType: each glyph is sampled on its own design grid, so every letter is made of whole, equal
pixels. Body text (Nunito) is ordinary anti-aliased text.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from fontTools.pens.pointInsidePen import PointInsidePen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "fonts"
SRC = ROOT / "assets" / "src"
OUT = ROOT / "assets"

# ---- Teul's interface palette (app/src/style.css) ---------------------------------------------------------------
INK = (244, 238, 223)        # --ink
MUTED = (163, 168, 207)      # --muted
DIM = (108, 113, 153)        # --dim
AMBER = (246, 179, 71)       # --amber
AMBER_INK = (58, 30, 8)      # --amber-ink
CREAM = (255, 231, 176)      # .title-name colour
TEAL = (79, 209, 184)        # --teal
ROSE = (239, 111, 138)       # --rose
LINE = (11, 12, 24)          # --line / outline --fo
# framed boxes: fill, light edge (top-left), dark edge (bottom-right), outline
PANEL = dict(f=(35, 38, 74), fl=(58, 63, 114), fd=(22, 24, 47), fo=LINE)        # .settings-card / .dlg-card
CARD = dict(f=(42, 45, 85), fl=(65, 70, 126), fd=(27, 29, 58), fo=LINE)         # .card
CHIP = dict(f=(45, 49, 96), fl=(71, 77, 138), fd=(29, 32, 66), fo=LINE)         # .chip
GOLD = dict(f=(246, 179, 71), fl=(255, 224, 160), fd=(196, 122, 34), fo=AMBER_INK)  # .cta
MUTE_BTN = dict(f=(58, 63, 114), fl=(90, 97, 166), fd=(38, 42, 82), fo=LINE)     # .cta.muted
TEAL_BTN = dict(f=(63, 191, 166), fl=(143, 240, 220), fd=(34, 128, 110), fo=(10, 42, 36))  # .cta.secondary
STAGE = dict(f=(20, 22, 44), fl=LINE, fd=(45, 49, 96), fo=LINE)                  # .preview-stage (sunken)
DROP = (4, 4, 12, 140)       # --drop: 0 4px 0 rgba(4,4,12,.55)


# ---- pixel fonts sampled on their design grid -------------------------------------------------------------------
class PixelFont:
    """A pixel font read cell by cell: `pitch` font units per design pixel, cell (0, 0) at (`x0`, `y0`)."""

    def __init__(self, path: Path, pitch: float, x0: float, y0: float, rows: tuple[int, int]):
        self.font = TTFont(path)
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.hmtx = self.font["hmtx"]
        self.pitch, self.x0, self.y0 = pitch, x0, y0
        self.lo, self.hi = rows  # design rows below / above the baseline row 0
        self.cache: dict[str, tuple[np.ndarray, int]] = {}

    def glyph(self, ch: str) -> tuple[np.ndarray, int]:
        if ch in self.cache:
            return self.cache[ch]
        name = self.cmap.get(ord(ch)) or self.cmap.get(ord("?"))
        adv = self.hmtx[name][0]
        cols = max(1, int(adv // self.pitch))
        rows = self.hi - self.lo
        bm = np.zeros((rows, cols + 1), bool)
        g = self.glyphs[name]
        for r in range(rows):
            k = self.hi - 1 - r  # design row index, counted up from the baseline row
            cy = self.y0 + (k + 0.5) * self.pitch
            for c in range(cols + 1):
                cx = self.x0 + (c + 0.5) * self.pitch
                pen = PointInsidePen(self.glyphs, (cx, cy))
                g.draw(pen)
                bm[r, c] = pen.getResult()
        self.cache[ch] = (bm, cols)
        return bm, cols

    def bitmap(self, text: str, spacing: int = 0) -> np.ndarray:
        parts, x = [], 0
        for ch in text:
            bm, adv = self.glyph(ch)
            parts.append((x, bm))
            x += adv + spacing
        w = max([x] + [px + bm.shape[1] for px, bm in parts])
        out = np.zeros((self.hi - self.lo, w), bool)
        for px, bm in parts:
            out[:, px:px + bm.shape[1]] |= bm
        # trim empty right edge
        used = np.where(out.any(0))[0]
        return out[:, : (used[-1] + 1 if len(used) else 1)]

    @property
    def cap_row(self) -> int:
        """Row in the bitmap where cap height begins (the top row of a capital)."""
        return 0

    def width(self, text: str, s: int, spacing: int = 0) -> int:
        return self.bitmap(text, spacing).shape[1] * s


# Pixelify Sans: ~91 units per design pixel, cells start at x=60, the baseline row starts at y=-12; capitals are
# 7 rows tall, descenders 2. Tiny5: an exact 128-unit grid from the origin; capitals 5 rows, descenders 1.
PIXELIFY = PixelFont(FONTS / "PixelifySans-Regular.ttf", 91.0, 60.0, -12.0, (-2, 7))
TINY = PixelFont(FONTS / "Tiny5-Regular.ttf", 128.0, 0.0, 0.0, (-1, 5))


def nunito(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / ("Nunito-Bold.ttf" if bold else "Nunito-Regular.ttf")), size)


def blit_bits(img: Image.Image, bm: np.ndarray, x: int, y: int, s: int, color) -> None:
    """Paints a bitmap with s×s image pixels per design pixel; (x, y) is the top-left of the bitmap."""
    h, w = bm.shape
    mask = Image.fromarray((bm * 255).astype(np.uint8), "L").resize((w * s, h * s), Image.NEAREST)
    img.paste(Image.new(img.mode, mask.size, color if len(color) == len(img.mode) else (*color, 255)), (x, y), mask)


def pixel_text(img, x, y, text, font: PixelFont, s: int, color, shadows=(), spacing=0) -> int:
    """Draws pixel text whose capitals start at y (top) and returns its width. Shadows: (dx, dy, color) in design px."""
    bm = font.bitmap(text, spacing)
    for dx, dy, c in shadows:
        blit_bits(img, bm, x + dx * s, y + dy * s, s, c)
    blit_bits(img, bm, x, y, s, color)
    return bm.shape[1] * s


def text_height(font: PixelFont, s: int) -> int:
    """Height of capitals only (the bitmap also carries descender rows below)."""
    return font.hi * s


# ---- Teul's framed boxes ----------------------------------------------------------------------------------------
def frame(d: ImageDraw.ImageDraw, x, y, w, h, u, pal, outline=True) -> None:
    """A box as Teul draws it: an outline `u` wide on each side (corners left open, so it looks rounded in pixels),
    a light edge along the top and left inside, a dark one along the bottom and right."""
    if outline:
        d.rectangle([x, y - u, x + w - 1, y - 1], fill=pal["fo"])
        d.rectangle([x, y + h, x + w - 1, y + h + u - 1], fill=pal["fo"])
        d.rectangle([x - u, y, x - 1, y + h - 1], fill=pal["fo"])
        d.rectangle([x + w, y, x + w + u - 1, y + h - 1], fill=pal["fo"])
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=pal["f"])
    d.rectangle([x, y + h - u, x + w - 1, y + h - 1], fill=pal["fd"])
    d.rectangle([x + w - u, y, x + w - 1, y + h - 1], fill=pal["fd"])
    d.rectangle([x, y, x + w - 1, y + u - 1], fill=pal["fl"])
    d.rectangle([x, y, x + u - 1, y + h - 1], fill=pal["fl"])


def drop(d: ImageDraw.ImageDraw, x, y, w, h, u, dy) -> None:
    """The flat drop shadow under raised things (Teul's --drop), the same open-cornered shape as the outline."""
    d.rectangle([x, y + h + u, x + w - 1, y + h + u + dy - 1], fill=DROP)
    d.rectangle([x - u, y + dy, x - 1, y + h + dy - 1], fill=DROP)
    d.rectangle([x + w, y + dy, x + w + u - 1, y + h + dy - 1], fill=DROP)


def cover(im: Image.Image, w: int, h: int, focus=(0.5, 0.5), resample=Image.LANCZOS) -> Image.Image:
    """Scales and crops to fill w×h, keeping the focus point (fractions of the source) in view."""
    sc = max(w / im.width, h / im.height)
    nw, nh = math.ceil(im.width * sc), math.ceil(im.height * sc)
    im = im.resize((nw, nh), resample)
    left = min(max(0, int(focus[0] * nw - w / 2)), nw - w)
    top = min(max(0, int(focus[1] * nh - h / 2)), nh - h)
    return im.crop((left, top, left + w, top + h))


def save(img: Image.Image, name: str) -> None:
    path = OUT / name
    if img.mode == "RGBA":
        # a palette PNG is several times smaller; these images have few colours
        q = img.quantize(colors=256, method=Image.FASTOCTREE, dither=Image.NONE)
        q.save(path, optimize=True)
        test = q.convert("RGBA")
        err = np.abs(np.asarray(test, int) - np.asarray(img, int)).max()
        if err > 40:  # photos inside cards: keep them truecolour
            img.save(path, optimize=True)
    else:
        img.save(path, optimize=True)
    print(f"{name:28s} {img.width}×{img.height}  {path.stat().st_size / 1024:6.1f} KB")


# ---- hero banner -----------------------------------------------------------------------------------------------
HEADLINE = ["Offline-first software", "for when it matters"]
SUBLINES = [("search & rescue vision · offline knowledge", None), ("cozy games", "— built in Ukraine")]


def hero() -> None:
    S = 3  # the title screen draws its town 3× on a 450-px-tall screen; the banner keeps that scale
    scene = Image.open(SRC / "teul-title-dusk-autumn.png").convert("RGB")  # 427×150 native pixels
    img = scene.resize((scene.width * S, scene.height * S), Image.NEAREST).crop((0, 0, 1280, 450)).convert("RGBA")
    x, y, s = 72, 44, 5
    for line in HEADLINE:
        # Teul's title: cream letters standing on an amber step and a dark one
        pixel_text(img, x, y, line, PIXELIFY, s, CREAM, shadows=[(0, 2, AMBER_INK), (0, 1, (196, 122, 34))], spacing=1)
        y += 13 * s
    y += 4
    s2 = 3
    for first, second in SUBLINES:
        w = pixel_text(img, x, y, first.upper(), TINY, s2, INK, shadows=[(0, 1, LINE)], spacing=1)
        if second:
            pixel_text(img, x + w + 4 * s2, y, second.upper(), TINY, s2, AMBER, shadows=[(0, 1, LINE)], spacing=1)
        y += 9 * s2
    save(img.convert("RGB"), "hero.png")


# ---- project cards ---------------------------------------------------------------------------------------------
K = 2            # image pixels per layout pixel (cards are shown 410 px wide, drawn 820 px wide)
U = 2 * K        # Teul's border unit (--u: 2px)
CW = 410 * K     # card width (image px), including the outline
PAD = 12 * K
THUMB_H = 124 * K


def thumb(name: str) -> Image.Image:
    """The picture at the top of each card, already sized to the sunken frame's inside."""
    w, h = CW - 2 * U - 2 * PAD - 2 * U, THUMB_H - 2 * U
    if name == "teul":
        # 1:1 crop of a real game screenshot (the market square), pixel for pixel; then 1× in a 2×-drawn card
        im = Image.open(SRC / "teul-square.png").convert("RGB")
        cx, cy = 640, 470
        return im.crop((cx - w // 2, cy - h // 2, cx - w // 2 + w, cy - h // 2 + h))
    if name == "hae":
        im = Image.open(SRC / "hae-hero.jpg").convert("RGB")
        cx, cy = 430, 520  # the group of people in the middle of the frame, 1:1
        return im.crop((cx - w // 2, cy - h // 2, cx - w // 2 + w, cy - h // 2 + h))
    if name == "dal":
        im = Image.open(SRC / "dal-hero-still.jpg").convert("RGB")
        return cover(im, w, h, (0.5, 0.42))
    if name == "byeol":
        # the left panel of the README figure, turned into a dark plot so it sits in the card
        im = Image.open(SRC / "byeol-overview.png").convert("RGB")
        left = im.crop((int(im.width * 0.095), int(im.height * 0.17), int(im.width * 0.53), int(im.height * 0.70)))
        inv = ImageOps.invert(left)
        hsv = np.asarray(inv.convert("HSV")).copy()
        hsv[..., 0] = (hsv[..., 0].astype(int) + 128) % 256  # invert lightness, keep the hues
        dark = Image.fromarray(hsv, "HSV").convert("RGB")
        # map pure black (the old white) onto the stage colour
        arr = np.asarray(dark).astype(float)
        bg = np.array(STAGE["f"], float)
        arr = bg + arr * (1 - bg / 255.0)
        dark = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
        return cover(dark, w, h, (0.5, 0.5))
    if name == "kovcheg":
        im = Image.open(SRC / "kovcheg-ui.png").convert("RGB")
        return cover(im.crop((420, 0, 1280, 560)), w, h, (0.5, 0.0))
    if name == "kmit":
        # three phone screens side by side, their tops
        shots = [Image.open(SRC / f).convert("RGB") for f in ("kmit-home.png", "kmit-lesson.png", "kmit-hint.png")]
        out = Image.new("RGB", (w, h), (233, 238, 250))
        cw = (w - 4 * 8 * K) // 3
        for i, s in enumerate(shots):
            t = cover(s.crop((0, 40, s.width, 40 + s.width * h // cw)), cw, h - 8 * K, (0.5, 0.0))
            out.paste(t, (8 * K + i * (cw + 8 * K), 8 * K))
        return out
    raise KeyError(name)


def wrap(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if font.getlength(t) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def chip(img, d, x, y, label, pal=CHIP, color=INK) -> int:
    """A small framed label (Teul's .chip); returns its width with the outline."""
    f = nunito(12 * K, True)
    w, h = int(f.getlength(label)) + 2 * 8 * K, CHIP_H
    frame(d, x + U, y + U, w, h, U, pal)
    d.text((x + U + 8 * K, y + U + h // 2), label, font=f, fill=color, anchor="lm")
    return w + 2 * U


CHIP_H = 24 * K


CARDS = [
    dict(key="teul", title="Teul", tag="game", desc="A cozy, fully offline life sim in pixel-art isometry: a small Ukrainian town that lives by your real calendar and clock.", chips=["Rust + wasm", "TypeScript", "Android · desktop · web"]),
    dict(key="hae", title="hae", tag="SAR · thermal", desc="Open thermal person detector for search-and-rescue drones, trained from scratch. Real-time sibling: hae-n-ir-ext-kdf.", chips=["313 k params", "int8 383 KB", "Pi Zero 2 W"]),
    dict(key="dal", title="dal", tag="SAR · tracking", desc="Keeps a box on a person in drone video, frame after frame. Classic MOSSE + Kalman + ego-motion, with a Survival@N benchmark.", chips=["no GPU", "numpy + OpenCV", "Pi Zero 2 W"]),
    dict(key="byeol", title="byeol", tag="SAR · ego-motion", desc="Predicts how the camera image moves from the drone's own sensors, so tracking holds even over textureless water.", chips=["pure numpy", "no training", "with covariance"]),
    dict(key="kovcheg", title="Kovcheg", alt="Ковчег", tag="offline RAG", desc="Offline answers with exact sources from your own documents. For emergencies, mini PCs and USB sticks.", chips=["SQLite FTS5", "optional local LLM", "100 % offline"]),
    dict(key="kmit", title="Kmit", tag="learning", desc="An offline learning companion for Ukrainian schoolchildren, with hints that never give the answer away. Pre-alpha.", chips=["Rust + Tauri", "Android", "dataset: 6,301 tasks"]),
]


def card(c: dict) -> Image.Image:
    body = nunito(14 * K)
    lines_h = 20 * K
    inner_w = CW - 2 * U - 2 * PAD
    desc_lines = 3
    title_h = 7 * 3 * K
    ch = CHIP_H + 2 * U
    H = U + PAD + THUMB_H + 12 * K + title_h + 12 * K + desc_lines * lines_h + 10 * K + ch + PAD + U
    img = Image.new("RGBA", (CW, H + 4 * K), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    drop(d, U, U, CW - 2 * U, H - 2 * U, U, 4 * K)
    frame(d, U, U, CW - 2 * U, H - 2 * U, U, CARD)
    # sunken picture
    tx, ty = U + PAD, U + PAD
    frame(d, tx + U, ty, inner_w - 2 * U, THUMB_H, U, STAGE)
    img.paste(thumb(c["key"]), (tx + 2 * U, ty + U))
    # title in Pixelify, the way Teul sets its own name: cream with an amber step under it
    y = ty + THUMB_H + 12 * K
    s = 3 * K
    w = pixel_text(img, tx + U, y, c["title"], PIXELIFY, s, CREAM, shadows=[(0, 1, (196, 122, 34))])
    x = tx + U + w + 8 * K
    if c.get("alt"):
        f = nunito(13 * K, True)
        d.text((x, y + 7 * s - 2 * K), c["alt"], font=f, fill=MUTED, anchor="ls")
        x += int(f.getlength(c["alt"])) + 8 * K
    # tag on the right
    tag = c["tag"].upper()
    tw = TINY.width(tag, 2 * K, spacing=1)
    pixel_text(img, CW - U - PAD - U - tw, y + 7 * s - 5 * 2 * K, tag, TINY, 2 * K, TEAL, spacing=1)
    # description
    y += title_h + 12 * K
    for i, line in enumerate(wrap(c["desc"], body, inner_w - 2 * U)[:desc_lines]):
        d.text((tx + U, y + i * lines_h), line, font=body, fill=INK)
    # chips
    y += desc_lines * lines_h + 10 * K
    x = tx
    for label in c["chips"]:
        x += chip(img, d, x, y, label) + 4 * K
    return img


# ---- buttons ---------------------------------------------------------------------------------------------------
PLAY = np.array([[1 if c <= min(r, 8 - r) else 0 for c in range(5)] for r in range(9)], bool)
ARROW = np.array([[0, 0, 1, 1, 1, 1, 1], [0, 0, 0, 0, 0, 1, 1], [0, 0, 0, 0, 1, 0, 1], [0, 0, 0, 1, 0, 0, 1], [0, 0, 1, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0, 0]], bool)


BTN_W = 196 * K  # every button the same width, so a row of them lines up


def button(label: str, sub: str, pal=GOLD, color=AMBER_INK, icon=PLAY) -> Image.Image:
    s = 2 * K  # 4 image px per design pixel
    tw = PIXELIFY.width(label, s)
    sf = nunito(11 * K, True)
    sw = int(sf.getlength(sub))
    iw = icon.shape[1] * s
    w = BTN_W - 2 * U
    assert 14 * K + iw + 8 * K + max(tw, sw) + 10 * K <= w, label
    h = 46 * K
    img = Image.new("RGBA", (w + 2 * U, h + 2 * U + 4 * K), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    drop(d, U, U, w, h, U, 4 * K)
    frame(d, U, U, w, h, U, pal)
    x = U + 14 * K
    blit_bits(img, icon, x, U + (h - icon.shape[0] * s) // 2, s, color)
    x += iw + 8 * K
    pixel_text(img, x, U + 8 * K, label, PIXELIFY, s, color)
    d.text((x, U + h - 9 * K), sub, font=sf, fill=color, anchor="ls")
    return img


def main() -> None:
    OUT.mkdir(exist_ok=True)
    hero()
    for c in CARDS:
        save(card(c), f"card-{c['key']}.png")
    save(button("Play Teul", "in the browser, no install"), "btn-teul.png")
    save(button("hae demo", "thermal detector, in-browser"), "btn-hae.png")
    save(button("Kovcheg demo", "offline RAG, in-browser"), "btn-kovcheg.png")
    save(button("Hugging Face", "models · datasets · spaces", MUTE_BTN, INK, ARROW), "btn-hf.png")


if __name__ == "__main__":
    main()
