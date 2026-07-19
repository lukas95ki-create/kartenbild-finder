"""Schritt 2: Bildgenerierungs-Prompt bauen.

Baut aus Analyse-Ergebnis (Typ + Stimmung) einen Text-Prompt fuer die
Bild-KI. Der Prompt schliesst explizit alle Kreaturen, Pokemon-aehnlichen
Wesen, Logos und jede Schrift aus - es soll eine reine Landschafts-/
Umgebungsszene entstehen.
"""
from . import types as T

# Harte Ausschluesse - stehen in jedem Prompt und zusaetzlich im Negativ-Feld.
NEGATIVE = (
    "no creatures, no animals, no fantasy beasts, no monsters, "
    "no pokemon or pokemon-like beings, no characters, no people, "
    "no logos, no watermark, no text, no letters, no numbers, "
    "no frame, no border, no user interface"
)

STYLE = (
    "painterly digital art, artistic concept-art landscape, rich high-quality "
    "color palette, soft cinematic lighting, atmospheric depth, "
    "highly detailed environment, no signature"
)


def _clean(text):
    return str(text).strip().rstrip(".")


def _prompt_from_scene(scene, mood):
    """Baut den Prompt aus der individuell erkannten Kartenszene."""
    parts = [_clean(scene["setting"]) + "."]

    elements = scene.get("elements")
    if isinstance(elements, (list, tuple)) and elements:
        parts.append("Environment features: " + ", ".join(_clean(e) for e in elements) + ".")
    elif isinstance(elements, str) and elements.strip():
        parts.append("Environment features: " + _clean(elements) + ".")

    if scene.get("lighting"):
        parts.append("Lighting: " + _clean(scene["lighting"]) + ".")
    if scene.get("palette"):
        parts.append("Color palette: " + _clean(scene["palette"]) + ".")
    elif mood:
        parts.append(f"Overall mood: {mood}.")
    if scene.get("viewpoint"):
        parts.append("Composition: " + _clean(scene["viewpoint"]) + ".")
    return parts


def _prompt_from_type(analysis, mood):
    """Rueckfall: generische Szene aus der Typ-Tabelle (offline / ohne Vision)."""
    entry = T.entry_for(analysis.get("type", T.DEFAULT_TYPE))
    parts = [entry["scene"] + ".", f"Color palette: {entry['palette']}."]
    if mood:
        parts.append(f"Overall mood: {mood}.")
    return parts


def build_prompt(analysis, extra_style=None):
    """Erzeugt (prompt, negative_prompt) aus dem Analyse-Dict.

    Wenn die Vision-Analyse eine konkrete Szene geliefert hat, wird der
    Prompt individuell daraus gebaut (Landschaft, Elemente, Licht, Palette,
    Blickrichtung), sodass der Hintergrund erkennbar zur jeweiligen Karte
    passt. Ohne Szene (offline / --no-vision) greift die generische
    Typ-Tabelle als Rueckfall.
    """
    mood = analysis.get("mood") or ""
    scene = analysis.get("scene")
    if isinstance(scene, dict) and scene.get("setting"):
        parts = _prompt_from_scene(scene, mood)
    else:
        parts = _prompt_from_type(analysis, mood)

    parts.append("Pure landscape environment scene only, no living beings, "
                 "no creatures.")
    parts.append(STYLE + ".")
    if extra_style:
        parts.append(extra_style + ".")
    parts.append("Strictly exclude: " + NEGATIVE + ".")

    return " ".join(parts), NEGATIVE


# Ausschluesse speziell fuer den generierten AUSSEN-Bereich beim Outpainting.
# (Die Karte in der Mitte darf/soll Kreatur, Rahmen und Text enthalten -
#  nur der neu gemalte Rand muss frei davon sein.)
OUTPAINT_NEGATIVE = (
    "Extremely important: the outer painted areas must contain ONLY the same "
    "kind of empty scenery and environment as the card's background. Do NOT "
    "repeat, mirror, duplicate or extend the creature/character that sits on "
    "the card - it must appear nowhere outside the card. No creatures, no "
    "animals, no monsters, no pokemon-like beings, no characters, no people, "
    "no eyes, no faces, no text, no letters, no numbers, no logos, no "
    "watermark, no card frame, no borders, no panels in the generated areas"
)


_EDGE_LABEL = {"left": "left", "right": "right", "top": "top", "bottom": "bottom"}
_EDGE_AXIS = {"left": "height", "right": "height", "top": "width", "bottom": "width"}


def _edge_instructions(edges):
    """Baut pro Kante eine explizite Fortsetzungs-Anweisung aus der Edge-Map.

    Nur was eine Kante nachweislich verlaesst, wird dort fortgesetzt - am
    Austrittspunkt, gern hinter einem natuerlichen Verdecker (Busch/Laub)
    kaschiert, damit kleine Ungenauigkeiten nicht auffallen.
    """
    lines = []
    if not isinstance(edges, dict):
        return lines
    for side in ("left", "right", "top", "bottom"):
        items = edges.get(side)
        if not isinstance(items, (list, tuple)) or not items:
            continue
        axis = _EDGE_AXIS[side]
        for it in items:
            if not isinstance(it, dict) or not it.get("element"):
                continue
            desc = _clean(it["element"])
            det = []
            if it.get("span"):
                det.append(f"at {_clean(it['span'])} along the {axis}")
            if it.get("angle"):
                det.append(_clean(it["angle"]))
            if it.get("thickness"):
                det.append(_clean(it["thickness"]))
            if it.get("color"):
                det.append(_clean(it["color"]))
            tail = (" (" + ", ".join(det) + ")") if det else ""
            lines.append(
                f"At the {side} card edge the {desc}{tail} exits the crop - "
                f"continue ONLY that one element straight beyond the edge at "
                f"the same position, scale, angle and color; you may softly "
                f"hide the transition behind natural foliage or bushes.")
    return lines


