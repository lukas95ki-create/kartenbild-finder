# eBay-Vorlagen (File Exchange)

Hier gehören die beiden **originalen eBay-Vorlagen-CSVs** hinein, aus denen die
Header für `ebay-export.html` stammen:

| Datei | Zweck | Ziel-Export |
|-------|-------|-------------|
| *(Einzel-/Draft-Vorlage)* | Kopfzeile für Einzel-Entwürfe | Export A → `ebay-entwuerfe.csv` |
| *(Varianten-/Kategorie-Vorlage)* | Kopfzeile für Varianten-Angebote | Export B → `ebay-varianten.csv` |

> Die konkreten Vorlagendateien werden vom Projektinhaber committet.

## Wichtig

Die beiden Header sind in `ebay-export.html` **fest hinterlegt** (Konstanten
`HEADER_A` und `HEADER_B`) und stimmen 1:1 mit den in der Aufgabe angegebenen
Vorlagen überein. Das Tool funktioniert also auch, wenn dieser Ordner (noch)
leer ist.

Wenn sich eine offizielle eBay-Vorlage ändert (z. B. neue File-Exchange-Version
oder zusätzliche Pflichtspalten), bitte:

1. die neue Vorlage hier ablegen,
2. den entsprechenden Header in `ebay-export.html` (`HEADER_A` / `HEADER_B`)
   aktualisieren – die Spaltenreihenfolge steuert dort direkt die
   CSV-Serialisierung.
