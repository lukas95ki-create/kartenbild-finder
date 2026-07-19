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


def build_canvas_illustration(card_img, bbox, edit_size=EDIT_SIZE):
    """Wie build_canvas, aber es wird nur die ILLUSTRATION geschuetzt.

    bbox: [x0,y0,x1,y1] als Bruchteile 0..1 = Illustrations-Bereich in der
    Karte (ohne Rahmen/Textboxen). Die Illustration wird an ihrer korrekten
    relativen Position INNERHALB der Mittelkachel platziert; der schmale Ring
    zwischen Illustrationsrand und Kachelgrenze (Rahmen) gehoert mit zum
    generierten Bereich - so schliesst die Fortsetzung an der physischen
    Kartenkante an, nicht an der Illustrationskante, und das Modell
    konditioniert auf echte Szenerie statt auf den Kartenrahmen.

    Rueckgabe: (canvas_rgba, mask_rgba, card_tile_full, geo).
    """
    W, H = edit_size
    ox, oy, gw, gh = _grid_box(W, H)
    tw, th = gw // 3, gh // 3
    cx = (W - tw) // 2
    cy = (H - th) // 2

    card_rgb = card_img.convert("RGB")
    cw, ch = card_rgb.size
    x0, y0, x1, y1 = bbox
    illo = card_rgb.crop((int(x0 * cw), int(y0 * ch), int(x1 * cw), int(y1 * ch)))

    # Illustration an ihrer relativen Position in der Mittelkachel.
    ix = cx + int(round(x0 * tw))
    iy = cy + int(round(y0 * th))
    iw = max(1, int(round((x1 - x0) * tw)))
    ih = max(1, int(round((y1 - y0) * th)))
    illo = illo.resize((iw, ih), Image.LANCZOS)

    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.paste(illo, (ix, iy))

    # Maske: nur die Illustration schuetzen (opak), Rest generieren.
    mask = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(mask).rectangle([ix, iy, ix + iw, iy + ih],
                                   fill=(255, 255, 255, 255))

    # Fuer den Vorschau-Composite: die KOMPLETTE Original-Karte auf Kachelmass.
    card_tile_full = card_rgb.resize((tw, th), Image.LANCZOS)

    geo = {"card_box": (cx, cy, tw, th),
           "illo_box": (ix, iy, iw, ih),
           "grid_box": (ox, oy, gw, gh),
           "edit_size": (W, H)}
    return canvas, mask, card_tile_full, geo


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


# Arbeits-Kachelbreite fuer den Stability-Pfad; Ergebnis-Raster bleibt so
# unter den Pixel-Limits der API und wird danach auf 300 DPI hochskaliert.
STABILITY_TILE_W = 512


def stability_plan(card_img, bbox=None, tile_w=STABILITY_TILE_W):
    """Bereitet den Stability-Outpaint vor.

    Als Basis geht die ILLUSTRATION (falls bbox gegeben, ohne Rahmen/Text) auf
    Kachelmass; erweitert wird um genau eine Kachel je Seite. Fuer den
    Vorschau-Composite wird zusaetzlich die komplette Karte auf Kachelmass
    geliefert.
    Rueckgabe: (feed_tile, card_tile_full, dict(left,right,up,down), geo).
    """
    tile_h = int(round(tile_w / GRID_RATIO))
    card_rgb = card_img.convert("RGB")
    if bbox:
        cw, ch = card_rgb.size
        x0, y0, x1, y1 = bbox
        feed = card_rgb.crop((int(x0 * cw), int(y0 * ch),
                              int(x1 * cw), int(y1 * ch)))
    else:
        feed = card_rgb
    feed_tile = feed.resize((tile_w, tile_h), Image.LANCZOS)
    card_tile_full = card_rgb.resize((tile_w, tile_h), Image.LANCZOS)
    grid_w, grid_h = tile_w * 3, tile_h * 3
    geo = {"card_box": (tile_w, tile_h, tile_w, tile_h),
           "grid_box": (0, 0, grid_w, grid_h),
           "edit_size": (grid_w, grid_h)}
    expand = {"left": tile_w, "right": tile_w, "up": tile_h, "down": tile_h}
    return feed_tile, card_tile_full, expand, geo


def blank_center(edit_result, geo, color=(128, 128, 128)):
    """Fuellt die Mittelkachel (Kartenposition) mit neutralem Grau.

    Fuer den Seam-Judge: so sieht er NUR den generierten Aussenbereich und
    kann Karten-Inhalt (Kreatur, Haus) nicht faelschlich als Aussen-Fund
    werten. Ein kleiner Ueberstand blendet auch den Rahmen-Ring mit aus.
    """
    out = edit_result.convert("RGB").copy()
    cx, cy, tw, th = geo["card_box"]
    pad = max(2, int(round(min(tw, th) * 0.02)))
    ImageDraw.Draw(out).rectangle(
        [cx - pad, cy - pad, cx + tw + pad, cy + th + pad], fill=color)
    return out


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
