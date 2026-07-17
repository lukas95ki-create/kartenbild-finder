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


def build_prompt(analysis, extra_style=None):
    """Erzeugt (prompt, negative_prompt) aus dem Analyse-Dict."""
    entry = T.entry_for(analysis.get("type", T.DEFAULT_TYPE))
    mood = analysis.get("mood") or ""
    scene = entry["scene"]
    palette = entry["palette"]

    parts = [
        scene + ".",
        f"Color palette: {palette}.",
    ]
    if mood:
        parts.append(f"Overall mood: {mood}.")
    parts.append("Pure environment scene only, empty of any living beings.")
    parts.append(STYLE + ".")
    if extra_style:
        parts.append(extra_style + ".")
    parts.append("Strictly exclude: " + NEGATIVE + ".")

    prompt = " ".join(parts)
    return prompt, NEGATIVE
