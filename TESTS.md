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
      `kartenbild-finder-v6.html`, `dashboard.html`, `sets-data.js`,
      **`shared.js`** (gemeinsame Bild-/Kartenlogik), **`inventar.js`**
      (Bestands-Modul, Schema v2) sowie der Ordner **`vendor/`** mit
      `xlsx.full.min.js` (lokale Excel-Bibliothek für den eBay-Export).
      **Alle** diese Dateien müssen beim Hochladen/Kopieren **mitgenommen** werden.
- [ ] Alles öffnet sich per Doppelklick (Protokoll `file://`) ohne Fehler.
- [ ] Optional (Phase 3): Ordner `assets/cards/` mit lokalen Bildern
      `SETCODE-NNN.jpg` (z. B. `M5-004.jpg`). Fehlt der Ordner, ist das
      **kein Fehler** — die App lädt dann automatisch die pokezentrum-Bilder
      (Auflösungs-Kaskade: lokal → pokezentrum → Platzhalter).

## 1. Startseite `index.html`
- [ ] Vier Kacheln sichtbar: „Kartenbild-Finder“, „Karten-Erfassung“,
      „eBay-Export“ und „Dashboard“.
- [ ] Klick auf Kachel 1 öffnet `kartenbild-finder-v6.html`.
- [ ] Klick auf Kachel 2 öffnet `erfassung.html`.
- [ ] Klick auf Kachel 3 öffnet die Haupt-App **direkt im Tab „eBay-Export“**
      (`kartenbild-finder-v6.html#ebay`).
- [ ] Klick auf Kachel 4 öffnet `dashboard.html`.

## 2. Kartenbild-Finder `kartenbild-finder-v6.html`, Tab „Kartensuche“ (unverändertes Verhalten)
- [ ] Oben zwei Tabs: **„Kartensuche“** (aktiv) und **„eBay-Export“**.
- [ ] Oben steht „48 Sets geladen“ (Set-Daten kommen aus `sets-data.js`).
- [ ] Sprach-Dropdown und Set-Dropdown sind befüllt.
- [ ] Nummer eingeben (z. B. `46`) + „Suchen“ → Karte(n) werden angezeigt.
- [ ] Namenssuche (z. B. `Darkrai`) funktioniert.
- [ ] Buttons „Alle Karten“, „ex-Karten“ usw. zeigen passende Karten.
- [ ] Tab-Wechsel zu „eBay-Export“ und zurück lässt die Suche unverändert.

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
      Ist ein **Lagerplatz** gesetzt, erscheint er in der Extra-Zeile (📦 R2-B5-F12).
- [ ] **Suche** (Name oder Nummer) filtert die Liste.
- [ ] **Filter** Set / Sprache / Status funktionieren (auch kombiniert).
- [ ] **Statuswechsel** durch Antippen der Status-Pille: Im Bestand → Gelistet → Verkauft → …
- [ ] **Bearbeiten** öffnet Dialog (Name, Menge, Einkaufspreis, **Lagerplatz**,
      Status, Notiz) und speichert. Lagerplatz (z. B. `R2-B5-F12`) bleibt nach
      Neuladen erhalten.
- [ ] **Löschen** fragt zur Sicherheit nach und entfernt den Eintrag erst nach Bestätigung.

## 5. Speicherung & Sicherung
- [ ] Nach Neuladen der Seite ist der Bestand noch da (localStorage).
- [ ] **CSV-Export**: Datei lädt herunter; in **deutschem Excel** öffnen →
      - [ ] Umlaute korrekt (UTF-8 mit BOM),
      - [ ] Spalten korrekt getrennt (Semikolon),
      - [ ] Spalten: Set; Nummer; **Kartencode**; Name; Sprache; Seltenheit;
            Menge; Status; Einkaufspreis; **Lagerplatz**; Notiz; Datum,
      - [ ] Kartencode kanonisch als `SETCODE-NNN` (z. B. `M5-004`),
      - [ ] Einkaufspreis mit Komma (z. B. `12,50`), Datum als `TT.MM.JJJJ`.
