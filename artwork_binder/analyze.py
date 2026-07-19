"""Schritt 1: Karten-Input & Analyse.

Erkennt Typ, Farbstimmung und (optional per Vision-API) den Pokemon-Namen.
Die Farb-Analyse laeuft immer offline mit Pillow; die Vision-Erkennung ist
optional und wird nur genutzt, wenn ein API-Key vorhanden und nicht per Flag
abgeschaltet ist. Alle Ergebnisse dienen ausschliesslich der internen
Prompt-Steuerung.
"""
import colorsys
import base64
import json
import os

from PIL import Image

from . import types as T


def _dominant_colors(img, n=5):
    """Liefert die n haeufigsten Farben als Liste von (rgb, anteil)."""
    small = img.convert("RGB").resize((160, 224))
    # Median-Cut-Quantisierung, dann Haeufigkeit ueber die Palette.
    q = small.quantize(colors=n, method=Image.MEDIANCUT)
    palette = q.getpalette()
    counts = q.getcolors()  # [(count, palette_index), ...]
    total = sum(c for c, _ in counts) or 1
    out = []
    for count, idx in sorted(counts, reverse=True):
        rgb = tuple(palette[idx * 3: idx * 3 + 3])
        out.append((rgb, count / total))
    return out


def _rgb_to_hsv(rgb):
    r, g, b = [v / 255.0 for v in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360.0, s, v


def _hue_in(hue, ranges):
    return any(lo <= hue <= hi for lo, hi in ranges)


def _classify_type(dominant):
    """Farb-Heuristik: waehlt einen Typ aus den dominanten Farben.

    Sehr saturierte, grossflaechige Farben zaehlen staerker. Die
    Metall/Finsternis-Regeln (grau bzw. sehr dunkel) werden gesondert
    behandelt, damit sie nicht faelschlich alle anderen schlagen.
    """
    scores = {k: 0.0 for k in T.TYPE_TABLE}
    for rgb, share in dominant:
        hue, sat, val = _rgb_to_hsv(rgb)
        for key, e in T.TYPE_TABLE.items():
            if "max_sat" in e and sat > e["max_sat"]:
                continue
            if "min_sat" in e and sat < e["min_sat"]:
                continue
            if "min_val" in e and val < e["min_val"]:
                continue
            if "max_val" in e and val > e["max_val"]:
                continue
            if e["hue"] and not _hue_in(hue, e["hue"]):
                continue
            # Gewicht: Flaechenanteil * (leichter Saettigungs-Bonus).
            weight = share * (0.5 + sat)
            scores[key] += weight
    best = max(scores, key=scores.get)
    if scores[best] <= 0:
        return T.DEFAULT_TYPE, 0.0
    total = sum(scores.values()) or 1
    return best, scores[best] / total


def _mood_words(dominant):
    """Grobe verbale Beschreibung der Farbstimmung fuer den Prompt."""
    rgb, _ = dominant[0]
    hue, sat, val = _rgb_to_hsv(rgb)
    brightness = "bright" if val > 0.6 else ("dim" if val > 0.3 else "dark")
    intensity = "vivid" if sat > 0.5 else ("muted" if sat > 0.2 else "desaturated")
    warm = "warm" if (hue < 70 or hue > 320) else ("cool" if 150 < hue < 280 else "neutral")
    return f"{brightness}, {intensity}, {warm}"


def color_analysis(image_path):
    """Reine Pillow-Analyse: dominante Farben, Typ-Schaetzung, Stimmung."""
    with Image.open(image_path) as img:
        dominant = _dominant_colors(img)
    guessed_type, confidence = _classify_type(dominant)
    return {
        "dominant_colors": [
            {"rgb": list(rgb), "hex": "#%02x%02x%02x" % rgb, "share": round(share, 3)}
            for rgb, share in dominant
        ],
        "mood": _mood_words(dominant),
        "type": guessed_type,
        "type_confidence": round(confidence, 3),
        "source": "color-heuristic",
    }


def _encode_image(image_path, max_edge=768):
    """Verkleinert und base64-kodiert das Bild fuer die Vision-API."""
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        img.thumbnail((max_edge, max_edge))
        from io import BytesIO
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("ascii")


VISION_SYSTEM = (
    "Du bist ein Kunst-Analyst fuer Sammelkarten-Illustrationen. Du bekommst "
    "das Foto einer Pokemon-Karte. Beschreibe AUSSCHLIESSLICH die "
    "Hintergrund-Landschaft/Umgebung der Illustration (die Szene, in der das "
    "Pokemon steht). Ignoriere dabei komplett: das Pokemon/die Kreatur selbst, "
    "den Kartenrahmen, jede Schrift, Zahlen, KP, Energie-Symbole, Holo-Muster "
    "und Logos. Wenn der Hintergrund knapp ist, leite den passenden Lebensraum "
    "aus dem Gesamtbild ab.\n"
    "Antworte NUR mit kompaktem JSON, keine Erklaerungen. Felder:\n"
    '"type": einer von wasser, feuer, pflanze, elektro, psycho, fee, '
    'finsternis, metall, kampf, normal;\n'
    '"name": Pokemon-Name falls lesbar, sonst null;\n'
    '"scene": Objekt mit\n'
    '   "setting" (ein praeziser englischer Satz, der das konkrete Biotop/die '
    'Umgebung benennt, z.B. "a snowy mountain coastline with an ice cave"),\n'
    '   "elements" (englische Liste konkreter Landschaftselemente, die '
    'tatsaechlich im Hintergrund zu sehen sind, z.B. ["snow","ice cave",'
    '"pine trees","frozen sea","mountains"]),\n'
    '   "lighting" (englische Beschreibung von Tageszeit/Wetter/Lichtstimmung),\n'
    '   "palette" (englische Beschreibung der dominanten Hintergrundfarben),\n'
    '   "viewpoint" (englische Beschreibung von Bildausschnitt/Blickrichtung/Tiefe);\n'
    '"environment_dna": Objekt, das NUR die WIEDERHOLBARE Umgebungs-Art '
    'beschreibt (Typen, keine konkreten Einzel-Objekte) mit englischen '
    'Feldern "vegetation" (Art der Pflanzen/Baeume, z.B. "lush deciduous '
    'foliage and bushes"), "ground" (Bodenart, z.B. "grassy soil with a '
    'stone path"), "sky" (Himmel, z.B. "bright blue sky with soft clouds"), '
    '"style" (Maltechnik/Strichfuehrung, z.B. "soft watercolor with fine ink '
    'outlines"), "horizon" (Perspektivhoehe/Horizontlinie, z.B. "low '
    'viewpoint, high horizon, looking slightly up");\n'
    '"unique_objects": englische Liste der KONKRETEN, WIEDERERKENNBAREN '
    'Einzel-Objekte/Landmarken in der Illustration, die es je nur EINMAL gibt '
    '(z.B. ["a house with a red tiled roof","a large brown tree trunk","a '
    'thick horizontal tree branch"]). Diese Liste ist eine VERBOTSLISTE fuer '
    'den Aussenbereich. Diffuse Flaechen (Gras, Himmel, Laub allgemein) '
    'gehoeren NICHT hierher;\n'
    '"edges": Objekt mit den vier Schluesseln "left","right","top","bottom". '
    'Pruefe JEDE der vier Kanten einzeln und sorgfaeltig. Jeder Wert ist eine '
    'Liste der STRUKTUR-Elemente (Baumstamm, Ast, Zweig, Dach, Gebaeude, Wand, '
    'Weg, Horizont, Bergkamm, Felskante, Gewaesserlinie o.ae.), die diese '
    'Kante beruehren, schneiden ODER im aeusseren Randdrittel dieser Kante '
    'klar auf sie zulaufen (also beim Fortsetzen ueber die Kante gefuehrt '
    'werden muessten). Nur wirklich diffuse Kanten ohne jede lineare Struktur '
    'bleiben leer. Pro Element ein Objekt mit: '
    '"element" (was es ist, engl.), '
    '"span" (Position entlang der Kante in Prozent - bei left/right als Hoehe '
    '0%=oben..100%=unten, bei top/bottom als Breite 0%=links..100%=rechts, '
    'z.B. "30-75%"), '
    '"angle" (Richtung/Neigung wo es die Kante trifft, engl., z.B. "tilted '
    'slightly right" oder "horizontal"), '
    '"thickness" (Dicke, engl.), "color" (Farbe, engl.). '
    'Diffuse Kanten (nur Himmel/Schnee/Wasser/Gras/Laub ohne klare Linien) '
    '=> leere Liste []. Nenne nur wirklich kantenkreuzende Strukturen.;\n'
    '"mood": kurze englische Farbstimmungs-Beschreibung.'
)


def vision_analysis(image_path, model="gpt-4o-mini", api_key=None):
    """Optionale Vision-Erkennung via OpenAI. Gibt None bei Fehler zurueck."""
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        b64 = _encode_image(image_path)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": VISION_SYSTEM},
                {"role": "user", "content": [
                    {"type": "text", "text": "Analysiere diese Karte."},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ]},
            ],
            response_format={"type": "json_object"},
            max_tokens=1000,
            temperature=0,
        )
        raw = resp.choices[0].message.content.strip()
        # Robust gegen ```json ... ``` Umrandung.
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        data = json.loads(raw)
        norm = T.normalize_type(data.get("type"))
        scene = data.get("scene")
        if not isinstance(scene, dict) or not scene.get("setting"):
            scene = None
        edges = data.get("edges")
        if not isinstance(edges, dict):
            edges = None
        dna = data.get("environment_dna")
        if not isinstance(dna, dict):
            dna = None
        uniq = data.get("unique_objects")
        if not isinstance(uniq, list):
            uniq = None
        else:
            uniq = [str(u).strip() for u in uniq if str(u).strip()]
        return {
            "type": norm or T.DEFAULT_TYPE,
            "name": (data.get("name") or None),
            "scene": scene,
            "environment_dna": dna,
            "unique_objects": uniq,
            "edges": edges,
            "mood": data.get("mood"),
            "source": "vision:" + model,
        }
    except Exception as exc:  # bewusst breit: Vision ist optional
        return {"error": str(exc), "source": "vision-failed"}


