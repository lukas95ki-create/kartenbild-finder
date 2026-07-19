"""Schritt 3: Bild-Generierung via API.

Standard-Anbieter: OpenAI Images API (gpt-image-1). Der Aufruf ist so
gekapselt, dass sich andere Anbieter leicht ergaenzen lassen. Der API-Key
kommt ausschliesslich aus der Umgebung (.env) - nie hartcodiert.

Zusaetzlich gibt es einen Offline-Platzhalter-Generator: er baut aus der
erkannten Farbstimmung einen Verlaufs-Hintergrund. So laesst sich die
komplette Pipeline (Zuschnitt + PDF) ohne API-Key testen und der Lauf
bricht nicht ab, falls kein Key gesetzt ist.
"""
import base64
import os

from io import BytesIO
from PIL import Image, ImageDraw, ImageFilter


# gpt-image-1 unterstuetzt bis 1536px Kante; Portrait passt am besten zum
# hochkanten 189x264mm-Raster. Danach wird auf Zielaufloesung hochskaliert.
OPENAI_SIZE = "1024x1536"


def _placeholder_image(analysis, width, height):
    """Baut einen weichen Verlaufs-Hintergrund aus den dominanten Farben."""
    cols = analysis.get("dominant_colors") or []
    if cols:
        top = tuple(cols[0]["rgb"])
        bottom = tuple(cols[-1]["rgb"]) if len(cols) > 1 else top
    else:
        top, bottom = (120, 140, 160), (40, 50, 70)

    base = Image.new("RGB", (1, height))
    for y in range(height):
        t = y / max(height - 1, 1)
        px = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        base.putpixel((0, y), px)
    img = base.resize((width, height))

    # Ein paar weiche Licht-Flecken fuer etwas Textur.
    overlay = Image.new("RGB", (width, height), (0, 0, 0))
    d = ImageDraw.Draw(overlay)
    mids = [tuple(c["rgb"]) for c in cols[1:3]] or [(200, 200, 200)]
    import random
    rnd = random.Random(sum(top) + sum(bottom))
    for i in range(6):
        cx, cy = rnd.randint(0, width), rnd.randint(0, height)
        r = rnd.randint(width // 6, width // 3)
        col = mids[i % len(mids)]
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    overlay = overlay.filter(ImageFilter.GaussianBlur(width // 8))
    return Image.blend(img, overlay, 0.35)


def generate_openai(prompt, width, height, model="gpt-image-1",
                    api_key=None, size=OPENAI_SIZE):
    """Ruft die OpenAI Images API auf und liefert ein PIL-Image."""
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY fehlt (in .env setzen).")
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    resp = client.images.generate(
        model=model,
        prompt=prompt,
        size=size,
        quality="high",
        n=1,
    )
    b64 = resp.data[0].b64_json
    img = Image.open(BytesIO(base64.b64decode(b64))).convert("RGB")
    return img


STABILITY_OUTPAINT_URL = "https://api.stability.ai/v2beta/stable-image/edit/outpaint"


def outpaint_stability(card_img, left, right, up, down, prompt=None,
                       creativity=0.5, api_key=None, output_format="png"):
    """Echtes pixelbasiertes Outpainting via Stability AI.

    Das Eingabebild (die Kartenillustration) wird um die angegebenen
    Pixelmengen nach links/rechts/oben/unten erweitert. Das Modell
    konditioniert direkt auf die echten Randpixel - dadurch schliessen
    Strukturen an der Kante an. Liefert ein PIL-Image (das fertige Raster).
    """
    api_key = api_key or os.environ.get("STABILITY_API_KEY")
    if not api_key:
        raise RuntimeError("STABILITY_API_KEY fehlt (in .env setzen).")
    import requests
    buf = BytesIO()
    card_img.convert("RGB").save(buf, "PNG")
    buf.seek(0)
    data = {"left": int(left), "right": int(right), "up": int(up),
            "down": int(down), "creativity": float(creativity),
            "output_format": output_format}
    if prompt:
        data["prompt"] = prompt[:9000]
    resp = requests.post(
        STABILITY_OUTPAINT_URL,
        headers={"Authorization": f"Bearer {api_key}", "Accept": "image/*"},
        files={"image": ("card.png", buf, "image/png")},
        data=data,
        timeout=180,
    )
    if resp.status_code != 200:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text[:300]
        raise RuntimeError(f"Stability {resp.status_code}: {detail}")
    return Image.open(BytesIO(resp.content)).convert("RGB")


def edit_openai(image_rgba, mask_rgba, prompt, model="gpt-image-2",
                api_key=None, size="1024x1536", quality="high"):
    """Ruft OpenAI images.edit (Outpainting) auf und liefert ein PIL-Image.

    image_rgba: Canvas mit Kartenpixeln in der Mitte, aussen transparent.
    mask_rgba:  RGBA-Maske - transparente Bereiche werden generiert, opake
                (die Kartenmitte) bleiben geschuetzt.
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY fehlt (in .env setzen).")
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    cb = BytesIO(); image_rgba.save(cb, "PNG"); cb.seek(0)
    mb = BytesIO(); mask_rgba.save(mb, "PNG"); mb.seek(0)
    resp = client.images.edit(
        model=model,
        image=("canvas.png", cb, "image/png"),
        mask=("mask.png", mb, "image/png"),
        prompt=prompt,
        size=size,
        quality=quality,
        n=1,
    )
    b64 = resp.data[0].b64_json
    return Image.open(BytesIO(base64.b64decode(b64))).convert("RGB")


def generate_image(prompt, analysis, width, height, provider="openai",
                   model="gpt-image-1", api_key=None, offline=False,
                   log=print):
    """Zentrale Generierungs-Funktion.

    Gibt (image, meta) zurueck. meta beschreibt, wie das Bild entstand,
    damit der Schritt nachvollziehbar bleibt. Faellt bei fehlendem Key oder
    API-Fehler automatisch auf den Offline-Platzhalter zurueck.
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY")

    if offline or (provider == "openai" and not api_key):
        reason = "explizit --offline" if offline else "kein OPENAI_API_KEY"
        log(f"  Bild-Generierung: Offline-Platzhalter ({reason})")
        img = _placeholder_image(analysis, width, height)
        return img, {"provider": "placeholder", "reason": reason}

    if provider == "openai":
        log(f"  Bild-Generierung: OpenAI {model} @ {OPENAI_SIZE} ...")
        try:
            img = generate_openai(prompt, width, height, model=model,
                                  api_key=api_key)
            return img, {"provider": "openai", "model": model,
                         "size": OPENAI_SIZE}
        except Exception as exc:
            log(f"  API-Fehler ({exc}) -> Offline-Platzhalter")
            img = _placeholder_image(analysis, width, height)
            return img, {"provider": "placeholder", "reason": f"api-error: {exc}"}

    raise ValueError(f"Unbekannter Provider: {provider}")
