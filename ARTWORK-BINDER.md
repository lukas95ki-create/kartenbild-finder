# Artwork-Binder-Generator

Vollautomatische Pipeline: aus **einem Kartenfoto** entsteht ein
**druckfertiges 9-Kachel-Binder-PDF-Paar** (A4 + US Letter) mit
KI-generiertem Landschafts-Hintergrund. Die mittlere Kachel bleibt frei –
dort kommt später die echte Pokémon-Karte in die 9-Pocket-Seite.

Ein Aufruf = fertiges PDF-Paar. Analyse → Prompt → Bildgenerierung →
Zuschnitt → PDF laufen automatisch.

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env      # OPENAI_API_KEY eintragen
```

Der API-Key wird ausschließlich aus der Umgebung / `.env` gelesen
(`OPENAI_API_KEY`) – niemals hartcodiert.

## Benutzung

Einzelne Karte:

```bash
python make_binder.py karte_wartortle.jpg --output wartortle --mode empty --cut-icons
```

Batch (z. B. ~50 Fotos in einem Ordner):

```bash
python make_binder.py --batch fotos/ --out-dir output --mode outlined --cut-icons
```

Ohne API testen (Platzhalter-Hintergrund aus der erkannten Farbstimmung):

```bash
python make_binder.py karte.jpg --offline
```

### Wichtige Flags

| Flag | Wirkung |
|------|---------|
| `--mode empty\|outlined` | Mittlere Kachel leer (nur Hintergrund) oder mit gestrichelter Platzhalter-Linie in Kartengröße |
| `--cut-icons` | Kleine Vektor-Scheren-Icons (≈4,5 mm) mittig auf jeder Schnittlinie |
| `--crop-marks` | Eckmarkierungen außerhalb des Rasters |
| `--offline` | Ohne Bild-API, Platzhalter-Hintergrund (zum Testen / als Fallback) |
| `--no-vision` | Vision-Typ/Name-Erkennung abschalten, nur Farb-Heuristik |
| `--type wasser` | Erkannten Typ manuell überschreiben |
| `--prompt "..."` | Bild-Prompt komplett manuell vorgeben |
| `--only A4\|letter` | Nur ein Seitenformat erzeugen (Standard: beide) |
| `--dpi 300` | Zielauflösung für Zuschnitt/PDF |
| `--model gpt-image-1` | Bild-Modell |
| `--provider openai` | Anbieter (austauschbar angelegt) |

## Pipeline & Ausgabe

Pro Karte entsteht `output/<name>/`:

| Datei | Inhalt |
|-------|--------|
| `<name>_log.json` | Erkannter Typ, Farben, Prompt, Generierungs-Meta – jeder Zwischenschritt nachvollziehbar |
| `<name>_artwork.png` | Generiertes Rohbild (voll, ungeschnitten) – für eigenen Neuzuschnitt |
| `<name>_grid.png` | Auf 189×264 mm zugeschnittenes Raster-Bild (300 DPI) |
| `<name>_A4.pdf` | Druckfertiges A4-PDF |
| `<name>_letter.pdf` | Druckfertiges US-Letter-PDF |

**Manuelle Korrektur:** Liegt die automatische Typ-Erkennung daneben, den
Lauf mit `--type <typ>` oder `--prompt "..."` wiederholen – das
`_log.json` zeigt, was erkannt wurde.

## Details der Schritte

1. **Analyse** – Farb-Analyse (Pillow, immer offline): dominante Farben,
   Stimmung, Typ-Heuristik. Optional Vision-API (`gpt-4o-mini`) für
   Typ + Pokémon-Name. Alles nur zur internen Prompt-Steuerung, nichts
   davon landet sichtbar im Endprodukt.
2. **Prompt** – typ-passende Landschafts-Szene (Wasser → Ozean/Riff,
   Feuer → Vulkan usw.). Schließt explizit **Kreaturen, Pokémon-ähnliche
   Wesen, Logos und jede Schrift** aus – reine Umgebungsszene, painterly.
3. **Generierung** – OpenAI Images API (`gpt-image-1`) in höchster
   Auflösung, danach Upscaling auf 300-DPI-Zielgröße. Bei fehlendem Key
   oder API-Fehler automatischer Fallback auf Platzhalter.
4. **Zuschnitt** – Cover-Fit ins 189×264 mm-Raster (3×3 × 63×88 mm,
   ≈744×1039 px/Kachel bei 300 DPI), mittig.
5. **Aussparung** – mittlere Kachel je nach `--mode`.
6. **PDF** – A4 und Letter aus einem Lauf, Raster mittig, gestrichelte
   graue Schnittlinien, optional Scheren-Icons und Eckmarkierungen.
7. **Output** – siehe Tabelle oben.

## Anderen Bild-Anbieter anbinden

In `artwork_binder/generate.py` eine Funktion analog zu `generate_openai`
ergänzen und in `generate_image()` unter einem neuen `--provider`-Wert
einhängen. Der Rest der Pipeline bleibt unverändert.
