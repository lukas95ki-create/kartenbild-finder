#!/usr/bin/env python3
"""Artwork-Binder-Generator - eine CLI fuer die komplette Pipeline.

Aus einem Kartenfoto entsteht vollautomatisch ein druckfertiges
9-Kachel-Binder-PDF-Paar (A4 + US Letter) mit KI-generiertem Hintergrund.

Beispiele:
  python make_binder.py karte_wartortle.jpg --output wartortle --mode empty --cut-icons
  python make_binder.py --batch fotos/ --out-dir output --mode outlined --cut-icons
  python make_binder.py karte.jpg --offline            # ohne API testen

Der OpenAI-API-Key wird aus der Umgebung / .env gelesen (OPENAI_API_KEY),
niemals hartcodiert.
"""
import argparse
import os
import sys

# .env laden, falls vorhanden (optional).
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from artwork_binder import pipeline, geometry


def build_parser():
    p = argparse.ArgumentParser(
        description="Artwork-Binder-Generator: Kartenfoto -> druckfertiges "
                    "9-Kachel-Binder-PDF (A4 + Letter) mit KI-Hintergrund.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("input", nargs="?", help="Kartenfoto (JPG/PNG). Entfaellt bei --batch.")
    p.add_argument("--batch", metavar="ORDNER",
                   help="Alle Bilder in ORDNER nacheinander verarbeiten.")
    p.add_argument("--output", "-o", help="Basisname der Ausgabe (nur Einzelmodus).")
    p.add_argument("--out-dir", default="output",
                   help="Zielordner fuer Ergebnisse (Standard: output/).")
    p.add_argument("--mode", choices=["empty", "outlined"], default="empty",
                   help="Mittlere Kachel: leer (nur Hintergrund) oder mit "
                        "gestrichelter Platzhalter-Linie (Standard: empty).")
    p.add_argument("--cut-icons", action="store_true",
                   help="Kleine Scheren-Icons auf die Schnittlinien setzen.")
    p.add_argument("--crop-marks", action="store_true",
                   help="Eckmarkierungen ausserhalb des Rasters zeichnen.")
    p.add_argument("--dpi", type=int, default=300,
                   help="Zielaufloesung fuer Zuschnitt/PDF (Standard: 300).")
    p.add_argument("--provider", default="openai",
                   help="Bild-API-Anbieter (Standard: openai).")
    p.add_argument("--model", default="gpt-image-1",
                   help="Bild-Modell fuer den Text-zu-Bild-Fallback (Standard: gpt-image-1).")
    p.add_argument("--edit-model", default="gpt-image-2",
                   help="Modell fuer das Card-Outpainting via images.edit (Standard: gpt-image-2).")
    p.add_argument("--no-outpaint", action="store_true",
                   help="Kein Card-Outpainting, stattdessen reines Text-zu-Bild.")
    p.add_argument("--vision-model", default="gpt-4o-mini",
                   help="Vision-Modell fuer Szenen/Typ/Name-Erkennung (Standard: gpt-4o-mini).")
    p.add_argument("--no-vision", action="store_true",
                   help="Vision-Analyse abschalten, nur Farb-Heuristik nutzen.")
    p.add_argument("--offline", action="store_true",
                   help="Ohne API: Platzhalter-Hintergrund aus der Farbstimmung.")
    p.add_argument("--type", dest="type_override",
                   help="Erkannten Typ manuell ueberschreiben (z.B. wasser).")
    p.add_argument("--prompt", dest="prompt_override",
                   help="Bild-Prompt komplett manuell vorgeben.")
    p.add_argument("--only", choices=["A4", "letter"],
                   help="Nur ein Seitenformat erzeugen (Standard: beide).")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    if not args.batch and not args.input:
        print("Fehler: entweder ein Kartenfoto ODER --batch angeben.", file=sys.stderr)
        return 2
    if args.batch and args.input:
        print("Fehler: --batch und Einzelbild nicht gleichzeitig.", file=sys.stderr)
        return 2

    formats = geometry.PAGE_SIZES
    if args.only:
        key = "A4" if args.only == "A4" else "letter"
        formats = {key: geometry.PAGE_SIZES[key]}

    common = dict(
        mode=args.mode, dpi=args.dpi, cut_icons=args.cut_icons,
        crop_marks=args.crop_marks, provider=args.provider, model=args.model,
        edit_model=args.edit_model, no_outpaint=args.no_outpaint,
        vision_model=args.vision_model, use_vision=not args.no_vision,
        offline=args.offline, type_override=args.type_override,
        prompt_override=args.prompt_override, formats=formats,
    )

    os.makedirs(args.out_dir, exist_ok=True)

    if args.batch:
        if not os.path.isdir(args.batch):
            print(f"Fehler: Ordner nicht gefunden: {args.batch}", file=sys.stderr)
            return 2
        pipeline.process_batch(args.batch, args.out_dir, **common)
    else:
        if not os.path.isfile(args.input):
            print(f"Fehler: Datei nicht gefunden: {args.input}", file=sys.stderr)
            return 2
        pipeline.process_card(args.input, args.out_dir, name=args.output, **common)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
