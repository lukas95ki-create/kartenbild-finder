# Test-Checkliste (manuell)

Diese Punkte sollten nach Änderungen kurz von Hand geprüft werden.
Am besten je einmal **lokal** (Datei per Doppelklick öffnen) **und** **gehostet**
(z. B. Netlify), sowie einmal am **Handy**.

> Hinweis zu Bildern: Die Kartenbilder kommen von `pokezentrum.de`. In manchen
> Vorschau-/Sandbox-Umgebungen werden externe Bilder blockiert – dann erscheint
> statt des Bildes ein Platzhalter („kein Bild“). Das ist kein Fehler der App;
> im echten Browser (Chrome/Safari) laden die Bilder normal.

## 0. Dateien / Struktur
- [ ] Im Hauptverzeichnis liegen: `index.html`, `erfassung.html`,
      `kartenbild-finder-v6.html`, `ebay-export.html`, `sets-data.js`.
- [ ] Alles öffnet sich per Doppelklick (Protokoll `file://`) ohne Fehler.

## 1. Startseite `index.html`
- [ ] Drei Kacheln sichtbar: „Kartenbild-Finder“, „Karten-Erfassung“ und „eBay-Export“.
- [ ] Klick auf Kachel 1 öffnet `kartenbild-finder-v6.html`.
- [ ] Klick auf Kachel 2 öffnet `erfassung.html`.
- [ ] Klick auf Kachel 3 öffnet `ebay-export.html`.

## 2. Kartenbild-Finder `kartenbild-finder-v6.html` (unverändertes Verhalten)
- [ ] Oben steht „48 Sets geladen“ (Set-Daten kommen jetzt aus `sets-data.js`).
- [ ] Sprach-Dropdown und Set-Dropdown sind befüllt.
- [ ] Nummer eingeben (z. B. `46`) + „Suchen“ → Karte(n) werden angezeigt.
- [ ] Namenssuche (z. B. `Darkrai`) funktioniert.
- [ ] Buttons „Alle Karten“, „ex-Karten“ usw. zeigen passende Karten.

## 3. Erfassen (`erfassung.html`, Tab „Erfassen“)
- [ ] Set-Dropdown ist **befüllt** und **nach Sprache gruppiert** (Optgroups Japanisch/Deutsch/Chinesisch).
      Ist es leer, erscheint eine deutliche Meldung „Kartendaten konnten nicht geladen werden“
      (dann `sets-data.js` neben `erfassung.html` prüfen bzw. hart neu laden).
- [ ] Sprach-Anzeige („Sprache: …“) passt zum gewählten Set.
- [ ] Nummernfeld öffnet am Handy die **Zahlentastatur** (`inputmode=numeric`).
- [ ] Nummer eingeben + Enter (oder „Hinzufügen“):
      - [ ] Kartenbild, Name und Seltenheit werden zur Kontrolle angezeigt.
      - [ ] Kurze Erfolgs-Einblendung (Toast) erscheint.
      - [ ] Nummernfeld wird geleert und wieder fokussiert (schnelles Weitertippen).
- [ ] **Gewähltes Set bleibt** nach dem Erfassen erhalten (auch nach Neuladen der Seite).
- [ ] **Nicht gefundene Nummer** (z. B. `999`): deutliche Warnung + Feld für
      manuelle Namenseingabe → „Manuell erfassen“ legt Eintrag an.
- [ ] **Bereits im Bestand** (gleiches Set/Nummer/Sprache erneut): Abfrage
      „Schon im Bestand – Menge um X erhöhen?“ → „erhöhen“ zählt hoch, „Abbrechen“ verwirft.
- [ ] **Rückgängig** macht die letzte Eingabe/Änderung zunichte.

## 4. Bestand (`erfassung.html`, Tab „Bestand“)
- [ ] Kopf zeigt: Karten gesamt, verschiedene Karten, „im Bestand“ + Aufteilung nach Sprache.
- [ ] Liste zeigt Mini-Kartenbild, Name, Set/Nummer/Sprache/Seltenheit, Menge, Status.
- [ ] **Suche** (Name oder Nummer) filtert die Liste.
- [ ] **Filter** Set / Sprache / Status funktionieren (auch kombiniert).
- [ ] **Statuswechsel** durch Antippen der Status-Pille: Im Bestand → Gelistet → Verkauft → …
- [ ] **Bearbeiten** öffnet Dialog (Name, Menge, Einkaufspreis, Status, Notiz) und speichert.
- [ ] **Löschen** fragt zur Sicherheit nach und entfernt den Eintrag erst nach Bestätigung.

