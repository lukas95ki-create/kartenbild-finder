"""Orchestrierung der Gesamt-Pipeline (Einzel- und Batch-Modus).

Jeder Zwischenschritt wird gespeichert:
  <name>_log.json      - Analyse + Prompt + Generierungs-Meta
  <name>_artwork.png   - generiertes Rohbild (voll, ungeschnitten)
  <name>_grid.png      - auf 189x264mm zugeschnittenes Raster-Bild
  <name>_A4.pdf / <name>_letter.pdf
So laesst sich jeder Schritt nachvollziehen und einzeln korrigieren.
"""
import json
import os
import time

from . import analyze as A
from . import prompt as P
from . import generate as GEN
from . import tiles as TL
from . import geometry as G
from . import pdf as PDF
from . import types as T


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def process_card(image_path, out_dir, name=None, mode="empty", dpi=300,
                 cut_icons=False, crop_marks=False, provider="openai",
                 model="gpt-image-1", vision_model="gpt-4o-mini",
                 use_vision=True, offline=False, type_override=None,
                 prompt_override=None, formats=None, log=print):
    """Fuehrt die komplette Pipeline fuer eine Karte aus. Gibt ein Ergebnis-
    Dict mit allen erzeugten Pfaden zurueck.
    """
    name = name or os.path.splitext(os.path.basename(image_path))[0]
    card_dir = os.path.join(out_dir, name)
    os.makedirs(card_dir, exist_ok=True)
    base = os.path.join(card_dir, name)
    formats = formats or G.PAGE_SIZES

    log(f"[{name}] Verarbeite {image_path}")

    # 1) Analyse
    analysis = A.analyze_card(image_path, use_vision=use_vision,
                              vision_model=vision_model, log=log)
    if type_override:
        norm = T.normalize_type(type_override) or type_override
        analysis["type"] = norm
        analysis["type_override"] = True
        log(f"  Typ manuell ueberschrieben: {norm}")

    # 2) Prompt
    if prompt_override:
        gen_prompt, negative = prompt_override, P.NEGATIVE
        log("  Prompt manuell ueberschrieben")
    else:
        gen_prompt, negative = P.build_prompt(analysis)
    log(f"  Prompt: {gen_prompt}")

    # 3) Bild-Generierung
    grid_w, grid_h, _, _ = G.grid_pixels(dpi)
    raw_img, gen_meta = GEN.generate_image(
        gen_prompt, analysis, grid_w, grid_h, provider=provider,
        model=model, offline=offline, log=log)
    raw_path = base + "_artwork.png"
    raw_img.save(raw_path)
    log(f"  Rohbild gespeichert: {raw_path} ({raw_img.size[0]}x{raw_img.size[1]})")

    # 4) Kachel-Zuschnitt (Cover-Fit auf Zielaufloesung)
    grid_img = TL.fit_to_grid(raw_img, dpi=dpi)
    grid_path = base + "_grid.png"
    grid_img.save(grid_path, dpi=(dpi, dpi))
    log(f"  Raster-Bild gespeichert: {grid_path} "
        f"({grid_img.size[0]}x{grid_img.size[1]} @ {dpi}dpi)")

    # 5-7) PDFs (mittlere Kachel = Aussparung je nach Modus)
    pdfs = PDF.render_all(base, grid_img, formats, mode=mode,
                          cut_icons=cut_icons, crop_marks=crop_marks, log=log)

    # Log/Sidecar
    record = {
        "name": name,
        "input": os.path.abspath(image_path),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "analysis": analysis,
        "prompt": gen_prompt,
        "negative_prompt": negative,
        "mode": mode,
        "dpi": dpi,
        "generation": gen_meta,
        "outputs": {
            "artwork_png": raw_path,
            "grid_png": grid_path,
            "pdfs": pdfs,
        },
    }
    log_path = base + "_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    log(f"  Log gespeichert: {log_path}")
    log(f"[{name}] Fertig.\n")
    return record


def process_batch(folder, out_dir, log=print, **kwargs):
    """Laeuft alle Bilder in einem Ordner nacheinander durch."""
    files = sorted(
        f for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in IMAGE_EXTS
    )
    if not files:
        log(f"Keine Bilddateien in {folder} gefunden.")
        return []
    log(f"Batch-Modus: {len(files)} Karten in {folder}\n")
    results = []
    for i, fn in enumerate(files, 1):
        log(f"=== ({i}/{len(files)}) {fn} ===")
        try:
            rec = process_card(os.path.join(folder, fn), out_dir, log=log,
                               **kwargs)
            results.append(rec)
        except Exception as exc:
            log(f"  FEHLER bei {fn}: {exc}")
            results.append({"name": fn, "error": str(exc)})
    ok = sum(1 for r in results if "error" not in r)
    log(f"Batch fertig: {ok}/{len(files)} erfolgreich.")
    return results
