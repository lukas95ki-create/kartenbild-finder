"""Schritt 4: Kachel-Zuschnitt.

Skaliert das generierte Bild so, dass es das 189x264mm-Raster bei Ziel-DPI
exakt fuellt (Cover-Fit, zentriert), und schneidet Ueberstand mittig weg.
Optional wird das Ergebnis in die 9 Einzelkacheln zerlegt, falls man sie
separat weiterverwenden will.
"""
from PIL import Image

from . import geometry as G


def fit_to_grid(image, dpi=300):
    """Cover-Fit: fuellt das komplette Raster, mittiger Zuschnitt, upscaling
    per Lanczos falls das Quellbild kleiner als die Zielaufloesung ist.
    """
    grid_w, grid_h, _, _ = G.grid_pixels(dpi)
    src_w, src_h = image.size
    scale = max(grid_w / src_w, grid_h / src_h)
    new_w, new_h = int(round(src_w * scale)), int(round(src_h * scale))
    resized = image.resize((new_w, new_h), Image.LANCZOS)

    left = (new_w - grid_w) // 2
    top = (new_h - grid_h) // 2
    cropped = resized.crop((left, top, left + grid_w, top + grid_h))
    cropped.info["dpi"] = (dpi, dpi)
    return cropped


def split_tiles(grid_image, dpi=300):
    """Zerlegt das Raster-Bild in die 9 Kacheln (Zeile fuer Zeile)."""
    _, _, tw, th = G.grid_pixels(dpi)
    tiles = []
    for row in range(G.GRID_ROWS):
        for col in range(G.GRID_COLS):
            box = (col * tw, row * th, (col + 1) * tw, (row + 1) * th)
            tiles.append(grid_image.crop(box))
    return tiles
