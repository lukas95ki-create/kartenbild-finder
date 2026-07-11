# eBay-Vorlagen (Originale)

Hier liegen die beiden **originalen eBay-Vorlagen-CSVs**, aus denen die
Kopfzeilen der Exporte in `kartenbild-finder-v6.html` stammen:

| Datei | Zweck | Ziel-Export |
|-------|-------|-------------|
| `eBay-draft-listing-template-*.csv` | Entwurfs-Vorlage „eBay-draft-listings-template_DE“ (4 `#INFO`-Zeilen + Kopfzeile) | Export A → `ebay-entwuerfe.csv` |
| `eBay-category-listing-template-*.csv` | Kategorie-Vorlage `fx_category_template_EBAY_DE` für Kategorie 183454 (Info-Zeile + Kopfzeile, 105 Spalten) | Export B → `ebay-varianten.csv` |

## Wichtig

Die Kopf-/Info-Zeilen sind in `kartenbild-finder-v6.html` **buchstabengetreu
fest hinterlegt** – in den DOM-freien Code-Blöcken zwischen den Markern
`@EBAY_DRAFT_CSV_START/_END` (Export A) und `@EBAY_CATEGORY_CSV_START/_END`
(Export B). Die Spaltenreihenfolge dort steuert direkt die CSV-Serialisierung.

Die automatisierten Tests (`node --test`, siehe
`tests/ebay-draft-csv.test.mjs`) gleichen die hinterlegten Kopfzeilen **gegen
die Dateien in diesem Ordner** ab. Die Dateinamen dürfen sich ändern, solange
sie mit `eBay-draft-listing-template` bzw. `eBay-category-listing-template`
beginnen und auf `.csv` enden – die Tests finden sie per Präfix.

Wenn sich eine offizielle eBay-Vorlage ändert (z. B. neue Version oder
zusätzliche Pflichtspalten), bitte:

1. die neue Vorlage **unverändert** hier ablegen (nicht in Excel öffnen und
   neu speichern – das verfälscht BOM/Trennzeichen/Zeilenenden),
2. die alte Vorlagendatei entfernen,
3. `node --test` ausführen – die Tests zeigen dann exakt, welche
   hinterlegten Kopfzeilen angepasst werden müssen.

Hinweis: Die Original-Kategorie-Vorlage enthält unterhalb der Kopfzeile nur
noch `Info;…`-Hinweiszeilen (Pflicht-Aspekte, empfohlene Werte). Diese werden
im Export **nicht** mit ausgegeben – eBay identifiziert den Upload an der
Info-Kennungszeile und der Kopfzeile.