def analyze_card(image_path, use_vision=True, vision_model="gpt-4o-mini",
                 api_key=None, log=print):
    """Kombinierte Analyse. Vision (falls verfuegbar) bestimmt Typ/Name,
    die Farb-Analyse liefert immer Palette + Stimmung als Rueckfall.
    """
    colors = color_analysis(image_path)
    result = {
        "image": os.path.basename(image_path),
        "type": colors["type"],
        "type_confidence": colors["type_confidence"],
        "name": None,
        "scene": None,
        "environment_dna": None,
        "unique_objects": None,
        "edges": None,
        "mood": colors["mood"],
        "dominant_colors": colors["dominant_colors"],
        "analysis_source": colors["source"],
    }
    log(f"  Farb-Analyse: Typ={colors['type']} "
        f"(Konfidenz {colors['type_confidence']}), Stimmung='{colors['mood']}'")

    if use_vision:
        v = vision_analysis(image_path, model=vision_model, api_key=api_key)
        if v and "error" not in v:
            result["type"] = v["type"] or result["type"]
            result["name"] = v.get("name")
            result["scene"] = v.get("scene")
            result["environment_dna"] = v.get("environment_dna")
            result["unique_objects"] = v.get("unique_objects")
            result["edges"] = v.get("edges")
            if v.get("mood"):
                result["mood"] = v["mood"]
            result["analysis_source"] = v["source"]
            log(f"  Vision-Analyse: Typ={v['type']}, Name={v.get('name')!r}")
            if v.get("scene"):
                log(f"  Erkannte Szene: {v['scene'].get('setting')}")
            else:
                log("  Hinweis: Vision lieferte keine Szene -> Typ-Fallback")
            if v.get("unique_objects"):
                log(f"  Verbotsliste (nicht duplizieren): {v['unique_objects']}")
            if v.get("edges"):
                n = sum(len(x) for x in v["edges"].values() if isinstance(x, list))
                log(f"  Edge-Map: {n} kantenkreuzende Struktur(en) erfasst")
        elif v and "error" in v:
            log(f"  Vision-Analyse uebersprungen ({v['error']})")
        else:
            log("  Vision-Analyse uebersprungen (kein API-Key)")

    return result


