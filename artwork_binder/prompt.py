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