## 5. Speicherung & Sicherung
- [ ] Nach Neuladen der Seite ist der Bestand noch da (localStorage).
- [ ] **CSV-Export**: Datei lädt herunter; in **deutschem Excel** öffnen →
      - [ ] Umlaute korrekt (UTF-8 mit BOM),
      - [ ] Spalten korrekt getrennt (Semikolon),
      - [ ] Spalten: Set; Nummer; Name; Sprache; Seltenheit; Menge; Status; Einkaufspreis; Notiz; Datum,
      - [ ] Einkaufspreis mit Komma (z. B. `12,50`), Datum als `TT.MM.JJJJ`.
- [ ] **JSON-Backup** exportiert eine `.json`-Datei.
- [ ] **JSON-Import** fragt bei vorhandenem Bestand: **Zusammenführen** (OK) oder **Ersetzen** (Abbrechen).
      - [ ] Zusammenführen erhöht bei gleichen Karten die Menge, ergänzt neue.
      - [ ] Ersetzen überschreibt den Bestand.

## 6. Mobil / Einhand
- [ ] Tippflächen (Buttons, Tabs, Status-Pille) sind groß genug für den Daumen.
- [ ] Erfassen ist ohne Zoomen/Scrollen in einem Rutsch möglich.

## 7. eBay-Export `ebay-export.html`
Testdatei: eine kleine `Karten-Archiv.xlsx` nachbauen — Sheet **„Erfassung“**,
Kopfzeile in **Zeile 3** (`Nr. | Set-Code | Kartennummer | Sprache | Anzahl |
Name | Notiz | Preis`) mit u. a.: einem Set-Block (Set-Code nur in der ersten
Zeile), einer Zeile mit `sv9 ` (Leerzeichen), zwei gleichen Karten (Set+Nummer),
einer Zeile mit Notiz `masterball`, einer Zeile ohne Preis, einem unbekannten
Set-Code und einer unbekannten Kartennummer.

- [ ] **Import**: Datei-Auswahl lädt die xlsx; beim ersten Mal wird SheetJS aus
      dem Netz nachgeladen (Internet nötig, danach im Cache).
- [ ] **Set-Vererbung**: Zeilen ohne Set-Code übernehmen den letzten Set-Code.
- [ ] **Trimmen/Normalisieren**: `sv9 ` → `SV9`, Nummer `5` → `005`.
- [ ] **Sprache**: globales Dropdown ist aus der Spalte „Sprache“ vorbelegt und
      gilt für den ganzen Import.
- [ ] **Duplikate**: gleiche Karte doppelt → **beide Zeilen gelb**,
      Hinweis „doppelt“ (nicht zusammengefasst).
- [ ] **Ball-Variante**: `masterball`/`pokeball` → **Zeile blau**, Titel-Zusatz
      „Master Ball“ / „Poke Ball“.
- [ ] **Preis fehlt**: Zeile ohne Preis wird im Preis-Feld als „Preis fehlt“
      (gelb) markiert.
- [ ] **Fehlerliste**: unbekannter Set-Code / unbekannte Nummer erscheinen
      **rot** in der Fehlerliste und sind **nicht** im Export.
- [ ] **Umschalter**: Vorbelegung Einzel/Variante nach Preisgrenze (Default
      4,00 €); pro Zeile umschaltbar; Massenaktionen „Alle → …“ funktionieren.
- [ ] **Einstellungen** (Standort, Bearbeitungszeit, Versand, Rücknahme) werden
      gemerkt (nach Neuladen noch da).
- [ ] **Export A** (`ebay-entwuerfe.csv`): nur Einzel-Zeilen, Action `Draft`,
      SKU `SETCODE-NNN`, Category `183454`, Price mit **Punkt**, Format
      `FixedPrice`.
- [ ] **Export B** (`ebay-varianten.csv`): pro Set eine Elternzeile (`Add`,
      `RelationshipDetails=Kartenname=Wert1;Wert2;…`) + Kindzeilen
      (`Relationship=Variation`, eigener Preis/Menge).
- [ ] Ist eine der beiden Gruppen leer, wird die jeweilige Datei **nicht**
      erzeugt.
- [ ] **CSV in Texteditor öffnen**: beginnt mit BOM, Felder mit `;` getrennt,
      Zeilenenden CRLF, Umlaute korrekt.
- [ ] **CSV in deutschem Excel öffnen**: Spalten korrekt getrennt, Umlaute ok.
- [ ] **Titelbild-Generator**: pro Varianten-Set ein 1600×1600-PNG mit Banner,
      Sprach-Flagge und Kartenraster; Auswahl der Rasterbilder per Klick
      änderbar; PNG-Download (bei blockierten Bildern erscheint der
      CORS-Hinweis).
