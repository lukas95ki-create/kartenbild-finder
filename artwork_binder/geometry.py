"""Gemeinsame Masse & Raster-Geometrie.

Kartengroesse 63x88mm (Standard), 3x3-Raster => 189x264mm Gesamtflaeche.
Bei 300 DPI ergibt eine Kachel rund 744x1039px.
"""

MM_PER_INCH = 25.4

CARD_W_MM = 63.0
CARD_H_MM = 88.0
GRID_COLS = 3
GRID_ROWS = 3

GRID_W_MM = CARD_W_MM * GRID_COLS   # 189
GRID_H_MM = CARD_H_MM * GRID_ROWS   # 264


def mm_to_px(mm, dpi):
    return int(round(mm / MM_PER_INCH * dpi))


def mm_to_pt(mm):
    """Millimeter -> PDF-Punkte (72 pt / inch)."""
    return mm / MM_PER_INCH * 72.0


def grid_pixels(dpi):
    """(breite, hoehe, kachel_breite, kachel_hoehe) in Pixel bei gegebenem DPI."""
    tw = mm_to_px(CARD_W_MM, dpi)
    th = mm_to_px(CARD_H_MM, dpi)
    return tw * GRID_COLS, th * GRID_ROWS, tw, th


# Seitenformate (Breite x Hoehe in mm).
PAGE_SIZES = {
    "A4": (210.0, 297.0),
    "letter": (215.9, 279.4),
}
