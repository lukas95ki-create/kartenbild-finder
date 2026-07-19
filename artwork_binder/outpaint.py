"""Kern-Mechanismus: masken-basiertes Card-Outpainting.

Statt reiner Text-zu-Bild-Generierung wird die echte Karte in die
Mittelkachel eines Raster-Canvas gelegt und das Modell (OpenAI
images.edit / gpt-image-2) malt nur die 8 aussen liegenden Kacheln weiter.
Dadurch setzt sich die Illustration ueber die Kartenkanten hinaus fort -
gleiche Farben, gleiche Kanten, gleicher Stil.

Ablauf:
  1. Canvas im Raster-Seitenverhaeltnis, Karte exakt in die Mitte.
  2. Maske: Mitte geschuetzt (opak), aussen zu generieren (transparent).
  3. images.edit-Aufruf mit kartenindividuellem Prompt.
  4. Safety-Composite: Original-Kartenpixel wieder exakt ueber die Mitte
     (garantiert Mitte = 100 % Original fuer die Vorschau).
  5. Auf Rastermass croppen und per Lanczos auf Ziel-DPI hochskalieren.
"""
from PIL import Image, ImageDraw

from . import geometry as G

# images.edit liefert feste Groessen; Hochformat passt zum Raster.
EDIT_SIZE = (1024, 1536)
GRID_RATIO = G.GRID_W_MM / G.GRID_H_MM   # 189/264 = 0.7159


def _grid_box(canvas_w, canvas_h):
    """Groesstes zentriertes Rechteck im Raster-Seitenverhaeltnis."""
    gw = min(canvas_w, int(round(canvas_h * GRID_RATIO)))
    gh = int(round(gw / GRID_RATIO))
    if gh > canvas_h:
        gh = canvas_h
        gw = int(round(gh * GRID_RATIO))
    ox = (canvas_w - gw) // 2
    oy = (canvas_h - gh) // 2
    return ox, oy, gw, gh


def build_canvas(card_img, edit_size=EDIT_SIZE):
    """Baut (canvas_rgba, mask_rgba, geo). geo enthaelt die Kachel-Koordinaten."""
    W, H = edit_size
    ox, oy, gw, gh = _grid_box(W, H)
    tw, th = gw // 3, gh // 3
    # Karte auf Kachelmass (unveraendertes Seitenverhaeltnis ~ 63:88).
    card = card_img.convert("RGB").resize((tw, th), Image.LANCZOS)
    cx = (W - tw) // 2
    cy = (H - th) // 2

    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.paste(card, (cx, cy))

    # Maske: transparent = generieren (aussen), opak = schuetzen (Karte).
    mask = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(mask).rectangle([cx, cy, cx + tw, cy + th],
                                   fill=(255, 255, 255, 255))

    geo = {"card_box": (cx, cy, tw, th),
           "grid_box": (ox, oy, gw, gh),
           "edit_size": (W, H)}
    return canvas, mask, card, geo


def _feathered_paste(base, card, box, feather=2):
    """Legt die Original-Karte exakt zurueck, mit optional weicher Kante."""
    cx, cy, tw, th = box
    if feather <= 0:
        base.paste(card, (cx, cy))
        return base
    m = Image.new("L", (tw, th), 0)
    ImageDraw.Draw(m).rectangle([feather, feather, tw - feather, th - feather],
                                fill=255)
    m = m.filter(__import__("PIL.ImageFilter", fromlist=["GaussianBlur"])
                 .GaussianBlur(feather))
    base.paste(card, (cx, cy), m)
    return base


def composite_card(edit_result, card_tile, geo, feather=2):
    """Legt die Original-Karte exakt in die Mitte des Edit-Ergebnisses.

    Rueckgabe in Edit-Aufloesung (nicht hochskaliert) - dient dem Seam-Check
    und als Basis fuer die Vorschau.
    """
    out = edit_result.copy()
    _feathered_paste(out, card_tile, geo["card_box"], feather=feather)
    return out


def compose_outputs(edit_result, card_tile, geo, dpi=300, feather=2):
    """Erzeugt (grid_pdf, preview) in Ziel-DPI.

    grid_pdf: Raster fuers PDF - Mitte = generierte Fortsetzung (wird spaeter
              von der echten Karte verdeckt).
    preview:  gleiches Raster, aber mit der Original-Karte exakt in der Mitte
              (Grundlage fuer Etsy-Produktbilder).
    """
    ox, oy, gw, gh = geo["grid_box"]
    grid_scene = edit_result.crop((ox, oy, ox + gw, oy + gh))

    preview_full = composite_card(edit_result, card_tile, geo, feather=feather)
    preview_scene = preview_full.crop((ox, oy, ox + gw, oy + gh))

    tgt_w, tgt_h, _, _ = G.grid_pixels(dpi)
    grid_pdf = grid_scene.resize((tgt_w, tgt_h), Image.LANCZOS)
    grid_pdf.info["dpi"] = (dpi, dpi)
    preview = preview_scene.resize((tgt_w, tgt_h), Image.LANCZOS)
    preview.info["dpi"] = (dpi, dpi)
    return grid_pdf, preview
