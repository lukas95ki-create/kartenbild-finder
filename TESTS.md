# Test-Checkliste (manuell)

> **Automatisierte Tests:** Für den eBay-Entwurfs-Export (Export A) gibt es
> automatisierte Tests in `tests/ebay-draft-csv.test.mjs`. Ausführen im
> Repo-Hauptverzeichnis mit `node --test` (Node ≥ 18, keine Abhängigkeiten).
> Geprüft werden: die vier `#INFO`-Zeilen der offiziellen Vorlage
> „eBay-draft-listings-template_DE“, die exakte Kopfzeile, UTF-8-BOM,
> CRLF-Zeilenenden, Semikolon-/Anführungszeichen-Escaping, `Action=Draft`,
> Punkt-Dezimaltrenner, Category ID pro Zeile, die Export-Modi
> (u. a. „Alle als Einzelentwürfe“ → genau eine CSV, Duplikate über
> Quantity zusammengefasst), die Export-B-Blockade bei leeren
> Pflichtfeldern sowie der **Abgleich beider Exporte gegen die
> Original-Vorlagendateien in `templates/`** (identische Info-/Kopfzeilen,
> gleiche Spaltenanzahl pro Zeile, BOM, CRLF).

Diese Punkte sollten nach Änderungen kurz von Hand geprüft werden.
Am besten je einmal **lokal** (Datei per Doppelklick öffnen) **und** **gehostet**
(z. B. Netlify), sowie einmal am **Handy**.

> Hinweis zu Bildern: Die Kartenbilder kommen von `pokezentrum.de`. In manchen
> Vorschau-/Sandbox-Umgebungen werden externe Bilder blockiert – dann erscheint
> statt des Bildes ein Platzhalter („kein Bild“). Das ist kein Fehler der App;
> im echten Browser (Chrome/Safari) laden die Bilder normal.

## 0. Dateien / Struktur
- [ ] Im Hauptverzeichnis liegen: `index.html`, `erfassung.html`,
      `kartenbild-finder-v6.html`, `sets-data.js` sowie der Ordner
      **`vendor/`** mit `xlsx.full.min.js` (lokale Excel-Bibliothek für den
      eBay-Export — muss beim Hochladen/Kopieren **mitgenommen** werden).
- [ ] Alles öffnet sich per Doppelklick (Protokoll `file://`) ohne Fehler.

## 1. Startseite `index.html`
- [ ] Drei Kacheln sichtbar: „Kartenbild-Finder“, „Karten-Erfassung“ und „eBay-Export“.
- [ ] Klick auf Kachel 1 öffnet `kartenbild-finder-v6.html`.
- [ ] Klick auf Kachel 2 öffnet `erfassung.html`.
- [ ] Klick auf Kachel 3 öffnet die Haupt-App **direkt im Tab „eBay-Export“**
      (`kartenbild-finder-v6.html#ebay`).

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
- [ ] **Export-Modus** (Dropdown im Import-Block, wird gemerkt): Standard ist
      **„Alle als Einzelentwürfe“** — Preisgrenzen-Feld ausgeblendet, nur der
      Export-A-Button sichtbar, ALLE Karten landen in der Entwurfs-CSV
      (doppelte Karten als EINE Zeile mit summierter Quantity).
      „Automatisch aufteilen“ zeigt Preisgrenze + beide Export-Buttons;
      „Alle als Variationen“ blendet Export A aus. Nach Neuladen ist der
      gewählte Modus noch da.
- [ ] **Umschalter** (nur im Modus „Automatisch aufteilen“ aktiv): Vorbelegung
      Einzel/Variante nach Preisgrenze (Default 4,00 €); pro Zeile
      umschaltbar; Massenaktionen „Alle → …“ funktionieren. In den festen
      Modi sind „Alle → …“ deaktiviert und der Zeilen-Umschalter zeigt einen
      Hinweis-Toast.
- [ ] **Einstellungen** (Standort, Bearbeitungszeit, Versand, Rücknahme) werden
      gemerkt (nach Neuladen noch da).
- [ ] **Export A** (`ebay-entwuerfe.csv`): beginnt mit den **vier `#INFO`-Zeilen**
      der offiziellen Vorlage „eBay-draft-listings-template_DE“ (Zeile 1:
      `#INFO;Version=0.0.2;Template= eBay-draft-listings-template_DE;;;;;;;`),
      Zeile 5 ist die Kopfzeile; danach nur Einzel-Zeilen, Action `Draft`,
      SKU `SETCODE-NNN`, Category `183454`, Price mit **Punkt**, Format
      `FixedPrice`.
- [ ] **Export A hochladen**: Verkäufercockpit Pro → Berichte → Hochladen
      akzeptiert die Datei (keine Meldung „Wir konnten Ihre Vorlage nicht
      identifizieren“); Entwürfe erscheinen unter ebay.de/sh/lst/drafts.
- [ ] **Export B** (`ebay-varianten.csv`): beginnt mit der Info-Kennungszeile
      `Info;Version=1.0.0;Template=fx_category_template_EBAY_DE` und der
      105-Spalten-Kopfzeile der offiziellen Kategorie-Vorlage 183454
      (`templates/eBay-category-listing-template-*.csv`); danach pro Set eine
      Elternzeile (`Add`, `RelationshipDetails=Kartenname=Wert1;Wert2;…`,
      Angebots-Einstellungen in Standort-/Versand-/Rücknahme-Spalten) +
      Kindzeilen (`Relationship=Variation`, eigener Preis/Menge/PicURL).
      **Achtung:** nutzt bewusst NICHT die Entwurfs-Vorlage (die kann keine
      Varianten) – Upload erzeugt aktive Angebote. Der Warnhinweis
      „Variationsangebote gehen beim Hochladen sofort live“ ist in der UI
      (CSV-Export-Karte) sichtbar.
- [ ] **Export-B-Blockade**: Sind Standort, Versandart, Versandkosten oder
      Bearbeitungszeit in den Angebots-Einstellungen leer, erzeugt Export B
      KEINE Datei; eine rote Meldung nennt die fehlenden Felder.
- [ ] Ist eine der beiden Gruppen leer, wird die jeweilige Datei **nicht**
      erzeugt.
- [ ] **CSV in Texteditor öffnen**: beginnt mit BOM, Felder mit `;` getrennt,
      Zeilenenden CRLF, Umlaute korrekt.
- [ ] **CSV in deutschem Excel öffnen**: Spalten korrekt getrennt, Umlaute ok.
- [ ] **Titelbild-Generator**: pro Varianten-Set ein 1600×1600-PNG mit Banner,
      Sprach-Flagge und Kartenraster; Auswahl der Rasterbilder per Klick
      änderbar; PNG-Download (bei blockierten Bildern erscheint der
      CORS-Hinweis).