SEAM_SYSTEM = (
    "Du pruefst ein Binder-Mockup. In der MITTE liegt eine ECHTE Sammelkarte "
    "mit ihrem eigenen silbernen Rahmen, Namen, KP und Textfeld; rundherum "
    "wurde per KI die Illustration ueber die Kartenkanten hinaus fortgesetzt.\n"
    "WICHTIG - was du IGNORIEREN musst (das ist KEIN Fehler): der silberne "
    "Kartenrahmen, der Textkasten, Schrift/Zahlen auf der Karte, ein leichter "
    "Helligkeits-, Glanz- oder Saettigungsunterschied zwischen Karte und "
    "Umgebung, sowie diffuse Flaechen (Himmel, Laub, Gras, Wasser, Schnee), "
    "die nur farblich grob passen muessen.\n"
    "Eine Kante ist NUR DANN schlecht, wenn eine KONKRETE lineare Struktur "
    "(Baumstamm, Ast, Dachkante, Wand, Weg, Horizont, Felskante), die an der "
    "Kartenkante klar sichtbar ist, ausserhalb FEHLT oder deutlich versetzt / "
    "im falschen Winkel / falscher Dicke weiterlaeuft (klar sichtbarer "
    "Bruch/Sprung). Du MUSST fuer jede als schlecht gemeldete Kante die "
    "konkrete Struktur benennen und wie sie versetzt ist. Kannst du keine "
    "konkrete versetzte Struktur benennen, ist die Kante ok. Sei nicht "
    "uebermaessig streng - im Zweifel ok.\n"
    "ZUSAETZLICH pruefst du auf DUPLIKATE: Dir wird eine Liste einzigartiger "
    "Objekte der Karte gegeben (z.B. 'a house with a red roof', 'a large tree "
    "trunk'). Erscheint eines davon im AUSSENbereich als eigene, zweite "
    "Instanz (zusaetzliches Haus/Dach, zweiter grosser Stamm usw.)? Jedes "
    "gefundene Duplikat ist ein Fehler.\n"
    "bad_edges enthaelt AUSSCHLIESSLICH die Schluessel \"left\"/\"right\"/"
    "\"top\"/\"bottom\" der wirklich gebrochenen Kanten. \"duplicates\" listet "
    "die duplizierten Objekte (aus der Liste) als englische Strings. \"ok\" "
    "muss genau dann true sein, wenn bad_edges UND duplicates leer sind.\n"
    "Antworte NUR als JSON: {\"ok\": true|false, \"bad_edges\": [...], "
    "\"duplicates\": [...], \"notes\": \"kurz\"}."
)


