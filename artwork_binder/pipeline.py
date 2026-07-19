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


def _resolve_outpaint_provider(requested, offline, log):
    """Waehlt den Outpaint-Provider. 'auto' = Stability wenn Key da, sonst
    gpt-image-2. Gibt (provider, openai_key) oder (None, None) zurueck."""
    if offline:
        return None, None
    stab_key = os.environ.get("STABILITY_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    if requested == "stability":
        if stab_key:
            return "stability", openai_key
        log("  Hinweis: STABILITY_API_KEY fehlt -> Fallback gpt-image-2")
        return ("openai", openai_key) if openai_key else (None, None)
    if requested == "openai":
        return ("openai", openai_key) if openai_key else (None, None)
    # auto: gpt-image-2 bevorzugt (empirisch besser fuers volle 3x3-Feld);
    # Stability nur auf explizite Anforderung, da es das Fernfeld oft flach
    # laesst und Randstrukturen literal verzerrt.
    if openai_key:
        return "openai", openai_key
    if stab_key:
        return "stability", openai_key
    return None, None


def _outpaint_grid(image_path, analysis, dpi, edit_model, seam_model,
                   offline, outpaint_provider, creativity, base, outputs,
                   seam_retries, log):
    """Kern-Weg: Card-Outpainting (Karte bleibt in der Mitte).

    Zwei Backends:
      - stability: echtes pixelbasiertes Outpainting (konditioniert auf die
        realen Randpixel der Karte) - primaer, Best-of-2.
      - openai:    masken-basiertes gpt-image-2 images.edit - Fallback.
    In beiden Faellen: gpt-4o-Seam-Check, bei Problemen gezielte Retries,
    bestes Ergebnis behalten. Gibt (grid_pdf, prompt, negative, meta) oder None.
    """
    provider, openai_key = _resolve_outpaint_provider(
        outpaint_provider, offline, log)
    if provider is None:
        return None
    stab_key = os.environ.get("STABILITY_API_KEY")

    card = Image.open(image_path)
    # Nur die Illustration (ohne Rahmen/Textboxen) als Basis - siehe Analyse.
    illo = analysis.get("illustration") or {}
    bbox = illo.get("bbox")
    if provider == "stability":
        _feed, card_tile, expand, geo = OP.stability_plan(card, bbox=bbox)
        size = f"{geo['edit_size'][0]}x{geo['edit_size'][1]}"
        max_attempts = 2  # Best-of-2
    else:
        if bbox:
            _canvas, _mask, card_tile, geo = OP.build_canvas_illustration(card, bbox)
        else:
            _canvas, _mask, card_tile, geo = OP.build_canvas(card)
        size = f"{geo['edit_size'][0]}x{geo['edit_size'][1]}"
        max_attempts = 1 + max(0, seam_retries)

    def _generate(prompt):
        if provider == "stability":
            return GEN.outpaint_stability(
                _feed, expand["left"], expand["right"], expand["up"],
                expand["down"], prompt=prompt, creativity=creativity,
                api_key=stab_key)
        return GEN.edit_openai(_canvas, _mask, prompt, model=edit_model,
                               api_key=openai_key, size=size)

    unique_objects = analysis.get("unique_objects") or []
    best = None            # (score, result, prompt, check)
    focus = None           # problematische Kanten fuer den naechsten Versuch
    forbid = None          # aussen duplizierte Objekte fuer den naechsten Versuch
    attempts_meta = []

    for attempt in range(1, max_attempts + 1):
        gen_prompt, negative = P.build_outpaint_prompt(
            analysis, focus_edges=focus, escalate_forbid=forbid)
        if attempt == 1:
            log(f"  Outpaint-Prompt: {gen_prompt}")
        else:
            log(f"  Retry {attempt-1}: Kanten={focus or []}, Duplikate={forbid or []}")
        log(f"  Outpainting (Versuch {attempt}/{max_attempts}, {provider}) @ "
            f"{size} ...")
        try:
            result = _generate(gen_prompt)
        except Exception as exc:
            if best is None:
                log(f"  Outpaint-Fehler ({exc}) -> Text-zu-Bild-Fallback")
                return None
            log(f"  Outpaint-Fehler ({exc}) -> behalte bisher bestes Ergebnis")
            break

        # Seam-Check auf dem Composite (Karte in der Mitte).
        composite = OP.composite_card(result, card_tile, geo)
        check = A.seam_check(composite, unique_objects=unique_objects,
                             api_key=openai_key, model=seam_model)
        if check is None:
            log("  Seam-Check uebersprungen (kein Key) - nehme dieses Ergebnis")
            best = (0, result, gen_prompt, {"skipped": True})
            break
        if "error" in check:
            log(f"  Seam-Check-Fehler ({check['error']}) - nehme dieses Ergebnis")
            best = (0, result, gen_prompt, check)
            break

        bad = check.get("bad_edges", [])
        dups = check.get("duplicates", [])
        creature = check.get("creature", False)
        # Kreatur im Aussenbereich ist hartes K.O. -> hohes Gewicht, damit ein
        # kreaturfreies Ergebnis immer bevorzugt wird.
        score = 0 if check.get("ok") else (len(bad) + len(dups) + (10 if creature else 0)) or 1
        attempts_meta.append({"attempt": attempt, "ok": check.get("ok"),
                              "bad_edges": bad, "duplicates": dups,
                              "creature": creature, "notes": check.get("notes", "")})
        status = "OK" if check.get("ok") else \
            f"Versatz={bad or []}, Duplikate={dups or []}, Kreatur={creature}"
        log(f"  Seam-Check: {status}"
            + (f" ({check.get('notes')})" if check.get('notes') else ""))

        if best is None or score < best[0]:
            best = (score, result, gen_prompt, check)
        if check.get("ok"):
            break
        focus = bad or None
        # Kreatur/Duplikat -> Objekt-Verbot beim Retry verschaerfen.
        forbid = dups or (["the creature / pokemon from the card"] if creature else None)

    score, result, gen_prompt, check = best
    negative = P.OUTPAINT_NEGATIVE

    # Rohes Edit-Ergebnis sichern (fuer Nachvollziehbarkeit).
    scene_path = base + "_scene.png"
    result.save(scene_path)
    outputs["scene_png"] = scene_path

    grid_pdf, preview = OP.compose_outputs(result, card_tile, geo, dpi=dpi)
    preview_path = base + "_preview.png"
    preview.save(preview_path, dpi=(dpi, dpi))
    outputs["preview_png"] = preview_path
    log(f"  Vorschau (Karte in Mitte) gespeichert: {preview_path}")

    meta = {"provider": ("stability-outpaint" if provider == "stability"
                         else "openai-outpaint"),
            "model": ("stable-image-outpaint" if provider == "stability"
                      else edit_model),
            "edit_size": list(geo["edit_size"]), "card_box": list(geo["card_box"]),
            "seam_attempts": attempts_meta, "seam_final": check}
    return grid_pdf, gen_prompt, negative, meta


def process_card(image_path, out_dir, name=None, mode="empty", dpi=300,
                 cut_icons=False, crop_marks=False, provider="openai",
                 model="gpt-image-1", edit_model="gpt-image-2",
                 vision_model="gpt-4o-mini", seam_model="gpt-4o",
                 outpaint_provider="auto", creativity=0.5,
                 use_vision=True, offline=False, no_outpaint=False,
                 seam_retries=2, type_override=None, prompt_override=None,
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
        op = _outpaint_grid(image_path, analysis, dpi, edit_model, seam_model,
                            offline, outpaint_provider, creativity, base,
                            outputs, seam_retries, log)

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