- [ ] **JSON-Backup** exportiert eine `.json`-Datei.
- [ ] **JSON-Import** fragt bei vorhandenem Bestand: **Zusammenführen** (OK) oder **Ersetzen** (Abbrechen).
      - [ ] Zusammenführen erhöht bei gleichen Karten die Menge, ergänzt neue.
      - [ ] Ersetzen überschreibt den Bestand.

## 6. Mobil / Einhand
- [ ] Tippflächen (Buttons, Tabs, Status-Pille) sind groß genug für den Daumen.
- [ ] Erfassen ist ohne Zoomen/Scrollen in einem Rutsch möglich.

## 7. eBay-Export (`kartenbild-finder-v6.html`, Tab „eBay-Export“)
Testdatei: eine kleine `.xlsx` nachbauen — Pflichtspalten
`Set-Code | Kartennummer | Anzahl` (Kopfzeile darf in einer beliebigen der
ersten 10 Zeilen und in einem beliebigen Tabellenblatt stehen), optional
`Sprache | Name | Notiz | Preis`. Mit u. a.: einem Set-Block (Set-Code nur in
der ersten Zeile), einer Zeile mit `sv8a ` (Leerzeichen), zwei gleichen Karten
(Set+Nummer), einer Zeile mit Notiz `masterball`, einem unbekannten Set-Code
und einer unbekannten Kartennummer.

### Import & Rückmeldungen
- [ ] **Import**: Datei-Auswahl lädt die xlsx über die **lokale** Bibliothek
      `vendor/xlsx.full.min.js` (kein Internet nötig; CDN nur als Notfall-Fallback).
- [ ] **Aus Erfassung-Bestand übernehmen** (Button ohne Excel): übernimmt die in
      der Karten-Erfassung gespeicherten Karten direkt in die Vorschau.
      - [ ] Verkaufte Karten werden übersprungen, Karten ohne Menge ebenfalls.
      - [ ] Jede Karte behält ihre **eigene Sprache** (unabhängig vom globalen
            Sprach-Dropdown).
      - [ ] Der in der Erfassung erfasste **Einkaufspreis** taucht **nicht** als
            Verkaufspreis auf — die Preise kommen aus den Preisregeln (Badge „Regel“).
      - [ ] Grüne Erfolgsmeldung mit Anzahl; leerer Bestand → **rote** Meldung.
- [ ] Während des Einlesens erscheint ein Ladehinweis; danach ein **grüner
      Erfolgs-Haken** mit Zusammenfassung („X Zeilen gelesen · Y Karten
      erkannt · …“) und aufklappbarer **Diagnose** (Blatt, Kopfzeile, Spalten).
- [ ] **Fehlerfälle sichtbar** (niemals stumm): Datei ohne Kopfzeile, Datei
      ohne Spalte „Anzahl“, kaputte Datei, fehlende Bibliothek → jeweils
      **rote** Meldung mit konkretem Grund.
- [ ] **Set-Vererbung**: Zeilen ohne Set-Code übernehmen den letzten Set-Code.
- [ ] **Trimmen/Normalisieren**: `sv8a ` → `SV8a`, Nummer `5` → `005`.
- [ ] **Sprache**: globales Dropdown ist aus der Spalte „Sprache“ vorbelegt
      (falls vorhanden) und gilt für den ganzen Import.
- [ ] **Duplikate**: gleiche Karte doppelt → **beide Zeilen gelb**, „doppelt“.
- [ ] **Ball-Variante**: `masterball`/`pokeball` → **Zeile blau**, Titel-Zusatz.
- [ ] **Fehlerliste**: unbekannter Set-Code / unbekannte Nummer erscheinen
      **rot** in der Fehlerliste und sind **nicht** im Export.

