"""Schritte 5-7: PDF-Layout & Output.

Legt das Raster-Bild mittig auf A4 bzw. US Letter, zeichnet duenne graue
gestrichelte Schnittlinien an allen Kachelraendern, optional kleine
Scheren-Icons (Vektor) auf den Linien und Eckmarkierungen. Die mittlere
Kachel bleibt frei - je nach Modus leer (nur Hintergrund) oder mit
gestrichelter Platzhalter-Linie in Kartengroesse.
"""
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color
from reportlab.lib.utils import ImageReader

from . import geometry as G

GREY = Color(0.45, 0.45, 0.45)
PLACEHOLDER_GREY = Color(0.35, 0.35, 0.35)
CUT_DASH = (2.2, 2.2)


def _draw_scissors(c, cx, cy, size):
    """Kleines Vektor-Scheren-Icon, zentriert auf (cx, cy)."""
    c.saveState()
    c.setStrokeColor(GREY)
    c.setLineWidth(0.5)
    c.setDash()  # durchgezogen
    s = size
    # Zwei Griff-Ringe unten.
    r = 0.13 * s
    c.circle(cx - 0.26 * s, cy - 0.42 * s, r, stroke=1, fill=0)
    c.circle(cx + 0.26 * s, cy - 0.42 * s, r, stroke=1, fill=0)
    # Zwei gekreuzte Klingen nach oben (Drehpunkt in der Mitte).
    p = c.beginPath()
    p.moveTo(cx - 0.26 * s, cy - 0.42 * s + r)
    p.lineTo(cx + 0.33 * s, cy + 0.5 * s)
    p.moveTo(cx + 0.26 * s, cy - 0.42 * s + r)
    p.lineTo(cx - 0.33 * s, cy + 0.5 * s)
    c.drawPath(p, stroke=1, fill=0)
    c.restoreState()


def _draw_crop_marks(c, ox, oy, gw, gh):
    """L-foermige Eckmarkierungen ausserhalb des Rasters."""
    c.saveState()
    c.setStrokeColor(GREY)
    c.setLineWidth(0.5)
    c.setDash()
    gap = G.mm_to_pt(2.0)
    ln = G.mm_to_pt(5.0)
    corners = [
        (ox, oy, -1, -1),            # unten links
        (ox + gw, oy, 1, -1),        # unten rechts
        (ox, oy + gh, -1, 1),        # oben links
        (ox + gw, oy + gh, 1, 1),    # oben rechts
    ]
    for x, y, sx, sy in corners:
        c.line(x + sx * gap, y, x + sx * (gap + ln), y)          # horizontal
        c.line(x, y + sy * gap, x, y + sy * (gap + ln))          # vertikal
    c.restoreState()


def render_pdf(path, grid_image, page_size_mm, mode="empty",
               cut_icons=False, crop_marks=False):
    """Schreibt eine PDF-Seite (ein Format) mit dem Raster."""
    page_w = G.mm_to_pt(page_size_mm[0])
    page_h = G.mm_to_pt(page_size_mm[1])
    gw = G.mm_to_pt(G.GRID_W_MM)
    gh = G.mm_to_pt(G.GRID_H_MM)
    tw = gw / G.GRID_COLS
    th = gh / G.GRID_ROWS
    ox = (page_w - gw) / 2.0
    oy = (page_h - gh) / 2.0

    c = canvas.Canvas(path, pagesize=(page_w, page_h))

    # Raster-Bild mittig.
    c.drawImage(ImageReader(grid_image), ox, oy, width=gw, height=gh,
                preserveAspectRatio=False, mask=None)

    # Gestrichelte Schnittlinien (aussen + zwischen den Kacheln).
    c.saveState()
    c.setStrokeColor(GREY)
    c.setLineWidth(0.5)
    c.setDash(*CUT_DASH)
    x_lines = [ox + i * tw for i in range(G.GRID_COLS + 1)]
    y_lines = [oy + i * th for i in range(G.GRID_ROWS + 1)]
    for x in x_lines:
        c.line(x, oy, x, oy + gh)
    for y in y_lines:
        c.line(ox, y, ox + gw, y)
    c.restoreState()

    # Mittlere Kachel: Platzhalter im 'outlined'-Modus.
    if mode == "outlined":
        inset = G.mm_to_pt(1.5)
        mx = ox + 1 * tw + inset
        my = oy + 1 * th + inset
        mw = tw - 2 * inset
        mh = th - 2 * inset
        c.saveState()
        c.setStrokeColor(PLACEHOLDER_GREY)
        c.setLineWidth(0.7)
        c.setDash(3.5, 2.5)
        c.rect(mx, my, mw, mh, stroke=1, fill=0)
        c.restoreState()

    # Scheren-Icons mittig auf jeder Schnittlinie.
    if cut_icons:
        size = G.mm_to_pt(4.5)
        cy_mid = oy + gh / 2.0
        cx_mid = ox + gw / 2.0
        for x in x_lines:
            _draw_scissors(c, x, cy_mid, size)
        for y in y_lines:
            _draw_scissors(c, cx_mid, y, size)

    if crop_marks:
        _draw_crop_marks(c, ox, oy, gw, gh)

    c.showPage()
    c.save()
    return path


def render_all(basepath, grid_image, formats, mode="empty",
               cut_icons=False, crop_marks=False, log=print):
    """Erzeugt aus einem Lauf beide Formate. formats: {"A4": .., "letter": ..}.

    basepath ist der Praefix, z.B. '.../wartortle' -> '..._A4.pdf' etc.
    """
    written = []
    for key, size in formats.items():
        suffix = "A4" if key.lower() == "a4" else key
        out = f"{basepath}_{suffix}.pdf"
        render_pdf(out, grid_image, size, mode=mode,
                   cut_icons=cut_icons, crop_marks=crop_marks)
        log(f"  PDF geschrieben: {out}")
        written.append(out)
    return written