def seam_check(image, unique_objects=None, api_key=None, model="gpt-4o-mini",
               max_edge=768):
    """Prueft ein Composite (Karte in der Mitte) auf saubere Kanten-Anschluesse
    UND auf duplizierte einzigartige Objekte im Aussenbereich.

    image: Pfad oder PIL.Image. unique_objects: Verbotsliste (aus der Analyse).
    Gibt dict(ok, bad_edges, duplicates, notes) zurueck oder None, wenn kein
    Key/Fehler (dann wird die Pruefung uebersprungen).
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        from io import BytesIO
        if isinstance(image, str):
            im = Image.open(image)
        else:
            im = image
        im = im.convert("RGB")
        im.thumbnail((max_edge, max_edge))
        buf = BytesIO(); im.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        objs = unique_objects or []
        obj_text = ("Einzigartige Objekte der Karte (Verbotsliste fuer aussen): "
                    + "; ".join(objs)) if objs else "Keine Objektliste uebergeben."
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SEAM_SYSTEM},
                {"role": "user", "content": [
                    {"type": "text", "text": obj_text + " Schliessen alle "
                     "kantenkreuzenden Strukturen sauber an, und taucht ein "
                     "einzigartiges Objekt aussen doppelt auf?"},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ]},
            ],
            response_format={"type": "json_object"},
            max_tokens=250,
            temperature=0,
        )
        data = json.loads(resp.choices[0].message.content)
        bad = data.get("bad_edges") or []
        bad = [e for e in bad if e in ("left", "right", "top", "bottom")]
        dups = data.get("duplicates") or []
        dups = [str(d).strip() for d in dups if str(d).strip()]
        return {"ok": bool(data.get("ok")) and not bad and not dups,
                "bad_edges": bad,
                "duplicates": dups,
                "notes": data.get("notes", "")}
    except Exception as exc:
        return {"error": str(exc)}
