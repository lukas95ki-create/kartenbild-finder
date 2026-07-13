# Architekturprüfung „Kartenfinder V6"

> **Status:** Planungsdokument (Aufgabe 2). Enthält **keine** Code-Änderungen.
> Grundlage: das vollständige V6-Anforderungsdokument („Erweiterung
> Kartenfinder V6 – Architekturprüfung und Implementierungsplanung").
> Jede Funktion wird bewertet nach: **technisch umsetzbar? · benötigte
> APIs/Bibliotheken · Risiken/Einschränkungen · bessere Alternative ·
> empfohlene Reihenfolge** (Kapitel 17).

---

## 0. Die zentrale Spannung zuerst

Das V6-Ziel lautet „vollständige Inventar-, Preis- und
eBay-**Automatisierungsplattform**". Die harte Projektbedingung lautet
zugleich: **kein Server, kein Build, keine Installation** (Schul-Laptop,
statische HTML-Dateien, Bibliotheken nur per CDN).

Diese beiden Ziele sind **nicht vollständig vereinbar**: Vollautomatik
(eBay Sell API, automatische Preisquellen) verlangt zwingend Geheimnisse
(Client-Secret, OAuth-Refresh-Tokens), die in einer statischen Seite nicht
sicher aufgehoben sind. Die Auflösung dieses Konflikts zieht sich durch das
ganze Dokument:

- **Stufe 1 – rein im Browser** (heutige Architektur): alles, was ohne
  Geheimnisse und ohne Serverprozess geht. Das ist mehr, als man denkt —
  ~80 % des gewünschten Workflows.
- **Stufe 2 – Hosting ohne Backend** (GitHub Pages/Netlify, gratis):
  schaltet Kamera (`getUserMedia`), PWA/Offline und sauberen
  Canvas-PNG-Export frei. Immer noch kein eigener Serverprozess.
- **Stufe 3 – serverloses Mini-Backend** (Cloudflare Worker, gratis-Tarif,
  oder VPS 3–5 €/Monat): nur für eBay-Sell-API und automatische
  Preis-Lookups. Optional, erst bei echtem Volumen.

| Rahmenbedingung | Konsequenz |
|-----------------|------------|
| Kein Server/Build/Installation | Statische HTML-Tools, CDN-Bibliotheken; Stufe 3 nur als bewusste, begründete Erweiterung |
| Start teils per `file://` | Kamera, Service Worker, File-System-Access-API sind dort **gesperrt** („secure context") → für Scanner/PWA ist Stufe 2 Voraussetzung |
| Bilder von pokezentrum.de (Erlaubnis liegt vor) | `<img>`-Anzeige ok; **kein CORS** → Canvas „tainted", `fetch` blockiert → betrifft Titelbild-Export und Bild-Caching |
| Cardmarket-API stark eingeschränkt, Scraping unzuverlässig | Automatische Preis**quellen** unrealistisch; automatische Preis**regeln** dagegen problemlos (Kap. 4) |

---

## 1. Scanner

### 1a. Modus 1 – Fotoerkennung

**Umsetzbar?** ⚠️ Ja — aber nicht so, wie beschrieben. Die Anforderung
„App erkennt Kartencode, Name, Set, Sprache, Nummer, Seltenheit aus dem
Foto" sollte **nicht** als Sechsfach-Bilderkennung gebaut werden.

**Bessere Umsetzung (dringend empfohlen):** Nur das **kleinste zuverlässige
Merkmal** per OCR erkennen — **Set-Code + Kartennummer** unten links
(z. B. `093/187` + `SV8a`). Alles andere (**Name, Set, Sprache, Seltenheit,
Bild**) wird daraus per **Lookup in `sets-data.js`** abgeleitet — exakt die
Datenbasis, die das Projekt schon hat und die `erfassung.html` heute für die
manuelle Nummerneingabe nutzt. Namens-OCR (verschiedene Fonts, Foil-Glanz,
japanische Schrift) wäre um Größenordnungen fehleranfälliger und ist
überflüssig, sobald der Code erkannt ist.

**APIs/Bibliotheken:**
- Foto-Aufnahme: `<input type="file" accept="image/*" capture="environment">`
  — öffnet am Handy direkt die Kamera-App. **Funktioniert ohne HTTPS und
  ohne `getUserMedia`**, sogar per `file://`. Das macht Modus 1 zur
  niedrigsten Einstiegshürde. (Am Laptop mit Webcam greift `capture` nicht —
  dort wäre es Datei-Auswahl oder eben Modus 2.)
- OCR: **tesseract.js** (WASM, per CDN, nach Erstladen offline nutzbar;
  Kern + Sprachdaten wenige MB).
- Vorverarbeitung: reines Canvas-2D (Zuschnitt, Hochskalieren, Graustufen,
  Schwellwert). **OpenCV.js (~8 MB) nur falls Perspektivkorrektur nötig
  wird** — erst einbauen, wenn Messungen es rechtfertigen.

**Risiken/Einschränkungen:**
- OCR auf dem kleinen, kontrastarmen Nummernfeld braucht zwingend
  **ROI-Zuschnitt** (der Nutzer legt die Karte in einen Rahmen auf dem
  Vorschaubild) + **Zeichen-Whitelist** (`tessedit_char_whitelist`: Ziffern,
  `/`, Set-Code-Zeichen). Ohne beides ist die Fehlerrate hoch.
- Foil-/Fullart-Karten (gerade die wertvollen SAR/UR) haben Glanz über dem
  Nummernfeld → Erkennungsquote sinkt; immer einen **Bestätigungsschritt**
  mit Kartenbild aus der DB anzeigen (falsche Zuordnung wäre teurer als
  1 s Mehraufwand).
- Alternative „Bild-Matching" (perzeptueller Hash des Fotos gegen eine
  vorberechnete Hash-DB aller Kartenbilder): technisch reizvoll und mit den
  vorhandenen `tools/*.py` vorbereitbar, aber ein eigenes Forschungsprojekt.
  **Nicht für den MVP.**

### 1b. Modus 2 – Live-Scanner

**Umsetzbar?** ⚠️ Ja, mit klaren Voraussetzungen — **und die Zielmarke
„1–2 Sekunden pro Karte" ist unrealistisch als Normalfall.**

**APIs/Bibliotheken:** `navigator.mediaDevices.getUserMedia` (Kamera-Stream),
tesseract.js **im Web Worker**, Frame-Throttling (nur jeden n-ten Frame
prüfen), Stabilitäts-Voting (gleiches Ergebnis in 2–3 aufeinanderfolgenden
Frames → akzeptieren).

**Risiken/Einschränkungen:**
1. **`file://` blockiert die Kamera.** `getUserMedia` verlangt HTTPS oder
   `localhost`. Vom Schul-Laptop per Doppelklick funktioniert Modus 2
   **nicht** — er setzt **Stufe 2 (Hosting)** voraus. Am Handy ohnehin.
2. **Realistische Geschwindigkeit:** tesseract.js braucht je nach Gerät
   0,3–2 s+ pro OCR-Versuch; mit Ausrichten, mehreren Frames bis zum
   stabilen Ergebnis und Mengen-Eingabe sind **2–5 s/Karte** realistisch.
   1–2 s sind nur unter Idealbedingungen erreichbar (fixierte
   Kamera-Halterung, gutes Licht, ROI, Karte immer an derselben Position).
   **Empfehlung: ehrlich messen** (Karten/Minute über einen 50-Karten-Stapel)
   statt die Zielmarke zu versprechen.
3. **Welche CV/OCR-Lösung?** Vergleich:

| Lösung | Bewertung |
|--------|-----------|
| **tesseract.js** (Browser, WASM) | ✅ Einzige Lösung, die die Rahmenbedingungen erfüllt (kein Server, kostenlos, offline nach Erstladen). Mit ROI+Whitelist+Worker gut genug. **Empfohlen.** |
| Cloud-OCR (Google Vision, Azure) | ❌ Schneller/genauer, aber API-Key läge lesbar in der statischen Seite → bräuchte Backend-Proxy; laufende Kosten; online-Pflicht. |
| Eigenes ML-Modell (TF.js/ONNX-Runtime-Web) | ❌ Für dieses Projekt überdimensioniert (Trainingsdaten, Pflege). Erst erwägen, wenn tesseract nachweislich scheitert. |
| Barcode-/QR-Scanner (`BarcodeDetector`, ZXing) | ❌ Entfällt — Pokémon-Karten tragen keinen Barcode. |

**Bessere Umsetzung / Einordnung:** Der Live-Scanner ist ein
**Assistenz-Modus, kein Ersatz** für die manuelle Eingabe. Wer die Nummern
kennt, tippt mit dem heutigen `erfassung.html`-Flow (Nummer → Enter) oft
schneller und fehlerfreier als jede OCR. Der Scanner lohnt v. a. bei
unbekannter Massenware. Beide Modi teilen sich denselben Kern
(ROI-OCR → DB-Lookup → Bestätigen → Menge/+1 → speichern); Modus 1 ist
der Sonderfall „ein Frame aus Datei statt Stream" — **ein Modul, zwei
Eingänge** (siehe Kap. 14).

---

## 2. Inventar

**Umsetzbar?** ✅ Vollständig, rein im Browser. `erfassung.html` **ist**
bereits dieses Inventar — es fehlen nur Felder.

**Nötig:** kein neues Framework. Schema-Erweiterung des bestehenden
localStorage-Formats um: `kartencode` (kanonisch `SETCODE-NNN`),
`lagerplatz` (Kap. 10), sowie die Mehrbenutzer-Vorbereitungsfelder
`owner`, `updatedAt`, `version` (Kap. 13). `Einkaufspreis`, `Erfassungsdatum`,
`Bild`(-URL-Cache), Status und Bearbeiten-Dialog existieren schon.

**Risiken/Einschränkungen:**
- **localStorage-Limit (~5 MB):** für Tausende Karten-Datensätze (ohne
  eingebettete Bilder!) unkritisch. Bilder gehören **nie** als Base64 in
  localStorage. Wachstumspfad: **IndexedDB** (nativ oder `localForage` per
  CDN) — erst migrieren, wenn es real eng wird; Schema mit `version`-Feld
  macht die Migration mechanisch.
- Backup bleibt Pflicht (JSON-Export existiert): localStorage kann durch
  Browser-Datenlöschung verschwinden. Empfehlung: Erinnerung im UI
  („letztes Backup vor X Tagen").

**Bessere Umsetzung:** Die Inventar-Logik (Schema, CRUD, Migration,
Duplikat-Erkennung) als **`inventar.js`** auslagern, damit Scanner,
Erfassung, Dashboard und eBay-Export **dieselbe** Bestandsquelle nutzen —
heute liest `ebay-export.html` stattdessen eine Excel-Datei. Beide Wege
(Excel-Import **und** Inventar-Übernahme) anbieten; Excel bleibt als
Massen-/Alt-Datenpfad wertvoll.

---

## 3. Bilddatenbank

**Umsetzbar?** ✅ Ja — als **Hybrid**, nicht als Entweder-oder.

**Bewertung der Idee „lokaler Ordner `assets/cards/SV8A093.jpg`":**

| Aspekt | Bewertung |
|--------|-----------|
| Offline-Fähigkeit, Geschwindigkeit | ✅ klar besser als Hotlinks |
| Kein Risiko durch URL-Änderungen bei pokezentrum | ✅ |
| **Canvas/CORS:** | ✅ **wichtigster Nebengewinn** — liegen die Bilder auf derselben Origin (gehostet), ist die Canvas nicht mehr „tainted" → der Titelbild-PNG-Export (Kap. 12) funktioniert sauber. Achtung: unter `file://` behandelt Chrome auch lokale Bilder als fremde Quelle — der saubere Export braucht Stufe 2 (Hosting). |
| Datenvolumen | ⚠️ alle ~48 Sets × Hunderte Karten × ~100–300 KB = mehrere GB wären unpraktisch. **Nur die aktiv verkauften Sets** lokal vorhalten. |
| Befüllung | ⚠️ per Browser-`fetch` unmöglich (kein CORS). Praktikabel: manuelles Speichern über den vorhandenen Kartenfinder-Mechanismus oder die bestehenden `tools/*.py`-Skripte (laufen auf einem beliebigen Privat-PC, nicht auf dem Schul-Laptop) — Ausgabe in den `assets/cards/`-Ordner mit normiertem Namen `SETCODE-NNN.jpg`. |

**Empfohlene Auflösungs-Kaskade** (erweitert die heutige `imgCandidates()`):
1. `assets/cards/SETCODE-NNN.jpg` (lokal/gleiche Origin) →
2. pokezentrum-URL (heutige Logik) →
3. Platzhalter.

**Copyright/Lizenz (wichtig):**
- Das Kartenmotiv ist urheberrechtlich geschützt (©Pokémon/Nintendo/
  Creatures); an den Galerie-Fotos hält pokezentrum eigene Rechte. Die
  **schriftliche Erlaubnis** deckt die Nutzung der pokezentrum-Bilder —
  es sollte geprüft/festgehalten werden, dass sie ausdrücklich **(a) das
  lokale Kopieren** und **(b) die kommerzielle Nutzung in eBay-Angeboten**
  umfasst, nicht nur das Verlinken.
- Das Repo mit lokal gespeicherten Bildern **nicht öffentlich** stellen
  (privates Repo/privater Host) — Weiterverbreitung ist ein anderer
  Tatbestand als eigene Nutzung.
- Stockfoto-Hinweis in der Angebotsbeschreibung (bereits umgesetzt)
  beibehalten.

---

## 4. Preisermittlung

**Umsetzbar?** ❌ automatische Preis**quellen** · ✅ automatische
Preis**regeln**. Diese Trennung ist die wichtigste Design-Entscheidung
des Kapitels.

**Datenquellen (Prüfergebnis):**

| Quelle | legal & zuverlässig verfügbar? |
|--------|--------------------------------|
| **Cardmarket-API** | ❌ Neue App-Zugänge werden praktisch nicht mehr vergeben; Preisdaten zudem an kommerzielle Bedingungen geknüpft; OAuth-1.0a-Secrets bräuchten ein Backend. |
| **Cardmarket scrapen** | ❌ Gegen ToS, Cloudflare-geschützt, im Browser durch CORS ohnehin unmöglich, serverseitig brüchig (bestätigte Erfahrung). |
| **eBay „Last Sold"** (Marketplace-Insights-API) | ❌ „Limited Release" — Zugang nur auf Antrag mit Business Case; OAuth serverseitig → Backend. Realistisch nicht zu bekommen. |
| **eBay Browse API** (aktive Angebote) | ⚠️ Technisch zugänglich, aber App-Token braucht Client-Secret → nur über Worker-Proxy (Stufe 3). Liefert Angebots-, nicht Verkaufspreise. |
| **Terapeak** (im eBay-Verkäuferkonto) | ✅ Legal, kostenlos, echte Verkaufsdaten — aber **manuell** (kein API-Zugriff). Guter Rechercheweg. |
| **Manuelle Preisspalte** | ✅ Zuverlässig, null Infrastruktur. **Bleibt Basis-Workflow.** |

**Empfohlene Architektur — „Preisquelle manuell, Preisregel automatisch":**
- Der Nutzer erfasst je Karte **einen Marktpreis** (z. B. Cardmarket-
  Niedrigstpreis, per **Deep-Link-Button** „Preis nachschlagen" in neuem
  Tab schnell ermittelt — nur eine Such-URL, keine API, ToS-konform).
- Eine **Regel-Engine in reinem JS** (`preislogik.js`) berechnet daraus den
  Verkaufspreis. Die gewünschten Regeln sind trivial umsetzbar und frei
  kombinierbar als Pipeline:
  `basis → +5 % → max(mindestpreis) → runden auf ,99`.
  Konfiguration als JSON in localStorage, mit Live-Vorschau in der Tabelle.
- **Eigene Verkaufshistorie als Preisquelle aufbauen** (Zusatzvorschlag,
  Kap. 18): Jeder tatsächliche Verkauf wird mit Datum/Preis protokolliert.
  Nach einigen Monaten hat die App eine **eigene, legale
  „Last-Sold"-Datenbank** für die häufig gehandelten Karten — das umgeht
  das API-Problem elegant und wird mit der Zeit besser.

**Risiken:** Preisregeln ohne verlässliche Quelle können falsche Sicherheit
suggerieren — UI sollte immer Quelle+Datum des Basispreises anzeigen
(„CM low, 12.07.").

---

## 5. eBay-Integration (Sell API als Standard)

**Umsetzbar?** ⚠️ Ja — aber **nur mit Backend (Stufe 3)**, und deshalb als
**spätere Ausbaustufe**, nicht als Standard von Tag 1. Empfehlung: CSV
bleibt Standard, bis das Listing-Volumen den Betrieb eines Workers
rechtfertigt; die Architektur wird aber **jetzt** darauf vorbereitet
(austauschbares Listing-Backend, Kap. 14).

**Antworten auf die konkreten Prüffragen:**

| Frage | Antwort |
|-------|---------|
| **Welche APIs?** | **Inventory API** (InventoryItem + Offer; Varianten über *Inventory Item Groups*) für veröffentlichte Angebote; **Listing API (Beta)** `createItemDraft` für Entwürfe (nur Einzelangebote); **Media API** für Bild-Upload; ggf. Fulfillment API (Verkäufe abrufen → Bestandsabgleich). Die alte Trading API (`AddFixedPriceItem`) kann Varianten ebenfalls, gilt aber als Legacy. |
| **Authentifizierung?** | OAuth 2.0 **Authorization-Code-Flow** mit registrierter Redirect-URL (RuName). Client-Secret und Refresh-Token (≈18 Monate gültig; Access-Token ≈2 h) **müssen serverseitig** liegen → Cloudflare Worker + KV oder VPS. In einer statischen Seite nicht sicher machbar — das ist der harte Grund, warum „API als Standard" der Rahmenbedingung widerspricht. |
| **API-Limits?** | Tages-Kontingente je API (typisch 5 000 bis in die Millionen Calls/Tag je nach API und Freischaltung). Für Einzelhändler-Volumen (Hunderte Listings) **kein praktisches Limit**; Erhöhung beantragbar. |
| **Bilder automatisch hochladen?** | ✅ Ja — zwei Wege: (a) **Media API** lädt Dateien in die eBay Picture Services; (b) einfacher: **externe Bild-URLs angeben** — eBay lädt sie **serverseitig** und kopiert sie in EPS. Dadurch funktionieren die pokezentrum-URLs (Erlaubnis vorausgesetzt) ohne jedes CORS-Problem — heute schon im CSV-Weg genutzt, gilt genauso für die API. |
| **Varianten voll automatisiert?** | ✅ Ja — Inventory API: `createOrReplaceInventoryItemGroup` mit `varyBy`-Aspekt (z. B. „Kartenname"), Kind-SKUs mit eigenem Preis/Menge, dann `publishOfferByInventoryItemGroup`. Achtung: der **Draft-Weg** (Listing API) unterstützt **keine** Varianten — automatische Varianten-*Entwürfe* gibt es nicht, nur direkt veröffentlichte Varianten-Angebote oder der CSV-Upload. |

**Minimal-Infrastruktur für den API-Weg:** ein Cloudflare Worker
(gratis-Tarif reicht) mit drei Endpunkten: OAuth-Redirect/Token-Tausch,
Token-Refresh (KV-Storage), API-Proxy für die Listing-Calls. Die statischen
Tools bleiben unverändert die UI.

**Risiken:** eBay-App-Registrierung/Review, Pflege bei API-Änderungen,
Fehlerbilder (Kategorie-/Aspekt-Validierung) — deutlich mehr Betriebsaufwand
als CSV. Deshalb: erst bei echtem Volumen.

---

## 6. CSV (Fallback)

**Umsetzbar?** ✅ **Bereits umgesetzt** (`ebay-export.html`): Export A
(Einzel-Entwürfe) + Export B (Varianten), Header 1:1 aus den offiziellen
Vorlagen (`/templates`), UTF-8+BOM/CRLF/Semikolon. Bewertung: Der CSV-Weg ist
nicht nur Fallback, sondern auf absehbare Zeit der **Standard** — er erfüllt
den kompletten Workflow ohne jede Infrastruktur. Einzige Pflege-Aufgabe:
Header-Konstanten aktualisieren, falls eBay die Vorlagen ändert.

---

## 7. Titelgenerator

**Umsetzbar?** ✅ Vollständig im Browser — reine String-Logik über den
DB-Feldern. Basis existiert in `ebay-export.html`.

**SEO-Empfehlungen (eBay-Suche „Cassini"):**
- Alle **80 Zeichen** ausnutzen, Keyword-first: `Pokémon [Kartenname]
  [Nummer/Total] [Setname] [Set-Code] [Seltenheit] [Sprache] [Zustand]` —
  z. B. `Pokémon Terastal Festival ex SV8A 093/187 Pikachu AR Japanisch NM`.
- Keine Füll-/Werbewörter („TOP", „RAR", „WOW") — kosten Zeichen, bringen
  keine Suche.
- **Prioritäts-Kürzung** statt hartem Abschneiden: Wenn >80 Zeichen, Tokens
  in definierter Reihenfolge opfern (z. B. zuerst Zustand, dann Setname
  ausgeschrieben → nur Code, dann Seltenheit).
- Benötigt Daten: `total` je Set (vorhanden) und **Seltenheit** (in
  `sets-data.js` nur teilweise gepflegt) — Datenpflege einplanen.

**⚠️ Inkonsistenz im Anforderungsdokument:** Das Titel-Beispiel enthält
**„NM"** (Near Mint = Zustandsangabe), während die Beschreibung bewusst
**ohne Zustandsangabe** bleibt (so auch im Auftrag zu Aufgabe 1 umgesetzt).
Ein Zustand im Titel ist eine rechtlich relevante Zusicherung und müsste
konsistent auch als ConditionID gesetzt werden. **Empfehlung:** Zustands-Token
als **optionale, standardmäßig deaktivierte** Einstellung — erst aktivieren,
wenn die Zustandsfrage insgesamt entschieden ist.

---

## 8. Beschreibungen

**Umsetzbar?** ✅ Bereits umgesetzt (festes HTML-Template mit
Stockfoto-Hinweis, ohne KI, ohne Freitext). Sinnvoller Ausbau: Template mit
Platzhaltern (`{{name}}`, `{{set}}`, `{{sprache}}` …) in localStorage
editierbar machen — bleibt standardisiert, aber ohne Code-Änderung
anpassbar. Kein Risiko, kein Bibliotheksbedarf.

---

## 9. Dashboard

**Umsetzbar?** ✅ Trivial, rein im Browser — reine Aggregation über das
Inventar: Gesamtanzahl (Σ Menge), verschiedene Karten, Gesamtwert
(Σ Preis×Menge), Ø-Verkaufspreis, gelistet/nicht gelistet (der
Status „Im Bestand/Gelistet/Verkauft" existiert bereits in
`erfassung.html`).

**Risiken:** Aussagekraft hängt an der Pflege von Preis- und Status-Feldern
— fehlende Preise als „unbewertet: N Karten" ausweisen statt still mit 0 zu
rechnen. **Umsetzung:** eigenes kleines `dashboard.html` (Architekturmuster
des Repos) oder dritter Tab in `erfassung.html`; kein Framework, ggf. reine
CSS-Balken statt Chart-Bibliothek.

---

## 10. Lagerverwaltung

**Umsetzbar?** ✅ Trivial als Datenmodell-Erweiterung: Felder
`regal`/`box`/`fach` (oder ein normierter String `R2-B5-F12`) am
Inventar-Eintrag + Filter/Anzeige.

**Mehrwert-Tipp:** Lagerplatz **in die SKU/CustomLabel** der eBay-Exporte
aufnehmen (z. B. `SV8A-093-R2B5`) — eBay zeigt die SKU auf der
Verkaufsübersicht, d. h. der Lagerplatz steht beim Verkauf **direkt auf dem
Bestellzettel**. Das ist der eigentliche Nutzen der Lagerverwaltung im
Versandalltag und kostet nur eine Namenskonvention.

---

## 11. eBay-Listing-Modi A/B/C

**Umsetzbar?** ✅ A und B sind **bereits umgesetzt** (`ebay-export.html`:
Umschalter Einzel/Variante, Varianten je Set gruppiert). Modus C existiert
im Kern ebenfalls schon: die **Preisgrenzen-Vorbelegung** (Default 4 €,
einstellbar) *ist* die erste Automatik-Regel.

**Ausbau Modus C:** die eine Schwelle zu einem kleinen, konfigurierbaren
Regelwerk verallgemeinern (JSON in localStorage): Preis-Schwelle global,
Ausnahmen je Seltenheit (z. B. „SAR immer einzeln"), Ausnahmen je Set.
Wichtig: Automatik nur als **Vorbelegung** — der manuelle Umschalter pro
Zeile bleibt immer das letzte Wort. Kein Bibliotheksbedarf, kein Risiko.

**Variantenstruktur (Prüffrage aus dem Dokument):** eBay unterstützt
Varianten über ein Merkmal-Raster (File Exchange:
`RelationshipDetails=Kartenname=Wert1;Wert2;…` in der Elternzeile,
`Relationship=Variation` je Kindzeile mit eigenem Preis/Menge/Bild;
API: Inventory Item Groups mit `varyBy`). Die im Dokument gewünschten
Varianten-Felder (Name, Nummer, Sprache, Preis, Bestand) sind damit
abbildbar: Name+Nummer als Variantenwert, Sprache als Artikelmerkmal des
Elternangebots (ein Angebot = eine Sprache; gemischtsprachige Sets besser
als getrennte Angebote), Preis/Bestand je Kindzeile. Umgesetzt und
dokumentiert in `ebay-export.html`.

---

## 12. Titelbild-Generator

**Umsetzbar?** ✅ Bereits umgesetzt (Canvas 1600×1600, Banner mit Setname,
SVG-Sprachflagge, Raster mit 8–12 Karten, höchstpreisige vorausgewählt,
PNG-Download).

**Verbleibendes Risiko = CORS:** pokezentrum-Bilder ohne CORS-Header machen
die Canvas „tainted" → PNG-Export scheitert (Hinweis + Screenshot-Fallback
sind eingebaut). **Saubere Lösung** = Kombination aus Kap. 3 + Stufe 2:
lokale Bilddatenbank der verkauften Sets **auf derselben Origin gehostet**
→ kein Taint, verlustfreier Export. Alternativ (ohne Hosting): Bilder per
Datei-Auswahl einlesen — Blob-URLs sind unkritisch für die Canvas.

„Einheitliches Layout/Wiedererkennung": ein fixes Template (Farbwelt,
Banner, Flaggenposition) ist bereits angelegt; ggf. um ein kleines
Logo/Händlerkennzeichen erweitern — reine Canvas-Arbeit ohne Risiko.

---

## 13. Mehrbenutzerfähigkeit / mehrere eBay-Konten

**Umsetzbar?** ✅ als Vorbereitung (gefordert) · ❌ echter Sync jetzt
(nicht gefordert).

**Jetzt (Datenmodell-Vorbereitung, kostenlos):**
- Je Inventar-Eintrag: stabile `id` (vorhanden), **`owner`** (vorerst
  `"local"`), **`updatedAt`**, **`version`** → macht spätere
  Synchronisation und Konfliktauflösung mechanisch möglich.
- **`account`-Entität** für eBay-Konten vorsehen: Einstellungsblock
  (Standort, Versand, Rücknahme — heute global in localStorage) wird „ein
  benannter Einstellungs-Satz von mehreren"; Exporte/Listings erhalten eine
  `accountId`. Solange es ein Konto gibt, ändert sich am Verhalten nichts.
- Backup-JSON-Schema versionieren (`app`, `version`, `entries[]`) —
  vorhanden, beibehalten.

**Später (nur bei echtem Bedarf):** Supabase oder Firebase (Browser-SDK per
CDN, Gratis-Tarif, kein eigener Server) für zentrale DB + Auth; mehrere
eBay-Konten = mehrere OAuth-Token-Sätze im Worker-KV (Stufe 3). **Zu klären
vor jedem echten Multi-User-Schritt:** Datenschutz/DSGVO (Schulkontext).

---

## 14. Architektur & Module

**Umsetzbar?** ✅ — aber „modular" heißt hier **nicht** Framework/Bundler,
sondern: **gemeinsame Skript-Dateien mit klaren Daten-Verträgen**, geladen
per `<script src>`. Das erfüllt „alle Module unabhängig erweiterbar" ohne
die Kein-Build-Bedingung zu verletzen.

**Abbildung der 8 gewünschten Module auf die Repo-Realität:**

| Gefordertes Modul | Umsetzung im Repo |
|-------------------|-------------------|
| Kartendaten (implizit) | `sets-data.js` (existiert) |
| Bildverwaltung | `shared.js` ✅ **umgesetzt** (Phase 1): `pad`/`findCardIn`/`imgCandidatesFor`/`cardInfo`/`findSetByCode`/`setByCodeLang` + Auflösungs-Kaskade aus Kap. 3 (lokal → pokezentrum). Von `erfassung.html` und `kartenbild-finder-v6.html` gemeinsam genutzt (vorher in beiden dupliziert) |
| Inventar | `inventar.js` ✅ **umgesetzt** (Phase 1): Schema v2 (`kartencode`, `lagerplatz`, `owner`, `updatedAt`, `version`), Laden/Speichern mit idempotenter Migration, `newEntry`/`normalize`/`touch`, Duplikat-Helfer über localStorage |
| Preislogik | `preislogik.js` (neu): Regel-Pipeline aus Kap. 4 |
| Scanner | `scanner.js` (neu, Phase 4): ROI-OCR-Kern mit zwei Eingängen (Foto/Stream) |
| Listing Engine | in `ebay-export.html`: Titel-/Beschreibungs-/Modus-Logik gegen eine **Backend-Schnittstelle** (`CsvBackend` heute, `ApiBackend` später am Worker) — das ist die entscheidende Naht für Kap. 5 |
| CSV Export | `CsvBackend` (existiert faktisch in `ebay-export.html`) |
| eBay API | `ApiBackend` + Cloudflare Worker (Stufe 3, später) |
| Dashboard | `dashboard.html` liest über `inventar.js` |

**Die Standalone-Tool-Struktur bleibt** (jedes Werkzeug eine HTML-Datei,
einzeln per Doppelklick lauffähig). Eine Migration zu einer SPA/Plattform
bringt **keinen** Mehrwert, der die verlorene Robustheit aufwiegt; selbst
für künftige Modularisierung reichen notfalls native ES-Module
(`<script type="module">`) ohne Bundler.

---

## 15. Backend-/Infrastruktur-Bedarf im Überblick

| Funktion | Stufe 1 (Browser) | Stufe 2 (Hosting) | Stufe 3 (Worker/VPS) |
|----------|:--:|:--:|:--:|
| Inventar, Dashboard, Lager, Preisregeln, Titel/Beschreibung, CSV, Modus A/B/C | ✅ | | |
| Scanner Modus 1 (Foto per Datei-Input, am Handy) | ✅¹ | ✅ | |
| Scanner Modus 2 (Live-Kamera), PWA/Offline | ❌ | ✅ | |
| Titelbild-PNG sauber (untainted Canvas) | ❌ | ✅ (+ lokale Bilder) | |
| eBay Sell API (Entwürfe/Listings/Bild-Upload) | ❌ | ❌ | ✅ |
| Automatische Preis-Lookups (Browse API) | ❌ | ❌ | ✅ |
| Mehrbenutzer-Sync / mehrere eBay-Konten | ❌ | ❌ | ✅ (Supabase bzw. Worker-KV) |

¹ per `<input capture>` am Smartphone; am Laptop nur Datei-Auswahl.
Stufe 2 = GitHub Pages/Netlify (gratis, kein Serverprozess).
Stufe 3 = Cloudflare Worker (gratis-Tarif) oder VPS 3–5 €/Monat.

---

## 16. Kritische Gesamtwürdigung der Anforderungen

1. **„Sell API als Standard, CSV nur Fallback" — umdrehen.** Unter den
   Projektbedingungen ist CSV der Standard (läuft heute, null Infrastruktur)
   und die API die Ausbaustufe. Die Architektur-Naht (austauschbares
   Listing-Backend) wird trotzdem sofort eingezogen, damit der Wechsel
   später kein Umbau ist. Zusätzlich: automatische **Varianten-Entwürfe**
   gibt es API-seitig nicht (Draft-API kann keine Varianten) — gerade der
   Varianten-Workflow bleibt also ohnehin beim CSV.
2. **„Automatische Preisberechnung aus Cardmarket/eBay-Sold" — in dieser
   Form nicht seriös machbar** (API-Zugänge, ToS, Zuverlässigkeit). Die
   tragfähige Form: manuelle/Deep-Link-Preisquelle + automatische
   Regel-Pipeline + eigene Verkaufshistorie als wachsende Datenbasis.
3. **„1–2 s pro Karte im Live-Scanner" — als Zielmarke streichen** und
   durch eine ehrliche Messgröße ersetzen (Karten/Minute im 50er-Stapel-
   Test). Erwartung: 2–5 s/Karte; manuelles Tippen bleibt für geübte
   Nutzer konkurrenzfähig.
4. **„Fotoerkennung erkennt Name/Set/Sprache/Seltenheit" — nicht als
   Bilderkennung bauen**, sondern als Code-OCR + DB-Lookup. Gleiches
   Ergebnis, Bruchteil der Komplexität.
5. **„NM" im Titel-Beispiel** kollidiert mit der bewussten
   Ohne-Zustand-Politik der Beschreibung/ConditionID → als optionales,
   default-deaktiviertes Token behandeln (Kap. 7).
6. **Lokale Bilddatenbank: ja, aber selektiv** (nur verkaufte Sets), als
   Kaskade vor den pokezentrum-URLs, Erlaubnis-Umfang schriftlich klären
   (Kap. 3).
7. **Modular ja — Plattform nein.** Die 8 Module entstehen als geteilte
   JS-Dateien + Standalone-Tools; SPA/Framework/Bundler brächte unter den
   Rahmenbedingungen nur Risiko.

---

## 17. Empfohlene Entwicklungsreihenfolge (MVP zuerst)

**Phase 0 — erledigt (der MVP existiert):** Erfassung + Inventar
(`erfassung.html`), eBay-CSV-Export mit Modus A/B und Preisgrenzen-Automatik
(`ebay-export.html`), Beschreibungs-Template, Titelbild-Generator v1.
Der Kernprozess „Karte erfassen → eBay-Entwurf" funktioniert bereits.

**Phase 1 — Fundament konsolidieren (klein, risikolos): ✅ umgesetzt.**
`shared.js` (Bildlogik entdoppelt, von beiden HTML-Tools genutzt) +
`inventar.js` mit Schema v2 (`kartencode`, `lagerplatz`, `owner`,
`updatedAt`, `version`; `accountId` noch offen) + Inventar→Export-Brücke
(Button „Aus Erfassung-Bestand übernehmen“ im eBay-Export, Excel-Import
bleibt). Zusätzlich vorgezogen: Lagerplatz-Feld in der Erfassung, Lagerplatz
in der SKU (Kap. 10), `kartencode`/`lagerplatz` in der CSV-Ausgabe.

**Phase 2 — Auswertung & Preis (rein Browser, hoher Alltagsnutzen):**
`dashboard.html` · `preislogik.js` (Regel-Pipeline + Editor) ·
Deep-Link-Preishelfer · Titelgenerator v2 (SEO-Template mit
Prioritäts-Kürzung) · Modus-C-Regeleditor · Lagerplatz in SKU.

**Phase 3 — Hosting & Bilder (Stufe 2):**
GitHub Pages/Netlify einrichten · lokale Bilddatenbank für aktiv verkaufte
Sets (`assets/cards/`, Kaskade) → sauberer Titelbild-PNG-Export ·
optional PWA/Offline.

**Phase 4 — Scanner (benötigt Phase 3 für Modus 2):**
zuerst **Modus 1** (Foto per Datei-Input + ROI-OCR + DB-Lookup +
Bestätigen/+1) — geringste Hürde, am Handy sofort nutzbar; dann **Modus 2**
(Live-Stream, Worker, Stabilitäts-Voting) mit ehrlicher
Geschwindigkeitsmessung.

**Phase 5 — Ausbaustufen mit Infrastruktur (Stufe 3, nur bei Bedarf):**
Cloudflare Worker (OAuth, Token-KV) → eBay-Entwürfe per Listing API,
Varianten-Listings per Inventory API, Bild-Upload per Media API ·
Preis-Lookups (Browse API) über den Worker · Verkaufsabruf (Fulfillment)
→ automatischer Bestandsabgleich · danach erst Multi-Account/Multi-User
(Supabase).

**Begründung der Reihenfolge:** Jede Phase liefert eigenständigen Nutzen und
keine Phase verbaut die nächste; alles Infrastrukturpflichtige liegt am Ende
und ist über die in Phase 1 eingezogenen Nähte (Inventar-Modul,
Listing-Backend-Schnittstelle) ohne Umbau andockbar.

---

## 18. Zusätzliche Funktionsvorschläge (mit Begründung)

1. **Verkaufshistorie/Preis-Log:** Beim Statuswechsel auf „Verkauft" Preis
   + Datum protokollieren. Nutzen: baut die einzige legal und dauerhaft
   verfügbare „Last-Sold"-Datenquelle selbst auf (Kap. 4) und liefert dem
   Dashboard echte Umsatzzahlen.
2. **Pickliste nach Lagerplatz:** Verkaufte/zu versendende Karten als nach
   Regal/Box/Fach sortierte Liste (Druck-CSS). Nutzen: der größte
   Zeitfresser beim Kartenverkauf ist das Heraussuchen — die Kombination
   aus Lagerfeld + SKU-Konvention (Kap. 10) macht daraus Minutenarbeit.
3. **eBay-Aktivberichte re-importieren:** Der aktive-Angebote-Report
   (CSV aus dem Verkäuferportal) enthält die SKUs → Abgleich setzt den
   Status „Gelistet" automatisch. Nutzen: schließt den Kreislauf
   Inventar↔eBay **ohne API**.
4. **Backup-Erinnerung + Datei-Backup:** Hinweis „letztes Backup vor X
   Tagen" und (gehostet, Chrome) File-System-Access-API für
   Ein-Klick-Backups in einen festen Ordner. Nutzen: localStorage ist der
   einzige Datenspeicher — Verlustschutz ist billig und kritisch.
5. **Etikettendruck für Lagerboxen** (Druck-CSS, Codes wie `R2-B5`):
   rundet die Lagerverwaltung ab, null Abhängigkeiten.

---

## 19. Zusammenfassung

- **MVP existiert bereits** (Phase 0); V6 ist als Ausbau in 5 Phasen
  planbar, von denen **die ersten vier ohne jeden Server** auskommen
  (Phase 3–4 brauchen lediglich kostenloses statisches HTTPS-Hosting).
- **Nicht wie gefordert umsetzen:** Sell-API-als-Standard (→ CSV Standard,
  API-Ausbaustufe über Worker), automatische Preisquellen (→ manuelle
  Quelle + automatische Regeln + eigene Historie), Sechsfach-Fotoerkennung
  (→ Code-OCR + DB-Lookup), 1–2-s-Scanner-Versprechen (→ ehrlich messen).
- **Sofort lohnend und risikolos:** `shared.js`/`inventar.js`, Dashboard,
  Preisregel-Engine, Titelgenerator v2, Modus-C-Regeln, Lagerfelder +
  SKU-Konvention.
- **Architektur:** Standalone-Tools + geteilte JS-Module beibehalten;
  Mehrbenutzer/Multi-Account nur als Datenmodell-Vorbereitung; jede
  Infrastruktur konsequent serverlos und optional.
