"""Pokemon-Typen: Farb-Heuristik und Szenen-Zuordnung.

Zentrale Tabelle, aus der sowohl die (offline) Farb-basierte Typ-Schaetzung
als auch der Bild-Prompt gespeist werden. Alles rein zur internen
Prompt-Steuerung - nichts davon landet sichtbar im Endprodukt.
"""

# Reihenfolge = Prioritaet bei der Farb-Heuristik (erste passende Regel gewinnt).
# hue-Bereiche in Grad (0-360) auf dem HSV-Farbkreis.
TYPE_TABLE = {
    "wasser": {
        "labels": ["wasser", "water", "aqua"],
        "hue": [(175, 255)],          # cyan - blau
        "min_sat": 0.18,
        "scene": "a serene coastal ocean reef, clear turquoise water, gentle "
                 "waves over pale sand, soft underwater light rays",
        "palette": "cool aquamarine, teal, deep blue and soft foam white",
    },
    "feuer": {
        "labels": ["feuer", "fire", "flamme"],
        "hue": [(0, 20), (345, 360)],  # rot - orange
        "min_sat": 0.25,
        "scene": "a dramatic volcanic landscape at dusk, glowing lava flows, "
                 "warm ember light, rugged basalt rock and rising heat haze",
        "palette": "molten orange, deep crimson, warm gold and charcoal black",
    },
    "pflanze": {
        "labels": ["pflanze", "grass", "blatt", "leaf"],
        "hue": [(75, 165)],           # gruen
        "min_sat": 0.18,
        "scene": "a lush verdant forest clearing, sunbeams through the canopy, "
                 "moss covered stones, ferns and soft dappled light",
        "palette": "vivid emerald, moss green, golden sunlight and earthy brown",
    },
    "elektro": {
        "labels": ["elektro", "electric", "blitz"],
        "hue": [(45, 65)],            # gelb
        "min_sat": 0.35,
        "scene": "a vast twilight sky above open plains crackling with distant "
                 "lightning, electric energy arcs and charged storm clouds",
        "palette": "bright yellow, electric white, deep indigo and stormy grey",
    },
    "psycho": {
        "labels": ["psycho", "psychic", "psy"],
        "hue": [(265, 300)],          # violett
        "min_sat": 0.2,
        "scene": "a surreal cosmic dreamscape, drifting nebulae, floating "
                 "crystalline formations and soft glowing mist",
        "palette": "deep violet, magenta, cosmic pink and starlit indigo",
    },
    "fee": {
        "labels": ["fee", "fairy"],
        "hue": [(300, 345)],          # pink - magenta
        "min_sat": 0.15,
        "scene": "an enchanted blossom meadow at golden hour, drifting petals, "
                 "soft bokeh light and gentle rolling hills",
        "palette": "soft pink, rose, lilac and warm pastel gold",
    },
    "finsternis": {
        "labels": ["finsternis", "dark", "unlicht"],
        "hue": [(200, 260)],          # dunkles blau-violett (niedrige Helligkeit)
        "min_sat": 0.0,
        "max_val": 0.32,             # nur bei sehr dunklen Karten
        "scene": "a moonlit nocturnal landscape, silvered clouds over dark "
                 "hills, deep shadow and a faint cold glow on the horizon",
        "palette": "midnight blue, deep purple, cold silver and near-black",
    },
    "metall": {
        "labels": ["metall", "steel", "stahl"],
        "hue": [(0, 360)],           # grau/silber -> ueber niedrige Saettigung
        "max_sat": 0.12,
        "min_val": 0.35,
        "scene": "a sleek industrial canyon of polished metal and stone, cool "
                 "reflective surfaces, sharp light and geometric structures",
        "palette": "brushed silver, cool grey, steel blue and pale highlight",
    },
    "kampf": {
        "labels": ["kampf", "fighting", "gestein", "boden"],
        "hue": [(20, 45)],           # braun/ocker
        "min_sat": 0.2,
        "scene": "a rugged desert canyon under harsh sun, weathered rock "
                 "formations, dry earth, dust and long dramatic shadows",
        "palette": "burnt sienna, ochre, sandy tan and warm terracotta",
    },
}

# Neutraler Rueckfall, wenn keine Regel greift.
DEFAULT_TYPE = "normal"
DEFAULT_ENTRY = {
    "labels": ["normal", "farblos", "colorless"],
    "hue": [],
    "scene": "a calm open grassland under a wide gentle sky, soft rolling "
             "hills, scattered light clouds and warm diffuse daylight",
    "palette": "warm neutral tones, soft green, cream and gentle sky blue",
}


def entry_for(type_name):
    """Liefert den Tabellen-Eintrag fuer einen Typnamen (oder Default)."""
    return TYPE_TABLE.get(type_name, DEFAULT_ENTRY)


def normalize_type(text):
    """Mappt beliebigen Freitext (dt./engl.) auf einen internen Typ-Schluessel."""
    if not text:
        return None
    t = text.strip().lower()
    if t in TYPE_TABLE or t == DEFAULT_TYPE:
        return t
    for key, entry in TYPE_TABLE.items():
        if t in entry["labels"]:
            return key
    if t in DEFAULT_ENTRY["labels"]:
        return DEFAULT_TYPE
    return None