def _dna_clause(analysis):
    """Umgebungs-DNA (wiederholbare Art der Umgebung) fuer den Aussenbereich."""
    scene = analysis.get("scene") if isinstance(analysis.get("scene"), dict) else {}
    dna = analysis.get("environment_dna") if isinstance(analysis.get("environment_dna"), dict) else {}
    bits = []
    palette = dna.get("palette") or scene.get("palette")
    light = dna.get("light") or scene.get("lighting")
    if palette:
        bits.append("the same color palette (" + _clean(palette) + ")")
    if light:
        bits.append("the same light direction and time of day (" + _clean(light) + ")")
    if dna.get("style"):
        bits.append("the same brushwork and painting style (" + _clean(dna["style"]) + ")")
    if dna.get("vegetation"):
        bits.append("the same kind of vegetation (" + _clean(dna["vegetation"]) + ")")
    if dna.get("ground"):
        bits.append("the same kind of ground (" + _clean(dna["ground"]) + ")")
    if dna.get("sky"):
        bits.append("the same kind of sky (" + _clean(dna["sky"]) + ")")
    horizon = dna.get("horizon") or scene.get("viewpoint")
    if horizon:
        bits.append("one consistent horizon height and perspective (" + _clean(horizon) + ")")
    if not bits:
        bits = ["the same palette, light, brushwork and perspective"]
    return "Use " + ", ".join(bits) + " everywhere, at one consistent scale."


def _forbid_clause(analysis, escalate=None):
    """Dynamische Verbotsliste aus den einzigartigen Objekten der Karte."""
    objs = analysis.get("unique_objects") or []
    objs = [_clean(o) for o in objs if str(o).strip()]
    if escalate:
        objs = list(dict.fromkeys(objs + [_clean(o) for o in escalate]))
    if not objs:
        return ("Do NOT duplicate any recognizable landmark from the card. No "
                "second house, rooftop, building or large tree trunk anywhere "
                "in the outer area.")
    listed = "; ".join(objs)
    return ("The card already contains these unique objects: " + listed + ". Do "
            "NOT paint any additional or second instance of them anywhere in "
            "the outer area (no extra house/rooftop/building, no second large "
            "tree trunk). The only trunk or branch allowed outside the card is "
            "the direct continuation of the one that exits a card edge.")


def build_outpaint_prompt(analysis, extra_style=None, focus_edges=None,
                          escalate_forbid=None):
    """Prompt fuer das masken-basierte Card-Outpainting (images.edit).

    Konzept: Die Karte ist ein DETAIL-AUSSCHNITT eines groesseren Gemaeldes.
    Das Modell malt den REST dieses Gemaeldes drumherum - die weitere
    Umgebung (mehr Himmel, Laub, Wiese, Weg), NICHT eine Wiederholung der
    Karten-Motive. Umgebungs-DNA wird uebernommen, einzigartige Objekte
    (Haus, grosser Stamm ...) sind im Aussenbereich verboten. Nur echte
    kantenkreuzende Strukturen (Edge-Map) werden fortgesetzt.

    focus_edges:     Retry - Kanten, deren Struktur nachgebessert werden muss.
    escalate_forbid: Retry - Objekte, die aussen faelschlich dupliziert wurden.
    """
    edges = analysis.get("edges")
    mood = analysis.get("mood") or ""

    parts = [
        "The center of this canvas shows a DETAIL CROP of a larger painting. "
        "Paint the REST of that larger painting all around it: the wider "
        "surrounding environment, NOT a repetition of what the detail already "
        "shows. Any creature or character stays only on the central card and "
        "must never reappear outside it."
    ]
    # Hinweis: Das Setting wird bewusst NICHT woertlich uebernommen - es nennt
    # oft die einzigartige Landmarke ("garden with a house"), was das Modell
    # zum Duplizieren verleitet. Die Umgebung kommt stattdessen aus der DNA.

    # Umgebungs-DNA (wiederholbar) einsetzen.
    parts.append(_dna_clause(analysis))

    # Kantenweise Struktur-Fortsetzung (nur echte Austritte).
    edge_lines = _edge_instructions(edges)
    if edge_lines:
        parts.extend(edge_lines)

    # Verbot: keine duplizierten Landmarken.
    parts.append(_forbid_clause(analysis, escalate=escalate_forbid))
    parts.append(
        "No duplicated landmarks. The outer area should mostly show MORE of "
        "the environment - more sky, more foliage, open ground, a path "
        "continuing - not new focal objects. Keep one consistent scale, "
        "horizon line and perspective across the entire image, so it reads as "
        "one single painting with the card as a crop inside it.")

    # Retry: gezielte Verschaerfung fuer problematische Kanten.
    if focus_edges:
        sides = ", ".join(s for s in focus_edges if s in _EDGE_LABEL)
        if sides:
            parts.append(
                f"CRITICAL: the {sides} edge(s) previously did not line up. "
                f"Make the structure crossing the {sides} edge(s) continue "
                f"perfectly aligned - same position along the edge, same angle "
                f"and thickness - with no visible offset or break.")
    if escalate_forbid:
        parts.append(
            "CRITICAL: previously a duplicated object appeared outside. Remove "
            "any second copy of: " + "; ".join(_clean(o) for o in escalate_forbid)
            + ". Replace that area with plain surrounding environment.")

    if mood:
        parts.append(f"Overall mood: {mood}.")
    parts.append(STYLE + ".")
    if extra_style:
        parts.append(extra_style + ".")
    parts.append(OUTPAINT_NEGATIVE + ".")

    return " ".join(parts), OUTPAINT_NEGATIVE