### Preisregeln
- [ ] Excel **ohne Preisspalte** → alle Karten bekommen automatisch
      Regel-Preise, Badge **„Regel“** (Defaults: „ex“ + Japanisch → 1,50 €,
      alle übrigen → 1,00 €).
- [ ] Excel **mit Preisspalte** → diese Zeilen zeigen Badge **„Manuell“** und
      behalten den Excel-Preis.
- [ ] **„Verkäufe prüfen“** öffnet eBay.de (Verkaufte + Beendete Angebote) in
      neuem Tab — die App selbst macht **keine** Netzwerk-Abfragen an eBay.
- [ ] **Ø-Feld**: ex-Karte japanisch, Ø `2,00` → Preis **2,20 €**
      (Badge „Verkäufe +10 %“); Ø `1,00` → **1,50 €** (Mindestpreis greift).
- [ ] Preisfeld direkt editieren → Badge **„Manuell“**.
- [ ] Regel-Editor: Regeln hinzufügen/verschieben/löschen; Standard-Regel
      bleibt immer die letzte; Aufschlag-% und Rundung (aus/,49/,99) änderbar;
      alles überlebt ein Neuladen (localStorage).
- [ ] Zusammenfassung zeigt „X per Regel · Y per Verkaufsdaten · Z manuell“.
- [ ] Zeile ohne ermittelbaren Preis (Basispreis der Regel geleert) →
      **orange** markiert, Hinweis am Export, **nicht** in der CSV.

### Export & Titelbild
- [ ] **Umschalter**: Vorbelegung Einzel/Variante nach Preisgrenze (Default
      4,00 €); pro Zeile umschaltbar; Massenaktionen „Alle → …“ funktionieren.
- [ ] **Einstellungen** (Standort, Bearbeitungszeit, Versand, Rücknahme) werden
      gemerkt (nach Neuladen noch da).
- [ ] **Export A** (`ebay-entwuerfe.csv`): nur Einzel-Zeilen, Action `Draft`,
      SKU `SETCODE-NNN`, Category `183454`, Price mit **Punkt**, Format
      `FixedPrice`.
- [ ] **Lagerplatz in SKU**: Karten, die per „Aus Erfassung-Bestand übernehmen“
      geladen wurden und einen Lagerplatz haben, tragen ihn an der SKU/CustomLabel
      (z. B. `M5-004-R2B5F12`) — sichtbar in Export A und in den Kindzeilen von Export B.
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

## 8. Dashboard (`dashboard.html`)
- [ ] Liest **denselben Bestand** wie die Erfassung (Browser-Speicher);
      bei leerem Bestand erscheint ein Hinweis mit Link zur Erfassung.
- [ ] **KPI-Kacheln**: Karten gesamt (Σ Menge), verschiedene Karten,
      **Einkaufswert** (Σ Einkaufspreis × Menge), Ø Einkaufspreis (je
      bewerteter Karte), **unbewertet** (Anzahl ohne Einkaufspreis).
- [ ] Karten **ohne Einkaufspreis** werden als „unbewertet“ gezählt, **nicht**
      mit 0 € in den Wert eingerechnet.
- [ ] **Status-Verteilung**: gestapelter Balken + Liste (Im Bestand / Gelistet /
      Verkauft) mit Menge, Prozent und Wert je Status; jede Zeile hat Farbfeld
      **und** Textlabel (nicht nur Farbe).
- [ ] **Nach Sprache** und **Top-Sets**: Balken nach Menge, absteigend sortiert,
      mit Zahl am Ende.
- [ ] **Backup-Erinnerung**: nach einem JSON-Backup in der Erfassung zeigt das
      Dashboard „Letztes Backup vor X Tagen“ (ab 7 Tagen als Warnung); ohne
      Backup einen neutralen Hinweis.
- [ ] Mobil: Kacheln und Balken brechen sauber um, **kein** horizontales Scrollen.
