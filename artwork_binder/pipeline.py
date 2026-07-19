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

from PIL import Image

from . import analyze as A
from . import prompt as P
from . import generate as GEN
from . import tiles as TL
from . import geometry as G
from . import pdf as PDF
from . import outpaint as OP
from . import types as T


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _outpaint_grid(image_path, analysis, dpi, edit_model, offline, api_key,
                   base, outputs, log):
    """Kern-Weg: masken-basiertes Card-Outpainting (Karte bleibt in der Mitte).

    Gibt (grid_pdf_img, gen_prompt, negative, gen_meta) zurueck oder None,
    wenn kein Outpainting moeglich ist (offline / kein Key) - dann greift der
    Text-zu-Bild-Fallback.
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if offline or not api_key:
        return None

    gen_prompt, negative = P.build_outpaint_prompt(analysis)
    log(f"  Outpaint-Prompt: {gen_prompt}")

    card = Image.open(image_path)
    canvas, mask, card_tile, geo = OP.build_canvas(card)
    log(f"  Outpainting: OpenAI {edit_model} images.edit @ "
        f"{geo['edit_size'][0]}x{geo['edit_size'][1]} "
        f"(Karte geschuetzt in der Mitte) ...")
    try:
        result = GEN.edit_openai(canvas, mask, gen_prompt, model=edit_model,
                                 api_key=api_key,
                                 size=f"{geo['edit_size'][0]}x{geo['edit_size'][1]}")
    except Exception as exc:
        log(f"  Outpaint-Fehler ({exc}) -> Text-zu-Bild-Fallback")
        return None

    # Rohes Edit-Ergebnis sichern (fuer Nachvollziehbarkeit).
    scene_path = base + "_scene.png"
    result.save(scene_path)
    outputs["scene_png"] = scene_path

    grid_pdf, preview = OP.compose_outputs(result, card_tile, geo, dpi=dpi)
    # Vorschau MIT Karte in der Mitte (Etsy-Produktbild-Grundlage).
    preview_path = base + "_preview.png"
    preview.save(preview_path, dpi=(dpi, dpi))
    outputs["preview_png"] = preview_path
    log(f"  Vorschau (Karte in Mitte) gespeichert: {preview_path}")

    meta = {"provider": "openai-outpaint", "model": edit_model,
            "edit_size": list(geo["edit_size"]), "card_box": list(geo["card_box"])}
    return grid_pdf, gen_prompt, negative, meta


def process_card(image_path, out_dir, name=None, mode="empty", dpi=300,
                 cut_icons=False, crop_marks=False, provider="openai",
                 model="gpt-image-1", edit_model="gpt-image-2",
                 vision_model="gpt-4o-mini", use_vision=True, offline=False,
                 no_outpaint=False, type_override=None, prompt_override=None,
                 formats=None, log=print):
    """Fuehrt die komplette Pipeline fuer eine Karte aus. Gibt ein Ergebnis-
    Dict mit allen erzeugten Pfaden zurueck.

    Kern-Mechanismus ist masken-basiertes Card-Outpainting (die echte Karte
    bleibt in der Mitte, das Modell malt nur aussen weiter). Text-zu-Bild
    dient nur noch als Rueckfall (offline / kein Key / --no-outpaint).
    """
    name = name or os.path.splitext(os.path.basename(image_path))[0]
    card_dir = os.path.join(out_dir, name)
    os.makedirs(card_dir, exist_ok=True)
    base = os.path.join(card_dir, name)
    formats = formats or G.PAGE_SIZES
    outputs = {}

    log(f"[{name}] Verarbeite {image_path}")

    # 1) Analyse (liefert individuelle Szene fuer den Prompt)
    analysis = A.analyze_card(image_path, use_vision=use_vision,
                              vision_model=vision_model, log=log)
    if type_override:
        norm = T.normalize_type(type_override) or type_override
        analysis["type"] = norm
        analysis["type_override"] = True
        log(f"  Typ manuell ueberschrieben: {norm}")

    grid_path = base + "_grid.png"

    # 2-4) Kern: Card-Outpainting
    op = None
    if not no_outpaint and not prompt_override:
        op = _outpaint_grid(image_path, analysis, dpi, edit_model, offline,
                            None, base, outputs, log)

    if op is not None:
        grid_img, gen_prompt, negative, gen_meta = op
        grid_img.save(grid_path, dpi=(dpi, dpi))
        log(f"  Raster-Bild gespeichert: {grid_path} "
            f"({grid_img.size[0]}x{grid_img.size[1]} @ {dpi}dpi)")
    else:
        # Rueckfall: reines Text-zu-Bild (offline / kein Key / --no-outpaint).
        if prompt_override:
            gen_prompt, negative = prompt_override, P.NEGATIVE
            log("  Prompt manuell ueberschrieben")
        else:
            gen_prompt, negative = P.build_prompt(analysis)
            log("  Rueckfall Text-zu-Bild")
        log(f"  Prompt: {gen_prompt}")
        grid_w, grid_h, _, _ = G.grid_pixels(dpi)
        raw_img, gen_meta = GEN.generate_image(
            gen_prompt, analysis, grid_w, grid_h, provider=provider,
            model=model, offline=offline, log=log)
        raw_path = base + "_artwork.png"
        raw_img.save(raw_path)
        outputs["artwork_png"] = raw_path
        grid_img = TL.fit_to_grid(raw_img, dpi=dpi)
        grid_img.save(grid_path, dpi=(dpi, dpi))
        log(f"  Raster-Bild gespeichert: {grid_path} "
            f"({grid_img.size[0]}x{grid_img.size[1]} @ {dpi}dpi)")

    outputs["grid_png"] = grid_path

    # 5-7) PDFs (mittlere Kachel = Aussparung je nach Modus)
    pdfs = PDF.render_all(base, grid_img, formats, mode=mode,
                          cut_icons=cut_icons, crop_marks=crop_marks, log=log)
    outputs["pdfs"] = pdfs

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
        "outputs": outputs,
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
