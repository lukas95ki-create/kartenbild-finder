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
    "Du bist ein Bild-Analyst. Du bekommst das Foto einer Pokemon-Sammelkarte. "
    "Antworte NUR mit kompaktem JSON, keine Erklaerungen. Felder: "
    '"type" (einer von: wasser, feuer, pflanze, elektro, psycho, fee, '
    'finsternis, metall, kampf, normal), '
    '"name" (Pokemon-Name falls lesbar, sonst null), '
    '"mood" (kurze englische Farbstimmungs-Beschreibung).'
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
            max_tokens=120,
            temperature=0,
        )
        raw = resp.choices[0].message.content.strip()
        # Robust gegen ```json ... ``` Umrandung.
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        data = json.loads(raw)
        norm = T.normalize_type(data.get("type"))
        return {
            "type": norm or T.DEFAULT_TYPE,
            "name": (data.get("name") or None),
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
            if v.get("mood"):
                result["mood"] = v["mood"]
            result["analysis_source"] = v["source"]
            log(f"  Vision-Analyse: Typ={v['type']}, Name={v.get('name')!r}")
        elif v and "error" in v:
            log(f"  Vision-Analyse uebersprungen ({v['error']})")
        else:
            log("  Vision-Analyse uebersprungen (kein API-Key)")

    return result
